"""
步骤间依赖解析器（SDD-算法 §三）

从"上一步结果"中提取关键实体（品牌名/区域名），注入到下一步的 {{prev_result}}。

3 层策略：
  1. 从结论文本正则匹配品牌/区域关键词（最长优先）
  2. 从结果数据第一行第一列取（如排名类查询）
  3. 根据 step_type 给默认值

提取失败不阻断 SOP，思考链里加 DEPENDENCY_WARNING 提示。
"""

from __future__ import annotations
import re
from typing import Optional, Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from services.sop.models import StepResult


class DependencyResolver:
    """从 StepResult 中提取 {{prev_result}} 实体。"""

    # 关键词列表（按从长到短排序，优先匹配"广汽埃安"而非"埃安"）
    BRAND_KEYWORDS: List[str] = [
        "广汽埃安", "广汽传祺", "广汽昊铂",
        "埃安", "传祺", "昊铂",
    ]
    REGION_KEYWORDS: List[str] = [
        "华东", "华南", "华北", "西南", "华中", "东北", "西北",
    ]
    MODEL_KEYWORDS: List[str] = [
        "影豹", "GS8", "M8", "AION S", "AION Y", "AION V",
    ]

    def extract_prev_result(
        self,
        prev_step_result: Optional[Dict[str, Any]],
        step_type: str,
    ) -> Optional[str]:
        """
        Args:
            prev_step_result: 上一步的 dict（来自 StepResult.to_dict()）
            step_type: 当前步骤的 step_type（用于决定兜底默认值）

        Returns:
            提取到的实体字符串；提取失败返回 None（VariableReplacer 会兜底）
        """
        if not prev_step_result:
            return None
        if prev_step_result.get("status") not in ("success",):
            # 失败的步骤不提取，避免把错误信息当成实体
            return None

        # 策略 1：从结论文本匹配
        conclusion = prev_step_result.get("conclusion") or ""
        entity = self._extract_from_text(conclusion)
        if entity:
            return entity

        # 策略 2：从结果数据第一行第一列取
        result = prev_step_result.get("result") or {}
        rows = result.get("rows") or []
        if rows and len(rows) > 0:
            first_value = rows[0][0] if rows[0] else None
            if first_value and self._is_valid_entity(str(first_value)):
                return str(first_value)

        # 策略 3：兜底按 step_type
        return self._default_for_step_type(step_type)

    def make_warning_note(self, used_default: str) -> Dict[str, Any]:
        """生成 DEPENDENCY_WARNING 备注，供 thinking_steps 展示。"""
        return {
            "step": 0,
            "name": "依赖解析",
            "content": (
                f"未从上一步结果提取到具体实体，使用默认值「{used_default}」。"
                "建议手动核对上一步结论是否包含品牌/区域名。"
            ),
            "status": "warning",
            "duration_ms": 0,
        }

    # ---- private ----

    def _extract_from_text(self, text: str) -> Optional[str]:
        """从结论文本中提取第一个出现的实体关键词。"""
        if not text:
            return None
        # 把所有候选打平，按"出现位置最早"原则取
        candidates = self.BRAND_KEYWORDS + self.REGION_KEYWORDS + self.MODEL_KEYWORDS
        positions = []
        for kw in candidates:
            idx = text.find(kw)
            if idx >= 0:
                positions.append((idx, kw))
        if not positions:
            return None
        positions.sort()
        return positions[0][1]

    def _is_valid_entity(self, value: str) -> bool:
        """判断一个字符串是否像一个实体名（不是数字/日期/百分比）。"""
        if not value or not value.strip():
            return False
        v = value.strip()
        if v.isdigit():
            return False
        # 纯百分比数字
        if v.endswith("%") and v[:-1].replace(".", "").isdigit():
            return False
        # 日期：YYYY-MM-DD 或 YYYY/MM/DD
        if re.match(r"^\d{4}[-/]\d{1,2}([-/]\d{1,2})?$", v):
            return False
        # 全是数字 + 逗号/点（千分位数字）
        if re.match(r"^[\d,.]+$", v):
            return False
        return True

    def _default_for_step_type(self, step_type: str) -> Optional[str]:
        """提取失败时的兜底。返回 None 表示 VariableReplacer 不替换该占位符。"""
        defaults = {
            "drilldown": "全部品牌",
            "breakdown": "全部",
            "trend": "全集团",
        }
        return defaults.get(step_type)
