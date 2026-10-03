"""
大区销售排行 builder
口径：M02 总交付量 + 同比/环比
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


def _f(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except Exception:
        return default


def build(month: str) -> ReportPayload:
    if not month or len(month) != 7:
        raise ValueError(f"month 必须 YYYY-MM，当前={month}")

    # 本月各大区销量
    region_sql = f"""
    SELECT
        region_name,
        SUM(delivered_units) AS units,
        SUM(gross_revenue) AS revenue
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{month}'
    GROUP BY region_name
    ORDER BY units DESC
    """
    region_rows = _safe_query(region_sql)
    if not region_rows:
        raise RuntimeError(f"{month} 无大区销量")

    ym_y, ym_m = month.split("-")
    yoy_month = f"{int(ym_y) - 1}-{ym_m}"
    m_int = int(ym_m)
    if m_int == 1:
        mom_month = f"{int(ym_y) - 1}-12"
    else:
        mom_month = f"{ym_y}-{m_int - 1:02d}"

    # 同比月份各大区销量
    yoy_sql = f"""
    SELECT region_name, SUM(delivered_units) AS units
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{yoy_month}'
    GROUP BY region_name
    """
    yoy_rows = _safe_query(yoy_sql)
    yoy_map = {r["region_name"]: _i(r["units"]) for r in yoy_rows}

    # 环比月份各大区销量
    mom_sql = f"""
    SELECT region_name, SUM(delivered_units) AS units
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '{mom_month}'
    GROUP BY region_name
    """
    mom_rows = _safe_query(mom_sql)
    mom_map = {r["region_name"]: _i(r["units"]) for r in mom_rows}

    # KPI: Top / Bottom
    sorted_by_units = sorted(region_rows, key=lambda r: _i(r["units"]), reverse=True)
    top = sorted_by_units[0]
    bottom = sorted_by_units[-1]

    # 同比最高/最低
    yoy_pcts = []
    for r in region_rows:
        region = r["region_name"]
        cur = _i(r["units"])
        prev = yoy_map.get(region, 0)
        if prev:
            yoy_pcts.append((region, (cur - prev) * 100.0 / prev))
    highest_yoy = max(yoy_pcts, key=lambda x: x[1]) if yoy_pcts else ("—", 0)
    lowest_yoy = min(yoy_pcts, key=lambda x: x[1]) if yoy_pcts else ("—", 0)

    kpis: List[ReportKpi] = [
        ReportKpi(label="冠军大区", value=top["region_name"], unit="",
                 hint=f"销量 {int(top['units'])} 辆"),
        ReportKpi(label="垫底大区", value=bottom["region_name"], unit="",
                 hint=f"销量 {int(bottom['units'])} 辆"),
        ReportKpi(label="最高同比", value=highest_yoy[0], unit=f"{highest_yoy[1]:+.1f}%",
                 trend="up" if highest_yoy[1] > 0 else "down"),
        ReportKpi(label="最低同比", value=lowest_yoy[0], unit=f"{lowest_yoy[1]:+.1f}%",
                 trend="up" if lowest_yoy[1] > 0 else "down"),
    ]

    # 图表 1: 大区排行表
    ranking_chart = ReportChart(
        chart_type="ranking",
        title=f"{month} 大区销售业绩排行",
        columns=["大区", "销量(辆)", "营收(万)", "同比(%)", "环比(%)"],
        data=[
            {
                "大区": r["region_name"],
                "销量(辆)": int(_i(r["units"])),
                "营收(万)": round(_f(r.get("revenue")) / 10000, 0),
                "同比(%)": round(
                    (_i(r["units"]) - yoy_map.get(r["region_name"], 0)) * 100.0
                    / max(yoy_map.get(r["region_name"], 1), 1),
                    1,
                ),
                "环比(%)": round(
                    (_i(r["units"]) - mom_map.get(r["region_name"], 0)) * 100.0
                    / max(mom_map.get(r["region_name"], 1), 1),
                    1,
                ),
            }
            for r in sorted_by_units
        ],
        x_axis="大区",
        y_axis="销量(辆)",
    )

    # 图表 2: 12 月趋势（近 12 月各大区销量）
    ym_y_int = int(ym_y)
    m_int = int(ym_m)
    months_back = []
    for i in range(11, -1, -1):
        m_calc = m_int - i
        y_calc = ym_y_int
        while m_calc <= 0:
            m_calc += 12
            y_calc -= 1
        months_back.append(f"{y_calc}-{m_calc:02d}")

    months_sql = " UNION ALL ".join(
        [f"SELECT '{m}' AS ym" for m in months_back]
    )
    trend_sql = f"""
    WITH months AS ({months_sql})
    SELECT
        m.ym,
        COALESCE(s.region_name, '—') AS region_name,
        COALESCE(s.units, 0) AS units
    FROM months m
    LEFT JOIN (
        SELECT STRFTIME('%Y-%m', sale_date) AS ym,
               region_name, SUM(delivered_units) AS units
        FROM fact_sales_daily
        WHERE STRFTIME('%Y-%m', sale_date) IN ({','.join([f"'{m}'" for m in months_back])})
        GROUP BY ym, region_name
    ) s ON m.ym = s.ym
    ORDER BY m.ym, s.region_name
    """
    trend_rows = _safe_query(trend_sql)

    # 透视成 (月 × 大区) 矩阵
    pivot: dict = {m: {} for m in months_back}
    for r in trend_rows:
        ym = r.get("ym", "")
        region = r.get("region_name", "")
        if not ym or not region or region == "—":
            continue
        pivot[ym][region] = int(_i(r.get("units")))

    # 提取所有出现的大区
    all_regions = sorted({r.get("region_name", "") for r in region_rows})
    trend_data = []
    for ym in months_back:
        row = {"月份": ym}
        for region in all_regions:
            row[region] = pivot[ym].get(region, 0)
        trend_data.append(row)

    trend_chart = ReportChart(
        chart_type="line",
        title=f"近 12 月 {len(all_regions)} 大区销量趋势",
        columns=["月份"] + all_regions,
        data=trend_data,
        x_axis="月份",
        y_axis="销量(辆)",
        series=all_regions,
    )

    alerts: List[ReportAlert] = []
    if lowest_yoy[1] < -5:
        alerts.append(ReportAlert(
            level="alert",
            title=f"{lowest_yoy[0]} 同比下滑 {lowest_yoy[1]:.1f}%",
            body="连续负增长，建议区域经理介入。",
        ))
    if highest_yoy[1] > 10:
        alerts.append(ReportAlert(
            level="info",
            title=f"{highest_yoy[0]} 同比 +{highest_yoy[1]:.1f}%",
            body="连续高增长，建议保持资源投入。",
        ))

    return ReportPayload(
        report_id="regional-ranking",
        title="大区销售排行",
        subtitle=f"{month} 5 大区业绩多维对比",
        month=month,
        generated_at=datetime.datetime.now().isoformat(),
        is_mocked=False,
        kpis=kpis,
        charts=[ranking_chart, trend_chart],
        alerts=alerts,
    )
