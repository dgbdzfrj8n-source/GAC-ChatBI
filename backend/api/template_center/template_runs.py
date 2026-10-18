"""
归因模板 v3 - 运行实例路由
端点：
  POST /api/template-center/templates/{id}/runs        启动 run（同步执行骨架）
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

router = APIRouter(prefix="/api/template-center", tags=["template-center"])


def _get_db() -> TemplateDB:
    settings = get_settings()
    return TemplateDB(settings.DATABASE_PATH)


def _execute_run_synchronously(
    db: TemplateDB,
    run_id: str,
    steps: list,
    user_params: dict,
) -> None:
    """
    v3 简化执行器（同步骨架）：
    - 遍历 steps，对每步：
      1) 写入 step_execution
      2) 根据 type 调对应执行器（NL2SQL/Strategy/Aggregation/Conclusion）
      3) 写 output_data + duration_ms
    - 最后写 run summary

    注意：这是骨架实现，Phase C 接入 workflow.orchestrator 真实 NL2SQL
    """
    db.update_run_status(run_id, RunStatus.RUNNING.value, completed_steps=0)
    completed = 0
    last_output = None
    step_outputs = []
    run_started = time.time()

    for idx, step in enumerate(steps):
        step_name = step.get("name", f"Step {idx + 1}")
        step_type = step.get("type", StepType.NL2SQL.value)
        # 解析变量（用户填的 + 上一步输出）
        resolved = {**user_params, "prev_step_output": json.dumps(last_output, ensure_ascii=False) if last_output else ""}
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
                output = _exec_nl2sql(step, resolved)
            elif step_type == StepType.STRATEGY.value:
                output = _exec_strategy(step, last_output)
            elif step_type == StepType.AGGREGATION.value:
                output = _exec_aggregation(step, last_output)
            elif step_type == StepType.CONCLUSION.value:
                output = _exec_conclusion(step, last_output, step_outputs)
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


# --------- 4 种 step 类型的执行器（骨架）---------
def _exec_nl2sql(step: dict, params: dict) -> dict:
    """NL2SQL 步骤（骨架）：返回变量 + 问题模板"""
    question = step.get("question", "")
    # 简单变量替换：{var} -> params.get(var)
    for k, v in params.items():
        question = question.replace("{" + k + "}", str(v))
    return {
        "type": "nl2sql",
        "resolved_question": question,
        "metrics": step.get("metrics", []),
        "dimensions": step.get("dimensions", []),
        "note": "v3 骨架：未实际跑 NL2SQL（Phase C 接入）",
    }


def _exec_strategy(step: dict, prev_output: dict) -> dict:
    """Strategy 步骤（骨架）"""
    strategy = step.get("strategy", "topn")
    return {
        "type": "strategy",
        "strategy": strategy,
        "applied_to": prev_output,
        "note": "v3 骨架：未实际跑策略计算",
    }


def _exec_aggregation(step: dict, prev_output: dict) -> dict:
    """Aggregation 步骤（骨架）"""
    return {
        "type": "aggregation",
        "aggregation": step.get("aggregation", "sum"),
        "group_by": step.get("group_by", []),
        "input": prev_output,
        "note": "v3 骨架：未实际跑聚合",
    }


def _exec_conclusion(step: dict, prev_output: dict, all_outputs: list) -> dict:
    """Conclusion 步骤（骨架）"""
    return {
        "type": "conclusion",
        "prompt_template": step.get("prompt", ""),
        "context_step_count": len(all_outputs),
        "last_output": prev_output,
        "note": "v3 骨架：未实际调 LLM（Phase C 接入）",
    }


def _exec_llm_direct(step: dict, params: dict) -> dict:
    """LLM direct 步骤（骨架）"""
    return {
        "type": "llm_direct",
        "params": params,
        "note": "v3 骨架：未实际调 LLM",
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
    _execute_run_synchronously(db, run.run_id, ver.steps, body.params)
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
