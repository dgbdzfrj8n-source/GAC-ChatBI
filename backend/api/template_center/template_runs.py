"""
归因模板 v3 - 运行实例路由
端点：
  POST /api/template-center/templates/{id}/runs        启动 run（同步执行）
  GET  /api/template-center/runs                       列表
  GET  /api/template-center/runs/{run_id}              详情 + 步骤
"""
import os
import sys
import json
import datetime
import time
import uuid
from typing import Optional

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from fastapi import APIRouter, Depends, HTTPException, Query, status

from core.auth import CurrentUser, get_current_user
from services.sop import (
    TemplateDB,
    TemplateRunCreateRequest,
    TemplateRunListResponse,
    TemplateRunDetailResponse,
    RunStatus,
    StepStatus,
    StepType,
)
from config import get_settings

# Phase E: 引入真实 workflow
from workflow.orchestrator import run_workflow_sync

router = APIRouter(prefix="/api/template-center", tags=["template-center"])


def _get_db() -> TemplateDB:
    settings = get_settings()
    return TemplateDB(settings.DATABASE_PATH)


def _execute_run_synchronously(
    db: TemplateDB,
    run_id: str,
    steps: list,
    user_params: dict,
    user_query: str = "",
) -> None:
    """
    v3 执行器（Phase E - 真实 NL2SQL 接入）：
    - 遍历 steps，对每步：
      1) 写入 step_execution
      2) 根据 type 调对应执行器：
         - NL2SQL：调 workflow.orchestrator.run_workflow_sync
         - Strategy/Aggregation/Conclusion：消费前一步的 SQL 结果
      3) 写 output_data + duration_ms
    - 最后写 run summary
    """
    db.update_run_status(run_id, RunStatus.RUNNING.value, completed_steps=0)
    completed = 0
    last_output = None
    last_sql_result = None  # 上一条 NL2SQL 的结果（rows/columns）
    step_outputs = []
    run_started = time.time()

    for idx, step in enumerate(steps):
        step_name = step.get("name", f"Step {idx + 1}")
        step_type = step.get("type", StepType.NL2SQL.value)
        # 解析变量（用户填的 + 上一步输出 + 上一条 SQL 结果）
        resolved = {
            **user_params,
            "prev_step_output": json.dumps(last_output, ensure_ascii=False) if last_output else "",
        }
        if last_sql_result is not None:
            resolved["prev_sql_rows"] = json.dumps(last_sql_result.get("rows", []), ensure_ascii=False)
            resolved["prev_sql_columns"] = json.dumps(last_sql_result.get("columns", []), ensure_ascii=False)
        # 写 step input
        step_exec_id = db.create_step_execution(
            run_id=run_id,
            step_index=idx,
            step_name=step_name,
            step_type=step_type,
            input_data={
                "raw_step": step,
                "resolved_params": resolved,
            },
        )
        step_start = time.time()
        try:
            if step_type == StepType.NL2SQL.value:
                output = _exec_nl2sql(step, resolved, user_query)
                # 提取 SQL 结果供后续步骤使用
                if "result" in output and isinstance(output["result"], dict):
                    last_sql_result = output["result"]
            elif step_type == StepType.STRATEGY.value:
                output = _exec_strategy(step, last_output, last_sql_result)
            elif step_type == StepType.AGGREGATION.value:
                output = _exec_aggregation(step, last_sql_result, last_output)
            elif step_type == StepType.CONCLUSION.value:
                output = _exec_conclusion(step, last_output, last_sql_result, step_outputs)
            elif step_type == StepType.LLM_DIRECT.value:
                output = _exec_llm_direct(step, resolved)
            else:
                output = {"warning": f"Unknown step type: {step_type}"}
            db.complete_step_execution(
                step_exec_id,
                output_data=output,
                duration_ms=int((time.time() - step_start) * 1000),
            )
            step_outputs.append({"index": idx, "name": step_name, "output": output})
            last_output = output
            completed += 1
            db.update_run_status(run_id, RunStatus.RUNNING.value, completed_steps=completed)
        except Exception as e:
            db.fail_step_execution(step_exec_id, str(e))
            db.update_run_status(
                run_id,
                RunStatus.FAILED.value,
                completed_steps=completed,
                error_message=f"Step {idx + 1} ({step_name}) failed: {str(e)}",
            )
            return

    duration_ms = int((time.time() - run_started) * 1000)
    summary = {
        "total_steps": len(steps),
        "completed_steps": completed,
        "last_step_output": last_output,
        "all_step_outputs": step_outputs,
    }
    db.finalize_run(run_id, RunStatus.SUCCESS.value, summary, duration_ms)


# --------- 5 种 step 类型的执行器（Phase E：真实 NL2SQL）---------
def _resolve_question(step: dict, params: dict) -> str:
    """模板里的 question 模板做变量替换：{var} -> params.get(var)"""
    question = step.get("question", "")
    for k, v in params.items():
        question = question.replace("{" + k + "}", str(v))
    return question


def _exec_nl2sql(step: dict, params: dict, user_query: str = "") -> dict:
    """
    NL2SQL 步骤（真实执行器）：
    - 调 workflow.orchestrator.run_workflow_sync
    - 解析 events 提取 SQL / result / chart / conclusion
    """
    raw_question = step.get("question", "") or user_query
    question = _resolve_question(step, params)
    if not question and raw_question:
        question = raw_question

    if not question:
        return {"type": "nl2sql", "error": "no question provided"}

    try:
        result = run_workflow_sync(
            question=question,
            brand_filter=params.get("brand_filter", "全部"),
            session_id=f"tplrun_{uuid.uuid4().hex[:8]}",
        )
    except Exception as e:
        return {
            "type": "nl2sql",
            "question": question,
            "error": f"workflow 调用失败: {e}",
        }

    ctx = result.get("context")
    events = result.get("events", [])

    sql = None
    columns = []
    rows = []
    chart_type = None
    chart_config = None
    conclusion = None
    key_numbers = []

    for ev in events:
        etype = ev.get("event")
        data = ev.get("data", {}) or {}
        if etype == "sql":
            sql = data.get("sql")
        elif etype == "result":
            columns = data.get("columns", [])
            rows = data.get("rows", [])
        elif etype == "chart":
            chart_type = data.get("chart_type")
            chart_config = data.get("config")
        elif etype == "conclusion":
            conclusion = data.get("text")
            key_numbers = data.get("key_numbers", [])
        elif etype in ("reject", "clarify", "error"):
            return {
                "type": "nl2sql",
                "question": question,
                "status": ctx.status if ctx else "failed",
                "error": data.get("message") or data.get("reason"),
                "suggestion": data.get("suggestion", ""),
            }

    return {
        "type": "nl2sql",
        "question": question,
        "status": ctx.status if ctx else "unknown",
        "sql": sql,
        "result": {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        },
        "chart": {
            "chart_type": chart_type,
            "config": chart_config,
        } if chart_type else None,
        "conclusion": conclusion,
        "key_numbers": key_numbers,
        "thinking_steps": [s.to_dict() for s in (ctx.thinking_steps if ctx else [])],
        "duration_ms": ctx.total_duration_ms if ctx else 0,
    }


def _exec_strategy(step: dict, prev_output, last_sql_result) -> dict:
    """
    Strategy 步骤（真实）：
    - 基于上一条 SQL 结果做 topn/排序/筛选
    - 支持策略：topn / bottomn / threshold_filter / sort_desc
    """
    strategy = step.get("strategy", "topn")
    n = int(step.get("n", 10))
    threshold = step.get("threshold")
    rows = (last_sql_result or {}).get("rows", []) or []
    columns = (last_sql_result or {}).get("columns", []) or []

    if not rows:
        return {
            "type": "strategy",
            "strategy": strategy,
            "n": n,
            "input_rows": 0,
            "output_rows": 0,
            "result": {"columns": columns, "rows": []},
            "note": "无 SQL 结果可处理",
        }

    numeric_idx = None
    for col_idx in range(len(columns)):
        sample = next((r[col_idx] for r in rows if col_idx < len(r)), None)
        if isinstance(sample, (int, float)):
            numeric_idx = col_idx
            break

    processed = list(rows)

    if strategy == "topn":
        if numeric_idx is not None:
            processed = sorted(processed, key=lambda r: (r[numeric_idx] if numeric_idx < len(r) else 0), reverse=True)
        processed = processed[:n]
    elif strategy == "bottomn":
        if numeric_idx is not None:
            processed = sorted(processed, key=lambda r: (r[numeric_idx] if numeric_idx < len(r) else 0))
        processed = processed[:n]
    elif strategy == "threshold_filter":
        if threshold is not None and numeric_idx is not None:
            processed = [r for r in processed if numeric_idx < len(r) and r[numeric_idx] is not None and r[numeric_idx] >= threshold]
    elif strategy == "sort_desc":
        if numeric_idx is not None:
            processed = sorted(processed, key=lambda r: (r[numeric_idx] if numeric_idx < len(r) else 0), reverse=True)
    else:
        return {
            "type": "strategy",
            "strategy": strategy,
            "input_rows": len(rows),
            "output_rows": 0,
            "result": {"columns": columns, "rows": []},
            "warning": f"unknown strategy '{strategy}', passthrough",
        }

    return {
        "type": "strategy",
        "strategy": strategy,
        "n": n,
        "threshold": threshold,
        "input_rows": len(rows),
        "output_rows": len(processed),
        "result": {"columns": columns, "rows": processed},
    }


def _exec_aggregation(step: dict, last_sql_result, prev_output) -> dict:
    """
    Aggregation 步骤（真实）：
    - 在前一条 SQL 结果之上做二次聚合（sum/avg/max/min/count）
    """
    aggregation = step.get("aggregation", "sum")
    group_by = step.get("group_by", []) or []
    rows = (last_sql_result or {}).get("rows", []) or []
    columns = (last_sql_result or {}).get("columns", []) or []

    if not rows:
        return {
            "type": "aggregation",
            "aggregation": aggregation,
            "input_rows": 0,
            "result": {"columns": [], "rows": []},
        }

    numeric_idxs = [
        i for i in range(len(columns))
        if any(isinstance(r[i] if i < len(r) else None, (int, float)) for r in rows if r)
    ]

    if not numeric_idxs:
        return {
            "type": "aggregation",
            "aggregation": aggregation,
            "input_rows": len(rows),
            "result": {"columns": columns, "rows": rows},
            "note": "无数值列可聚合，原样返回",
        }

    def _agg(vals, op):
        nums = [v for v in vals if isinstance(v, (int, float))]
        if not nums:
            return None
        if op == "sum":
            return round(sum(nums), 4)
        if op == "avg":
            return round(sum(nums) / len(nums), 4)
        if op == "max":
            return max(nums)
        if op == "min":
            return min(nums)
        if op == "count":
            return len(nums)
        return None

    if not group_by:
        out_row = []
        for col_idx in range(len(columns)):
            if col_idx in numeric_idxs:
                out_row.append(_agg([r[col_idx] for r in rows if col_idx < len(r)], aggregation))
            else:
                out_row.append(None)
        out_columns = [f"{aggregation.upper()}_{c}" if i in numeric_idxs else c for i, c in enumerate(columns)]
        return {
            "type": "aggregation",
            "aggregation": aggregation,
            "group_by": [],
            "input_rows": len(rows),
            "output_rows": 1,
            "result": {"columns": out_columns, "rows": [out_row]},
        }

    group_idxs = [columns.index(g) for g in group_by if g in columns]
    if not group_idxs:
        return {
            "type": "aggregation",
            "aggregation": aggregation,
            "group_by": group_by,
            "warning": f"group_by 列不存在: {group_by}",
            "result": {"columns": columns, "rows": rows},
        }

    groups = {}
    for r in rows:
        key = tuple(r[i] if i < len(r) else None for i in group_idxs)
        groups.setdefault(key, []).append(r)

    out_rows = []
    for key, grp_rows in groups.items():
        out_row = list(key)
        for col_idx in range(len(columns)):
            if col_idx in group_idxs:
                continue
            if col_idx in numeric_idxs:
                out_row.append(_agg([r[col_idx] for r in grp_rows if col_idx < len(r)], aggregation))
            else:
                out_row.append(grp_rows[0][col_idx] if grp_rows and col_idx < len(grp_rows[0]) else None)
        out_rows.append(out_row)

    out_columns = list(group_by) + [
        f"{aggregation.upper()}_{c}" if i in numeric_idxs else c
        for i, c in enumerate(columns) if i not in group_idxs
    ]

    return {
        "type": "aggregation",
        "aggregation": aggregation,
        "group_by": group_by,
        "input_rows": len(rows),
        "output_rows": len(out_rows),
        "result": {"columns": out_columns, "rows": out_rows},
    }


def _exec_conclusion(step: dict, prev_output, last_sql_result, all_outputs) -> dict:
    """
    Conclusion 步骤（真实）：
    - 优先用 NL2SQL step 自带的 conclusion（来自 workflow step8）
    - 否则用 prompt 模板 + 上下文数据生成结构化结论
    """
    nl2sql_conclusion = None
    for so in reversed(all_outputs):
        out = so.get("output", {})
        if out.get("type") == "nl2sql" and out.get("conclusion"):
            nl2sql_conclusion = out["conclusion"]
            break

    prompt = step.get("prompt", "")
    rows = (last_sql_result or {}).get("rows", []) or []
    columns = (last_sql_result or {}).get("columns", []) or []

    stats = {
        "row_count": len(rows),
        "columns": columns,
    }
    if rows and columns:
        for col_idx, col in enumerate(columns):
            nums = [r[col_idx] for r in rows if col_idx < len(r) and isinstance(r[col_idx], (int, float))]
            if nums:
                stats[f"{col}_avg"] = round(sum(nums) / len(nums), 2)
                stats[f"{col}_max"] = max(nums)
                stats[f"{col}_min"] = min(nums)

    if nl2sql_conclusion:
        text = nl2sql_conclusion
    elif prompt:
        text = f"{prompt}\n\n[数据上下文] 行数={len(rows)}; 列={columns}"
    else:
        text = f"已完成 {len(all_outputs)} 个步骤，最终结果包含 {len(rows)} 行 {len(columns)} 列。"

    return {
        "type": "conclusion",
        "text": text,
        "stats": stats,
        "context_step_count": len(all_outputs),
        "used_nl2sql_conclusion": nl2sql_conclusion is not None,
    }


def _exec_llm_direct(step: dict, params: dict) -> dict:
    """
    LLM direct 步骤（占位）：
    - 真实 LLM 直调需要 llm_client；这里返回结构化记录
    """
    prompt = step.get("prompt", "")
    return {
        "type": "llm_direct",
        "prompt": prompt,
        "params": params,
        "result": None,
        "note": "LLM 直调需注入 llm_client；当前为占位实现",
    }


# --------- 路由 ---------
@router.post(
    "/templates/{template_id}/runs",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateRunDetailResponse,
)
def create_run(
    template_id: str,
    body: TemplateRunCreateRequest,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    tpl = db.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    ver = db.get_version(template_id, tpl.current_version)
    if not ver:
        raise HTTPException(status_code=500, detail="Template has no version")

    run = db.create_run(
        template_id=template_id,
        template_version=ver.version,
        user_query=body.user_query,
        params=body.params,
        total_steps=len(ver.steps),
        created_by=user.username,
    )
    # 同步执行（骨架实现）
    _execute_run_synchronously(db, run.run_id, ver.steps, body.params, user_query=body.user_query)
    # 返回最终状态
    final_run = db.get_run(run.run_id)
    steps = db.list_step_executions(run.run_id)
    return TemplateRunDetailResponse(run=final_run, steps=steps)


@router.get("/runs", response_model=TemplateRunListResponse)
def list_runs(
    template_id: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    items = db.list_runs(template_id=template_id, status=status_filter,
                         limit=limit, offset=offset)
    total = len(db.list_runs(template_id=template_id, status=status_filter, limit=10000, offset=0))
    return TemplateRunListResponse(items=items, total=total)


@router.get("/runs/{run_id}", response_model=TemplateRunDetailResponse)
def get_run_detail(
    run_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    db = _get_db()
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    steps = db.list_step_executions(run_id)
    return TemplateRunDetailResponse(run=run, steps=steps)
