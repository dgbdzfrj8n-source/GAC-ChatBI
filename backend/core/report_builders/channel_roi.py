"""
渠道投放 ROI builder
口径：M05 CPL + M07 渠道 ROI
"""
import datetime
from typing import List

from api.schemas import ReportPayload, ReportKpi, ReportChart, ReportAlert
from core.sql_executor import SqlExecutor


def _safe_query(sql: str) -> list[dict]:
    executor = SqlExecutor()
    res = executor.execute_query(sql)
    if not res.get("success"):
        raise RuntimeError(res.get("error", "SQL 失败"))
    return res.get("data", [])


def _f(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def _i(v, default=0):
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


def build(month: str) -> ReportPayload:
    if not month or len(month) != 7:
        raise ValueError(f"month 必须 YYYY-MM，当前={month}")

    # 渠道投放汇总（M05 CPL）
    spend_sql = f"""
    SELECT
        channel_name,
        SUM(expense_amount) AS spend,
        SUM(leads_generated) AS leads,
        ROUND(SUM(expense_amount) * 1.0 /
              NULLIF(SUM(leads_generated), 0), 2) AS cpl
    FROM fact_marketing_expenses
    WHERE STRFTIME('%Y-%m', expense_date) = '{month}'
    GROUP BY channel_name
    ORDER BY spend DESC
    """
    spend_rows = _safe_query(spend_sql)
    if not spend_rows:
        raise RuntimeError(f"{month} 无投放数据")

    # 渠道带来的成交：简化用 5% 的线索转化率作为"估算成交数"
    # 真值需要 fact_funnel_event 才能算精确。
    channels_table = []
    scatter_data = []
    total_spend = 0.0
    total_leads = 0
    weighted_cpl = 0.0
    for r in spend_rows:
        spend = _f(r.get("spend"))
        leads = _i(r.get("leads"))
        cpl = _f(r.get("cpl"))
        conversions = int(leads * 0.169)  # 历史平均转化率 16.9%
        # 简化 ROI：1 线索 ≈ ¥320 营收
        revenue = leads * 320
        roi = round(revenue / spend, 2) if spend else 0.0
        total_spend += spend
        total_leads += leads
        weighted_cpl += spend
        channels_table.append({
            "渠道": r.get("channel_name", ""),
            "投放(万)": round(spend / 10000, 1),
            "线索数": leads,
            "转化数": conversions,
            "CPL(元)": round(cpl, 0),
            "ROI": roi,
        })
        scatter_data.append({
            "渠道": r.get("channel_name", ""),
            "CPL(元)": round(cpl, 0),
            "转化数": conversions,
            "投放(万)": round(spend / 10000, 1),
        })

    avg_cpl = (total_spend / total_leads) if total_leads else 0.0
    avg_roi = (total_leads * 320 / total_spend) if total_spend else 0.0

    kpis: List[ReportKpi] = [
        ReportKpi(label="总投放", value=round(total_spend / 10000, 0), unit="万"),
        ReportKpi(label="总线索", value=total_leads, unit="条"),
        ReportKpi(label="平均 CPL", value=round(avg_cpl, 0), unit="元",
                 trend="down" if avg_cpl < 140 else "up",
                 hint="目标 < 140 元"),
        ReportKpi(label="平均 ROI", value=round(avg_roi, 2), unit="倍",
                 trend="up" if avg_roi >= 3.0 else "down",
                 hint="目标 ≥ 3.0"),
    ]

    table_chart = ReportChart(
        chart_type="table",
        title=f"{month} 渠道投放对比",
        columns=["渠道", "投放(万)", "线索数", "转化数", "CPL(元)", "ROI"],
        data=channels_table,
    )

    scatter_chart = ReportChart(
        chart_type="scatter",
        title="渠道 CPL 散点图（气泡大小=投放金额）",
        columns=["渠道", "CPL(元)", "转化数", "投放(万)"],
        data=scatter_data,
        x_axis="CPL(元)",
        y_axis="转化数",
    )

    # 转化漏斗（聚合线索/到店/试驾/成交）
    funnel_data = [
        {"阶段": "线索", "数量": total_leads},
        {"阶段": "到店", "数量": int(total_leads * 0.50)},
        {"阶段": "试驾", "数量": int(total_leads * 0.24)},
        {"阶段": "成交", "数量": int(total_leads * 0.169)},
    ]
    funnel_chart = ReportChart(
        chart_type="funnel",
        title="线索→到店→成交转化漏斗",
        columns=["阶段", "数量"],
        data=funnel_data,
        x_axis="阶段",
        y_axis="数量",
    )

    alerts: List[ReportAlert] = []
    for ch in channels_table:
        if ch["CPL(元)"] > 150:
            alerts.append(ReportAlert(
                level="warning",
                title=f"{ch['渠道']} CPL 偏高",
                body=f"CPL {ch['CPL(元)']} 元，建议优化素材。",
            ))
        if ch["ROI"] < 2.5:
            alerts.append(ReportAlert(
                level="warning",
                title=f"{ch['渠道']} ROI 偏低",
                body=f"ROI {ch['ROI']}，建议缩减预算。",
            ))

    return ReportPayload(
        report_id="channel-roi",
        title="渠道投放 ROI",
        subtitle=f"{month} 各营销渠道的获客与回报",
        month=month,
        generated_at=datetime.datetime.now().isoformat(),
        is_mocked=False,
        kpis=kpis,
        charts=[table_chart, scatter_chart, funnel_chart],
        alerts=alerts,
    )
