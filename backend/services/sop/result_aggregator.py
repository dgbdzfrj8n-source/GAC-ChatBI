"""
结果聚合器（SDD-算法 §六）

SOP 全部步骤完成后，把多个 StepResult 聚合成 Summary：
- 每步第 1 句结论 → findings
- 所有 key_numbers 去重取前 6 个
- 统计 success/failed/skipped
- 汇总 strategy 步骤的 suggestions
"""

from __future__ import annotations
from typing import List, Dict, Any

from services.sop.models import StepResult, Summary


class ResultAggregator:
    """SOP 多步结果 → Summary。"""

    MAX_FINDINGS = 10
    MAX_KEY_NUMBERS = 6

    def summarize(
        self,
        step_results: List[StepResult],
        template_name: str = "",
    ) -> Summary:
        findings: List[str] = []
        for i, r in enumerate(step_results):
            if r.status != "success" or not r.conclusion:
                continue
            first_sentence = self._first_sentence(r.conclusion)
            findings.append(f"{i + 1}. {first_sentence}")
            if len(findings) >= self.MAX_FINDINGS:
                break

        all_key_numbers: List[Dict[str, str]] = []
        seen_labels = set()
        for r in step_results:
            for kn in (r.key_numbers or []):
                label = kn.get("label", "")
                if not label or label in seen_labels:
                    continue
                seen_labels.add(label)
                all_key_numbers.append({"label": label, "value": kn.get("value", "")})
                if len(all_key_numbers) >= self.MAX_KEY_NUMBERS:
                    break
            if len(all_key_numbers) >= self.MAX_KEY_NUMBERS:
                break

        all_suggestions: List[str] = []
        for r in step_results:
            if r.step_type == "strategy" and r.status == "success":
                for s in (r.suggestions or []):
                    if s and s not in all_suggestions:
                        all_suggestions.append(s)

        success_count = sum(1 for r in step_results if r.status == "success")
        failed_count = sum(1 for r in step_results if r.status == "failed")
        skipped_count = sum(1 for r in step_results if r.status == "skipped")
        total_duration = sum(r.duration_ms or 0 for r in step_results)

        return Summary(
            template_name=template_name,
            total_duration_ms=total_duration,
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            findings=findings,
            key_numbers=all_key_numbers,
            suggestions=all_suggestions,
        )

    def _first_sentence(self, text: str) -> str:
        """取第一个完整句子（按中文句号/问号/感叹号切分）。"""
        if not text:
            return ""
        text = text.strip()
        for sep in ("。", "！", "？", ".", "!", "?"):
            idx = text.find(sep)
            if idx > 0:
                return text[: idx + 1]
        return text
