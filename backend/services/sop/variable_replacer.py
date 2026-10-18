"""
变量替换器（SDD-算法 §二）

支持的占位符：
  {{brand}}        - params.brand             ("全部" 时替换为 "全集团")
  {{time}}         - params.time_range        (按 _normalize_time 转自然语言)
  {{region}}       - params.region            ("全部" 时替换为 "各区域")
  {{metric}}       - template.metric_key      (从 semantic_v2.json 查中文名)
  {{prev_result}}  - DependencyResolver 输出  (可能为 None)
"""

from __future__ import annotations
import re
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.semantic_service import SemanticService


class VariableReplacer:
    """单步查询模板的变量替换。"""

    # 快捷时间选项 → 自然语言
    TIME_QUICK_MAP: Dict[str, str] = {
        "本月": "本月",
        "上月": "上个月",
        "本季度": "本季度",
        "上季度": "上一季度",
        "今年": "今年",
        "去年": "去年",
    }

    # 匹配任意 {{xxx}} 占位符
    PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")

    def __init__(self, semantic_service: Optional["SemanticService"] = None):
        # 允许缺省 semantic_service（仅在替换 {{metric}} 时报错）
        self.semantic = semantic_service

    def replace(
        self,
        query_template: str,
        params: Dict,
        prev_result: Optional[str] = None,
    ) -> str:
        """同步执行所有占位符替换。

        Args:
            query_template: 模板中的自然语言查询串，如 "{{time}} {{brand}}的{{metric}}"
            params: 运行参数 dict，至少包含 brand/time_range/region，可选 metric_key
            prev_result: 上一步提取出的关键实体（品牌/区域名）

        Returns:
            替换完成后的完整自然语言问题
        """
        ctx = {
            "brand": params.get("brand", "全部"),
            "time_range": params.get("time_range", "上季度"),
            "region": params.get("region", "全部"),
            "metric_key": params.get("metric_key", "delivered_units"),
            "prev_result": prev_result,
        }
        return self.PLACEHOLDER_RE.sub(lambda m: self._resolve(m.group(1), ctx), query_template)

    def _resolve(self, name: str, ctx: Dict) -> str:
        """占位符 → 实际值。未知占位符原样保留便于调试。"""
        if name == "brand":
            return "全集团" if ctx["brand"] == "全部" else ctx["brand"]
        if name == "time":
            return self._normalize_time(ctx["time_range"])
        if name == "region":
            return "各区域" if ctx["region"] == "全部" else f'{ctx["region"]}区域'
        if name == "metric":
            return self._resolve_metric(ctx["metric_key"])
        if name == "prev_result":
            prev = ctx.get("prev_result")
            return prev if prev else "全部品牌"
        # 未知变量：原样返回，让 LLM 自行处理（不静默吞错）
        return f"{{{{{name}}}}}"

    def _resolve_metric(self, metric_key: str) -> str:
        """metric_key → 中文名。从语义层查；查不到时给个保底显示。"""
        if self.semantic is None:
            return metric_key
        try:
            name = self.semantic.get_metric_name(metric_key)
            return name or metric_key
        except Exception:
            return metric_key

    def _normalize_time(self, time_range: str) -> str:
        """快捷时间选项 → 自然语言。原值透传（用户可能直接传 "2025Q2"）。"""
        return self.TIME_QUICK_MAP.get(time_range, time_range)
