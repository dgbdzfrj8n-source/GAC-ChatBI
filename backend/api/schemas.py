"""
FastAPI 前后端通信协议与数据契约规范 (Pydantic V2)
定义输入参数、流式状态节点、问数结构体、指标字典与 Bad Case 反馈结构。
"""

from pydantic import BaseModel, Field
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
class SopAnalysisRequest(BaseModel):
    """Sprint 5.3 SOP 归因引擎入参"""
    brand_name: str = Field(..., description="品牌名称（如 广汽埃安/广汽传祺/昊铂）")
    year_month: str = Field(..., description="分析月份 YYYY-MM，如 2025-03")
    threshold_pct: Optional[float] = Field(95.0, ge=0, le=200, description="达成率预警阈值，默认 95%")

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

