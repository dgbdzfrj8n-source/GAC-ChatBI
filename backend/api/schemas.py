"""
FastAPI 前后端通信协议与数据契约规范 (Pydantic V2)
定义输入参数、流式状态节点、问数结构体、指标字典与 Bad Case 反馈结构。
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional

# --- 1. 问数交互契约 ---
class ChatQueryRequest(BaseModel):
    query: str = Field(..., description="业务自然语言问数提问", min_length=1)
    force_mock: bool = Field(False, description="是否强制启用 0-Latency Mock 演示兜底模式")
    session_id: Optional[str] = Field("default_session", description="多轮会话标识")

class ChatQueryResponse(BaseModel):
    query: str = Field(..., description="原始业务提问")
    thought_steps: List[str] = Field(..., description="Agent 思考与剪枝链路明细")
    sql: str = Field(..., description="生成的只读 SQL 语句")
    success: bool = Field(..., description="查询与解析是否成功")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="查询拉取到的结构化数据行")
    columns: List[str] = Field(default_factory=list, description="列名清单")
    row_count: int = Field(0, description="数据行数")
    execution_time_ms: float = Field(0.0, description="底层 SQL 聚合计算耗时(ms)")
    chart_type: str = Field("table", description="推荐可视化类型: line | bar | pie | dual_axis | table")
    echarts_option: Optional[Dict[str, Any]] = Field(None, description="ECharts 标准可视化配置字典")
    summary_insight: str = Field(..., description="经营分析师专业归因与关键结论")
    healed: bool = Field(False, description="是否触发并成功完成了 1 次自愈重试")
    engine: str = Field("DuckDB", description="底层数仓计算引擎")
    error: Optional[str] = Field(None, description="错误详情(若有)")
    is_unsupported_entity: bool = Field(False, description="是否触发了「暂不支持实体维度」诚实提示拦截")

# --- 2. 经营指标库契约 ---
class MetricItem(BaseModel):
    metric_id: str
    metric_name: str
    business_domain: str
    definition: str
    unit: str
    calculation_rule: str
    example_query: Optional[str] = None

class MetricListResponse(BaseModel):
    version: str
    domain_group: str
    metrics: List[MetricItem]

# --- 3. Bad Case 收集反馈契约 ---
class BadCaseFeedbackRequest(BaseModel):
    query: str = Field(..., description="触发问题的用户提问")
    sql: Optional[str] = Field(None, description="有问题的 SQL")
    feedback_type: str = Field(..., description="问题类型：口径不准 | SQL报错 | 图表不适配 | 数据缺失")
    user_comment: Optional[str] = Field("", description="业务用户填写的补充说明")


# --- 4. SOP 高频归因引擎契约 ---
# ─── 归因维度模板（P0 增强） ────────────────────────────────────────────
class AttributionTemplateItem(BaseModel):
    """单个归因维度模板条目"""
    id: str
    name: str
    description: str = ""
    scope: str = Field(..., description="system（系统预设） 或 user（用户自定义）")
    owner_role: Optional[str] = None
    owner_user: Optional[str] = None
    dimensions: List[str] = Field(..., description="该模板的归因维度列表")
    # ⭐ P1 新增：模板绑定的归因指标
    metric_key: str = Field(
        "delivered_units",
        description="归因指标键：delivered_units / gross_revenue / customer_leads / conversion_rate / avg_price",
    )
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AttributionTemplateListResponse(BaseModel):
    """模板列表响应"""
    system_presets: List[AttributionTemplateItem]
    role_default_id: Optional[str] = Field(None, description="当前角色绑定的默认模板 ID")
    role_defaults_map: Dict[str, str] = Field(default_factory=dict, description="所有角色的默认模板映射")
    user_templates: List[AttributionTemplateItem] = Field(default_factory=list)


class AttributionTemplateCreateRequest(BaseModel):
    """新建用户自定义模板"""
    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field("", max_length=200)
    dimensions: List[str] = Field(..., min_length=1, max_length=4)
    # ⭐ P1 新增：模板绑定的归因指标（必填，默认 delivered_units）
    metric_key: str = Field(
        "delivered_units",
        description="归因指标键，必须在白名单内",
    )
    owner_role: Optional[str] = None
    owner_user: Optional[str] = None


class AttributionTemplateUpdateRequest(BaseModel):
    """更新模板（仅 user scope）"""
    template_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    dimensions: Optional[List[str]] = None
    # ⭐ P1 新增：可选更新指标
    metric_key: Optional[str] = None
    owner_user: Optional[str] = None


class AttributionTemplateDeleteRequest(BaseModel):
    """删除模板（仅 user scope）"""
    template_id: str
    owner_user: Optional[str] = None


class AttributionTemplateResponse(BaseModel):
    """单个模板操作响应"""
    success: bool
    template: Optional[AttributionTemplateItem] = None
    template_id: Optional[str] = None
    deleted_id: Optional[str] = None
    error: Optional[str] = None


# ─── 归因维度可用枚举（P0：用户可选维度清单） ─────────────────────────
SUPPORTED_DIMENSIONS: List[str] = [
    "brand_name",     # 品牌维度（广丰 / 广本 / 自主）
    "region_name",    # 区域维度（华南 / 华北 / 华东）
    "model_name",     # 车型维度（轿车 / SUV / MPV）
    "energy_type",    # 能源类型（纯电 / 混动 / 燃油）
    "price_segment",  # 价格段维度（高价车 / 中价车 / 低价车）
    "monthly",        # 时间维度（周内波动 / 月初月末）
]

# ─── 归因指标目录契约（P1） ─────────────────────────────────────────
SUPPORTED_METRICS: List[Dict[str, Any]] = [
    {
        "key": "delivered_units",
        "label": "总交付量",
        "unit": "辆",
        "description": "当期交付的整车数量（核心销量口径）",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "price_segment", "monthly"],
    },
    {
        "key": "gross_revenue",
        "label": "总营收",
        "unit": "元",
        "description": "当期开票总营收（财务口径）",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "price_segment"],
    },
    {
        "key": "customer_leads",
        "label": "进店线索量",
        "unit": "条",
        "description": "当期进店/留资的意向客户数（获客口径）",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "monthly"],
    },
    {
        "key": "conversion_rate",
        "label": "客流转化率",
        "unit": "%",
        "description": "交付量/线索量的比值（终端转化效率）",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "price_segment"],
    },
    {
        "key": "avg_price",
        "label": "单车成交均价",
        "unit": "元/辆",
        "description": "营收/交付量的比值（产品结构稳定性）",
        "applicable_dimensions": ["brand_name", "region_name", "model_name", "energy_type", "price_segment"],
    },
]


class MetricCatalogResponse(BaseModel):
    """归因指标目录响应（前端下拉框渲染用）"""
    metrics: List[Dict[str, Any]] = Field(..., description="5 个推荐归因指标")


class SopAnalysisRequest(BaseModel):
    """Sprint 5.3 SOP 归因引擎入参"""
    brand_name: str = Field(..., description="品牌名称（如 广汽埃安/广汽传祺/昊铂）")
    year_month: str = Field(..., description="分析月份 YYYY-MM，如 2025-03")
    threshold_pct: Optional[float] = Field(95.0, ge=0, le=200, description="达成率预警阈值，默认 95%")
    # ⭐ P0 新增：用户自定义归因维度列表
    selected_dimensions: List[str] = Field(
        default_factory=lambda: ["brand_name", "region_name", "model_name"],
        description="用户选定的归因维度列表，可选：brand_name/model_name/region_name/energy_type/price_segment/monthly"
    )
    # ⭐ P1 新增：归因指标（白名单兜底，默认 delivered_units）
    metric_key: Optional[str] = Field(
        "delivered_units",
        description="归因指标键：delivered_units / gross_revenue / customer_leads / conversion_rate / avg_price",
    )
    # ⭐ P1 新增：可选模板 ID（传了就从模板取 metric_key + dimensions，前端不用再传两个）
    template_id: Optional[str] = Field(
        None,
        description="归因模板 ID，传了之后自动用模板的指标和维度覆盖请求体",
    )

class SopStepInfo(BaseModel):
    step: int
    step_name: str
    status: str
    content: Dict[str, Any] = Field(default_factory=dict, description="该步骤原始数据")

class SopAnalysisResponse(BaseModel):
    """Sprint 5.3 SOP 归因引擎出参：四步下钻 + 高管摘要"""
    success: bool
    brand: str
    year_month: str
    fulfillment_rate_pct: float
    gap_units: int
    gap_grade: str
    gap_reason: str
    steps: List[Dict[str, Any]] = Field(..., description="四步下钻完整明细")
    recommendations: List[Dict[str, Any]] = Field(default_factory=list, description="可执行策略清单")
    executive_summary: str = Field(..., description="高管可读的归因摘要")
    execution_time_ms: float = 0.0
    # ⭐ P0 新增：归因贡献明细（指标波动 = 各维度贡献之和）
    selected_dimensions: List[str] = Field(default_factory=list, description="本次归因使用的维度列表")
    attribution_breakdown: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="归因贡献明细：[{\"dimension\": \"华南区域\", \"contribution\": -800, \"contribution_pct\": 66.7, \"reason\": \"当地新能源渗透率上升\"}, ...]"
    )
    supported_dimensions: List[str] = Field(
        default_factory=lambda: SUPPORTED_DIMENSIONS,
        description="系统支持的可选归因维度清单（用于前端渲染选择器）"
    )
    # ⭐ P1 新增：本次归因使用的指标元数据（key/label/unit）
    metric: Optional[Dict[str, Any]] = Field(
        None,
        description="本次归因指标元数据：{key, label, unit, applicable_dimensions}",
    )
    supported_metrics: List[Dict[str, Any]] = Field(
        default_factory=lambda: SUPPORTED_METRICS,
        description="系统支持的归因指标目录（前端下拉框渲染用）",
    )


# --- 6. P2-2 语义层（Semantic Layer）契约 ---
class SemanticLayerResponse(BaseModel):
    """语义层完整快照（指标/维度/同义词 三层）"""
    version: str
    domain_group: str
    metrics: List[Dict[str, Any]] = Field(..., description="指标层 6 项")
    dimensions: List[Dict[str, Any]] = Field(..., description="维度层：自动从 schema 抽取的字段")
    glossary: List[Dict[str, Any]] = Field(..., description="同义词层：业务术语")


class MetricUpdateRequest(BaseModel):
    """指标层编辑：definition / calculation_rule / example_query 可改"""
    definition: Optional[str] = None
    calculation_rule: Optional[str] = None
    example_query: Optional[str] = None


class GlossaryUpdateRequest(BaseModel):
    """术语层编辑：definition / synonyms / related_metrics"""
    definition: Optional[str] = None
    synonyms: Optional[List[str]] = None
    related_metrics: Optional[List[str]] = None


class SemanticPreviewRequest(BaseModel):
    """模拟问数：把语义层应用到 RAG 召回"""
    query: str = Field(..., description="业务自然语言问数", min_length=1)


class SemanticPreviewResponse(BaseModel):
    """模拟问数召回结果"""
    query: str
    matched_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    matched_terms: List[Dict[str, Any]] = Field(default_factory=list)
    sample_sql: Optional[str] = Field(None)


# ─── ⭐ P2-SprintA：SOP 步骤化模板（管理员可视化编排分析思路） ──────────
from uuid import uuid4 as _uuid4
from typing import Literal

# 8 种 step_type 枚举（含目标对比 + YoY/MoM）
STEP_TYPE_VALUES = (
    "overall_kpi",          # 整体达成率 vs 目标
    "yoy_compare",          # YoY 同比（本期 vs 去年同期）
    "period_compare",       # 环比/同期对比（本期 vs 上期）
    "horizontal_compare",   # 横向对比（多 brand/region 并列）
    "drill_down",           # 下钻找异常
    "cross_attribution",    # 跨域归因（贡献度拆解）
    "anomaly_alert",        # 异常告警（z-score）
    "strategy_recommend",   # 策略建议（基于 depends_on 的 step）
)


def _validate_metric_in_whitelist(v: str) -> str:
    """校验 metric_key 是否在白名单内（与 sop_analyzer.METRIC_DIMENSION_MATRIX 同源）"""
    try:
        from core.sop_analyzer import METRIC_DIMENSION_MATRIX
        if v not in METRIC_DIMENSION_MATRIX:
            raise ValueError(f"不支持的指标: {v}")
        return v
    except ImportError:
        # 单测环境拿不到 core.sop_analyzer 时退化为硬编码白名单兜底
        _FALLBACK = {"delivered_units", "gross_revenue", "customer_leads", "conversion_rate", "avg_price"}
        if v not in _FALLBACK:
            raise ValueError(f"不支持的指标: {v}")
        return v


def _validate_dims_match_metric(metric_key: str, dims: List[str]) -> List[str]:
    """校验 dims 是否在 metric 的 applicable_dimensions 内"""
    try:
        from core.sop_analyzer import METRIC_DIMENSION_MATRIX, DIMENSION_FIELD_MAP
        metric_cfg = METRIC_DIMENSION_MATRIX.get(metric_key, {})
        allowed = set(metric_cfg.get("applicable_dimensions", []))
        bad = [d for d in dims if d not in allowed or d not in DIMENSION_FIELD_MAP]
        if bad:
            raise ValueError(f"维度 {bad} 不适用于指标 {metric_key}（allowed={sorted(allowed)}）")
        return dims
    except ImportError:
        return dims  # 单测环境兜底


class StepSpec(BaseModel):
    """
    SOP 单步原子步骤（管理员在后台配置的最小单元）
    - step_type：决定 SOP 执行引擎走哪条 SQL 构造路径
    - group_by：本步骤聚合的维度（drill_down/horizontal_compare 必填，overall_kpi/yoy_compare 可空）
    - depends_on：strategy_recommend 必填，指向上一步 step_id
    - order：1..N 连续（由 AttributionTemplate 校验器兜底）
    """
    model_config = {"extra": "forbid"}  # 严格拒绝未声明字段

    step_id: str = Field(default_factory=lambda: f"step_{_uuid4().hex[:6]}")
    title: str = Field(..., min_length=2, max_length=30, description="展示名（中文）")
    step_type: Literal[
        "overall_kpi", "yoy_compare", "period_compare",
        "horizontal_compare", "drill_down",
        "cross_attribution", "anomaly_alert", "strategy_recommend"
    ] = Field(..., description="SOP 步骤类型（决定 SQL 构造路径）")
    metric_key: str = Field(..., description="归因指标键（白名单内）")
    group_by: List[str] = Field(default_factory=list, description="聚合维度；空 = 不分组（整体 KPI）")
    compare_with: Optional[Dict[str, Any]] = Field(None, description="对比模式详情：{mode, plan_field, period}")
    compare_mode: Literal["plan", "yoy", "mom", "yoy_mom"] = Field("plan", description="对比基准：目标/同比/环比")
    compare_period: Optional[str] = Field(None, description="对比期，如 2025-Q3")
    threshold: Optional[Dict[str, float]] = Field(None, description="异常判定阈值：{warn, bad}")
    top_n: Optional[int] = Field(None, ge=1, le=100, description="Top N 截断")
    depends_on: Optional[str] = Field(None, description="关联的上游 step_id（strategy_recommend 必填）")
    order: int = Field(..., ge=1, le=20, description="执行顺序，1..N 连续")

    @field_validator("metric_key")
    @classmethod
    def _check_metric(cls, v: str) -> str:
        return _validate_metric_in_whitelist(v)

    @field_validator("group_by")
    @classmethod
    def _check_dims(cls, v: List[str], info) -> List[str]:
        metric = info.data.get("metric_key")
        if metric and v:
            return _validate_dims_match_metric(metric, v)
        return v


class AttributionTemplateV2(BaseModel):
    """
    SOP 步骤化模板（P2-SprintA）
    - scope：system / role_default / market / user 四类
    - steps：1..10 步，order 必须 1..N 连续
    - depends_on 必须指向同模板内已存在的 step_id
    - strategy_recommend 必须 depends_on 一个 step
    """
    model_config = {"extra": "forbid"}

    id: str
    name: str = Field(..., min_length=2, max_length=50)
    description: str = Field(default="", max_length=200)
    scope: Literal["system", "role_default", "market", "user"] = "user"
    owner_role: Optional[str] = None
    owner_user: Optional[str] = None
    metric_key: Optional[str] = Field(
        None,
        description="模板默认指标（可被 step 自身 metric_key 覆盖；为空时用 DEFAULT_METRIC_KEY）",
    )
    steps: List[StepSpec] = Field(..., min_length=1, max_length=10)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @model_validator(mode="after")
    def _check_steps(self):
        # 1. order 连续 1..N
        orders = sorted(s.order for s in self.steps)
        if orders != list(range(1, len(self.steps) + 1)):
            raise ValueError(
                f"step.order 必须 1..{len(self.steps)} 连续无重复，当前 orders={orders}"
            )
        # 2. step_id 在模板内唯一
        ids = [s.step_id for s in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError(f"step_id 必须唯一，当前 ids={ids}")
        # 3. depends_on 必须指向已存在的 step_id
        id_set = set(ids)
        for s in self.steps:
            if s.depends_on and s.depends_on not in id_set:
                raise ValueError(f"step '{s.step_id}' 的 depends_on='{s.depends_on}' 不存在")
        # 4. strategy_recommend 必须 depends_on
        for s in self.steps:
            if s.step_type == "strategy_recommend" and not s.depends_on:
                raise ValueError(f"strategy_recommend step '{s.step_id}' 必须 depends_on 一个 step")
        # 5. yoy_compare / period_compare 必须指定 compare_period
        for s in self.steps:
            if s.step_type in ("yoy_compare", "period_compare") and not s.compare_period:
                raise ValueError(
                    f"step '{s.step_id}' 是 {s.step_type}，必须指定 compare_period（如 '2025-Q3'）"
                )
        # 6. template-level metric_key 也需在白名单
        if self.metric_key:
            _validate_metric_in_whitelist(self.metric_key)
        return self


class TemplateCreateRequestV2(BaseModel):
    """新建模板（含 steps，P2-SprintA）"""
    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=2, max_length=50)
    description: str = Field(default="", max_length=200)
    scope: Literal["system", "role_default", "market", "user"] = "user"
    steps: List[StepSpec] = Field(..., min_length=1, max_length=10)
    change_reason: Optional[str] = Field(None, max_length=100, description="变更原因（写入审计）")


class TemplateUpdateRequestV2(BaseModel):
    """更新模板（含 steps，P2-SprintA）"""
    model_config = {"extra": "forbid"}

    template_id: Optional[str] = Field(
        None,
        description="模板 ID（RESTful 风格下从路径参数传入即可，body 不必再传）",
    )
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    steps: Optional[List[StepSpec]] = Field(None, min_length=1, max_length=10)
    change_reason: Optional[str] = Field(None, max_length=100)


class TemplateCloneRequestV2(BaseModel):
    """克隆模板（market → user）"""
    model_config = {"extra": "forbid"}

    source_template_id: str
    target_scope: Literal["market", "user"] = "user"
    new_name: Optional[str] = Field(None, min_length=2, max_length=50)


class TemplateAuditItem(BaseModel):
    """审计快照条目"""
    audit_id: str
    template_id: str
    version_no: int
    snapshot: Dict[str, Any]
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    changed_at: Optional[str] = None


class TemplateAuditListResponse(BaseModel):
    """审计历史响应"""
    template_id: str
    history: List[TemplateAuditItem]

