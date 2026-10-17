"""
Workflow Context - 链路上下文对象
定义 Text2SQL 全链路各步骤之间传递的数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class ThinkingStep:
    """思考链中的单个步骤"""
    step: int                          # 步骤序号 1-8
    name: str                           # 步骤名称
    content: str                        # 步骤内容描述
    status: str = "running"            # running/done/error
    duration_ms: int = 0               # 执行耗时（毫秒）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "name": self.name,
            "content": self.content,
            "status": self.status,
            "duration_ms": self.duration_ms
        }


@dataclass
class Metric:
    """指标定义"""
    metric_id: str                      # M01-M30
    metric_name: str                    # 指标名称
    business_domain: str                 # 业务域
    definition: str                      # 业务定义
    unit: str                           # 单位
    calculation_rule: str                # 计算公式
    required_tables: List[str]           # 涉及表
    related_dimensions: List[str]        # 涉及维度
    notes: str = ""                     # 注意事项
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Metric":
        return cls(
            metric_id=data.get("metric_id", ""),
            metric_name=data.get("metric_name", ""),
            business_domain=data.get("business_domain", ""),
            definition=data.get("definition", ""),
            unit=data.get("unit", ""),
            calculation_rule=data.get("calculation_rule", ""),
            required_tables=data.get("required_tables", []),
            related_dimensions=data.get("related_dimensions", []),
            notes=data.get("notes", "")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.metric_id,
            "name": self.metric_name,
            "domain": self.business_domain,
            "unit": self.unit,
            "definition": self.definition,
            "formula": self.calculation_rule,
            "related_tables": self.required_tables,
            "related_dimensions": self.related_dimensions,
            "notes": self.notes
        }


@dataclass
class QueryResult:
    """SQL查询结果"""
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    row_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count
        }


@dataclass
class ErrorInfo:
    """错误信息"""
    code: str                           # 错误码
    message: str                        # 用户可读的错误信息
    detail: str = ""                    # 技术详情
    suggestion: str = ""                # 给用户的建议
    retries: int = 0                    # 已重试次数
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
            "suggestion": self.suggestion,
            "retries": self.retries
        }


@dataclass
class ChartConfig:
    """图表配置"""
    chart_type: str                     # single_kpi/bar/line/pie/funnel/table/rank
    field_mapping: Dict[str, str] = field(default_factory=dict)  # x/y/category/value映射
    config: Dict[str, Any] = field(default_factory=dict)         # 完整ECharts配置
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "field_mapping": self.field_mapping,
            "config": self.config
        }


@dataclass
class ClarifySlot:
    """澄清槽位"""
    brand: Optional[str] = None         # 品牌
    time_range: Optional[str] = None    # 时间范围
    metric: Optional[str] = None        # 指标
    dimension: Optional[str] = None      # 分析维度
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brand": self.brand,
            "time_range": self.time_range,
            "metric": self.metric,
            "dimension": self.dimension
        }


@dataclass
class WorkflowContext:
    """
    Text2SQL 全链路上下文对象
    所有步骤共享此对象，每步读取输入、写入输出
    """
    # === 输入 ===
    question: str = ""                  # 用户原始问题
    brand_filter: str = "全部"         # 全局品牌筛选
    session_id: str = ""                # 会话ID
    clarify_context: Optional[ClarifySlot] = None  # 澄清后补充的维度
    
    # === Step1 输出：意图识别 ===
    intent: Optional[str] = None         # query_type: 指标查询/对比/趋势/归因/非业务
    intent_confidence: float = 0.0
    intent_reasoning: str = ""
    
    # === Step2 输出：指标匹配 ===
    matched_metric: Optional[Metric] = None
    metric_confidence: float = 0.0
    synonym_mapping: Dict[str, str] = field(default_factory=dict)  # {"销量": "delivered_units"}
    
    # === Step3 输出：维度解析 ===
    dimensions: Dict[str, Any] = field(default_factory=dict)  # {"brand": "广汽埃安", "time": "2025-03"}
    missing_dimensions: List[str] = field(default_factory=list)
    dimension_confidence: float = 0.0
    
    # === Step4 输出：表定位 ===
    table_list: List[str] = field(default_factory=list)
    compact_schema: str = ""
    join_hints: List[str] = field(default_factory=list)
    
    # === Step5 输出：SQL生成 ===
    sql: Optional[str] = None
    sql_attempts: int = 0
    sql_token_count: int = 0
    
    # === Step6 输出：执行校验 ===
    result: Optional[QueryResult] = None
    execution_time_ms: int = 0
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    # === Step7 输出：可视化决策 ===
    chart_config: Optional[ChartConfig] = None
    
    # === Step8 输出：业务解读 ===
    conclusion: Optional[str] = None
    key_numbers: List[Dict[str, str]] = field(default_factory=list)  # [{"label": "实际交付量", "value": "4,462辆"}]
    
    # === 全局状态 ===
    status: str = "running"             # running/success/failed/clarify/reject
    total_duration_ms: int = 0
    thinking_steps: List[ThinkingStep] = field(default_factory=list)
    error: Optional[ErrorInfo] = None
    
    def add_thinking_step(self, step: int, name: str, content: str, 
                          status: str = "done", duration_ms: int = 0):
        """添加思考链步骤"""
        self.thinking_steps.append(ThinkingStep(
            step=step,
            name=name,
            content=content,
            status=status,
            duration_ms=duration_ms
        ))
    
    def set_error(self, code: str, message: str, detail: str = "", 
                  suggestion: str = "", retries: int = 0):
        """设置错误状态"""
        self.error = ErrorInfo(
            code=code,
            message=message,
            detail=detail,
            suggestion=suggestion,
            retries=retries
        )
        self.status = "failed"
    
    def set_reject(self, reason: str, supported_domains: List[str] = None):
        """设置拒答状态"""
        if supported_domains is None:
            supported_domains = ["整车销售", "经营财务", "市场营销", "渠道经营", "库存管理"]
        self.set_error(
            code="OUT_OF_SCOPE",
            message=reason,
            suggestion=f"支持的业务域：{', '.join(supported_domains)}"
        )
        self.status = "reject"
    
    def set_clarify(self, question: str, options: List[Dict[str, str]]):
        """设置澄清状态"""
        self.error = ErrorInfo(
            code="CLARIFY_NEEDED",
            message=question,
            suggestion=""
        )
        self.clarify_options = options
        self.status = "clarify"
