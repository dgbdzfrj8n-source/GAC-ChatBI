"""
库存预警 builder
口径：M08 周转天数 + M09 库存系数
数据源：fact_dealer_inventory_daily + fact_sales_daily（最近 30 天销量）
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


def _status(coef: float) -> str:
    if coef >= 2.5:
        return "严重滞销"
    if coef >= 1.8:
        return "高库存"
    if coef >= 1.5:
        return "预警"
    return "正常"


def build(month: str) -> ReportPayload:
    if not month or len(month) != 7:
        raise ValueError(f"month 必须 YYYY-MM，当前={month}")

    # 最新库存快照日
    latest_sql = """
    SELECT MAX(snapshot_date) AS latest_date
    FROM fact_dealer_inventory_daily
    """
    latest_rows = _safe_query(latest_sql)
    if not latest_rows or not latest_rows[0].get("latest_date"):
        raise RuntimeError("库存表无数据")

    latest_date = str(latest_rows[0]["latest_date"])[:10]  # YYYY-MM-DD

    # 经销商级库存系数
    dealer_sql = f"""
    WITH inv AS (
        SELECT dealer_name, brand_name, region_name,
               SUM(inventory_units) AS inventory_units
        FROM fact_dealer_inventory_daily
        WHERE snapshot_date = DATE '{latest_date}'
        GROUP BY dealer_name, brand_name, region_name
    ),
    sales AS (
        SELECT dealer_name, SUM(delivered_units) AS recent_30d
        FROM fact_sales_daily
        WHERE sale_date >= DATE '{latest_date}' - INTERVAL '30 days'
          AND sale_date <= DATE '{latest_date}'
        GROUP BY dealer_name
    )
    SELECT
        inv.dealer_name, inv.brand_name, inv.region_name,
        inv.inventory_units,
        COALESCE(sales.recent_30d, 0) AS recent_30d,
        ROUND(inv.inventory_units * 30.0 /
              NULLIF(sales.recent_30d, 0), 1) AS turnover_days,
        ROUND(inv.inventory_units * 1.0 /
              NULLIF(sales.recent_30d, 0), 2) AS coefficient
    FROM inv
    LEFT JOIN sales ON inv.dealer_name = sales.dealer_name
    ORDER BY coefficient DESC
    """
    dealer_rows = _safe_query(dealer_sql)
    if not dealer_rows:
        raise RuntimeError(f"快照日 {latest_date} 无经销商库存数据")

    # KPI
    total_inv = sum(_i(r.get("inventory_units")) for r in dealer_rows)
    alert_dealers = sum(1 for r in dealer_rows if _f(r.get("coefficient")) >= 1.5)
    avg_turnover = (
        sum(_f(r.get("turnover_days")) for r in dealer_rows) / len(dealer_rows)
        if dealer_rows else 0
    )
    high_coef_models = len(set(
        r.get("model_name", "") for r in dealer_rows
        if _f(r.get("coefficient")) >= 1.5
    ))

    kpis: List[ReportKpi] = [
        ReportKpi(label="总库存台数", value=total_inv, unit="辆"),
        ReportKpi(label="预警经销商", value=alert_dealers, unit="家",
                 trend="up" if alert_dealers > 5 else "down"),
        ReportKpi(label="平均周转天数", value=round(avg_turnover, 0), unit="天",
                 trend="up" if avg_turnover > 45 else "down"),
        ReportKpi(label="高库存车型数", value=high_coef_models, unit="款"),
    ]

    # 图表 1: 经销商库存预警明细
    detail_chart = ReportChart(
        chart_type="table",
        title="经销商库存预警明细（Top 20）",
        columns=["经销商", "品牌", "大区", "库存(辆)", "30日销量",
                 "周转天数", "库存系数", "状态"],
        data=[
            {
                "经销商": r.get("dealer_name", ""),
                "品牌": r.get("brand_name", ""),
                "大区": r.get("region_name", ""),
                "库存(辆)": _i(r.get("inventory_units")),
                "30日销量": _i(r.get("recent_30d")),
                "周转天数": round(_f(r.get("turnover_days")), 1),
                "库存系数": round(_f(r.get("coefficient")), 2),
                "状态": _status(_f(r.get("coefficient"))),
            }
            for r in dealer_rows[:20]
        ],
    )

    # 图表 2: 周转天数 Top10
    top10_rows = sorted(
        dealer_rows, key=lambda r: _f(r.get("turnover_days")), reverse=True
    )[:10]
    top10_chart = ReportChart(
        chart_type="ranking",
        title="周转天数 Top10 经销商",
        columns=["经销商", "周转天数"],
        data=[
            {
                "经销商": r.get("dealer_name", ""),
                "周转天数": round(_f(r.get("turnover_days")), 1),
            }
            for r in top10_rows
        ],
        x_axis="经销商",
        y_axis="周转天数",
    )

    # 图表 3: 大区维度（聚合）
    region_agg = {}
    for r in dealer_rows:
        region = r.get("region_name", "")
        if not region:
            continue
        if region not in region_agg:
            region_agg[region] = {"inv": 0, "sales": 0}
        region_agg[region]["inv"] += _i(r.get("inventory_units"))
        region_agg[region]["sales"] += _i(r.get("recent_30d"))

    region_chart = ReportChart(
        chart_type="bar",
        title="大区库存压力分布",
        columns=["大区", "总库存(辆)", "30日销量", "库存系数"],
        data=[
            {
                "大区": region,
                "总库存(辆)": v["inv"],
                "30日销量": v["sales"],
                "库存系数": round(v["inv"] / v["sales"], 2) if v["sales"] else 0,
            }
            for region, v in region_agg.items()
        ],
        x_axis="大区",
        y_axis="总库存(辆)",
    )

    alerts: List[ReportAlert] = []
    for r in dealer_rows[:5]:  # 取最严重的前 5 条
        coef = _f(r.get("coefficient"))
        if coef >= 2.5:
            alerts.append(ReportAlert(
                level="alert",
                title=f"{r.get('dealer_name', '')} 严重滞销",
                body=f"库存系数 {coef:.2f}，建议跨区调拨。",
            ))
        elif coef >= 1.8:
            alerts.append(ReportAlert(
                level="warning",
                title=f"{r.get('dealer_name', '')} 高库存",
                body=f"库存系数 {coef:.2f}，需关注。",
            ))

    return ReportPayload(
        report_id="inventory-warning",
        title="经销商库存预警",
        subtitle=f"快照日 {latest_date} 库存健康度",
        month=month,
        generated_at=datetime.datetime.now().isoformat(),
        is_mocked=False,
        kpis=kpis,
        charts=[region_chart, detail_chart, top10_chart],
        alerts=alerts,
    )
