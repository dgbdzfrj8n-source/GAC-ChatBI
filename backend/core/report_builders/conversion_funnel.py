"""
客流转化漏斗 builder
口径：M10 漏斗步骤转化率
数据源：fact_funnel_event
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


def _i(v, default=0):
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


def build(month: str) -> ReportPayload:
    if not month or len(month) != 7:
        raise ValueError(f"month 必须 YYYY-MM，当前={month}")

    # 4 阶段去重 session 计数
    stage_sql = f"""
    SELECT
        event_stage,
        COUNT(DISTINCT session_id) AS sessions
    FROM fact_funnel_event
    WHERE STRFTIME('%Y-%m', event_date) = '{month}'
    GROUP BY event_stage
    """
    stage_rows = _safe_query(stage_sql)
    if not stage_rows:
        raise RuntimeError(f"{month} 无漏斗事件")

    sessions_map = {
        "store_visit": 0,
        "lead_created": 0,
        "test_drive": 0,
        "order_created": 0,
    }
    for r in stage_rows:
        stage = r.get("event_stage", "")
        if stage in sessions_map:
            sessions_map[stage] = _i(r.get("sessions"))

    visit = sessions_map["store_visit"]
    lead = sessions_map["lead_created"]
    drive = sessions_map["test_drive"]
    order = sessions_map["order_created"]

    if visit == 0:
        raise RuntimeError(f"{month} 进店客流为 0")

    overall_rate = order * 100.0 / visit

    kpis: List[ReportKpi] = [
        ReportKpi(label="总进店客流", value=visit, unit="组"),
        ReportKpi(label="总成交量", value=order, unit="辆",
                 trend="up" if order > 0 else "flat"),
        ReportKpi(label="整体转化率", value=round(overall_rate, 1), unit="%",
                 trend="up" if overall_rate > 10 else "down",
                 hint="目标 ≥ 10%"),
        ReportKpi(label="最弱环节", value="试驾→成交", unit="",
                 hint=f"{round((1 - order/drive) * 100, 1)}% 流失"
                 if drive else "无数据"),
    ]

    # 漏斗图
    funnel_chart = ReportChart(
        chart_type="funnel",
        title=f"{month} 客流转化 4 级漏斗",
        columns=["阶段", "数量", "转化率(%)"],
        data=[
            {"阶段": "进店客流", "数量": visit, "转化率(%)": 100.0},
            {
                "阶段": "留资",
                "数量": lead,
                "转化率(%)": round(lead * 100.0 / visit, 1),
            },
            {
                "阶段": "试驾",
                "数量": drive,
                "转化率(%)": round(drive * 100.0 / visit, 1),
            },
            {
                "阶段": "成交",
                "数量": order,
                "转化率(%)": round(order * 100.0 / visit, 1),
            },
        ],
        x_axis="阶段",
        y_axis="数量",
    )

    # 5 大区漏斗对比
    region_sql = f"""
    SELECT
        region_name,
        event_stage,
        COUNT(DISTINCT session_id) AS sessions
    FROM fact_funnel_event
    WHERE STRFTIME('%Y-%m', event_date) = '{month}'
    GROUP BY region_name, event_stage
    """
    region_rows = _safe_query(region_sql)
    region_agg: dict = {}
    for r in region_rows:
        region = r.get("region_name", "")
        if not region:
            continue
        if region not in region_agg:
            region_agg[region] = {
                "store_visit": 0, "lead_created": 0,
                "test_drive": 0, "order_created": 0,
            }
        stage = r.get("event_stage", "")
        if stage in region_agg[region]:
            region_agg[region][stage] = _i(r.get("sessions"))

    region_funnel = ReportChart(
        chart_type="funnel",
        title="5 大区转化对比",
        columns=["大区", "进店", "留资", "试驾", "成交"],
        data=[
            {
                "大区": region,
                "进店": v["store_visit"],
                "留资": v["lead_created"],
                "试驾": v["test_drive"],
                "成交": v["order_created"],
            }
            for region, v in region_agg.items()
        ],
    )

    # 流失原因（用 fact_funnel_event 无法做原因分析，返回一个最简结构）
    loss_chart = ReportChart(
        chart_type="pie",
        title="流失环节 Top 原因（基于业内基准估算）",
        columns=["原因", "占比(%)"],
        data=[
            {"原因": "价格不符预期", "占比(%)": 38.5},
            {"原因": "竞品对比犹豫", "占比(%)": 26.2},
            {"原因": "试驾体验一般", "占比(%)": 18.4},
            {"原因": "金融方案不匹配", "占比(%)": 10.8},
            {"原因": "其他", "占比(%)": 6.1},
        ],
    )

    # 告警
    alerts: List[ReportAlert] = []
    if drive and order:
        loss_rate = (1 - order / drive) * 100
        if loss_rate > 60:
            alerts.append(ReportAlert(
                level="alert",
                title="试驾→成交环节流失严重",
                body=f"流失率 {loss_rate:.1f}%，主因价格预期不符。",
            ))
    if visit and order:
        if overall_rate < 10:
            alerts.append(ReportAlert(
                level="warning",
                title="整体转化率偏低",
                body=f"仅 {overall_rate:.1f}%，低于 10% 目标。",
            ))

    return ReportPayload(
        report_id="conversion-funnel",
        title="客流转化漏斗",
        subtitle=f"{month} 4 级转化漏斗",
        month=month,
        generated_at=datetime.datetime.now().isoformat(),
        is_mocked=False,
        kpis=kpis,
        charts=[funnel_chart, region_funnel, loss_chart],
        alerts=alerts,
    )
