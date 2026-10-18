"""
步骤编排器（SDD-算法 §七）

对外暴露 `execute_step(run_id, step_index, params)`，是后端 API 唯一调用的入口。
把"读配置 + 变量替换 + 依赖解析 + 调用 NL2SQL/Strategy + 写回 run + 返回结果"串成一条线。
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional, Protocol

from services.sop.models import StepResult, StepExecutionError
from services.sop.variable_replacer import VariableReplacer
from services.sop.dependency_resolver import DependencyResolver
from services.sop.nl2sql_invoker import NL2SQLInvoker
from services.sop.strategy_generator import StrategyGenerator

logger = logging.getLogger(__name__)


class _TemplateRepo(Protocol):
    """后端服务实现的接口（duck-typed 协议，方便后端阶段填实现）。"""
    def get_with_steps(self, template_id: str): ...


class _RunRepo(Protocol):
    def get(self, run_id: str): ...
    def update(self, run) -> None: ...


class StepOrchestrator:
    """SOP 步骤编排器。"""

    def __init__(
        self,
        template_repo: _TemplateRepo,
        run_repo: _RunRepo,
        nl2sql_invoker: Optional[NL2SQLInvoker] = None,
        strategy_generator: Optional[StrategyGenerator] = None,
        variable_replacer: Optional[VariableReplacer] = None,
        dependency_resolver: Optional[DependencyResolver] = None,
        semantic_service=None,
    ):
        self.template_repo = template_repo
        self.run_repo = run_repo
        self.replacer = variable_replacer or VariableReplacer(semantic_service)
        self.dependency = dependency_resolver or DependencyResolver()
        self.nl2sql = nl2sql_invoker or NL2SQLInvoker()
        self.strategy_gen = strategy_generator or StrategyGenerator()

    async def execute_step(
        self,
        run_id: str,
        step_index: int,
        params: Dict[str, Any],
    ) -> StepResult:
        """
        执行 SOP 的某一步。
        - 自动做变量替换 + 依赖解析
        - 失败捕获后转 StepResult(status='failed', error=...)，不抛异常到 API 层
        """
        run = self.run_repo.get(run_id)
        if run is None:
            return StepResult.failed(
                step_name="", step_type="",
                error_msg=f"运行记录不存在：run_id={run_id}",
            )
        if run.status == "completed":
            return StepResult.failed(
                step_name="", step_type="",
                error_msg="该运行已完成，如需重新执行请创建新运行",
            )

        template = self.template_repo.get_with_steps(run.template_id)
        if template is None:
            return StepResult.failed(
                step_name="", step_type="",
                error_msg=f"模板不存在：template_id={run.template_id}",
            )
        if step_index < 0 or step_index >= len(template.steps):
            return StepResult.failed(
                step_name="", step_type="",
                error_msg=f"步骤序号越界：step_index={step_index}, 共{len(template.steps)}步",
            )

        step = template.steps[step_index]
        step_name = step.get("step_name") if isinstance(step, dict) else step.step_name
        step_type = step.get("step_type") if isinstance(step, dict) else step.step_type
        query_template = (
            step.get("query_template") if isinstance(step, dict) else step.query_template
        )

        # ---- 变量替换 ----
        prev_result = None
        prev_step_result = None
        if step_index > 0:
            prev_step_result_dict = (
                run.step_results[step_index - 1] if run.step_results else None
            )
            prev_result = self.dependency.extract_prev_result(
                prev_step_result_dict, step_type
            )
        replaced_question = self.replacer.replace(
            query_template,
            {**params, "metric_key": template.metric_key},
            prev_result=prev_result,
        )

        # ---- 执行（按 step_type 分支） ----
        try:
            if step_type == "strategy":
                # 策略步骤：基于前几步结论生成建议
                previous_results = self._rebuild_step_results(run.step_results[:step_index])
                result = await self.strategy_gen.generate(previous_results, template.name)
            else:
                # 普通步骤：调用 NL2SQL
                result = await self.nl2sql.execute_with_retry(replaced_question, params)

            result.status = "success"
            result.step_name = step_name
            result.step_type = step_type
            result.replaced_question = replaced_question

            # 依赖兜底备注
            if (
                step_index > 0
                and prev_result is None
                and self._template_uses_prev(query_template)
            ):
                result.thinking_steps = [
                    self.dependency.make_warning_note(
                        self.dependency._default_for_step_type(step_type) or "全部品牌"
                    ),
                    *result.thinking_steps,
                ]

        except StepExecutionError as e:
            logger.warning("SOP step %d failed: %s", step_index, e)
            result = StepResult.failed(step_name, step_type, str(e))

        # ---- 写回 run ----
        if run.step_results is None:
            run.step_results = []
        # 保证数组长度足够
        while len(run.step_results) <= step_index:
            run.step_results.append(None)
        run.step_results[step_index] = result.to_dict()
        self.run_repo.update(run)

        return result

    # ---- private ----

    def _rebuild_step_results(self, dicts: List[Optional[Dict]]) -> List[StepResult]:
        """把存进 DuckDB 的 dict 列表还原为 StepResult 对象。"""
        results: List[StepResult] = []
        for d in dicts:
            if d is None:
                results.append(StepResult())
                continue
            try:
                results.append(StepResult(**d))
            except TypeError:
                # 字段不匹配时退化为空对象
                results.append(StepResult(step_name=d.get("step_name", "")))
        return results

    def _template_uses_prev(self, query_template: str) -> bool:
        return "{{prev_result}}" in (query_template or "")
