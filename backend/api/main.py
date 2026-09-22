"""
广汽云 ChatBI 后端智能服务入口 (FastAPI)
功能清单：
1. GET /api/health: 服务健康检查与数据库引擎状态；
2. GET /api/metrics: 指标语义字典查询（供给前端指标侧边栏）；
3. POST /api/chat: 核心问数端点（集成 Schema 剪枝 + SQL 生成 + 执行 + ECharts 自适应推荐 + 经营洞察）；
4. POST /api/feedback: Bad Case 回收与闭环沉淀接口。
"""

import os
import sys

# Render/Docker 部署兼容：无论 Root Directory 是仓库根目录还是 backend，
# 都把 backend 目录注入到 sys.path，让相对导入 `from api.xxx` 生效
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_CURRENT_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import json
import datetime
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from core.auth import CurrentUser, get_current_user
from api.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    MetricListResponse,
    BadCaseFeedbackRequest,
    SopAnalysisRequest,
    SopAnalysisResponse,
    SemanticLayerResponse,
    MetricUpdateRequest,
    GlossaryUpdateRequest,
    SemanticPreviewRequest,
    SemanticPreviewResponse,
    # 归因模板中心（P0）
    AttributionTemplateItem,
    AttributionTemplateListResponse,
    AttributionTemplateCreateRequest,
    AttributionTemplateUpdateRequest,
    AttributionTemplateDeleteRequest,
    AttributionTemplateResponse,
    # 归因指标目录（P1）
    MetricCatalogResponse,
    SUPPORTED_METRICS,
    # ⭐ P2-SprintB：SOP 步骤化模板（V2 schemas）
    StepSpec,
    AttributionTemplateV2,
    TemplateCreateRequestV2,
    TemplateUpdateRequestV2,
    TemplateCloneRequestV2,
    TemplateAuditItem,
    TemplateAuditListResponse,
)
from core.nl2sql_engine import Nl2SqlEngine
from core.chart_recommender import ChartRecommender
from core.sop_analyzer import SopAnalyzer

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
METRICS_PATH = os.path.join(BACKEND_DIR, "core", "metrics_dict.json")
BAD_CASES_PATH = os.path.join(BACKEND_DIR, "eval", "bad_cases.json")

# 初始化 FastAPI 应用
app = FastAPI(
    title="广汽云 ChatBI 智能问数服务 API",
    description="面向大型车企集团的全链路经营决策问数 Agent 服务端",
    version="1.0.0"
)

# 配置 CORS 跨域支持（支持 Netlify 与本地 Next.js 访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# [Sprint 10] 注册鉴权路由（Mock IAM）
# ============================================================
from api.auth_router import router as auth_router
app.include_router(auth_router)

# 实例化单例 Agent 引擎与图表推荐器
nl2sql_engine = Nl2SqlEngine()
chart_recommender = ChartRecommender()
sop_analyzer = SopAnalyzer()

# P2-4: 初始化审计 + Bad Case 表（DuckDB）
from services.audit_log import ensure_audit_tables
ensure_audit_tables()

# Render 平台健康检查端点（默认 GET /，不依赖业务初始化）
@app.get("/", tags=["基础监控"])
def root():
    return {
        "status": "ok",
        "service": "GAC-ChatBI API",
        "version": "1.2.0",
        "endpoints": [
            "/api/health",
            "/api/metrics",
            "/api/chat",
            "/api/chat/stream",
            "/api/feedback",
            "/api/sop/analyze",
            "/api/dashboard/snapshot",
            "/docs"
        ]
    }

@app.get("/api/health", tags=["基础监控"])
def health_check():
    """健康检查与引擎探测"""
    return {
        "status": "healthy",
        "service": "GAC-ChatBI API",
        "engine": nl2sql_engine.sql_executor.engine_type,
        "database_file": nl2sql_engine.sql_executor.db_path,
        "timestamp": datetime.datetime.now().isoformat()
    }


@app.get("/api/debug/llm", tags=["基础监控"])
def debug_llm():
    """调试端点：诊断 LLM 配置是否正确注入 + 真实调用 DeepSeek"""
    import os as _os
    from core.nl2sql_engine import HAS_OPENAI_SDK, _call_llm_direct
    return _call_llm_direct()


@app.get("/api/metrics", response_model=MetricListResponse, tags=["指标资产"])
def get_metrics_dict():
    """获取集团标准经营分析指标体系字典"""
    if not os.path.exists(METRICS_PATH):
        raise HTTPException(status_code=404, detail="指标字典文件未找到")
    
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.post("/api/chat", response_model=ChatQueryResponse, tags=["智能问数"])
def chat_query(req: ChatQueryRequest, user: CurrentUser = Depends(get_current_user)):
    """
    核心智能问数端点：
    自然语言提问 -> 剪枝 -> SQL生成 -> 数据库执行 -> 自适应ECharts推断 -> 经营分析洞察

    [Sprint 10] 新增：行级权限 + 字段级脱敏
      - 业务用户：张三只能看「埃安 + 广州」
      - 手机号/身份证自动脱敏为 138****5678
    """
    # 1. 运行问数主引擎（注入 user 用于权限过滤）
    result = nl2sql_engine.ask(req.query, force_mock=req.force_mock, current_user=user)

    # 2. 生成自适应 ECharts 图表配置
    chart_info = chart_recommender.recommend(
        query=req.query,
        columns=result.get("columns", []),
        data=result.get("data", [])
    )

    # 3. 构造统一响应体
    return ChatQueryResponse(
        query=req.query,
        thought_steps=result["thought_steps"],
        sql=result["sql"] or "",
        success=result["success"],
        data=result["data"],
        columns=result["columns"],
        row_count=result["row_count"],
        execution_time_ms=result["execution_time_ms"],
        chart_type=chart_info["chart_type"],
        echarts_option=chart_info["echarts_option"],
        summary_insight=result["summary_insight"] or "查询完成，已生成最新经营视图。",
        healed=result.get("healed", False),
        engine=result.get("engine", "DuckDB"),
        error=result.get("error"),
        is_unsupported_entity=result.get("is_unsupported_entity", False),
        is_empty_result=result.get("is_empty_result", False),
    )


@app.get("/api/chat/quick-suggestions", tags=["智能问数"])
def quick_suggestions():
    """
    返回 15 条精确问数快捷提问 + 每条对应的 SQL 模板元信息。
    前端用此接口渲染 SuggestionPills（每条保证 100% 命中正确 SQL）。
    """
    from core.query_templates import QUERY_TEMPLATES
    return {
        "suggestions": [
            {
                "id": t["id"],
                "label": t["label"],
                "domain": t["domain"],
                "chart_hint": t["chart_hint"],
                "icon": {
                    "整车销售": "🚗",
                    "经营财务": "💰",
                    "市场营销": "📢",
                    "渠道经营": "🏪",
                }.get(t["domain"], "📊"),
            }
            for t in QUERY_TEMPLATES
        ],
        "total": len(QUERY_TEMPLATES),
        "version": "1.8.1",
    }


@app.post("/api/feedback", tags=["运营治理"])
def collect_bad_case(req: BadCaseFeedbackRequest):
    """Bad Case 反馈收集池"""
    os.makedirs(os.path.dirname(BAD_CASES_PATH), exist_ok=True)

    cases = []
    if os.path.exists(BAD_CASES_PATH):
        try:
            raw = json.load(open(BAD_CASES_PATH, "r", encoding="utf-8"))
            cases = raw.get("cases", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        except Exception:
            cases = []

    case_record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": req.query,
        "sql": req.sql,
        "feedback_type": req.feedback_type,
        "user_comment": req.user_comment
    }
    cases.append(case_record)

    with open(BAD_CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    return {"status": "success", "message": "Bad Case 反馈已成功记录至运营池", "total_cases": len(cases)}


# ─── P0 增强：归因维度模板中心（必须先初始化，sop_analyze 会用到） ─────────
from core.attribution_templates import AttributionTemplateManager
template_manager = AttributionTemplateManager()

# ⭐ P2-SprintB：SOP 步骤化执行引擎（run / preview 用）
from core.sop_executor import SopExecutor
sop_executor = SopExecutor()


# ─── Sprint 5.3 SOP 高频归因引擎 ──────────────────────────────────────
@app.post("/api/sop/analyze", response_model=SopAnalysisResponse, tags=["SOP 归因引擎"])
def sop_analyze(req: SopAnalysisRequest):
    """
    Sprint 5.3 + P1: 高频归因 SOP（销量达成异常 / 预算偏差 / 费用异常波动）

    执行四步下钻 SOP：
      Step 1 大盘对标 —— 目标 vs 实际，达成率评级
      Step 2 维度下钻 —— 车型 × 大区双维度定位最大缺口贡献者
      Step 3 跨域归因 —— 关联营销投放 / 终端客流 / 折扣力度
      Step 4 策略建议 —— 生成可执行经营策略（带预算影响估算）

    ⭐ P1 新增：
      - metric_key：归因指标（默认 delivered_units）
      - template_id：归因模板 ID（传了则从模板自动取 metric_key + dimensions）
    """
    import time
    start = time.time()
    try:
        # ⭐ P1：若传了 template_id，从模板取指标 + 维度（覆盖请求体）
        metric_key = req.metric_key
        selected_dimensions = req.selected_dimensions
        if req.template_id:
            tpl = template_manager.get_template(req.template_id)
            if tpl:
                metric_key = tpl.get("metric_key", metric_key)
                selected_dimensions = tpl.get("dimensions", selected_dimensions)

        result = sop_analyzer.analyze_fulfillment_gap(
            brand_name=req.brand_name,
            year_month=req.year_month,
            threshold_pct=req.threshold_pct or 95.0,
            selected_dimensions=selected_dimensions,
            metric_key=metric_key,  # ⭐ P1
        )

        # 提取第 1 步的评级原因
        steps = result.get("steps", [])
        step1 = steps[0] if steps else {}

        # 提取第 4 步的建议
        step4 = steps[3] if len(steps) >= 4 else {}
        recommendations = step4.get("recommendations", []) if step4 else []

        elapsed_ms = (time.time() - start) * 1000

        return SopAnalysisResponse(
            success=True,
            brand=result.get("brand", req.brand_name),
            year_month=result.get("year_month", req.year_month),
            fulfillment_rate_pct=result.get("fulfillment_rate_pct", 0) or 0,
            gap_units=result.get("gap_units", 0) or 0,
            gap_grade=step1.get("grade", "未知") if step1 else "未知",
            gap_reason=step1.get("gap_reason", "") if step1 else "",
            steps=steps,
            recommendations=recommendations,
            executive_summary=result.get("executive_summary", ""),
            execution_time_ms=round(elapsed_ms, 1),
            # ⭐ P0 新增
            selected_dimensions=result.get("selected_dimensions", selected_dimensions or []),
            attribution_breakdown=result.get("attribution_breakdown", []),
            # ⭐ P1 新增
            metric=result.get("metric"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SOP 引擎执行异常: {str(e)}")


# ─── P1：归因指标目录端点 ─────────────────────────────────────────
@app.get("/api/sop/supported-metrics", response_model=MetricCatalogResponse, tags=["SOP 归因引擎"])
def list_supported_metrics():
    """返回系统支持的归因指标清单（前端下拉框渲染用）"""
    return MetricCatalogResponse(metrics=SUPPORTED_METRICS)


@app.get("/api/sop/templates", response_model=AttributionTemplateListResponse, tags=["归因模板"])
def list_attribution_templates(role: Optional[str] = None, user: Optional[str] = None):
    """
    列出全部归因维度模板：
    - system_presets: 系统预设模板（5 个）
    - role_default_id: 当前角色绑定的默认模板 ID
    - role_defaults_map: 所有角色的默认模板映射
    - user_templates: 当前用户的自定义模板
    """
    result = template_manager.list_templates(role=role, user=user)
    return AttributionTemplateListResponse(**result)


@app.post("/api/sop/templates/create", response_model=AttributionTemplateResponse, tags=["归因模板"])
def create_attribution_template(req: AttributionTemplateCreateRequest):
    """创建用户自定义归因模板（最多 4 个维度 + 1 个归因指标）"""
    result = template_manager.create_template(
        name=req.name,
        dimensions=req.dimensions,
        description=req.description,
        owner_role=req.owner_role,
        owner_user=req.owner_user,
        metric_key=req.metric_key,  # ⭐ P1
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
    return AttributionTemplateResponse(success=True, template=AttributionTemplateItem(**result["template"]))


@app.post("/api/sop/templates/update", response_model=AttributionTemplateResponse, tags=["归因模板"])
def update_attribution_template(req: AttributionTemplateUpdateRequest):
    """更新用户自定义归因模板（系统预设不可改）"""
    result = template_manager.update_template(
        template_id=req.template_id,
        name=req.name,
        dimensions=req.dimensions,
        description=req.description,
        owner_user=req.owner_user,
        metric_key=req.metric_key,  # ⭐ P1
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
    return AttributionTemplateResponse(success=True, template_id=result.get("template_id"))


@app.post("/api/sop/templates/delete", response_model=AttributionTemplateResponse, tags=["归因模板"])
def delete_attribution_template(req: AttributionTemplateDeleteRequest):
    """删除用户自定义归因模板（系统预设不可删）"""
    result = template_manager.delete_template(req.template_id, owner_user=req.owner_user)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))
    return AttributionTemplateResponse(success=True, deleted_id=result.get("deleted_id"))


@app.get("/api/sop/templates/{template_id}", response_model=AttributionTemplateResponse, tags=["归因模板"])
def get_attribution_template(template_id: str):
    """获取单个模板详情（含维度列表）"""
    t = template_manager.get_template(template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    return AttributionTemplateResponse(success=True, template=AttributionTemplateItem(**t))


# ────────────────────────────────────────────────────────────────────
# ⭐ P2-SprintB：SOP 步骤化模板（V2 路由）
#   - /api/templates/v2/*             业务用户 CRUD + clone + audit
#   - /api/templates/v2/{id}/run      按模板跑完整 SOP（核心端点）
#   - /api/templates/v2/{id}/preview  预览前 2 步
#   - /api/admin/templates/*          admin 系统模板管理（role 权限门禁）
# ────────────────────────────────────────────────────────────────────


# ─── 业务用户：V2 模板 CRUD（兼容老接口 + 新 steps） ─────────────────
@app.post("/api/templates/v2/create", tags=["模板 V2"])
def v2_create_template(
    req: TemplateCreateRequestV2,
    user: CurrentUser = Depends(get_current_user),
):
    """
    业务用户新建 V2 模板（含 steps SOP 步骤化结构）
    - scope 默认 user（业务用户自用）
    - 自动写 audit 初始快照
    """
    try:
        steps_payload = [s.model_dump() for s in req.steps]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"steps 校验失败: {e}")

    result = template_manager.create_template(
        name=req.name,
        description=req.description,
        scope="user",  # 业务用户只能创建 user scope
        steps=steps_payload,
        owner_user=user.username,
        owner_role=user.role,
        updated_by=user.username,
        change_reason=req.change_reason or "create via API",
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
    return result


@app.put("/api/templates/v2/{template_id}", tags=["模板 V2"])
def v2_update_template(
    template_id: str,
    req: TemplateUpdateRequestV2,
    user: CurrentUser = Depends(get_current_user),
):
    """业务用户更新自有模板（非自有/preset 走 admin 端点）"""
    if template_id.startswith("preset_"):
        raise HTTPException(status_code=403, detail="系统预设模板请使用 /api/admin/templates/{id}")
    # body 里的 template_id 应与路径一致（兼容老调用方）
    if req.template_id and req.template_id != template_id:
        raise HTTPException(status_code=400, detail=f"路径与 body template_id 不一致: {template_id} vs {req.template_id}")
    steps_payload = [s.model_dump() for s in req.steps] if req.steps else None
    result = template_manager.update_template(
        template_id=template_id,
        name=req.name,
        description=req.description,
        steps=steps_payload,
        owner_user=user.username,
        updated_by=user.username,
        change_reason=req.change_reason or f"update by {user.username}",
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
    tpl = template_manager.get_template(template_id)
    return {"success": True, "template_id": template_id, "template": tpl}


@app.delete("/api/templates/v2/{template_id}", tags=["模板 V2"])
def v2_delete_template(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """业务用户删除自有模板"""
    if template_id.startswith("preset_"):
        raise HTTPException(status_code=403, detail="系统预设模板不可删除")
    result = template_manager.delete_template(template_id, owner_user=user.username)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))
    return result


@app.post("/api/templates/v2/clone", tags=["模板 V2"])
def v2_clone_template(
    req: TemplateCloneRequestV2,
    user: CurrentUser = Depends(get_current_user),
):
    """
    业务用户克隆模板（market / preset → user）
    - 业务用户必传 owner_user
    - 克隆后 scope=user，归当前用户所有
    """
    result = template_manager.clone_template(
        source_template_id=req.source_template_id,
        target_scope=req.target_scope,
        new_name=req.new_name,
        owner_user=user.username,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "克隆失败"))
    return result


@app.get("/api/templates/v2/{template_id}/audit", response_model=TemplateAuditListResponse, tags=["模板 V2"])
def v2_template_audit(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
    limit: int = 10,
):
    """查看模板变更历史（业务用户只能看自己可见的模板）"""
    # 简单鉴权：业务用户只能看自己创建的 user 模板 + 所有 system/market
    tpl = template_manager.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    if tpl.get("scope") == "user" and tpl.get("owner_user") != user.username and user.role not in ("admin", "analyst"):
        raise HTTPException(status_code=403, detail="无权查看该模板的审计历史")
    history = template_manager.get_audit_history(template_id, limit=limit)
    items = [TemplateAuditItem(**h) for h in history]
    return TemplateAuditListResponse(template_id=template_id, history=items)


# ─── 业务用户：Run + Preview（核心端点） ───────────────────────────────
class TemplateRunRequest(BaseModel):
    """模板执行请求"""
    time_window: Optional[Dict[str, str]] = Field(
        None, description='{"start":"2025-02-01","end":"2025-04-30"}，None 用默认'
    )
    max_steps: Optional[int] = Field(None, ge=1, le=20, description="限制执行步数（preview 用）")
    llm_conclusion: bool = Field(False, description="是否启用 LLM 生成详细结论（默认关闭）")


@app.post("/api/templates/v2/{template_id}/run", tags=["模板 V2"])
def v2_template_run(
    template_id: str,
    req: TemplateRunRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    核心端点：按模板跑完整 SOP，返回结构化归因报告
    - 行级过滤 + 字段脱敏自动应用（业务用户只看自己部门+区域）
    - 每个 step 输出 status (ok/warn/bad) + conclusion + data + sql
    """
    tpl = template_manager.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    # 鉴权：业务用户只能跑自己可见的模板
    if tpl.get("scope") == "user" and tpl.get("owner_user") not in (None, user.username) and user.role not in ("admin", "analyst"):
        raise HTTPException(status_code=403, detail="无权执行该模板")
    try:
        result = sop_executor.run(
            template=tpl,
            user=user,
            time_window=req.time_window,
            max_steps=req.max_steps,
            llm_conclusion=req.llm_conclusion,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SOP 执行异常: {e}")
    return result


@app.post("/api/templates/v2/{template_id}/preview", tags=["模板 V2"])
def v2_template_preview(
    template_id: str,
    req: TemplateRunRequest,
    user: CurrentUser = Depends(get_current_user),
):
    """
    预览端点：仅跑前 2 步（max_steps=2 默认），用于 SOP 编排器实时反馈
    - 适用于前端管理员配置模板时实时看 DuckDB 查询结果
    """
    tpl = template_manager.get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    # 预览不需要鉴权（管理员预览自己配的模板）
    max_steps = req.max_steps if req.max_steps else 2
    try:
        result = sop_executor.run(
            template=tpl,
            user=user,
            time_window=req.time_window,
            max_steps=max_steps,
            llm_conclusion=False,
        )
        # 标记为预览
        result["is_preview"] = True
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览异常: {e}")


# ─── 管理员：系统模板管理（role 权限门禁） ─────────────────────────────
def _is_admin(user: CurrentUser) -> bool:
    return user.role in ("admin", "analyst")


@app.post("/api/admin/templates", tags=["管理员-模板"])
def admin_create_template(
    req: TemplateCreateRequestV2,
    user: CurrentUser = Depends(get_current_user),
):
    """管理员新建 system / role_default / market 模板"""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail=f"权限不足：需要 admin/analyst，当前 {user.role}")
    try:
        steps_payload = [s.model_dump() for s in req.steps]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"steps 校验失败: {e}")
    result = template_manager.create_template(
        name=req.name,
        description=req.description,
        scope=req.scope,  # admin 可指定 system/role_default/market/user
        steps=steps_payload,
        owner_role=user.role,
        updated_by=user.username,
        change_reason=req.change_reason or f"admin create by {user.username}",
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "创建失败"))
    return result


@app.put("/api/admin/templates/{template_id}", tags=["管理员-模板"])
def admin_update_template(
    template_id: str,
    req: TemplateUpdateRequestV2,
    user: CurrentUser = Depends(get_current_user),
):
    """管理员更新模板（含 preset_*，自动 seed DB override）"""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail=f"权限不足：需要 admin/analyst，当前 {user.role}")
    steps_payload = [s.model_dump() for s in req.steps] if req.steps else None
    result = template_manager.update_template(
        template_id=template_id,
        name=req.name,
        description=req.description,
        steps=steps_payload,
        owner_user=None,  # admin update 不按 owner 过滤（允许改任何 user 模板）
        allow_preset=True,  # admin 可改 preset_*
        updated_by=user.username,
        change_reason=req.change_reason or f"admin update by {user.username}",
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "更新失败"))
    tpl = template_manager.get_template(template_id)
    return {"success": True, "template_id": template_id, "template": tpl}


@app.delete("/api/admin/templates/{template_id}", tags=["管理员-模板"])
def admin_delete_template(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
):
    """管理员删除模板（preset_* 默认仍禁删；需 allow=True 才删）"""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail=f"权限不足：需要 admin/analyst，当前 {user.role}")
    result = template_manager.delete_template(template_id, allow_preset=False)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "删除失败"))
    return result


@app.get("/api/admin/templates/{template_id}/audit", response_model=TemplateAuditListResponse, tags=["管理员-模板"])
def admin_template_audit(
    template_id: str,
    user: CurrentUser = Depends(get_current_user),
    limit: int = 50,
):
    """管理员查模板完整审计历史（limit 默认 50，可看更多）"""
    if not _is_admin(user):
        raise HTTPException(status_code=403, detail=f"权限不足：需要 admin/analyst，当前 {user.role}")
    history = template_manager.get_audit_history(template_id, limit=limit)
    items = [TemplateAuditItem(**h) for h in history]
    return TemplateAuditListResponse(template_id=template_id, history=items)


# ─── Sprint 5.1 SSE 流式问数端点 ──────────────────────────────────────
@app.post("/api/chat/stream", tags=["智能问数"])
async def chat_stream(req: ChatQueryRequest, user: CurrentUser = Depends(get_current_user)):
    """
    Sprint 5.1: SSE 流式问数端点

    流式事件类型：
      - thought  : Agent 思考链路（剪枝/表关联/SQL 计划）
      - sql      : 生成的 SQL
      - data     : 查询结果数据
      - chart    : ECharts 图表配置
      - insight  : 经营分析师核心洞察（逐字流式）
      - done     : 完成事件（含耗时统计）
    """
    from fastapi.responses import StreamingResponse
    import asyncio

    async def event_generator():
        try:
            # Step 1: 流式输出思考链（伪流式，模拟 Agent 推理过程）
            yield f"event: thought\ndata: {json.dumps({'step': 1, 'text': '🔍 正在解析提问语义...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            yield f"event: thought\ndata: {json.dumps({'step': 2, 'text': '📊 动态 Schema 剪枝中...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # Step 2: 同步执行 NL2SQL 主链路（最耗时的部分）
            result = nl2sql_engine.ask(req.query, force_mock=req.force_mock)

            # Step 2.1: 如果是闲聊/元问题，直接发 meta_answer 事件，跳过 SQL 生成
            if result.get("is_meta_answer"):
                meta_text = result.get("summary_insight") or "你好！我是广汽云 ChatBI。"
                # 按标点分块流式推送
                chunks = []
                current = ""
                for char in meta_text:
                    current += char
                    if char in "。！？；\n" or len(current) >= 10:
                        chunks.append(current)
                        current = ""
                if current:
                    chunks.append(current)
                for chunk in chunks:
                    yield f"event: meta_answer\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)
                yield f"event: done\ndata: {json.dumps({'success': True, 'healed': False, 'engine': 'meta'}, ensure_ascii=False)}\n\n"
                return

            # Step 3: 推送 SQL
            sql_text = (result.get("sql") or "").replace("\n", " ")
            yield f"event: sql\ndata: {json.dumps({'sql': sql_text}, ensure_ascii=False)}\n\n"

            # Step 4: 推送思考步骤明细
            for step_text in (result.get("thought_steps") or []):
                clean_step = step_text.replace("\n", " ")
                yield f"event: thought\ndata: {json.dumps({'step': 99, 'text': clean_step}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)

            # Step 5: 推送查询结果数据
            data_payload = {
                "columns": result.get("columns", []),
                "rows": result.get("data", []),
                "row_count": result.get("row_count", 0),
                "execution_time_ms": result.get("execution_time_ms", 0)
            }
            yield f"event: data\ndata: {json.dumps(data_payload, ensure_ascii=False)}\n\n"

            # [P0 修复] 0 行结果特殊处理：给出友好提示，避免静默失败
            if result.get("is_empty_result"):
                empty_msg = (
                    "📭 当前查询条件在数仓中无匹配数据。\n\n"
                    "可能原因：\n"
                    "• 业务维度/粒度不在数仓支持范围（如颜色、城市、个体客户、竞品数据）\n"
                    "• 时间范围超出数仓覆盖（当前数仓覆盖 2024-01 至 2025-04）\n\n"
                    "💡 **可分析维度**：品牌 / 车型 / 大区 / 月份\n"
                    "📌 点击下方 15 条快捷提问，每条都能精准返回图表与数据"
                )
                for chunk in [empty_msg[i:i+40] for i in range(0, len(empty_msg), 40)]:
                    yield f"event: insight\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.03)
                yield f"event: empty\ndata: {json.dumps({'reason': 'no_matching_data', 'query': req.query}, ensure_ascii=False)}\n\n"
                yield f"event: done\ndata: {json.dumps({'success': True, 'healed': False, 'engine': result.get('engine', 'DuckDB'), 'empty': True}, ensure_ascii=False)}\n\n"
                return

            # Step 6: 推送图表配置
            # [P1 修复] 优先使用模板的 chart_hint（避免 chart_recommender 把 Q10 误判为 dual_axis）
            tmpl_chart_hint = None
            try:
                if result.get("template_id"):
                    tmpl_chart_hint = result["template_id"]  # 这里只是占位，下面单独查
            except Exception:
                pass
            # 通过 sql 引用检查是否是模板命中（看 thought_steps 是否有"已命中 15 条精确问数模板"）
            used_template = any("已命中 15 条精确问数模板" in (s or "") for s in (result.get("thought_steps") or []))
            chart_info = chart_recommender.recommend(
                query=req.query,
                columns=result.get("columns", []),
                data=result.get("data", []),
                template_chart_hint=result.get("_chart_hint") if used_template else None,
            )
            chart_payload = {
                "chart_type": chart_info.get("chart_type", "table"),
                "echarts_option": chart_info.get("echarts_option") or {}
            }
            yield f"event: chart\ndata: {json.dumps(chart_payload, ensure_ascii=False)}\n\n"

            # Step 7: 流式推送经营洞察（逐字）
            insight_text = result.get("summary_insight") or "查询完成，已生成最新经营视图。"
            # 按中文标点和空格分块，避免截断词组
            chunks = []
            current = ""
            for char in insight_text:
                current += char
                if char in "。！？；\n" or len(current) >= 8:
                    chunks.append(current)
                    current = ""
            if current:
                chunks.append(current)

            for chunk in chunks:
                yield f"event: insight\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.08)

            # Step 8: 完成事件
            done_payload = {
                "success": True,
                "healed": result.get("healed", False),
                "engine": result.get("engine", "DuckDB")
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

        except Exception as e:
            err_msg = str(e).replace("\n", " ")
            yield f"event: error\ndata: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ─── Sprint 5.2 驾驶舱大屏数据聚合端点 ────────────────────────────────
@app.get("/api/dashboard/snapshot", tags=["驾驶舱大屏"])
def dashboard_snapshot(latest_month: str = "2025-04"):
    """
    Sprint 5.2: 一次拉取大屏所需的全部数据（4 个 KPI + 趋势 + 排名 + 预警）

    通过 latest_month 控制要分析的月份，避免对账期硬编码。
    """
    try:
        prev_month_calculator = sop_analyzer._prev_month(latest_month)

        snapshot = {
            "meta": {
                "latest_month": latest_month,
                "prev_month": prev_month_calculator,
                "generated_at": datetime.datetime.now().isoformat()
            },
            "kpis": {},
            "trend": {},
            "ranking": {},
            "alerts": []
        }

        # 1. KPI 卡片组：整体达成率 / 总交付 / 总营收 / 平均 CPL
        kpi_sql = f"""
        WITH sales AS (
            SELECT
                SUM(delivered_units) AS total_units,
                SUM(gross_revenue) / 10000.0 AS total_revenue_wan
            FROM fact_sales_daily
            WHERE STRFTIME('%Y-%m', sale_date) = '{latest_month}'
        ),
        budget AS (
            SELECT SUM(target_units) AS total_target
            FROM dim_budget_target
            WHERE year_month = '{latest_month}'
        ),
        mkt AS (
            SELECT
                ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 2) AS cpl
            FROM fact_marketing_expenses
            WHERE STRFTIME('%Y-%m', expense_date) = '{latest_month}'
        )
        SELECT
            sales.total_units,
            sales.total_revenue_wan,
            budget.total_target,
            ROUND(sales.total_units * 100.0 / NULLIF(budget.total_target, 0), 2) AS fulfillment_rate,
            mkt.cpl
        FROM sales, budget, mkt
        """
        kpi_res = nl2sql_engine.sql_executor.execute_query(kpi_sql)
        if kpi_res["success"] and kpi_res["data"]:
            row = kpi_res["data"][0]
            snapshot["kpis"] = {
                "fulfillment_rate_pct": row.get("fulfillment_rate") or 0,
                "total_units": int(row.get("total_units") or 0),
                "total_revenue_wan": round(row.get("total_revenue_wan") or 0, 1),
                "avg_cpl": row.get("cpl") or 0
            }

        # 2. 趋势：近 12 个月各品牌月交付量（按数据最大月份倒推）
        trend_sql = """
        SELECT
            STRFTIME('%Y-%m', sale_date) AS month,
            brand_name,
            SUM(delivered_units) AS units
        FROM fact_sales_daily
        WHERE sale_date >= (
            SELECT DATE_TRUNC('month', MAX(sale_date)) - INTERVAL '11 months'
            FROM fact_sales_daily
        )
        GROUP BY month, brand_name
        ORDER BY month
        """
        trend_res = nl2sql_engine.sql_executor.execute_query(trend_sql)
        if trend_res["success"]:
            snapshot["trend"] = {"data": trend_res["data"], "columns": trend_res.get("columns", [])}

        # 3. 品牌排名：本期各品牌达成率
        rank_sql = f"""
        WITH s AS (
            SELECT brand_name, SUM(delivered_units) AS actual
            FROM fact_sales_daily
            WHERE STRFTIME('%Y-%m', sale_date) = '{latest_month}'
            GROUP BY brand_name
        ),
        b AS (
            SELECT brand_name, SUM(target_units) AS target
            FROM dim_budget_target
            WHERE year_month = '{latest_month}'
            GROUP BY brand_name
        )
        SELECT
            s.brand_name,
            s.actual,
            b.target,
            ROUND(s.actual * 100.0 / NULLIF(b.target, 0), 2) AS fulfillment_rate
        FROM s
        JOIN b ON s.brand_name = b.brand_name
        ORDER BY fulfillment_rate DESC
        """
        rank_res = nl2sql_engine.sql_executor.execute_query(rank_sql)
        if rank_res["success"]:
            snapshot["ranking"] = {"data": rank_res["data"], "columns": rank_res.get("columns", [])}

        # 4. 异常预警：达成率 < 95% 的品牌自动跑 SOP
        for r in (rank_res.get("data") or []):
            if r.get("fulfillment_rate") is not None and r["fulfillment_rate"] < 95:
                try:
                    sop_report = sop_analyzer.analyze_fulfillment_gap(
                        brand_name=r["brand_name"],
                        year_month=latest_month,
                        threshold_pct=95.0,
                        selected_dimensions=["brand_name", "region_name", "model_name"]  # 报警场景用默认维度
                    )
                    snapshot["alerts"].append({
                        "brand": r["brand_name"],
                        "fulfillment_rate": r["fulfillment_rate"],
                        "gap_units": sop_report.get("gap_units", 0),
                        "executive_summary": sop_report.get("executive_summary", ""),
                        "top_recommendation": (sop_report["steps"][3].get("recommendations", [{}])[0]
                                              if len(sop_report.get("steps", [])) >= 4
                                                 and sop_report["steps"][3].get("recommendations")
                                              else None)
                    })
                except Exception as sop_err:
                    # 单品牌 SOP 失败不影响整体快照
                    snapshot["alerts"].append({
                        "brand": r["brand_name"],
                        "fulfillment_rate": r["fulfillment_rate"],
                        "error": str(sop_err)
                    })

        return snapshot

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"驾驶舱大屏数据聚合异常: {str(e)}")


# ============================================================
# P2-2: 语义层（Semantic Layer）管理 API
# ============================================================
@app.get("/api/semantic", response_model=SemanticLayerResponse, tags=["语义层"])
async def get_semantic_layer():
    """获取语义层完整快照（指标 / 维度 / 同义词 三层）"""
    try:
        from services.semantic_layer import get_full_snapshot
        return get_full_snapshot()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取语义层失败: {str(e)}")


@app.put("/api/semantic/metrics/{metric_id}", tags=["语义层"])
async def update_metric_definition(metric_id: str, body: MetricUpdateRequest):
    """编辑指标口径（definition / calculation_rule / example_query 三字段可改）"""
    try:
        from services.semantic_layer import update_metric
        updates = {k: v for k, v in body.model_dump(exclude_none=True).items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="无可更新字段")
        result = update_metric(metric_id, updates)
        return {"success": True, "metric_id": metric_id, "updated_fields": list(updates.keys()), "metric": result}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新指标失败: {str(e)}")


@app.put("/api/semantic/glossary/{term_name}", tags=["语义层"])
async def update_glossary_term(term_name: str, body: GlossaryUpdateRequest):
    """编辑业务术语（definition / synonyms / related_metrics）"""
    try:
        from services.semantic_layer import update_glossary
        updates = {k: v for k, v in body.model_dump(exclude_none=True).items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="无可更新字段")
        result = update_glossary(term_name, updates)
        return {"success": True, "term_name": term_name, "updated_fields": list(updates.keys()), "term": result}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新术语失败: {str(e)}")


@app.post("/api/semantic/preview", response_model=SemanticPreviewResponse, tags=["语义层"])
async def preview_semantic_recall(body: SemanticPreviewRequest):
    """模拟问数：把当前语义层应用到召回，返回命中的指标/术语 + 示例 SQL"""
    try:
        from services.semantic_layer import preview_query
        return preview_query(body.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


# ============================================================
# P2-1: 数据管理（CSV 导入 / 导出 / 列表 / 预览 / 删除）
# ============================================================
from fastapi import UploadFile, File, Form
from fastapi.responses import PlainTextResponse, Response


@app.get("/api/data/uploads", tags=["数据管理"])
async def list_uploads():
    """列出所有用户上传的 CSV/DuckDB 表"""
    try:
        from services.data_manager import list_user_tables
        return {"success": True, "tables": list_user_tables()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取用户表失败: {str(e)}")


@app.get("/api/data/default-tables", tags=["数据管理"])
async def default_tables():
    """
    返回 3 张默认业务表的元信息（让用户打开数据管理页就有内容看）。
    用户也可以上传自己的 CSV 表（list_uploads 返回）。
    """
    try:
        from services.data_manager import get_default_tables_meta
        return get_default_tables_meta()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取默认表失败: {str(e)}")


@app.get("/api/data/stats", tags=["数据管理"])
async def data_stats():
    """用户库容量统计"""
    try:
        from services.data_manager import get_stats
        return get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取统计失败: {str(e)}")


@app.post("/api/data/upload", tags=["数据管理"])
async def upload_csv(
    file: UploadFile = File(..., description="CSV 文件"),
    table_name: str = Form(..., description="目标表名（自动加 user_ 前缀）"),
):
    """上传 CSV 到用户库（独立 DuckDB 文件，不影响业务主库）"""
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件为空")
        # 解码（兼容 utf-8 / gbk）
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise HTTPException(status_code=400, detail="文件编码无法识别（仅支持 utf-8 / gbk）")

        from services.data_manager import import_csv
        result = import_csv(text, table_name)
        return {"success": True, **result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@app.get("/api/data/preview/{table_name}", tags=["数据管理"])
async def preview_data(table_name: str, limit: int = 50, source: str = "user"):
    """
    预览前 N 行
    - source=user (默认): 用户上传的 CSV 表
    - source=business : 业务默认表（fact_sales_daily / dim_budget_target / fact_marketing_expenses）
    """
    try:
        from services.data_manager import preview_table
        return preview_table(table_name, limit, source=source)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


@app.get("/api/data/details/{table_name}", tags=["数据管理"])
async def get_table_details(table_name: str, limit: int = 20, source: str = "user"):
    """
    「明细查询」专用端点（Chat 页"明细"按钮直接调用，不走 NL2SQL）

    返回结构：
      - columns: 列表字段信息 [{name, type}, ...]
      - data: 前 N 行原始数据（按表名智能选时间列倒序）
      - row_count: 总行数
      - summary: 一句话概要（如"fact_sales_daily 共 9,237 行，按 sale_date 倒序展示前 20 行"）
      - chart_hint: 表格型（前端用 Table 组件呈现）
    """
    try:
        from services.data_manager import get_table_details_smart
        return get_table_details_smart(table_name, limit=limit, source=source)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"明细查询失败: {str(e)}")


@app.get("/api/data/export/{table_name}", tags=["数据管理"])
async def export_data(table_name: str):
    """导出用户表为 CSV 下载"""
    try:
        from services.data_manager import export_table_csv
        csv_content = export_table_csv(table_name)
        return Response(
            content=csv_content,
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{table_name}.csv"',
                "Content-Type": "text/csv; charset=utf-8",
            },
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


@app.delete("/api/data/{table_name}", tags=["数据管理"])
async def delete_data(table_name: str):
    """删除用户表 + CSV 归档"""
    try:
        from services.data_manager import delete_table
        return delete_table(table_name)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


# ============================================================
# P2-3: 角色身份（前端权限矩阵数据源）
# ============================================================
@app.get("/api/roles", tags=["系统"])
async def list_roles():
    """列出所有角色 + 权限矩阵（前端按此渲染菜单与守卫）

    权限规则：
      - executive 高管：驾驶舱/归因/概览
      - analyst 分析师：全量问数 + 指标库 + 数据管理 + 语义层
      - product 产品经理：全功能
      - guest 访客：核心问数 + 驾驶舱（只读）
    """
    return {
        "success": True,
        "default_role": "product",
        "roles": [
            {
                "id": "executive",
                "label": "高管视角",
                "description": "驾驶舱大屏 / 归因报告 / 业务概览",
                "icon": "👔",
                "color": "indigo",
                "badge": "管",
            },
            {
                "id": "analyst",
                "label": "分析师",
                "description": "全量问数 + 指标库 + 数据管理 + 语义层",
                "icon": "📊",
                "color": "blue",
                "badge": "分",
            },
            {
                "id": "product",
                "label": "AI 产品经理",
                "description": "全功能 + 语义层编辑 + 演示模式",
                "icon": "🤖",
                "color": "purple",
                "badge": "PM",
            },
            {
                "id": "guest",
                "label": "访客",
                "description": "核心问数 + 驾驶舱大屏（只读）",
                "icon": "👤",
                "color": "gray",
                "badge": "客",
            },
        ],
        "permissions": {
            "/":             ["executive", "analyst", "product", "guest"],
            "/dashboard":    ["executive", "analyst", "product", "guest"],
            "/reports":      ["executive", "analyst", "product"],
            "/metrics":      ["executive", "analyst", "product"],
            "/tables":       ["analyst", "product"],
            "/data-manager": ["analyst", "product"],
            "/history":      ["analyst", "product"],
            "/semantic":     ["product"],
            "/bad-case":     ["analyst", "product"],
            "/audit":        ["executive", "analyst", "product"],
            "/settings":     ["executive", "analyst", "product"],
            "/help":         ["executive", "analyst", "product", "guest"],
        },
    }


# ============================================================
# P2-4: 操作审计日志 API
# ============================================================
from services.audit_log import write_audit, list_audit, audit_stats


class AuditWriteRequest(BaseModel):
    actor: str = Field(..., description="操作者（角色名 / user-id）")
    action: str = Field(..., description="动作：create / update / delete / query / export / feedback / login")
    resource: str = Field(..., description="资源：semantic_term / metric / dataset / chat / data_manager / bad_case")
    resource_id: Optional[str] = Field(None, description="资源 ID")
    payload: Optional[Dict[str, Any]] = Field(None, description="变更内容（diff）")
    note: Optional[str] = Field(None, description="备注")


@app.post("/api/audit/log", tags=["操作审计"])
def api_write_audit(req: AuditWriteRequest, request: Request):
    """写入一条审计日志（前端自动调用）"""
    ip = request.client.host if request.client else "127.0.0.1"
    audit_id = write_audit(
        actor=req.actor,
        action=req.action,
        resource=req.resource,
        resource_id=req.resource_id,
        payload=req.payload,
        ip=ip,
        note=req.note,
    )
    return {"success": True, "audit_id": audit_id}


@app.get("/api/audit/list", tags=["操作审计"])
def api_list_audit(
    actor: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    limit: int = 100,
):
    """查询审计日志（按时间倒序）"""
    items = list_audit(
        actor=actor, action=action, resource=resource, limit=limit
    )
    return {"success": True, "items": items, "count": len(items)}


@app.get("/api/audit/stats", tags=["操作审计"])
def api_audit_stats():
    """审计日志统计概览"""
    return {"success": True, **audit_stats()}


# ============================================================
# P2-7: Bad Case 闭环 API（语义层自动学习）
# ============================================================
from services.audit_log import (
    submit_bad_case,
    list_bad_case,
    resolve_bad_case,
    bad_case_stats,
)


class BadCaseSubmitRequest(BaseModel):
    actor: str = Field(..., description="反馈者")
    query: str = Field(..., description="原始问题")
    sql_text: Optional[str] = Field(None, description="生成的 SQL")
    result_summary: Optional[str] = Field(None, description="结果摘要")
    feedback_type: str = Field(..., description="positive / negative / correction")
    feedback_label: Optional[str] = Field(None, description="问题标签：sql错误/口径偏差/数据缺失/其他")
    correction: Optional[str] = Field(None, description="用户修正口径")


@app.post("/api/bad-case/submit", tags=["Bad Case 闭环"])
def api_submit_bad_case(req: BadCaseSubmitRequest):
    """提交一条 Bad Case 反馈"""
    if req.feedback_type not in ("positive", "negative", "correction"):
        raise HTTPException(400, "feedback_type 必须是 positive / negative / correction")

    # 同步写审计日志
    write_audit(
        actor=req.actor,
        action="feedback",
        resource="bad_case",
        payload={
            "feedback_type": req.feedback_type,
            "feedback_label": req.feedback_label,
            "correction": req.correction,
            "query_preview": req.query[:80],
        },
    )

    case_id = submit_bad_case(
        actor=req.actor,
        query=req.query,
        sql_text=req.sql_text,
        result_summary=req.result_summary,
        feedback_type=req.feedback_type,
        feedback_label=req.feedback_label,
        correction=req.correction,
    )
    return {"success": True, "case_id": case_id}


@app.get("/api/bad-case/list", tags=["Bad Case 闭环"])
def api_list_bad_case(
    feedback_type: Optional[str] = None,
    resolved: Optional[bool] = None,
    limit: int = 100,
):
    """查询 Bad Case 列表"""
    items = list_bad_case(
        feedback_type=feedback_type, resolved=resolved, limit=limit
    )
    return {"success": True, "items": items, "count": len(items)}


class BadCaseResolveRequest(BaseModel):
    case_id: str
    resolved_by: str
    semantic_term_id: Optional[str] = Field(
        None, description="关联到语义层 term 后，下次同类问数会更准"
    )


@app.post("/api/bad-case/resolve", tags=["Bad Case 闭环"])
def api_resolve_bad_case(req: BadCaseResolveRequest):
    """闭环 Bad Case：标记解决 + 关联语义层"""
    resolve_bad_case(
        case_id=req.case_id,
        resolved_by=req.resolved_by,
        semantic_term_id=req.semantic_term_id,
    )
    write_audit(
        actor=req.resolved_by,
        action="update",
        resource="bad_case",
        resource_id=req.case_id,
        payload={"status": "resolved", "semantic_term_id": req.semantic_term_id},
        note="Bad Case 闭环",
    )
    return {"success": True}


@app.get("/api/bad-case/stats", tags=["Bad Case 闭环"])
def api_bad_case_stats():
    """Bad Case 统计概览"""
    return {"success": True, **bad_case_stats()}


# ============================================================
# P2-4: 启动期写入"系统初始化"审计
# ============================================================
try:
    write_audit(
        actor="system",
        action="create",
        resource="system",
        note="服务启动 / 审计表初始化",
    )
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
