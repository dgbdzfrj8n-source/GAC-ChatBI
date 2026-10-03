"""
报表中心执行器 (Sprint 8)
核心职责：
1. 注册 6 张报表的 builder；
2. 路由 report_id → 对应 builder；
3. 统一错误处理：SQL 失败 → 自动降级到 Mock 数据；
4. 提供静态 registry 元数据供前端渲染卡片列表。

设计原则：
- 任何 2 张报表不允许共用 SQL/builder（保证每张报表的"业务问题"独立）；
- 所有 SQL 走 SQLExecutor 的只读安全校验；
- 失败时优雅降级，不让任何一张报表点不开。
"""
import os
import json
import datetime
import logging
from typing import Callable, Dict

from api.schemas import ReportPayload

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
MOCKS_DIR = os.path.join(BACKEND_DIR, "report_mocks")

# ── 报表元数据 (Registry) ──────────────────────────────────────
REGISTRY: list[dict] = [
    {
        "report_id": "budget-fulfillment",
        "name": "预算达成分析",
        "category": "整车销售",
        "description": "本月各品牌预算完成进度、达成率分布与弱项明细",
        "icon": "🎯",
        "status": "ready",
        "estimated_sprint": "Sprint 8.1",
    },
    {
        "report_id": "sales-attribution",
        "name": "销量归因分析",
        "category": "整车销售",
        "description": "销量同比/环比波动的多维根因：渠道/大区/价格带瀑布图",
        "icon": "📈",
        "status": "ready",
        "estimated_sprint": "Sprint 8.1",
    },
    {
        "report_id": "channel-roi",
        "name": "渠道投放 ROI",
        "category": "市场营销",
        "description": "各营销渠道的获客成本 (CPL)、转化率与投资回报率",
        "icon": "💰",
        "status": "ready",
        "estimated_sprint": "Sprint 8.1",
    },
    {
        "report_id": "inventory-warning",
        "name": "库存预警",
        "category": "库存管理",
        "description": "经销商库存周转天数、库存系数与高库存预警",
        "icon": "📦",
        "status": "ready",
        "estimated_sprint": "Sprint 8.1",
    },
    {
        "report_id": "conversion-funnel",
        "name": "客流转化漏斗",
        "category": "渠道经营",
        "description": "进店→留资→试驾→成交 4 级漏斗转化分析",
        "icon": "🌪️",
        "status": "ready",
        "estimated_sprint": "Sprint 8.1",
    },
    {
        "report_id": "regional-ranking",
        "name": "大区销售排行",
        "category": "整车销售",
        "description": "5 大区业绩多维对比 + 12 月趋势",
        "icon": "🏆",
        "status": "ready",
        "estimated_sprint": "Sprint 8.1",
    },
]


def list_registry() -> list[dict]:
    return REGISTRY


# ── ReportExecutor：路由 + 降级 ────────────────────────────────
class ReportExecutor:
    """
    单例执行器：
    - 启动时 import 6 个 builder，注册到 BUILDER_MAP；
    - execute(report_id, month) 返回 ReportPayload；
    - 任意 builder 抛异常 → 自动降级到 Mock。
    """

    def __init__(self) -> None:
        self._builders: Dict[str, Callable[[str], ReportPayload]] = {}
        self._register_all()

    def _register_all(self) -> None:
        from core.report_builders.budget_fulfillment import build as bf
        from core.report_builders.sales_attribution import build as sa
        from core.report_builders.channel_roi import build as cr
        from core.report_builders.inventory_warning import build as iw
        from core.report_builders.conversion_funnel import build as cf
        from core.report_builders.regional_ranking import build as rr

        self._builders = {
            "budget-fulfillment": bf,
            "sales-attribution": sa,
            "channel-roi": cr,
            "inventory-warning": iw,
            "conversion-funnel": cf,
            "regional-ranking": rr,
        }

    def execute(self, report_id: str, month: str) -> ReportPayload:
        """
        执行报表：
        1. report_id 不在 map → 抛 404；
        2. builder 抛异常 → 降级到 Mock (is_mocked=True)；
        3. 正常返回 builder 真实结果 (is_mocked=False)。
        """
        if report_id not in self._builders:
            raise KeyError(f"未知报表 ID: {report_id}")

        try:
            payload = self._builders[report_id](month)
            return payload
        except Exception as e:
            logger.exception(
                f"报表 {report_id} 在月份 {month} 执行失败，降级到 Mock: {e}"
            )
            return self._load_mock(report_id, month)

    def _load_mock(self, report_id: str, month: str) -> ReportPayload:
        """从 backend/report_mocks/{report_id}.json 读取 Mock 数据。"""
        mock_path = os.path.join(MOCKS_DIR, f"{report_id.replace('-', '_')}.json")
        if not os.path.exists(mock_path):
            # Mock 也不存在 → 返回一个最简兜底
            return ReportPayload(
                report_id=report_id,
                title=report_id,
                subtitle="(Mock 数据缺失)",
                month=month,
                generated_at=datetime.datetime.now().isoformat(),
                is_mocked=True,
                kpis=[],
                charts=[],
                alerts=[
                    {
                        "level": "alert",
                        "title": "Mock 数据缺失",
                        "body": f"找不到 {mock_path}，请补充。",
                    }
                ],
            )
        with open(mock_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # 同步 month 字段（Mock 是写死的 2025-03，但前端可能请求别的月份）
        raw["month"] = month
        raw["is_mocked"] = True
        raw["generated_at"] = datetime.datetime.now().isoformat()
        return ReportPayload(**raw)


# 模块级单例
report_executor = ReportExecutor()
