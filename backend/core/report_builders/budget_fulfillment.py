"""
预算达成分析报表 builder
口径：M01 销售达成率（见 backend/core/metrics_dict.json）
SQL 模板：CTE 按月聚合事实表 → JOIN 预算表 → 计算达成率
"""
import datetime
import json
import os
from typing import List

from api.schemas import ReportPayload, ReportKpi, ReportChart, ReportAlert
from core.sql_executor import SqlExecutor

MOCK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "report_mocks", "budget_fulfillment.json",
)


def _safe_query(sql: str, params: tuple = ()) -> list[dict]:
    """执行只读 SQL，失败抛异常（由 ReportExecutor 兜底为 Mock）"""
    executor = SqlExecutor()
    # 参数化注入（替换 ?）
    if params:
        try:
            sql = sql.replace("?", "'" + str(params[0]) + "'")
        except Exception:
            pass
    result = executor.execute_query(sql)
    if not result.get("success"):
        raise RuntimeError(result.get("error", "SQL 执行失败"))
    return result.get("data", [])


def _empty_payload(month: str) -> ReportPayload:
    return ReportPayload(
        report_id="budget-fulfillment",
        title="预算达成分析",
        subtitle="本月各品牌预算完成进度",
        month=month,
        generated_at=datetime.datetime.now().isoformat(),
        is_mocked=False,
        kpis=[],
        charts=[],
        alerts=[{
            "level": "info",
            "title": "本月暂无达成数据",
            "body": f"维度表中无 {month} 的预算/销量记录。",
        }],
    )


def build(month: str) -> ReportPayload:
    """
    真实 SQL 路径：返回 is_mocked=False 的 ReportPayload。
    任何 SQL 异常都向上抛出，由 ReportExecutor 兜底到 Mock。
    """
    if not month or len(month) != 7:
        raise ValueError(f"month 必须是 YYYY-MM 格式，当前={month}")

    # SQL 1: 品牌综合达成率
    brand_sql = f"""
    WITH s_agg AS (
        SELECT brand_name, SUM(delivered_units) AS actual_units
        FROM fact_sales_daily
        WHERE STRFTIME('%Y-%m', sale_date) = '{month}'
        GROUP BY brand_name
    ),
    b AS (
        SELECT brand_name, target_units
        FROM dim_budget_target
        WHERE year_month = '{month}'
    )
    SELECT
        s.actual_units AS actual,
        COALESCE(b.target_units, 0) AS target,
        s.actual_units * 100.0 / NULLIF(b.target_units, 0) AS rate
    FROM s_agg s
    LEFT JOIN b ON s.brand_name = b.brand_name
    ORDER BY rate DESC
    """
    brand_rows = _safe_query(brand_sql)

    if not brand_rows:
        return _empty_payload(month)

    # KPI 汇总
    total_actual = sum(r["actual"] or 0 for r in brand_rows)
    total_target = sum(r["target"] or 0 for r in brand_rows)
    overall_rate = (total_actual * 100.0 / total_target) if total_target else 0

    kpis: List[ReportKpi] = [
        ReportKpi(
            label="综合达成率", value=round(overall_rate, 1), unit="%",
            trend="up" if overall_rate >= 95 else "down",
            hint="高于 95% 阈值" if overall_rate >= 95 else "低于 95% 阈值",
        ),
        ReportKpi(label="目标总台数", value=int(total_target), unit="辆"),
        ReportKpi(label="实际总交付", value=int(total_actual), unit="辆"),
        ReportKpi(
            label="差额", value=int(total_actual - total_target), unit="辆",
            trend="up" if total_actual >= total_target else "down",
        ),
    ]

    # SQL 2: 大区达成率
    region_sql = f"""
    WITH s_agg AS (
        SELECT region_name, SUM(delivered_units) AS actual_units
        FROM fact_sales_daily
        WHERE STRFTIME('%Y-%m', sale_date) = '{month}'
        GROUP BY region_name
    ),
    b AS (
        SELECT brand_name, target_units
        FROM dim_budget_target
        WHERE year_month = '{month}'
    )
    SELECT
        s.region_name,
        SUM(s.actual_units) AS actual,
        SUM(COALESCE(b.target_units, 0)) / 3 AS target,
        ROUND(SUM(s.actual_units) * 100.0 /
              NULLIF(SUM(COALESCE(b.target_units, 0)) / 3, 0), 1) AS rate
    FROM s_agg s
    LEFT JOIN b ON 1=1
    GROUP BY s.region_name
    ORDER BY rate DESC
    """
    region_rows = _safe_query(region_sql)

    # 图表 1: 品牌达成率横向条形
    brand_chart = ReportChart(
        chart_type="bar",
        title=f"{month} 品牌达成率对比",
        columns=["品牌", "目标(辆)", "实际(辆)", "达成率(%)"],
        data=[
            {
                "品牌": r.get("brand_name", ""),
                "目标(辆)": int(r.get("target", 0)),
                "实际(辆)": int(r.get("actual", 0)),
                "达成率(%)": round(r.get("rate", 0) or 0, 1),
            }
            for r in brand_rows
        ],
        x_axis="品牌",
        y_axis="达成率(%)",
    )

    # 图表 2: 大区达成率
    region_chart = ReportChart(
        chart_type="bar",
        title=f"{month} 大区达成率分布",
        columns=["大区", "达成率(%)"],
        data=[
            {
                "大区": r.get("region_name", ""),
                "达成率(%)": round(r.get("rate", 0) or 0, 1),
            }
            for r in region_rows
        ],
        x_axis="大区",
        y_axis="达成率(%)",
    )

    # 弱项明细表
    weak_rows = [r for r in region_rows if r.get("rate") and r["rate"] < 95]
    weak_chart = ReportChart(
        chart_type="table",
        title="弱项明细（达成率 < 95%）",
        columns=["大区", "实际(辆)", "目标(辆)", "达成率(%)"],
        data=[
            {
                "大区": r.get("region_name", ""),
                "实际(辆)": int(r.get("actual", 0)),
                "目标(辆)": int(r.get("target", 0)),
                "达成率(%)": round(r.get("rate", 0) or 0, 1),
            }
            for r in weak_rows
        ],
    )

    # 告警：达成率 < 85% 的视为严重
    alerts: List[ReportAlert] = []
    for r in region_rows:
        rate = r.get("rate") or 0
        if rate < 85:
            alerts.append(ReportAlert(
                level="alert",
                title=f"{r.get('region_name', '')} 严重欠产",
                body=f"达成率 {rate:.1f}%，建议区域经理介入。",
            ))
        elif rate < 95:
            alerts.append(ReportAlert(
                level="warning",
                title=f"{r.get('region_name', '')} 低于阈值",
                body=f"达成率 {rate:.1f}%，需关注。",
            ))

    return ReportPayload(
        report_id="budget-fulfillment",
        title="预算达成分析",
        subtitle=f"{month} 各品牌预算完成进度",
        month=month,
        generated_at=datetime.datetime.now().isoformat(),
        is_mocked=False,
        kpis=kpis,
        charts=[brand_chart, region_chart, weak_chart],
        alerts=alerts,
    )
