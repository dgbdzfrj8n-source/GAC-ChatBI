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
