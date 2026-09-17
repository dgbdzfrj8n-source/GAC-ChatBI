"""
广汽云 ChatBI 汽车销量达成异常归因 SOP 引擎
实施手册 Sprint 4 核心模块

设计目标：
传统 ChatBI 只能查出"AION Y 3月未达标"，本引擎的高级能力是
自动执行四步下钻归因 SOP，为经营决策提供可行动的策略建议。

SOP 流程：
  第 1 步：大盘对标 —— 计算品牌整体销量缺口
  第 2 步：维度下钻 —— 自动下钻车型与大区，定位最大缺口
  第 3 步：跨域归因 —— 关联营销投放、终端客流、竞品折扣
  第 4 步：策略建议 —— 生成针对性可执行策略
"""

import os
import re
from typing import Dict, Any, List, Optional
from core.sql_executor import SqlExecutor
from core.metrics_dict import load_metrics


# ─── P0：归因维度 → 表字段 映射表（用于动态 SQL 构建） ─────────────────
DIMENSION_FIELD_MAP: Dict[str, str] = {
    "brand_name":    "brand_name",
    "region_name":   "region_name",
    "model_name":    "model_name",
    "energy_type":   "energy_type",
    "price_segment": "price_segment",
    "monthly":       "STRFTIME('%Y-%m', sale_date)",
}

# 维度中文标签（用于归因明细输出）
DIMENSION_LABEL_MAP: Dict[str, str] = {
    "brand_name":    "品牌",
    "region_name":   "区域",
    "model_name":    "车型",
    "energy_type":   "能源类型",
    "price_segment": "价格段",
    "monthly":       "时间",
}


class SopAnalyzer:
    """
    四步归因 SOP 引擎：
    1. 大盘对标（Brand Gap Analysis）
    2. 维度下钻（Dimension Drill-Down: Model × Region）
    3. 跨域归因（Cross-Domain Attribution）
    4. 策略建议（Actionable Recommendations）
    """

    def __init__(self):
        self.executor = SqlExecutor()
        self.metrics = load_metrics()

    def analyze_fulfillment_gap(
        self,
        brand_name: str,
        year_month: str,
        threshold_pct: float = 95.0,
        selected_dimensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        执行完整的四步归因 SOP。

        Args:
            brand_name: 品牌名称（如 "广汽埃安"）
            year_month: 分析月份（格式 YYYY-MM）
            threshold_pct: 达成率预警阈值，默认 95%
            selected_dimensions: 用户选定的归因维度列表（None 则使用默认 3 个）

        Returns:
            包含四步结果 + 归因贡献明细 的完整归因报告
        """
        # 默认维度
        if not selected_dimensions:
            selected_dimensions = ["brand_name", "region_name", "model_name"]

        # 维度白名单过滤，防止 SQL 注入
        valid_dims = [d for d in selected_dimensions if d in DIMENSION_FIELD_MAP]
        if not valid_dims:
            valid_dims = ["brand_name", "region_name", "model_name"]

        steps = []

        # ─── 第 1 步：大盘对标 ───────────────────────────────────────
        gap_report = self._step1_brand_gap(brand_name, year_month)
        # 注入 brand/year_month 上下文供下游步骤使用
        gap_report["brand"] = brand_name
        gap_report["year_month"] = year_month
        steps.append(gap_report)

        # 第 2 步：维度下钻（若大盘未达标）—— 用用户选定的维度动态构建
        drill_report = None
        attribution_breakdown: List[Dict[str, Any]] = []
        if gap_report["fulfillment_rate_pct"] < threshold_pct:
            drill_report = self._step2_drill_down_dynamic(
                brand_name, year_month, valid_dims
            )
            steps.append(drill_report)

            # ⭐ P0 新增：算归因贡献明细（指标波动 = 各维度贡献之和 + 占比）
            attribution_breakdown = self._compute_attribution_breakdown(
                brand_name, year_month, valid_dims
            )

        # 第 3 步：跨域归因
        attribution_report = None
        if drill_report:
            attribution_report = self._step3_cross_domain(
                brand_name, year_month,
                worst_model=drill_report.get("worst_model"),
                worst_region=drill_report.get("worst_region")
            )
            steps.append(attribution_report)

        # 第 4 步：策略建议（注入归因明细进每条建议）
        recommendation_report = self._step4_recommendations(
            gap_report, drill_report, attribution_report, attribution_breakdown
        )
        steps.append(recommendation_report)

        return {
            "brand": brand_name,
            "year_month": year_month,
            "fulfillment_rate_pct": gap_report["fulfillment_rate_pct"],
            "gap_units": gap_report["gap_units"],
            "gap_reason": gap_report["gap_reason"],
            "steps": steps,
            "selected_dimensions": valid_dims,
            "attribution_breakdown": attribution_breakdown,
            "executive_summary": self._build_executive_summary(gap_report, drill_report, attribution_report, recommendation_report, attribution_breakdown)
        }

    # ─── ⭐ P0 新增：动态维度下钻（替代原硬编码的 _step2_drill_down） ────────
    def _step2_drill_down_dynamic(
        self,
        brand_name: str,
        year_month: str,
        selected_dimensions: List[str]
    ) -> Dict[str, Any]:
        """
        根据用户选定的维度动态构建下钻 SQL，输出每个维度的贡献排名。
        """
        prev_month = self._prev_month(year_month)
        per_dim_results: Dict[str, List[Dict[str, Any]]] = {}

        for dim_key in selected_dimensions:
            dim_field = DIMENSION_FIELD_MAP[dim_key]
            dim_label = DIMENSION_LABEL_MAP[dim_key]

            # 取本期和上期对比数据
            sql = f"""
            WITH curr AS (
                SELECT {dim_field} AS dim_value, SUM(delivered_units) AS curr_units
                FROM fact_sales_daily
                WHERE brand_name = '{brand_name}'
                  AND STRFTIME('%Y-%m', sale_date) = '{year_month}'
                GROUP BY {dim_field}
            ),
            prev AS (
                SELECT {dim_field} AS dim_value, SUM(delivered_units) AS prev_units
                FROM fact_sales_daily
                WHERE brand_name = '{brand_name}'
                  AND STRFTIME('%Y-%m', sale_date) = '{prev_month}'
                GROUP BY {dim_field}
            )
            SELECT
                COALESCE(c.dim_value, p.dim_value) AS dim_value,
                COALESCE(c.curr_units, 0) AS curr_units,
                COALESCE(p.prev_units, 0) AS prev_units,
                (COALESCE(c.curr_units, 0) - COALESCE(p.prev_units, 0)) AS delta
            FROM curr c
            FULL OUTER JOIN prev p ON c.dim_value = p.dim_value
            ORDER BY curr_units DESC
            """
            res = self.executor.execute_query(sql)
            if res.get("success") and res.get("data"):
                per_dim_results[dim_key] = res["data"]

        # 兼容性字段：保留 worst_model / worst_region 给 step3 使用
        worst_model = None
        worst_region = None
        if "model_name" in per_dim_results and per_dim_results["model_name"]:
            # delta 最小（下滑最多）的车型
            worst_model = min(
                per_dim_results["model_name"],
                key=lambda x: x.get("delta", 0)
            ).get("dim_value")
        if "region_name" in per_dim_results and per_dim_results["region_name"]:
            worst_region = min(
                per_dim_results["region_name"],
                key=lambda x: x.get("delta", 0)
            ).get("dim_value")

        # 找出最大贡献和最弱大区（保留原有逻辑，给前端展示用）
        top_model = (
            per_dim_results.get("model_name", [{}])[0].get("dim_value")
            if per_dim_results.get("model_name") else None
        )
        top_region = (
            per_dim_results.get("region_name", [{}])[0].get("dim_value")
            if per_dim_results.get("region_name") else None
        )

        return {
            "step": 2,
            "step_name": "维度下钻（自定义）",
            "status": "success",
            "selected_dimensions": selected_dimensions,
            "per_dimension": [
                {
                    "dimension_key": k,
                    "dimension_label": DIMENSION_LABEL_MAP.get(k, k),
                    "rows": per_dim_results.get(k, [])
                } for k in selected_dimensions
            ],
            "worst_model": worst_model,
            "worst_region": worst_region,
            "top_model": top_model,
            "top_region": top_region
        }

    # ─── ⭐ P0 新增：归因贡献明细（核心算法） ─────────────────────────
    def _compute_attribution_breakdown(
        self,
        brand_name: str,
        year_month: str,
        selected_dimensions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        核心算法：对每个用户选定的维度，计算该维度对当期指标波动的贡献量与占比。

        公式：
            维度贡献量 = 该维度当期销量 - 该维度上期销量
            总波动量 = 品牌当期总销量 - 品牌上期总销量
            贡献占比 = 维度贡献量 / 总波动量 × 100%

        输出格式符合方案：
            "广丰本月销量较上月下滑 1,200 辆，其中：
             ① 华南区域贡献 -800 辆（66.7%，当地新能源渗透率上升）
             ② 轿车品类贡献 -500 辆（41.7%，雷凌改款换代）
             ③ SUV新品增量 +100 辆（-8.3%，新车上市对冲）"
        """
        prev_month = self._prev_month(year_month)

        # 1. 先算总波动量（基准）
        total_sql = f"""
        SELECT
            SUM(CASE WHEN STRFTIME('%Y-%m', sale_date) = '{year_month}' THEN delivered_units ELSE 0 END) AS curr_total,
            SUM(CASE WHEN STRFTIME('%Y-%m', sale_date) = '{prev_month}' THEN delivered_units ELSE 0 END) AS prev_total
        FROM fact_sales_daily
        WHERE brand_name = '{brand_name}'
          AND STRFTIME('%Y-%m', sale_date) IN ('{year_month}', '{prev_month}')
        """
        total_res = self.executor.execute_query(total_sql)
        if not total_res.get("success") or not total_res.get("data"):
            return []
        total_curr = total_res["data"][0].get("curr_total") or 0
        total_prev = total_res["data"][0].get("prev_total") or 0
        total_delta = total_curr - total_prev
        if total_delta == 0:
            return []  # 没有波动则不归因

        # 2. 对每个维度算贡献
        breakdown: List[Dict[str, Any]] = []
        for dim_key in selected_dimensions:
            dim_field = DIMENSION_FIELD_MAP[dim_key]
            dim_label = DIMENSION_LABEL_MAP[dim_key]

            sql = f"""
            WITH curr AS (
                SELECT {dim_field} AS dim_value, SUM(delivered_units) AS units
                FROM fact_sales_daily
                WHERE brand_name = '{brand_name}'
                  AND STRFTIME('%Y-%m', sale_date) = '{year_month}'
                GROUP BY {dim_field}
            ),
            prev AS (
                SELECT {dim_field} AS dim_value, SUM(delivered_units) AS units
                FROM fact_sales_daily
                WHERE brand_name = '{brand_name}'
                  AND STRFTIME('%Y-%m', sale_date) = '{prev_month}'
                GROUP BY {dim_field}
            )
            SELECT
                COALESCE(c.dim_value, p.dim_value) AS dim_value,
                COALESCE(c.units, 0) - COALESCE(p.units, 0) AS contribution
            FROM curr c
            FULL OUTER JOIN prev p ON c.dim_value = p.dim_value
            """
            res = self.executor.execute_query(sql)
            if not res.get("success") or not res.get("data"):
                continue

            # 取贡献绝对值最大的 Top 3 成员
            sorted_rows = sorted(
                res["data"],
                key=lambda x: abs(x.get("contribution", 0) or 0),
                reverse=True
            )[:3]

            for row in sorted_rows:
                contribution = row.get("contribution") or 0
                if abs(contribution) < 1:  # 跳过无显著变化的
                    continue
                pct = round(contribution / abs(total_delta) * 100, 1) if total_delta != 0 else 0
                breakdown.append({
                    "dimension_key": dim_key,
                    "dimension_label": dim_label,
                    "member": row.get("dim_value") or "未知",
                    "contribution": int(contribution),
                    "contribution_pct": pct,
                    "reason": self._infer_reason(dim_key, contribution)
                })

        # 按贡献绝对值排序
        breakdown.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        return breakdown[:6]  # 最多展示 6 条

    def _infer_reason(self, dim_key: str, contribution: int) -> str:
        """根据维度+方向给出归因推断（简化版，避免 LLM 调用的延迟）"""
        direction = "下滑" if contribution < 0 else "增长"
        reason_map = {
            "brand_name":    f"该品牌{direction} {abs(contribution)} 辆（结构性占比变化）",
            "region_name":   f"该区域{direction} {abs(contribution)} 辆（终端需求波动）",
            "model_name":    f"该车型{direction} {abs(contribution)} 辆（产品周期/竞品冲击）",
            "energy_type":   f"该能源类型{direction} {abs(contribution)} 辆（市场结构迁移）",
            "price_segment": f"该价格段{direction} {abs(contribution)} 辆（消费偏好变化）",
            "monthly":       f"该时段{direction} {abs(contribution)} 辆（季节性/节庆效应）",
        }
        return reason_map.get(dim_key, f"变动 {abs(contribution)} 辆")

    def _step1_brand_gap(self, brand_name: str, year_month: str) -> Dict[str, Any]:
        """
        第 1 步：大盘对标
        计算品牌销量缺口：目标 vs 实际，达成率，缺口量级评级
        """
        sql = f"""
        WITH s_agg AS (
            SELECT 
                SUM(delivered_units) AS actual_units
            FROM fact_sales_daily
            WHERE brand_name = '{brand_name}'
              AND STRFTIME('%Y-%m', sale_date) = '{year_month}'
        ),
        b_target AS (
            SELECT target_units
            FROM dim_budget_target
            WHERE brand_name = '{brand_name}' AND year_month = '{year_month}'
        )
        SELECT 
            s.actual_units,
            b.target_units,
            ROUND(s.actual_units * 100.0 / NULLIF(b.target_units, 0), 2) AS fulfillment_rate_pct,
            (b.target_units - s.actual_units) AS gap_units
        FROM s_agg s, b_target b
        """
        res = self.executor.execute_query(sql)
        if not res["success"] or not res["data"]:
            return {
                "step": 1,
                "step_name": "大盘对标",
                "status": "error",
                "error": res.get("error", "查询无结果")
            }

        row = res["data"][0]
        actual = row["actual_units"] or 0
        target = row["target_units"] or 0
        rate = row["fulfillment_rate_pct"] or 0.0
        gap = row["gap_units"] or 0

        if rate >= 100:
            grade = "达标"
            reason = f"当期表现优秀，超额交付 {abs(gap):,} 辆"
        elif rate >= 95:
            grade = "基本达标"
            reason = f"达成率 {rate}%，略低于目标，缺口仅 {gap:,} 辆，属正常波动范围"
        elif rate >= 85:
            grade = "未达标-轻度"
            reason = f"达成率 {rate}%，缺口 {gap:,} 辆，需要关注"
        else:
            grade = "未达标-严重"
            reason = f"达成率仅 {rate}%，缺口高达 {gap:,} 辆，触发深度归因"

        return {
            "step": 1,
            "step_name": "大盘对标",
            "status": "success",
            "actual_units": actual,
            "target_units": target,
            "fulfillment_rate_pct": rate,
            "gap_units": gap,
            "grade": grade,
            "gap_reason": reason
        }

    def _step2_drill_down(self, brand_name: str, year_month: str) -> Optional[Dict[str, Any]]:
        """
        第 2 步：维度下钻
        从车型和大区两个维度定位最大缺口贡献者
        """
        # 2a. 车型维度下钻
        model_sql = f"""
        WITH monthly AS (
            SELECT 
                model_name,
                SUM(delivered_units) AS actual_units,
                ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 2) AS avg_price
            FROM fact_sales_daily
            WHERE brand_name = '{brand_name}'
              AND STRFTIME('%Y-%m', sale_date) = '{year_month}'
            GROUP BY model_name
        )
        SELECT 
            model_name,
            actual_units,
            avg_price,
            ROW_NUMBER() OVER (ORDER BY actual_units DESC) AS rank
        FROM monthly
        ORDER BY actual_units DESC
        """
        model_res = self.executor.execute_query(model_sql)

        # 2b. 大区维度下钻
        region_sql = f"""
        SELECT 
            region_name,
            SUM(delivered_units) AS actual_units,
            SUM(customer_leads) AS total_leads,
            ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS conversion_rate
        FROM fact_sales_daily
        WHERE brand_name = '{brand_name}'
          AND STRFTIME('%Y-%m', sale_date) = '{year_month}'
        GROUP BY region_name
        ORDER BY actual_units DESC
        """
        region_res = self.executor.execute_query(region_sql)

        if not model_res["success"] or not region_res["success"]:
            return None

        # 找出最大贡献车型和最弱大区
        worst_model = None
        worst_model_gap_pct = 0.0
        if model_res["data"]:
            # 以第一名为基准，计算其他车型的相对缺口
            top_units = model_res["data"][0]["actual_units"]
            for row in model_res["data"][1:]:
                gap_ratio = (top_units - row["actual_units"]) / top_units
                if gap_ratio > worst_model_gap_pct:
                    worst_model_gap_pct = gap_ratio
                    worst_model = row["model_name"]

        worst_region = None
        worst_region_conv = 100.0
        if region_res["data"]:
            for row in region_res["data"]:
                if row["conversion_rate"] < worst_region_conv:
                    worst_region_conv = row["conversion_rate"]
                    worst_region = row["region_name"]

        return {
            "step": 2,
            "step_name": "维度下钻",
            "status": "success",
            "models": model_res["data"],
            "regions": region_res["data"],
            "worst_model": worst_model,
            "worst_model_gap_ratio": round(worst_model_gap_pct * 100, 1),
            "worst_region": worst_region,
            "worst_region_conversion_rate": worst_region_conv,
            "top_model": model_res["data"][0]["model_name"] if model_res["data"] else None,
            "top_region": region_res["data"][0]["region_name"] if region_res["data"] else None
        }

    def _step3_cross_domain(
        self,
        brand_name: str,
        year_month: str,
        worst_model: Optional[str] = None,
        worst_region: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        第 3 步：跨域归因
        关联营销投放、终端客流、折扣力度三个外部因素
        """
        # 3a. 营销投放情况
        mkt_sql = f"""
        SELECT 
            SUM(expense_amount) AS total_expense,
            SUM(leads_generated) AS total_leads,
            ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 2) AS cpl
        FROM fact_marketing_expenses
        WHERE brand_name = '{brand_name}'
          AND STRFTIME('%Y-%m', expense_date) = '{year_month}'
        """
        mkt_res = self.executor.execute_query(mkt_sql)

        # 3b. 终端客流情况
        leads_sql = f"""
        SELECT 
            SUM(customer_leads) AS total_leads,
            ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS conversion_rate
        FROM fact_sales_daily
        WHERE brand_name = '{brand_name}'
          AND STRFTIME('%Y-%m', sale_date) = '{year_month}'
        """
        leads_res = self.executor.execute_query(leads_sql)

        # 3c. 折扣率情况
        discount_sql = f"""
        SELECT 
            ROUND(AVG(discount_rate) * 100, 2) AS avg_discount_rate_pct
        FROM fact_sales_daily
        WHERE brand_name = '{brand_name}'
          AND STRFTIME('%Y-%m', sale_date) = '{year_month}'
        """
        disc_res = self.executor.execute_query(discount_sql)

        # 3d. 与上月环比客流变化（归因关键线索）
        prev_month = self._prev_month(year_month)
        leads_trend_sql = f"""
        SELECT 
            SUM(CASE WHEN STRFTIME('%Y-%m', sale_date) = '{year_month}' THEN customer_leads ELSE 0 END) AS curr_leads,
            SUM(CASE WHEN STRFTIME('%Y-%m', sale_date) = '{prev_month}' THEN customer_leads ELSE 0 END) AS prev_leads
        FROM fact_sales_daily
        WHERE brand_name = '{brand_name}'
        """
        trend_res = self.executor.execute_query(leads_trend_sql)

        findings = []
        if trend_res["success"] and trend_res["data"]:
            curr = trend_res["data"][0]["curr_leads"] or 0
            prev = trend_res["data"][0]["prev_leads"] or 0
            if prev > 0:
                change_pct = round((curr - prev) / prev * 100, 1)
                if abs(change_pct) > 10:
                    direction = "下滑" if change_pct < 0 else "增长"
                    findings.append(f"当期进店客流环比{direction} {abs(change_pct)}%，是销量缺口的关键归因线索")

        if mkt_res["success"] and mkt_res["data"]:
            row = mkt_res["data"][0]
            findings.append(f"本期营销总投入 {row['total_expense'] or 0:,.0f} 元，带来留资线索 {row['total_leads'] or 0:,} 条，CPL {row['cpl'] or 0:.0f} 元/条")

        if disc_res["success"] and disc_res["data"]:
            findings.append(f"终端平均折扣率 {disc_res['data'][0]['avg_discount_rate_pct'] or 0:.1f}%")

        return {
            "step": 3,
            "step_name": "跨域归因",
            "status": "success",
            "marketing_spend": mkt_res["data"][0] if mkt_res["success"] and mkt_res["data"] else None,
            "terminal_leads": leads_res["data"][0] if leads_res["success"] and leads_res["data"] else None,
            "avg_discount_rate": disc_res["data"][0] if disc_res["success"] and disc_res["data"] else None,
            "leads_trend_vs_prev_month": trend_res["data"][0] if trend_res["success"] and trend_res["data"] else None,
            "findings": findings
        }

    def _step4_recommendations(
        self,
        gap_report: Dict[str, Any],
        drill_report: Optional[Dict[str, Any]],
        attribution_report: Optional[Dict[str, Any]],
        attribution_breakdown: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        第 4 步：策略建议
        基于前 3 步分析结果 + 归因贡献明细，生成可执行的经营策略建议
        每条建议会附带 attribution_detail（方案要求的格式）
        """
        recommendations = []
        urgency = "低"
        attribution_breakdown = attribution_breakdown or []

        if gap_report.get("fulfillment_rate_pct", 100) >= 95:
            recommendations.append({
                "type": "保持",
                "priority": "低",
                "action": f"继续保持当期经营节奏，{gap_report['brand']} 达成率稳健",
                "budget_impact": "无需调整",
                "attribution_detail": []
            })
        else:
            urgency = "高" if gap_report.get("fulfillment_rate_pct", 100) < 85 else "中"
            # 取归因明细中绝对值最大的前 3 条作为本建议的 detail
            top_attribution = attribution_breakdown[:3] if attribution_breakdown else []
            recommendations.append({
                "type": "短期促销",
                "priority": "高",
                "action": f"针对{gap_report['brand']}全系追加限时置换补贴 3,000~5,000 元/台，激活存量客户换购需求",
                "budget_impact": f"预计追加营销费用 {int(gap_report.get('gap_units', 0) * 3000):,} 元",
                # ⭐ P0 新增：归因明细（符合方案要求格式）
                "attribution_detail": top_attribution
            })

        if drill_report and drill_report.get("worst_model"):
            recommendations.append({
                "type": "车型专项",
                "priority": "中",
                "action": f"对 {drill_report['worst_model']} 启动专项购车节活动，配合区域商圈巡展提升曝光",
                "budget_impact": "从费用预算中调剂 10~15%",
                "attribution_detail": []
            })

        if drill_report and drill_report.get("worst_region"):
            recommendations.append({
                "type": "区域下沉",
                "priority": "中",
                "action": f"加强 {drill_report['worst_region']} 渠道渗透，增派外展外拓团队，缩短成交决策链路",
                "budget_impact": "调用 dim_budget_target 中 expense_limit 的 5~8%",
                "attribution_detail": []
            })

        if attribution_report:
            for finding in attribution_report.get("findings", []):
                if "客流下滑" in finding or "下滑" in finding:
                    recommendations.append({
                        "type": "获客增强",
                        "priority": "高",
                        "action": "客流进店量下滑是核心根因，建议增加线上信息流投放（懂车帝/抖音），并激活老客户裂变",
                        "budget_impact": "增投 15~20 万元信息流",
                        "attribution_detail": []
                    })
                    break

        return {
            "step": 4,
            "step_name": "策略建议",
            "status": "success",
            "urgency": urgency,
            "recommendations": recommendations
        }

    def _prev_month(self, year_month: str) -> str:
        """计算上一个月的 YYYY-MM 格式"""
        year, month = map(int, year_month.split("-"))
        if month == 1:
            return f"{year - 1}-12"
        return f"{year}-{month - 1:02d}"

    def _build_executive_summary(
        self,
        gap_report: Dict[str, Any],
        drill_report: Optional[Dict[str, Any]],
        attribution_report: Optional[Dict[str, Any]],
        recommendation_report: Dict[str, Any],
        attribution_breakdown: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """生成高管可读的经营归因摘要（⭐ P0 包含归因贡献明细格式）"""
        lines = []
        lines.append(f"【{gap_report['brand']} {gap_report['year_month']} 经营归因摘要】")
        lines.append(f"整体达成率 {gap_report.get('fulfillment_rate_pct', 0)}%，{gap_report.get('gap_reason', '')}")

        if drill_report:
            lines.append(f"下钻发现：{drill_report.get('top_model')} 为主力支撑车型，{drill_report.get('worst_model')} 贡献最大缺口")
            if drill_report.get("worst_region"):
                lines.append(f"区域维度：{drill_report.get('worst_region')} 客流转化率最低，需重点关注")

        # ⭐ P0 新增：归因贡献明细输出（符合方案要求："指标波动 = 各维度贡献之和 + 占比"）
        if attribution_breakdown:
            lines.append("")
            lines.append("【归因贡献明细】")
            gap_units = gap_report.get("gap_units", 0) or 0
            # 区分正贡献（拉低缺口）和负贡献（拉高缺口）
            for idx, item in enumerate(attribution_breakdown[:6], 1):
                arrow = "①" if idx == 1 else ("②" if idx == 2 else ("③" if idx == 3 else f"({idx})"))
                lines.append(
                    f"{arrow} {item['dimension_label']}·{item['member']} "
                    f"贡献 {item['contribution']:+,} 辆 "
                    f"（占比 {item['contribution_pct']:+.1f}%，{item['reason']}）"
                )

        if attribution_report:
            for f in attribution_report.get("findings", []):
                lines.append(f"归因线索：{f}")

        if recommendation_report.get("recommendations"):
            top_rec = recommendation_report["recommendations"][0]
            lines.append(f"首要建议（{top_rec['priority']}/紧急度-{recommendation_report.get('urgency', '中')}）：{top_rec['action']}")

        return "\n".join(lines)


def run_quick_sop_demo():
    """快速 SOP 演示（用于测试与 Demo）"""
    analyzer = SopAnalyzer()

    # 模拟一个未达标的月份进行完整 SOP 分析
    report = analyzer.analyze_fulfillment_gap(
        brand_name="广汽埃安",
        year_month="2025-03",
        threshold_pct=95.0
    )

    print("=" * 70)
    print("  四步归因 SOP 执行报告")
    print("=" * 70)
    print(f"\n品牌：{report['brand']}，月份：{report['year_month']}")
    print(f"达成率：{report['fulfillment_rate_pct']}%，缺口：{report['gap_units']:,} 辆")
    print(f"\n高管摘要：\n{report['executive_summary']}")

    for step in report["steps"]:
        print(f"\n{'─' * 40}")
        print(f"  第 {step['step']} 步：{step['step_name']}")
        if step["status"] == "error":
            print(f"  ⚠ {step.get('error')}")
        else:
            if step["step"] == 1:
                print(f"  实际交付：{step['actual_units']:,} 辆 | 目标：{step['target_units']:,} 辆")
                print(f"  评级：{step['grade']} | 原因：{step['gap_reason']}")
            elif step["step"] == 2:
                print(f"  车型排名（Top3）：")
                for m in step["models"][:3]:
                    print(f"    {m['rank']}. {m['model_name']}: {m['actual_units']:,} 辆")
                print(f"  最大缺口车型：{step['worst_model']}（相对 Top1 缺口 {step['worst_model_gap_ratio']}%）")
                print(f"  转化率最低大区：{step['worst_region']}（{step['worst_region_conversion_rate']}%）")
            elif step["step"] == 3:
                print(f"  归因发现：")
                for f in step["findings"]:
                    print(f"    • {f}")
            elif step["step"] == 4:
                print(f"  紧急度：{step['urgency']}")
                for rec in step["recommendations"]:
                    print(f"    [{rec['type']}/{rec['priority']}] {rec['action']}")
                    print(f"    预算影响：{rec['budget_impact']}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_quick_sop_demo()
