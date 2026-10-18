"""
SOP 执行过程的统一数据模型。

- `StepResult`：单步执行结果（与前端 SDD §三 TypeScript StepResult 字段对齐）
- `Summary`：SOP 完成后聚合的总结
- `StepExecutionError`：单步执行异常（用于上层捕获 + 标记 failed）
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class StepExecutionError(Exception):
    """SOP 单步执行错误。捕获后转 StepResult(status='failed', error=...)"""
    message: str
    step_index: Optional[int] = None

    def __str__(self) -> str:
        return f"StepExecutionError(step_index={self.step_index}): {self.message}"


@dataclass
class StepResult:
    """单步执行结果（与前端 TypeScript `StepResult` 字段一致）。"""
    step_name: str = ""
    step_type: str = ""                              # overview/horizontal/drilldown/breakdown/trend/strategy
    status: str = "success"                          # success / failed / skipped
    replaced_question: Optional[str] = None
    thinking_steps: List[Dict[str, Any]] = field(default_factory=list)
    sql: Optional[str] = None
    result: Optional[Dict[str, Any]] = None          # {columns: [...], rows: [[...], ...]}
    chart_type: Optional[str] = None                  # single_kpi/bar/line/pie/table/text
    chart_config: Optional[Dict[str, Any]] = None
    conclusion: Optional[str] = None
    key_numbers: List[Dict[str, str]] = field(default_factory=list)  # [{label, value}]
    suggestions: List[str] = field(default_factory=list)             # 仅 strategy 步骤用
    error: Optional[str] = None
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转为 dict，供 FastAPI 返回 + 存 DuckDB JSON 字段。"""
        return asdict(self)

    @classmethod
    def failed(cls, step_name: str, step_type: str, error_msg: str,
               duration_ms: int = 0) -> "StepResult":
        """工厂方法：构造一个失败结果。"""
        return cls(
            step_name=step_name,
            step_type=step_type,
            status="failed",
            error=error_msg,
            duration_ms=duration_ms,
        )

    @classmethod
    def skipped(cls, step_name: str, step_type: str) -> "StepResult":
        """工厂方法：用户跳过。"""
        return cls(
            step_name=step_name,
            step_type=step_type,
            status="skipped",
            duration_ms=0,
        )


@dataclass
class Summary:
    """SOP 全部步骤完成后聚合的总结。"""
    template_name: str = ""
    total_duration_ms: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    findings: List[str] = field(default_factory=list)              # 每步 1 句话
    key_numbers: List[Dict[str, str]] = field(default_factory=list)  # 去重前 6 个
    suggestions: List[str] = field(default_factory=list)            # strategy 步骤的建议

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
