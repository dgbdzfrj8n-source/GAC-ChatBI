"""
策略建议生成器（SDD-算法 §五）

strategy 步骤不执行 SQL，把前几步 conclusion 喂给大模型，让它生成 3 条策略建议。
失败时给模板兜底，避免 SOP 在最后一步崩掉。
"""

from __future__ import annotations
import json
import logging
from typing import List, Dict, Any, Optional

from services.sop.models import StepResult

logger = logging.getLogger(__name__)


class StrategyGenerator:
    """基于前几步结论生成策略建议。"""

    PROMPT_TEMPLATE = """你是广汽集团的资深经营分析师。基于以下归因分析发现，给出 3 条具体、可执行的策略建议。

【分析模板】{template_name}
【分析发现】
{conclusions_block}

要求：
1. 每条建议必须针对上面的具体发现，不泛泛而谈
2. 建议要具体到动作（如「加大 XX 区域的营销投入」，不是「加强管理」）
3. 按优先级排序，最重要的放第一条
4. 同时提取 3~5 个关键数字列表（label + value）

只返回严格 JSON（不要 markdown 代码块），格式：
{{"conclusion":"3 条建议的汇总文字","key_numbers":[{{"label":"标签","value":"数值"}}],"suggestions":["建议 1","建议 2","建议 3"]}}"""

    FALLBACK_CONCLUSION = "建议进一步分析以上发现，制定针对性改进措施。"
    FALLBACK_SUGGESTIONS = [
        "针对表现最弱的维度开展专题分析",
        "对比同期数据，定位具体下滑原因",
        "对关键责任区域/品牌/车型下达改进目标",
    ]

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: 注入式 LLM 客户端。需有 `async chat(prompt) -> str` 接口。
                        默认懒加载（core.llm_client.ChatCompletionClient）。
        """
        self._llm = llm_client

    def _ensure_llm(self):
        if self._llm is None:
            from core.llm_client import ChatCompletionClient
            self._llm = ChatCompletionClient()

    async def generate(
        self,
        previous_results: List[StepResult],
        template_name: str,
    ) -> StepResult:
        """生成策略建议。

        Args:
            previous_results: 之前所有步骤的 StepResult 列表（仅取 conclusion 字段）
            template_name: 模板名称（喂给 LLM 当上下文）
        """
        conclusions_block = self._build_conclusions_block(previous_results)
        prompt = self.PROMPT_TEMPLATE.format(
            template_name=template_name,
            conclusions_block=conclusions_block,
        )

        try:
            self._ensure_llm()
            raw = await self._llm.chat(prompt)
            parsed = self._parse_json_response(raw)
        except Exception as e:  # noqa: BLE001
            logger.warning("StrategyGenerator 失败，使用兜底: %s", e)
            return self._fallback_result()

        return StepResult(
            thinking_steps=[{
                "step": 0,
                "name": "策略生成",
                "content": "基于前几步结论生成策略建议",
                "status": "done",
                "duration_ms": 0,
            }],
            sql=None,
            result=None,
            chart_type="text",
            chart_config=None,
            conclusion=parsed.get("conclusion") or self.FALLBACK_CONCLUSION,
            key_numbers=parsed.get("key_numbers") or [],
            suggestions=parsed.get("suggestions") or self.FALLBACK_SUGGESTIONS,
        )

    def _build_conclusions_block(self, previous_results: List[StepResult]) -> str:
        """把前几步结论拼成 LLM 易读的文本块。"""
        lines = []
        for i, r in enumerate(previous_results):
            if r.status == "success" and r.conclusion:
                lines.append(f"第 {i + 1} 步（{r.step_name}）：{r.conclusion}")
        if not lines:
            lines.append("（前序步骤无有效结论）")
        return "\n".join(lines)

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """LLM 返回可能包了 markdown ```json 块，做清洗。"""
        if not raw:
            return {}
        text = raw.strip()
        # 去掉 markdown 包裹
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("StrategyGenerator JSON 解析失败: %s, raw=%s", e, raw[:200])
            return {}

    def _fallback_result(self) -> StepResult:
        return StepResult(
            thinking_steps=[{
                "step": 0,
                "name": "策略生成",
                "content": "LLM 调用失败，使用模板兜底建议",
                "status": "warning",
                "duration_ms": 0,
            }],
            sql=None,
            result=None,
            chart_type="text",
            chart_config=None,
            conclusion=self.FALLBACK_CONCLUSION,
            key_numbers=[],
            suggestions=list(self.FALLBACK_SUGGESTIONS),
        )
