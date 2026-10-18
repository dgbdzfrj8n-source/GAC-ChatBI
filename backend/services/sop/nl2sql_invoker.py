"""
NL2SQL 调用器（SDD-算法 §四）

复用现有 `workflow.orchestrator.Text2SQLWorkflow`，不通过 HTTP 自调用。
把 Workflow 的 async event 流解析为结构化 StepResult。

超时：30s
重试：1 次（避免整体 SOP 流程耗时过长）
"""

from __future__ import annotations
import asyncio
import time
import logging
from typing import Any, Dict, List, Optional

from services.sop.models import StepResult, StepExecutionError

logger = logging.getLogger(__name__)


class NL2SQLInvoker:
    """调用 Text2SQL Workflow 跑单步查询。"""

    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 1  # SOP 场景下重试 1 次

    def __init__(self, workflow=None):
        """
        Args:
            workflow: 注入式依赖，便于测试时 mock。默认懒加载。
        """
        self._workflow = workflow
        self._WorkflowContext = None  # 懒加载 workflow.context.WorkflowContext

    def _ensure_workflow(self):
        """懒加载 Workflow + Context 类。"""
        if self._workflow is None:
            from workflow.orchestrator import Text2SQLWorkflow
            from workflow.context import WorkflowContext
            self._workflow = Text2SQLWorkflow()
            self._WorkflowContext = WorkflowContext

    async def execute_with_retry(
        self,
        question: str,
        params: Dict[str, Any],
    ) -> StepResult:
        """带超时和重试的入口。"""
        last_error: Optional[Exception] = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    self.execute(question, params),
                    timeout=self.TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError:
                last_error = StepExecutionError(
                    f"查询超时（>{self.TIMEOUT_SECONDS}s），请简化问题后重试"
                )
                logger.warning("NL2SQLInvoker attempt %d timeout", attempt + 1)
            except StepExecutionError as e:
                last_error = e
                logger.warning("NL2SQLInvoker attempt %d error: %s", attempt + 1, e)
            except Exception as e:  # noqa: BLE001
                last_error = StepExecutionError(f"查询失败：{str(e)}")
                logger.exception("NL2SQLInvoker unexpected error")

        # 全部重试都失败
        raise last_error or StepExecutionError("查询失败")

    async def execute(self, question: str, params: Dict[str, Any]) -> StepResult:
        """
        调用一次 Workflow.run()，解析事件流为 StepResult。
        失败由 execute_with_retry 处理；这里只负责"单次执行"。
        """
        self._ensure_workflow()
        start = time.time()
        context = self._WorkflowContext(
            question=question,
            brand_filter=params.get("brand", "全部"),
            session_id=f"sop_step_{int(time.time() * 1000)}",
            user=params.get("user"),
        )

        try:
            events: List[Dict[str, Any]] = []
            async for event in self.workflow_run(context):
                events.append(event)
        except Exception as e:  # noqa: BLE001
            raise StepExecutionError(f"Workflow 执行异常：{e}")

        step_result = self._parse_events(events, context)
        step_result.duration_ms = int((time.time() - start) * 1000)
        return step_result

    async def workflow_run(self, context):
        """薄封装，便于 mock。"""
        async for event in self._workflow.run(context):
            yield event

    # ---- private ----

    def _parse_events(self, events: List[Dict[str, Any]], context) -> StepResult:
        """把 Workflow 的 SSE 事件解析为结构化 StepResult。

        事件类型（与 workflow/orchestrator.py ChatEvent 对齐）：
        - thinking_step
        - sql
        - result
        - chart
        - conclusion
        - error
        """
        thinking_steps: List[Dict[str, Any]] = []
        sql: Optional[str] = None
        result_data: Optional[Dict[str, Any]] = None
        chart_type: Optional[str] = None
        chart_config: Optional[Dict[str, Any]] = None
        conclusion: Optional[str] = None
        key_numbers: List[Dict[str, str]] = []

        for ev in events:
            event_type = ev.get("event")
            data = ev.get("data") or {}

            if event_type == "thinking_step":
                thinking_steps.append(data)
            elif event_type == "sql":
                sql = data.get("sql")
            elif event_type == "result":
                result_data = {
                    "columns": data.get("columns", []),
                    "rows": data.get("rows", []),
                }
            elif event_type == "chart":
                chart_type = data.get("chart_type")
                chart_config = {
                    "field_mapping": data.get("field_mapping"),
                    "config": data.get("config"),
                }
            elif event_type == "conclusion":
                conclusion = data.get("text")
                raw_kn = data.get("key_numbers") or []
                key_numbers = [
                    {"label": str(k.get("label", "")), "value": str(k.get("value", ""))}
                    for k in raw_kn
                    if isinstance(k, dict)
                ]
            elif event_type == "error":
                raise StepExecutionError(data.get("message", "Workflow 内部错误"))

        return StepResult(
            thinking_steps=thinking_steps,
            sql=sql,
            result=result_data,
            chart_type=chart_type,
            chart_config=chart_config,
            conclusion=conclusion,
            key_numbers=key_numbers,
        )
