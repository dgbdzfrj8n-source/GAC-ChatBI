"""
销量归因分析 builder
口径：M03 单车成交均价 + M02 总交付量
输出：3 个瀑布图（渠道 / 大区 / 价格带）
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


def _to_int(v, default=0):
    try:
        return int(v) if v is not None else default
    except Exception:
        return default


def _to_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def build(month: str) -> ReportPayload:
    if not month or len(month) != 7:
        raise ValueError(f"month 必须 YYYY-MM，当前={month}")

    # 本月总销量
    total_sql = f"""
    SELECT
        SUM(delivered_units) AS units,
        SUM(gross_revenue) AS revenue,
        COUNT(DISTINCT brand_name) AS brand_cnt
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{month}'
    """
    total_rows = _safe_query(total_sql)
    if not total_rows or not total_rows[0].get("units"):
        raise RuntimeError(f"{month} 无销量数据")
    total_units = _to_int(total_rows[0]["units"])

    # 同比月份
    ym_y, ym_m = month.split("-")
    yoy_year = int(ym_y) - 1
    yoy_month = f"{yoy_year}-{ym_m}"
    yoy_sql = f"""
    SELECT SUM(delivered_units) AS units
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{yoy_month}'
    """
    yoy_rows = _safe_query(yoy_sql)
    yoy_units = _to_int(yoy_rows[0]["units"]) if yoy_rows else 0

    yoy_pct = (total_units - yoy_units) * 100.0 / yoy_units if yoy_units else 0.0

    # 环比月份（上一月）
    m_int = int(ym_m)
    if m_int == 1:
        mom_month = f"{int(ym_y) - 1}-12"
    else:
        mom_month = f"{ym_y}-{m_int - 1:02d}"
    mom_sql = f"""
    SELECT SUM(delivered_units) AS units
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{mom_month}'
    """
    mom_rows = _safe_query(mom_sql)
    mom_units = _to_int(mom_rows[0]["units"]) if mom_rows else 0
    mom_pct = (total_units - mom_units) * 100.0 / mom_units if mom_units else 0.0

    # 渠道贡献瀑布：按 brand_name 维度（因为 fact_marketing_expenses 没带 brand 聚合的销量，简化用品牌做渠道代理维度）
    # 实际这里把渠道映射为"投放来源主导的品牌"作为归因——简单方案。
    channel_sql = f"""
    SELECT brand_name, SUM(delivered_units) AS units
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{month}'
    GROUP BY brand_name
    ORDER BY units DESC
    """
    channel_rows = _safe_query(channel_sql)
    # 构造瀑布：基线 = 整体均值
    baseline = total_units // len(channel_rows) if channel_rows else 0
    channel_data = [{"渠道": "基线均值", "贡献(辆)": baseline}]
    delta_sum = 0
    for r in channel_rows:
        delta = _to_int(r["units"]) - baseline
        delta_sum += delta
        channel_data.append({
            "渠道": r.get("brand_name", ""),
            "贡献(辆)": delta,
        })
    channel_data.append({"渠道": "合计", "贡献(辆)": baseline + delta_sum})

    channel_chart = ReportChart(
        chart_type="waterfall",
        title=f"{month} 品牌（渠道代理）贡献瀑布",
        columns=["渠道", "贡献(辆)"],
        data=channel_data,
        x_axis="渠道",
        y_axis="贡献(辆)",
    )

    # 大区贡献瀑布
    region_sql = f"""
    SELECT region_name, SUM(delivered_units) AS units
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{month}'
    GROUP BY region_name
    ORDER BY units DESC
    """
    region_rows = _safe_query(region_sql)
    region_baseline = total_units // len(region_rows) if region_rows else 0
    region_data = [{"大区": "基线均值", "贡献(辆)": region_baseline}]
    delta_sum = 0
    for r in region_rows:
        delta = _to_int(r["units"]) - region_baseline
        delta_sum += delta
        region_data.append({
            "大区": r.get("region_name", ""),
            "贡献(辆)": delta,
        })
    region_data.append({"大区": "合计", "贡献(辆)": region_baseline + delta_sum})

    region_chart = ReportChart(
        chart_type="waterfall",
        title=f"{month} 大区贡献瀑布",
        columns=["大区", "贡献(辆)"],
        data=region_data,
        x_axis="大区",
        y_axis="贡献(辆)",
    )

    # 价格带贡献瀑布（按车型指导价分档）
    model_sql = f"""
    SELECT model_name, SUM(delivered_units) AS units,
           AVG(gross_revenue / NULLIF(delivered_units, 0)) AS avg_price
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{month}'
    GROUP BY model_name
    ORDER BY avg_price ASC
    """
    model_rows = _safe_query(model_sql)
    if model_rows:
        model_baseline = total_units // len(model_rows)
        price_data = [{"价格带": "基线均值", "贡献(辆)": model_baseline}]
        delta_sum = 0
        for r in model_rows:
            delta = _to_int(r["units"]) - model_baseline
            delta_sum += delta
            price = _to_float(r.get("avg_price"))
            tier = "10万以下" if price < 100000 else (
                "10-15万" if price < 150000 else (
                    "15-20万" if price < 200000 else (
                        "20-25万" if price < 250000 else "25万以上"
                    )
                )
            )
            price_data.append({"价格带": tier, "贡献(辆)": delta})
        price_data.append({"价格带": "合计", "贡献(辆)": model_baseline + delta_sum})
    else:
        price_data = []

    price_chart = ReportChart(
        chart_type="waterfall",
        title=f"{month} 价格带贡献瀑布",
        columns=["价格带", "贡献(辆)"],
        data=price_data,
        x_axis="价格带",
        y_axis="贡献(辆)",
    )

    kpis: List[ReportKpi] = [
        ReportKpi(label="本月总销量", value=total_units, unit="辆",
                 trend="up" if mom_pct > 0 else "down",
                 hint=f"环比 {mom_pct:+.1f}%"),
        ReportKpi(label="同比变动", value=round(yoy_pct, 1), unit="%",
                 trend="up" if yoy_pct > 0 else "down"),
        ReportKpi(label="环比变动", value=round(mom_pct, 1), unit="%",
                 trend="up" if mom_pct > 0 else "down"),
        ReportKpi(label="贡献最弱品牌",
                 value=channel_rows[-1].get("brand_name", "") if channel_rows else "—",
                 unit="",
                 hint="销量最低品牌"),
    ]

    alerts: List[ReportAlert] = []
    if yoy_pct < -5:
        alerts.append(ReportAlert(
            level="alert",
            title="同比下滑",
            body=f"本月销量同比 {yoy_pct:+.1f}%，需重点归因。",
        ))
    # 找最弱大区
    if region_rows:
        weakest = min(region_rows, key=lambda r: _to_int(r["units"]))
        alerts.append(ReportAlert(
            level="warning",
            title=f"{weakest.get('region_name', '')} 销量垫底",
            body=f"本月 {_to_int(weakest['units'])} 辆，建议区域经理关注。",
        ))

    return ReportPayload(
        report_id="sales-attribution",
        title="销量归因分析",
        subtitle=f"{month} 销量波动的多维根因",
        month=month,
        generated_at=datetime.datetime.now().isoformat(),
        is_mocked=False,
        kpis=kpis,
        charts=[channel_chart, region_chart, price_chart],
        alerts=alerts,
    )
