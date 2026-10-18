"""
归因模板 SOP 执行算法包
============================

按 SDD-算法 v2.0 文档实现，6 个核心类：

- `StepResult` / `Summary`：统一数据模型
- `VariableReplacer`：`{{brand}}/{{time}}/{{region}}/{{prev_result}}/{{metric}}` 替换
- `DependencyResolver`：从上一步结果提取关键实体（品牌/区域）
- `NL2SQLInvoker`：调用现有 `Text2SQLWorkflow.run()` 并解析事件流
- `StrategyGenerator`：基于前几步结论，让大模型生成 3 条策略建议
- `ResultAggregator`：聚合多步结果生成 Summary
- `StepOrchestrator`：编排一切，对外暴露 `execute_step(run_id, step_index, params)`

设计原则：
1. 复用 `workflow.orchestrator.Text2SQLWorkflow`，**不重新实现 NL2SQL**
2. 同步返回 StepResult（不是 SSE 流），方便写入 DuckDB
3. 单步失败不阻断整体，由前端决定重试 / 跳过
4. DuckDB 作为数据底座（与 .cursorrules 一致）
"""

from .models import StepResult, Summary, StepExecutionError
from .variable_replacer import VariableReplacer
from .dependency_resolver import DependencyResolver
from .nl2sql_invoker import NL2SQLInvoker
from .strategy_generator import StrategyGenerator
from .result_aggregator import ResultAggregator
from .step_orchestrator import StepOrchestrator

__all__ = [
    "StepResult",
    "Summary",
    "StepExecutionError",
    "VariableReplacer",
    "DependencyResolver",
    "NL2SQLInvoker",
    "StrategyGenerator",
    "ResultAggregator",
    "StepOrchestrator",
]
