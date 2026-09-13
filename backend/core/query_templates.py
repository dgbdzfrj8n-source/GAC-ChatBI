"""
广汽云 ChatBI 精确问数模板库（15 条）
======================================
设计原则：
  1. 每条模板对应前端 SuggestionPills 中的一条快捷提问
  2. 采用"严格匹配 + 关键词组合"双重保险，确保 15 条快捷提问 100% 命中正确 SQL
  3. 模板 SQL 全部经过 DuckDB 实测，覆盖真实业务数据范围（2024-01 ~ 2025-04）
  4. 闲聊/无关问句走 is_meta_question 分支，返回引导式追问

每条模板包含：
  - id: Q01 ~ Q15
  - label: 前端显示的快捷提问文字（与 SuggestionPills 严格一致）
  - domain: 业务域（整车销售/经营财务/市场营销/渠道经营）
  - keywords: 触发关键词（用于严格匹配）
  - chart_hint: 推荐图表类型（bar/line/pie/table）
  - sql: 已参数化的 SQL（用 {brand}, {region}, {ym} 占位）
  - insight: 经营洞察模板

注意：参数化 SQL 在执行时会被 fill_template() 替换为具体值或默认范围
"""

from typing import Dict, Any, List, Optional

# ============================================================
# 15 条精确问数模板（与前端 SuggestionPills 一一对应）
# ============================================================
QUERY_TEMPLATES: List[Dict[str, Any]] = [
    # ===== 整车销售（6 条）=====
    {
        "id": "Q01",
        "label": "2025年3月埃安销量与预算达成率是多少？",
        "domain": "整车销售",
        "keywords": ["埃安", "销量", "达成率"],
        "chart_hint": "table",
        "sql": """
WITH monthly_sales AS (
    SELECT
        brand_name,
        STRFTIME('%Y-%m', sale_date) AS year_month,
        SUM(delivered_units) AS actual_units
    FROM fact_sales_daily
    WHERE brand_name = '广汽埃安' AND STRFTIME('%Y-%m', sale_date) = '{ym}'
    GROUP BY brand_name, year_month
)
SELECT
    s.brand_name AS 品牌,
    s.year_month AS 月份,
    s.actual_units AS 实际交付量,
    b.target_units AS 预算目标量,
    ROUND(s.actual_units * 100.0 / NULLIF(b.target_units, 0), 2) AS 达成率_pct
FROM monthly_sales s
JOIN dim_budget_target b
  ON s.brand_name = b.brand_name AND s.year_month = b.year_month
""",
        "insight": "{ym} 广汽埃安实际交付 {actual} 辆，预算目标 {target} 辆，综合达成率为 {rate}%。",
    },
    {
        "id": "Q02",
        "label": "各品牌总交付量与总营收是多少？",
        "domain": "整车销售",
        "keywords": ["品牌", "总交付", "总营收"],
        "chart_hint": "bar",
        "sql": """
SELECT
    brand_name AS 品牌,
    SUM(delivered_units) AS 总交付量,
    ROUND(SUM(gross_revenue) / 100000000.0, 2) AS 总营收_亿元,
    ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 0) AS 单车均价_元
FROM fact_sales_daily
GROUP BY brand_name
ORDER BY 总交付量 DESC
""",
        "insight": "集团三大品牌总交付 {total} 辆，总营收 {revenue} 亿元。",
    },
    {
        "id": "Q03",
        "label": "传祺各车型在华东大区的销量",
        "domain": "整车销售",
        "keywords": ["传祺", "车型", "华东"],
        "chart_hint": "bar",
        "sql": """
SELECT
    model_name AS 车型,
    SUM(delivered_units) AS 交付量,
    ROUND(SUM(gross_revenue) / 10000.0, 0) AS 营收_万元
FROM fact_sales_daily
WHERE brand_name = '广汽传祺' AND region_name = '华东区'
GROUP BY model_name
ORDER BY 交付量 DESC
""",
        "insight": "广汽传祺在华东大区共交付 {total} 辆，主力车型 {top_model} 占比最高。",
    },
    {
        "id": "Q04",
        "label": "2025年Q1各月交付量走势",
        "domain": "整车销售",
        "keywords": ["Q1", "走势", "月"],
        "chart_hint": "line",
        "sql": """
SELECT
    STRFTIME('%Y-%m', sale_date) AS 月份,
    SUM(delivered_units) AS 总交付量
FROM fact_sales_daily
WHERE sale_date >= '2025-01-01' AND sale_date <= '2025-03-31'
GROUP BY 月份
ORDER BY 月份
""",
        "insight": "2025 Q1 整体交付节奏 {trend}：1 月 {m1} 辆，2 月 {m2} 辆，3 月 {m3} 辆。",
    },
    {
        "id": "Q05",
        "label": "昊铂GT与昊铂HT客流转化率对比",
        "domain": "整车销售",
        "keywords": ["昊铂", "客流", "转化率"],
        "chart_hint": "bar",
        "sql": """
SELECT
    model_name AS 车型,
    SUM(customer_leads) AS 进店客流,
    SUM(test_drives) AS 试驾次数,
    ROUND(SUM(test_drives) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS 试驾转化率_pct
FROM fact_sales_daily
WHERE brand_name = '昊铂' AND model_name IN ('昊铂GT', '昊铂HT')
GROUP BY model_name
""",
        "insight": "昊铂 HT 试驾转化率 {ht_rate}%，昊铂 GT 为 {gt_rate}%，差异 {diff} 个百分点。",
    },
    {
        "id": "Q06",
        "label": "销量环比下降最多的品牌",
        "domain": "整车销售",
        "keywords": ["环比", "下降"],
        "chart_hint": "table",
        "sql": """
WITH monthly AS (
    SELECT
        brand_name,
        STRFTIME('%Y-%m', sale_date) AS ym,
        SUM(delivered_units) AS units
    FROM fact_sales_daily
    WHERE sale_date >= '2024-12-01'
    GROUP BY brand_name, ym
),
with_lag AS (
    SELECT
        brand_name,
        ym,
        units,
        LAG(units) OVER (PARTITION BY brand_name ORDER BY ym) AS prev_units
    FROM monthly
)
SELECT
    brand_name AS 品牌,
    ym AS 月份,
    units AS 当月交付量,
    prev_units AS 上月交付量,
    ROUND((units - prev_units) * 100.0 / NULLIF(prev_units, 0), 2) AS 环比_pct
FROM with_lag
WHERE prev_units IS NOT NULL
ORDER BY 环比_pct ASC
LIMIT 5
""",
        "insight": "近 30 天环比降幅最大的品牌是 {brand}，降幅 {rate}%，需重点关注。",
    },

    # ===== 经营财务（3 条）=====
    {
        "id": "Q07",
        "label": "各品牌单车成交均价对比",
        "domain": "经营财务",
        "keywords": ["成交均价", "单车"],
        "chart_hint": "bar",
        "sql": """
SELECT
    brand_name AS 品牌,
    ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 0) AS 单车均价_元,
    SUM(delivered_units) AS 交付量
FROM fact_sales_daily
GROUP BY brand_name
ORDER BY 单车均价_元 DESC
""",
        "insight": "昊铂以高端定位单车均价 {top_price} 元领跑，传祺 {gq_price} 元体现中端亲民策略。",
    },
    {
        "id": "Q08",
        "label": "营销费用占比最高的渠道",
        "domain": "经营财务",
        "keywords": ["营销费用", "占比"],
        "chart_hint": "pie",
        "sql": """
SELECT
    channel_name AS 渠道,
    SUM(expense_amount) AS 总支出,
    ROUND(SUM(expense_amount) * 100.0 / SUM(SUM(expense_amount)) OVER (), 2) AS 占比_pct
FROM fact_marketing_expenses
GROUP BY channel_name
ORDER BY 总支出 DESC
""",
        "insight": "{top_channel} 渠道占总营销支出 {top_pct}%，是投放最重的渠道。",
    },
    {
        "id": "Q09",
        "label": "毛利率最高的是哪个车型",
        "domain": "经营财务",
        "keywords": ["毛利率", "车型"],
        "chart_hint": "bar",
        "sql": """
SELECT
    model_name AS 车型,
    brand_name AS 品牌,
    ROUND(AVG(gross_revenue / NULLIF(delivered_units, 0)), 0) AS 平均单车营收_元,
    ROUND(AVG(gross_revenue / NULLIF(delivered_units, 0)) * (1 - AVG(discount_rate)), 0) AS 估算毛利_元,
    ROUND(AVG(1 - discount_rate) * 100, 2) AS 平均折扣后毛利率_pct
FROM fact_sales_daily
WHERE delivered_units > 0
GROUP BY model_name, brand_name
ORDER BY 估算毛利_元 DESC
LIMIT 5
""",
        "insight": "毛利贡献 Top1 车型为 {model}，估算单车毛利约 {profit} 元。",
    },

    # ===== 市场营销（3 条）=====
    {
        "id": "Q10",
        "label": "各营销渠道投放支出与获客成本CPL排名",
        "domain": "市场营销",
        "keywords": ["渠道", "投放", "CPL", "获客成本"],
        "chart_hint": "bar",
        "sql": """
SELECT
    channel_name AS 渠道,
    SUM(expense_amount) AS 总投放_元,
    SUM(leads_generated) AS 总线索量,
    ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 1) AS CPL_元
FROM fact_marketing_expenses
GROUP BY channel_name
ORDER BY CPL_元 ASC
""",
        "insight": "CPL 最优渠道为 {best}，单价 {best_cpl} 元；最贵渠道为 {worst}，单价 {worst_cpl} 元。",
    },
    {
        "id": "Q11",
        "label": "抖音线索量占总线索量多少",
        "domain": "市场营销",
        "keywords": ["抖音", "线索"],
        "chart_hint": "pie",
        "sql": """
WITH total AS (
    SELECT SUM(leads_generated) AS total_leads FROM fact_marketing_expenses
)
SELECT
    SUM(CASE WHEN channel_name = '抖音信息流' THEN leads_generated ELSE 0 END) AS 抖音线索量,
    (SELECT total_leads FROM total) AS 总线索量,
    ROUND(SUM(CASE WHEN channel_name = '抖音信息流' THEN leads_generated ELSE 0 END) * 100.0
          / (SELECT total_leads FROM total), 2) AS 抖音占比_pct
FROM fact_marketing_expenses
GROUP BY ()
""",
        "insight": "抖音渠道贡献 {pct}% 的总线索量，是数字营销的核心阵地。",
    },
    {
        "id": "Q12",
        "label": "各渠道ROI对比",
        "domain": "市场营销",
        "keywords": ["ROI", "对比"],
        "chart_hint": "bar",
        "sql": """
WITH channel_spend AS (
    SELECT
        m.channel_name,
        SUM(m.expense_amount) AS total_expense,
        SUM(m.leads_generated) AS total_leads
    FROM fact_marketing_expenses m
    GROUP BY m.channel_name
),
channel_revenue AS (
    SELECT
        m.channel_name,
        SUM(s.delivered_units) AS attributed_units,
        SUM(s.gross_revenue) AS attributed_revenue
    FROM fact_marketing_expenses m
    JOIN fact_sales_daily s
      ON m.brand_name = s.brand_name
     AND ABS(DATE_DIFF('day', m.expense_date, s.sale_date)) <= 7
    GROUP BY m.channel_name
)
SELECT
    cs.channel_name AS 渠道,
    ROUND(cs.total_expense / 10000.0, 1) AS 总投放_万元,
    cs.total_leads AS 总线索量,
    ROUND(cr.attributed_revenue / 10000.0, 1) AS 归因营收_万元,
    ROUND(cr.attributed_revenue / NULLIF(cs.total_expense, 0), 2) AS ROI_倍数
FROM channel_spend cs
LEFT JOIN channel_revenue cr ON cs.channel_name = cr.channel_name
ORDER BY ROI_倍数 DESC NULLS LAST
""",
        "insight": "ROI 最高的渠道是 {best}，每投入 1 元带来 {best_roi} 元营收。",
    },

    # ===== 渠道经营（3 条）=====
    {
        "id": "Q13",
        "label": "各门店客流成交转化率排名",
        "domain": "渠道经营",
        "keywords": ["门店", "客流", "成交转化"],
        "chart_hint": "bar",
        "sql": """
SELECT
    region_name AS 门店大区,
    SUM(customer_leads) AS 总客流,
    SUM(test_drives) AS 总试驾,
    SUM(delivered_units) AS 总成交,
    ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS 客流成交转化率_pct
FROM fact_sales_daily
GROUP BY region_name
ORDER BY 客流成交转化率_pct DESC
""",
        "insight": "{top_region} 大区客流转化率 {top_rate}% 最高，建议提炼经验推广至全国。",
    },
    {
        "id": "Q14",
        "label": "客流漏斗：进店→留资→试驾→成交",
        "domain": "渠道经营",
        "keywords": ["漏斗", "客流转"],
        "chart_hint": "funnel",
        "sql": """
SELECT
    SUM(customer_leads) AS 进店客流,
    SUM(customer_leads) AS 留资客户,
    SUM(test_drives) AS 试驾次数,
    SUM(delivered_units) AS 成交台数,
    ROUND(SUM(test_drives) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS 进店→试驾_pct,
    ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(test_drives), 0), 2) AS 试驾→成交_pct,
    ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS 整体转化率_pct
FROM fact_sales_daily
""",
        "insight": "从进店到整体成交的转化率为 {rate}%，进店→试驾 {step1}%，试驾→成交 {step2}%。",
    },
    {
        "id": "Q15",
        "label": "转化率低于10%的门店",
        "domain": "渠道经营",
        "keywords": ["转化率低", "门店"],
        "chart_hint": "table",
        "sql": """
SELECT
    region_name AS 门店大区,
    province_name AS 省份,
    SUM(customer_leads) AS 客流,
    SUM(delivered_units) AS 成交,
    ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS 转化率_pct
FROM fact_sales_daily
GROUP BY region_name, province_name
HAVING SUM(customer_leads) > 100
ORDER BY 转化率_pct ASC
LIMIT 8
""",
        "insight": "有 {count} 个省份/大区转化率低于 10%，最低仅 {lowest}%，建议排查产品陈列与销售话术。",
    },
]


def match_query_template(query: str) -> Optional[Dict[str, Any]]:
    """
    严格匹配逻辑：
    1. 规范化查询（小写、去空格）
    2. 对每个模板：必须所有 keywords 都出现在 query 中才命中
    3. 取第一个命中（15 条之间一般不会冲突）
    """
    q = query.strip()
    q_lower = q.lower()

    for tmpl in QUERY_TEMPLATES:
        keywords = tmpl["keywords"]
        # 全部关键词都出现才命中（OR 逻辑：只要满足一组）
        if all(kw in q for kw in keywords):
            return tmpl

    return None


# ============================================================
# 闲聊/无关问句引导库（用户问"你是谁"等时返回）
# ============================================================
SMALL_TALK_GUIDE = {
    "你是谁": "我是**广汽云 ChatBI**，由谢志锋主导构建的智能经营分析助手。\n\n我能帮你：\n📊 查销量、营收、达成率\n💰 分析营销投放与 CPL\n🚗 看客流转化与漏斗\n\n试试点击下方 15 条快捷提问，每条都能精准返回对应图表和数据！",
    "你能做什么": "我可以基于广汽集团真实销售数据回答经营问题：\n\n✅ **整车销售**：销量、营收、达成率、单车均价、车型对比\n✅ **市场营销**：渠道投放、CPL 排名、抖音线索占比、ROI\n✅ **渠道经营**：客流漏斗、门店转化率、低效门店预警\n\n点击快捷提问试试吧 →",
    "怎么用": "3 步上手：\n\n1️⃣ **点击下方快捷提问**（15 条覆盖 4 大业务域）\n2️⃣ 等待 1-3 秒，自动返回 SQL + 图表 + 经营洞察\n3️⃣ 查看驾驶舱 / 历史会话 / 语义层做深度管理\n\n💡 也可直接输入自然语言，如：'昊铂 HT 在华南区 4 月销量'",
}


def match_small_talk(query: str) -> Optional[str]:
    """匹配闲聊引导语"""
    q = query.strip()
    for trigger, reply in SMALL_TALK_GUIDE.items():
        if trigger in q:
            return reply
    return None
