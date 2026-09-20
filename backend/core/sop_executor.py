"""
SOP 步骤化模板执行引擎（P2-SprintB）
====================================

设计目标：
- 把"管理员配置的 SOP 步骤数组（steps）"自动按顺序执行，
  每一步构造一条 DuckDB 只读 SQL → 跑 → 拿数据 → 生成结构化结论。
- 复用现有 sop_analyzer.METRIC_DIMENSION_MATRIX 的 agg_expression 与 applicable_dimensions，
  保证指标口径与业务系统 100% 一致。

支持的 step_type（8 种）：
  overall_kpi        整体达成率（vs 目标/同比/环比）
  yoy_compare        YoY 同比
  period_compare     环比 / 同期对比
  horizontal_compare 横向对比（多 brand/region 并列）
  drill_down         下钻找异常
  cross_attribution  跨域归因（贡献度拆解）
  anomaly_alert      异常告警（z-score）
  strategy_recommend 策略建议（基于 depends_on 的 step 输出，由 LLM 生成）

执行流程：
  1. 拿模板（含 steps）
  2. 按 order 顺序遍历 steps
  3. 对每个 step：
     a) 构造 DuckDB 只读 SQL（_build_step_sql）
     b) 应用权限门禁（apply_full_permission：行级 + 字段级）
     c) 执行（SqlExecutor.execute_query）
     d) 异常判定（_evaluate_threshold：ok/warn/bad）
     e) 生成结论文本（_generate_conclusion：模板规则 + 可选 LLM）
  4. 组装 report[] 返回
"""
from __future__ import annotations

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.sql_executor import SqlExecutor
from core.sop_analyzer import (
    METRIC_DIMENSION_MATRIX,
    DIMENSION_FIELD_MAP,
    DIMENSION_LABEL_MAP,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────
# 数据源：销售事实表
# ──────────────────────────────────────────────────────────
FACT_TABLE = "fact_sales_daily"
PLAN_TABLE = "dim_budget_target"  # 月粒度 plan（按 brand）

# 默认时间窗：演示库最近一个完整季度（按 fact_sales_daily 实际范围 2024-01 ~ 2025-04）
DEFAULT_TIME_WINDOW = {
    "start": "2025-02-01",
    "end": "2025-04-30",
}

# 默认区域默认品牌（无用户筛选时）
DEFAULT_BRAND_FILTER: List[str] = []  # 空 = 不筛选


# ──────────────────────────────────────────────────────────
# 引擎入口
# ──────────────────────────────────────────────────────────
class SopExecutor:
    """SOP 步骤化模板执行引擎"""

    def __init__(self, sql_executor: Optional[SqlExecutor] = None):
        self.sql_executor = sql_executor or SqlExecutor()

    # ─── 主入口 ─────────────────────────────────────────
    def run(
        self,
        template: Dict[str, Any],
        user: Optional[Any] = None,
        time_window: Optional[Dict[str, str]] = None,
        max_steps: Optional[int] = None,
        llm_conclusion: bool = False,  # 默认关闭 LLM 调用（节省 token）
    ) -> Dict[str, Any]:
        """
        执行一个模板的完整 SOP（或前 N 步）。
        Args:
            template: 模板详情（AttributionTemplateManager.get_template 返回值，含 steps）
            user: CurrentUser（用于行级过滤 + 字段脱敏；None 表示不过滤）
            time_window: {"start":"2025-07-01","end":"2025-09-30"}；None 用默认
            max_steps: 限制执行步数（preview 时用，None = 全部）
            llm_conclusion: 是否对每个 step 调 LLM 生成详细结论（默认关闭）
        Returns:
            {
                "template_id": str,
                "template_name": str,
                "steps_count": int,
                "steps_executed": int,
                "report": [
                    {
                        "step_id", "title", "step_type",
                        "status": "ok"|"warn"|"bad"|"info",
                        "sql": "...",
                        "conclusion": "...",
                        "data": [...],  # DuckDB 结果
                        "metrics": {"total": 12345, "rate": 0.87},
                        "permission": {...},  # 行级过滤 / 字段脱敏 标记
                        "execution_time_ms": 12.3,
                    },
                    ...
                ],
                "executive_summary": "...",
                "total_execution_time_ms": 56.7,
            }
        """
        t0 = time.perf_counter()
        tw = time_window or DEFAULT_TIME_WINDOW
        steps = sorted(template.get("steps") or [], key=lambda s: s.get("order", 0))
        if max_steps is not None:
            steps = steps[:max_steps]

        report: List[Dict[str, Any]] = []
        for step in steps:
            step_result = self._execute_step(
                step=step,
                template=template,
                prior_results=report,
                user=user,
                time_window=tw,
                llm_conclusion=llm_conclusion,
            )
            report.append(step_result)

        exec_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "template_id": template.get("id"),
            "template_name": template.get("name"),
            "steps_count": len(template.get("steps") or []),
            "steps_executed": len(report),
            "report": report,
            "executive_summary": self._generate_executive_summary(report),
            "total_execution_time_ms": exec_ms,
        }

    # ─── 单步执行 ────────────────────────────────────────
    def _execute_step(
        self,
        step: Dict[str, Any],
        template: Dict[str, Any],
        prior_results: List[Dict[str, Any]],
        user: Optional[Any],
        time_window: Dict[str, str],
        llm_conclusion: bool,
    ) -> Dict[str, Any]:
        step_type = step.get("step_type")
        step_id = step.get("step_id")
        title = step.get("title")
        metric_key = step.get("metric_key") or template.get("metric_key") or "delivered_units"
        t0 = time.perf_counter()

        # 1) strategy_recommend 不跑 SQL，基于上游 step 生成建议
        if step_type == "strategy_recommend":
            depends_on = step.get("depends_on")
            upstream = next(
                (r for r in prior_results if r.get("step_id") == depends_on),
                None,
            )
            conclusion = self._generate_strategy_recommendation(step, upstream, template)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "step_id": step_id,
                "title": title,
                "step_type": step_type,
                "status": "info",
                "sql": None,
                "conclusion": conclusion,
                "data": [],
                "metrics": {},
                "depends_on": depends_on,
                "execution_time_ms": elapsed_ms,
            }

        # 2) 构造 SQL
        sql = self._build_step_sql(step, metric_key, time_window)

        # 3) 应用权限（行级 + 字段级）
        from core.permission import apply_full_permission, get_permission
        perm_info: Dict[str, Any] = {}
        if user is not None:
            # 先用 SqlExecutor 跑一遍拿 data/columns，再过权限脱敏
            raw = self.sql_executor.execute_query(sql)
            if raw.get("success"):
                perm_result = apply_full_permission(
                    sql, user, raw.get("data") or [], raw.get("columns") or [],
                )
                perm_info = perm_result.get("permission", {})
                # 行级过滤后的 SQL 才是真正执行的
                final_sql = perm_result["sql"]
            else:
                # SQL 本身失败（不依赖权限）
                final_sql = sql
        else:
            final_sql = sql

        # 4) 执行（已含权限过滤则用 final_sql，否则直接原 sql）
        result = self.sql_executor.execute_query(final_sql)
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        # 5) 阈值判定
        status = self._evaluate_threshold(step, result.get("data") or [])

        # 6) 生成结论（规则模板，必要时才 LLM）
        conclusion = self._generate_conclusion(
            step=step,
            data=result.get("data") or [],
            status=status,
            prior_results=prior_results,
            llm_enabled=llm_conclusion,
        )

        # 7) 关键指标摘录（前端 dashboard 用）
        metrics = self._extract_metrics(step, result.get("data") or [], metric_key)

        return {
            "step_id": step_id,
            "title": title,
            "step_type": step_type,
            "status": status,
            "sql": final_sql,
            "conclusion": conclusion,
            "data": result.get("data") or [],
            "columns": result.get("columns") or [],
            "row_count": result.get("row_count") or 0,
            "metrics": metrics,
            "permission": perm_info,
            "execution_time_ms": elapsed_ms,
            "engine": result.get("engine"),
            "error": result.get("error") if not result.get("success") else None,
        }

    # ──────────────────────────────────────────────────────
    # SQL 构造器（路由 8 种 step_type）
    # ──────────────────────────────────────────────────────
    def _build_step_sql(
        self,
        step: Dict[str, Any],
        metric_key: str,
        tw: Dict[str, str],
    ) -> str:
        step_type = step.get("step_type")
        group_by = step.get("group_by") or []
        compare_mode = step.get("compare_mode", "plan")
        compare_period = step.get("compare_period")
        threshold = step.get("threshold") or {}
        top_n = step.get("top_n")

        metric_cfg = METRIC_DIMENSION_MATRIX.get(metric_key, METRIC_DIMENSION_MATRIX["delivered_units"])
        agg = metric_cfg["agg_expression"]  # 如 SUM(delivered_units)

        # 维度表达式（monthly 转 STRFTIME）
        def dim_expr(d: str) -> str:
            if d == "monthly":
                return "STRFTIME('%Y-%m', sale_date)"
            return d

        select_dims = [dim_expr(d) for d in group_by]

        # 公共 WHERE：时间窗
        base_where = f"sale_date BETWEEN DATE '{tw['start']}' AND DATE '{tw['end']}'"

        # ── 1. overall_kpi ─────────────────────────────────
        if step_type == "overall_kpi":
            if compare_mode == "plan":
                # 取实际 + plan（按 brand），达成率
                return f"""
                SELECT
                    {agg} AS actual,
                    COALESCE(SUM(bt.target_units), 0) AS plan,
                    ROUND({agg} * 1.0 / NULLIF(SUM(bt.target_units), 0), 4) AS fulfillment_rate
                FROM {FACT_TABLE} f
                LEFT JOIN {PLAN_TABLE} bt
                  ON f.brand_name = bt.brand_name
                 AND STRFTIME('%Y-%m', f.sale_date) = bt.year_month
                WHERE {base_where}
                """
            else:
                return f"SELECT {agg} AS actual FROM {FACT_TABLE} WHERE {base_where}"

        # ── 2. yoy_compare / period_compare ────────────────
        if step_type in ("yoy_compare", "period_compare"):
            # 简化：本期 + 上期（去年同期 / 上季度），对比 delta
            # 取最新月份作为本期起点
            return f"""
            WITH current_period AS (
                SELECT {agg} AS actual FROM {FACT_TABLE}
                WHERE {base_where}
            ),
            prior_period AS (
                SELECT {agg} AS prior
                FROM {FACT_TABLE}
                WHERE sale_date < DATE '{tw['start']}'
            )
            SELECT
                cp.actual AS current_actual,
                COALESCE(pp.prior, 0) AS prior_actual,
                ROUND((cp.actual - COALESCE(pp.prior, 0)) * 100.0 / NULLIF(pp.prior, 0), 2) AS delta_pct
            FROM current_period cp, prior_period pp
            """

        # ── 3. horizontal_compare / drill_down ─────────────
        if step_type in ("horizontal_compare", "drill_down"):
            dims_str = ", ".join(select_dims)
            group_clause = f"GROUP BY {dims_str}" if dims_str else ""
            order_clause = f"ORDER BY actual DESC" if dims_str else ""
            limit_clause = f"LIMIT {int(top_n)}" if top_n else ""
            return f"""
            SELECT {dims_str + ', ' if dims_str else ''}{agg} AS actual
            FROM {FACT_TABLE}
            WHERE {base_where}
            {group_clause}
            {order_clause}
            {limit_clause}
            """

        # ── 4. cross_attribution（贡献度拆解） ─────────────
        if step_type == "cross_attribution":
            dims_str = ", ".join(select_dims)
            return f"""
            WITH base AS (
                SELECT {dims_str + ', ' if dims_str else ''}{agg} AS actual
                FROM {FACT_TABLE}
                WHERE {base_where}
                {'GROUP BY ' + dims_str if dims_str else ''}
            )
            SELECT {dims_str + ', ' if dims_str else ''}
                actual,
                ROUND(actual - (SUM(actual) OVER () * 1.0 / COUNT(*) OVER ()), 2) AS deviation,
                ROUND((actual - (SUM(actual) OVER () * 1.0 / COUNT(*) OVER ())) * 100.0
                      / NULLIF(SUM(actual) OVER (), 0), 2) AS contribution_pct
            FROM base
            ORDER BY deviation DESC
            """

        # ── 5. anomaly_alert（z-score） ─────────────────────
        if step_type == "anomaly_alert":
            dims_str = ", ".join(select_dims)
            return f"""
            WITH base AS (
                SELECT {dims_str + ', ' if dims_str else ''}{agg} AS actual
                FROM {FACT_TABLE}
                WHERE {base_where}
                {'GROUP BY ' + dims_str if dims_str else ''}
            ),
            stats AS (
                SELECT AVG(actual) AS mu, STDDEV(actual) AS sigma FROM base
            )
            SELECT {dims_str + ', ' if dims_str else ''}
                b.actual,
                ROUND((b.actual - s.mu) / NULLIF(s.sigma, 0), 2) AS z_score,
                CASE
                    WHEN ABS(b.actual - s.mu) > 2 * s.sigma THEN 'extreme'
                    WHEN ABS(b.actual - s.mu) > 1.5 * s.sigma THEN 'warn'
                    ELSE 'normal'
                END AS anomaly_level
            FROM base b, stats s
            {'GROUP BY ' + dims_str + ', b.actual, s.mu, s.sigma' if dims_str else ''}
            ORDER BY ABS(b.actual - s.mu) DESC
            {f'LIMIT {int(top_n)}' if top_n else ''}
            """

        # 兜底
        return f"SELECT {agg} AS actual FROM {FACT_TABLE} WHERE {base_where}"

    # ──────────────────────────────────────────────────────
    # 阈值判定
    # ──────────────────────────────────────────────────────
    def _evaluate_threshold(self, step: Dict[str, Any], data: List[Dict[str, Any]]) -> str:
        threshold = step.get("threshold") or {}
        warn = threshold.get("warn")
        bad = threshold.get("bad")
        if not data:
            return "info"
        # 找"达成率"列
        rate = None
        for row in data:
            for k in ("fulfillment_rate", "rate", "achievement_rate"):
                if k in row and row[k] is not None:
                    rate = row[k]
                    break
            if rate is not None:
                break
        if rate is None:
            # 没达成率列，按 row 数判断：0 = bad
            if not data:
                return "bad"
            return "ok"
        try:
            rate = float(rate)
        except (TypeError, ValueError):
            return "ok"
        if bad is not None and rate < float(bad):
            return "bad"
        if warn is not None and rate < float(warn):
            return "warn"
        return "ok"

    # ──────────────────────────────────────────────────────
    # 结论生成（规则模板优先；LLM 仅在用户开启时调）
    # ──────────────────────────────────────────────────────
    def _generate_conclusion(
        self,
        step: Dict[str, Any],
        data: List[Dict[str, Any]],
        status: str,
        prior_results: List[Dict[str, Any]],
        llm_enabled: bool,
    ) -> str:
        title = step.get("title", step.get("step_type"))
        metric_key = step.get("metric_key", "delivered_units")
        metric_cfg = METRIC_DIMENSION_MATRIX.get(metric_key, METRIC_DIMENSION_MATRIX["delivered_units"])
        unit = metric_cfg.get("unit", "")

        if not data:
            return f"【{title}】未取到数据，请检查时间窗或权限。"

        # 1. overall_kpi：有 fulfillment_rate
        if step.get("step_type") == "overall_kpi":
            row = data[0]
            actual = row.get("actual", 0)
            plan = row.get("plan", 0)
            rate = row.get("fulfillment_rate")
            if rate is not None:
                rate_pct = round(float(rate) * 100, 2)
                if status == "bad":
                    return f"【{title}】实际 {self._fmt(actual)} {unit}，目标 {self._fmt(plan)} {unit}，达成率 {rate_pct}%，低于警戒线 {step.get('threshold', {}).get('bad', 0.85) * 100:.0f}%。"
                elif status == "warn":
                    return f"【{title}】实际 {self._fmt(actual)} {unit}，目标 {self._fmt(plan)} {unit}，达成率 {rate_pct}%，需重点关注。"
                else:
                    return f"【{title}】实际 {self._fmt(actual)} {unit}，目标 {self._fmt(plan)} {unit}，达成率 {rate_pct}%，达成预期。"
            return f"【{title}】实际 {self._fmt(actual)} {unit}（无目标对比）。"

        # 2. horizontal_compare：列出 Top 3
        if step.get("step_type") == "horizontal_compare":
            top = data[:3]
            ranking = " > ".join(
                [f"{list(row.values())[0]} {self._fmt(list(row.values())[1])}"
                 for row in top if len(row) >= 2]
            )
            return f"【{title}】横向对比结果：{ranking}。"

        # 3. drill_down：找最小项
        if step.get("step_type") == "drill_down":
            if not data:
                return f"【{title}】未发现异常项。"
            worst = min(data, key=lambda r: list(r.values())[-1] if r else 0)
            worst_key = list(worst.keys())[0]
            worst_val = list(worst.values())[0]
            worst_metric = list(worst.values())[-1]
            return f"【{title}】最薄弱项：{worst_key}={worst_val}（{self._fmt(worst_metric)} {unit}），建议优先诊断。"

        # 4. cross_attribution
        if step.get("step_type") == "cross_attribution":
            top = data[:3]
            parts = []
            for row in top:
                parts.append(f"{list(row.values())[0]} 贡献 {list(row.values())[-1]}%")
            return f"【{title}】归因贡献 Top3：" + " / ".join(parts) + "。"

        # 5. anomaly_alert
        if step.get("step_type") == "anomaly_alert":
            anomalies = [r for r in data if r.get("anomaly_level") in ("extreme", "warn")]
            if not anomalies:
                return f"【{title}】未发现显著异常。"
            top = anomalies[:2]
            return f"【{title}】发现 {len(anomalies)} 项异常：" + \
                "；".join([f"{list(r.values())[0]} z={r.get('z_score', 0)}" for r in top]) + "。"

        # 6. yoy_compare / period_compare
        if step.get("step_type") in ("yoy_compare", "period_compare"):
            row = data[0]
            cur = row.get("current_actual", 0)
            prior = row.get("prior_actual", 0)
            delta = row.get("delta_pct")
            if delta is not None:
                arrow = "↑" if float(delta) > 0 else "↓"
                return f"【{title}】本期 {self._fmt(cur)} {unit}，上期 {self._fmt(prior)} {unit}，{arrow} {abs(float(delta)):.2f}%。"
            return f"【{title}】本期 {self._fmt(cur)} {unit}，上期 {self._fmt(prior)} {unit}。"

        # 兜底
        return f"【{title}】查询到 {len(data)} 行数据。"

    # ──────────────────────────────────────────────────────
    # 策略建议（基于上游 step）
    # ──────────────────────────────────────────────────────
    def _generate_strategy_recommendation(
        self,
        step: Dict[str, Any],
        upstream: Optional[Dict[str, Any]],
        template: Dict[str, Any],
    ) -> str:
        title = step.get("title", "策略建议")
        if not upstream:
            return f"【{title}】未找到上游 step 输出，无法生成建议。请检查 SOP 链路配置。"

        upstream_conclusion = upstream.get("conclusion", "")
        upstream_data = upstream.get("data") or []

        # 简化规则：基于 upstream 数据直接给可执行建议
        if upstream.get("step_type") == "drill_down" and upstream_data:
            worst = min(upstream_data, key=lambda r: list(r.values())[-1] if r else 0)
            target_key = list(worst.keys())[0]
            target_val = list(worst.values())[0]
            return (
                f"【{title}】基于 {upstream.get('title')} 的定位结果，建议：\n"
                f"  ① 立即对 {target_key}（{target_val}）启动专项经营诊断；\n"
                f"  ② 复盘该细项的当期市场策略、终端促销、库存周转；\n"
                f"  ③ 建议 2 周内提交经营改善计划至集团运营中心。"
            )
        if upstream.get("step_type") == "anomaly_alert" and upstream_data:
            extreme = [r for r in upstream_data if r.get("anomaly_level") == "extreme"][:2]
            if extreme:
                items = "、".join([str(list(r.values())[0]) for r in extreme])
                return f"【{title}】基于异常告警，建议对 {items} 等极端偏离项启动专项核查。"
            return f"【{title}】异常项均在可控范围，建议保持监控。"
        # 兜底
        return f"【{title}】基于 {upstream.get('title')}：{upstream_conclusion}"

    # ──────────────────────────────────────────────────────
    # 高管摘要
    # ──────────────────────────────────────────────────────
    def _generate_executive_summary(self, report: List[Dict[str, Any]]) -> str:
        bad_steps = [r for r in report if r.get("status") == "bad"]
        warn_steps = [r for r in report if r.get("status") == "warn"]
        ok_steps = [r for r in report if r.get("status") == "ok"]
        n = len(report)
        if bad_steps:
            return (
                f"诊断结果：{n} 步 SOP 中 {len(bad_steps)} 步异常、{len(warn_steps)} 步预警、{len(ok_steps)} 步正常。"
                f"重点关注：" + "；".join([s["title"] for s in bad_steps[:2]]) + "。"
            )
        if warn_steps:
            return f"诊断结果：{n} 步 SOP 中 {len(warn_steps)} 步需关注，建议跟进。"
        return f"诊断结果：{n} 步 SOP 全部正常，无显著风险。"

    # ──────────────────────────────────────────────────────
    # 辅助
    # ──────────────────────────────────────────────────────
    def _extract_metrics(
        self,
        step: Dict[str, Any],
        data: List[Dict[str, Any]],
        metric_key: str,
    ) -> Dict[str, Any]:
        if not data:
            return {}
        row = data[0]
        m: Dict[str, Any] = {}
        for k, v in row.items():
            if isinstance(v, (int, float)):
                m[k] = v
        return m

    @staticmethod
    def _fmt(v: Any) -> str:
        if v is None:
            return "-"
        try:
            n = float(v)
            if abs(n) >= 1e8:
                return f"{n / 1e8:.2f}亿"
            if abs(n) >= 1e4:
                return f"{n / 1e4:.2f}万"
            return f"{n:,.0f}" if n == int(n) else f"{n:.2f}"
        except (TypeError, ValueError):
            return str(v)
