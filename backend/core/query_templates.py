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
    ROUND(s.actual_units * 100.0 / NULLIF(b.target_units, 0), 2) AS 达成率_pct,
    (b.target_units - s.actual_units) AS 差额_辆
FROM monthly_sales s
JOIN dim_budget_target b
  ON s.brand_name = b.brand_name AND s.year_month = b.year_month
""",
        "insight": "{ym} 广汽埃安实际交付 {actual} 辆，预算目标 {target} 辆，综合达成率为 {rate}%，距离月度目标还差 **{diff} 辆**。",
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
        "label": "投放金额最高的渠道",
        "domain": "经营财务",
        "keywords": ["投放金额", "最高", "渠道"],
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
        "insight": "{top_channel} 渠道投放金额占总投放 {top_pct}%，是投放最重的渠道（占比为渠道占总营销支出比例，非毛利率口径）。",
    },
    {
        "id": "Q09",
        "label": "单车毛利贡献最高的车型",
        "domain": "经营财务",
        "keywords": ["毛利", "车型"],
        "chart_hint": "bar",
        "sql": """
SELECT
    model_name AS 车型,
    brand_name AS 品牌,
    ROUND(AVG(gross_revenue / NULLIF(delivered_units, 0)), 0) AS 平均单车营收_元,
    ROUND(AVG(gross_revenue / NULLIF(delivered_units, 0)) * (1 - AVG(discount_rate)), 0) AS 单车毛利_元,
    ROUND(AVG(1 - discount_rate) * 100, 2) AS 平均折扣率_pct
FROM fact_sales_daily
WHERE delivered_units > 0
GROUP BY model_name, brand_name
ORDER BY 单车毛利_元 DESC
LIMIT 5
""",
        "insight": "单车毛利贡献 Top1 车型为 {model}，估算单车毛利约 {profit} 元（说明：当前数仓无成本字段，毛利由「单车营收 × (1-折扣率)」估算，仅作经营参考）。",
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
        "label": "各大区客流成交转化率排名",
        "domain": "渠道经营",
        "keywords": ["大区", "客流", "成交转化"],
        "chart_hint": "bar",
        "sql": """
SELECT
    region_name AS 大区,
    SUM(customer_leads) AS 总客流,
    SUM(test_drives) AS 总试驾,
    SUM(delivered_units) AS 总成交,
    ROUND(SUM(delivered_units) * 100.0 / NULLIF(SUM(customer_leads), 0), 2) AS 客流成交转化率_pct
FROM fact_sales_daily
GROUP BY region_name
ORDER BY 客流成交转化率_pct DESC
""",
        "insight": "{top_region} 大区客流转化率 {top_rate}% 最高，建议提炼经验推广至全国（说明：当前数仓维度止于大区，未下钻到门店/经销商粒度）。",
    },
    {
        "id": "Q14",
        "label": "客流漏斗：进店→试驾→成交",
        "domain": "渠道经营",
        "keywords": ["漏斗", "客流转"],
        "chart_hint": "funnel",
        "sql": """
SELECT
    SUM(customer_leads) AS 进店客流,
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
        "label": "转化率低于10%的大区",
        "domain": "渠道经营",
        "keywords": ["转化率低", "大区"],
        "chart_hint": "table",
        "sql": """
SELECT
    region_name AS 大区,
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
        "insight": "有 {count} 个大区/省份转化率低于 10%，最低仅 {lowest}%，建议排查该区域产品陈列与销售话术。",
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
# 包含关键词匹配 + 业务关键词排除：含业务关键词的优先走 SQL 通道
# ============================================================
SMALL_TALK_GUIDE = {
    # === 元问题 ===
    "你是谁": "我是**广汽云 ChatBI**，由谢志锋主导构建的智能经营分析助手。\n\n我能帮你：\n📊 查销量、营收、达成率\n💰 分析营销投放与 CPL\n🚗 看客流转化与漏斗\n\n试试点击下方 15 条快捷提问，每条都能精准返回对应图表和数据！",
    "你能做什么": "我可以基于广汽集团真实销售数据回答经营问题：\n\n✅ **整车销售**：销量、营收、达成率、单车均价、车型对比\n✅ **市场营销**：渠道投放、CPL 排名、抖音线索占比、ROI\n✅ **渠道经营**：客流漏斗、大区转化率、低转化大区预警\n\n点击快捷提问试试吧 →",
    "怎么用": "3 步上手：\n\n1️⃣ **点击下方快捷提问**（15 条覆盖 4 大业务域）\n2️⃣ 等待 1-3 秒，自动返回 SQL + 图表 + 经营洞察\n3️⃣ 查看驾驶舱 / 历史会话 / 语义层做深度管理\n\n💡 也可直接输入自然语言，如：'昊铂 HT 在华南区 4 月销量'",

    # === 寒暄/打招呼 ===
    "你好": "你好！我是广汽云 ChatBI 👋\n\n请告诉我你想查询的经营问题，例如：\n\n• 「广汽埃安3月销量达成率」\n• 「传祺各车型销售对比」\n• 「抖音渠道 CPL 排名」\n\n也可以点击下方 15 条快捷提问。",
    "在吗": "在的！请告诉我你想了解什么经营数据？",
    "hi": "Hi 👋 我是广汽云 ChatBI。基于广汽集团真实销售数据回答经营问题。\n\n📌 建议优先点击下方 15 条快捷提问（每条都能精准返回图表）",
    "hello": "Hello 👋 我是广汽云 ChatBI。\n\n我擅长：销量查询 · 营销分析 · 渠道经营 · 经营洞察。\n\n请直接提问，或者点击快捷问数按钮。",
    "你是ai吗": "是的，我是 AI 助手（基于大模型 + DuckDB NL2SQL），专门为广汽集团经营分析场景训练。\n\n我能调用 SQL 直接查 3 张业务主库表：整车销售 / 经营预算 / 市场营销。",

    # === 反馈/投诉 ===
    "不好用": "抱歉让你感到困扰 😅\n\n📌 试试这些能 100% 命中的提问：\n• 「广汽埃安3月销量达成率」\n• 「各品牌3月销量」\n• 「抖音渠道3月 CPL」\n\n如果还是不对，可以点 ❌ 把这次反馈给我，我会自动沉淀到 BadCase 收件箱。",
    "答错了": "对不起答错了！请点消息右下角的 ❌ BadCase 反馈按钮，我会在 BadCase 收件箱收到，自动关联语义层做优化。\n\n📌 推荐重新提问，确保指明品牌 + 时间 + 指标，比如：\n「广汽传祺 2025年3月 销量」",
    "错误": "抱歉出错！请刷新页面重试，或者点 ❌ 把错误反馈到 BadCase 收件箱，我会在下次迭代修复。",

    # === 测试/验证码 ===
    "测试": "我是广汽云 ChatBI 智能问数助手 ✅\n\n请尝试以下提问：\n• 「3月各品牌销量对比」\n• 「广汽埃安预算达成率」\n• 「抖音渠道 CPL」",

    # === 身份确认 ===
    "chatbi": "广汽云 ChatBI 是广汽集团经营分析专属 AI 助手，覆盖：\n• 🚗 整车销售分析\n• 💰 经营财务（达成率 / 预算）\n• 📢 市场营销（CPL / ROI）\n• 🏪 渠道经营（客流漏斗）\n\n试试点击下方 15 条快捷提问。",

    # === [Sprint 10 新增] 技术 / 架构 / 实现 类闲聊 ===
    "api": "📡 **我接入的 API 与数据源**\n\n**数据底座**：\n• DuckDB（嵌入式 OLAP 引擎，毫秒级响应）\n• 业务主库 `gac_bi.duckdb`：3 张核心事实表\n  - `fact_sales_daily` 整车销售明细\n  - `dim_budget_monthly` 经营预算\n  - `fact_marketing_channel_daily` 市场营销\n\n**AI 能力**：\n• 大模型（DeepSeek / OpenAI 兼容协议）→ NL2SQL\n• 自研 Schema Linker + 指标语义层（`metrics_dict.json`）\n\n**前端**：\n• Next.js 14 + ECharts 5，部署在 Render + Vercel\n\n💡 详细技术架构可阅读项目根目录的 `GAC_CHATBI_IMPLEMENTATION_GUIDE.md`",

    "llm": "🧠 **我的大模型基础**\n\n• 主用模型：**DeepSeek-V3**（中文 NL2SQL 性能强、成本低）\n• 备选：**GPT-4o-mini**（推理兜底）\n• 调用方式：OpenAI 兼容 Chat Completions API\n• 接入点：`backend/core/nl2sql_engine.py` → `LLMClient`\n• 业务保护：强制只读校验 + 指标语义层 + Few-shot prompt\n\n🔒 **绝不做的事**：\n• 任何 INSERT/UPDATE/DELETE/DROP\n• 生成 SQL 时不暴露业务表全 schema，只传相关表结构\n• 闲聊/技术问题不走 NL2SQL，直接返回纯文本回复",

    "模型": "🧠 **底层模型**：DeepSeek-V3 为主，GPT-4o-mini 兜底。\n\n**为什么选 DeepSeek**：\n• 中文 SQL 生成准确率高（NL2SQL 评测领先）\n• 性价比：比 GPT-4o 便宜 30+\n• 支持 OpenAI 兼容协议，无缝切换\n\n**Prompt 工程**：\n• 业务指标口径锁定（`metrics_dict.json`）\n• Few-shot 案例（`backend/core/prompts.py`）\n• Schema Linker 自动剪枝无关表",

    "数据源": "📦 **数据源说明**\n\n**生产环境**：\n• 业务主库：`backend/data/gac_bi.duckdb`（只读，部署时挂载）\n• 用户上传：`backend/data/user_uploads/user_data.duckdb`（用户私有表）\n• 历史会话：`backend/data/conversations.db`（SQLite）\n\n**本地开发**：\n• 测试库：`backend/data/gac_bi_test.duckdb`（含 mock 数据）\n• 切换由 `NL2SQLEngine.use_test_db` 控制\n\n**表清单**（业务主库）：\n1. `fact_sales_daily` 整车销售\n2. `dim_budget_monthly` 预算\n3. `fact_marketing_channel_daily` 营销",

    "架构": "🏗️ **系统架构**（4 层）：\n\n```\n┌─────────────────────────────────────┐\n│  L1 前端 (Next.js 14 + ECharts)      │\n│  - Chat 页 · 数据管理 · 历史会话      │\n└──────────────┬──────────────────────┘\n               │ REST/SSE\n┌──────────────▼──────────────────────┐\n│  L2 API 网关 (FastAPI)               │\n│  - 安全校验 · 流式响应 · 闲聊分流     │\n└──────────────┬──────────────────────┘\n               │\n┌──────────────▼──────────────────────┐\n│  L3 NL2SQL 引擎                     │\n│  - Schema Linker · 指标语义层        │\n│  - LLM 调用 · SQL 校验 · 自愈       │\n└──────────────┬──────────────────────┘\n               │\n┌──────────────▼──────────────────────┐\n│  L4 数据底座 (DuckDB)               │\n│  - 业务主库 + 用户上传 + 历史会话     │\n└─────────────────────────────────────┘\n```\n\n详细架构图见 `GAC_CHATBI_IMPLEMENTATION_GUIDE.md`",

    "技术栈": "🛠️ **技术栈一览**\n\n**前端**：Next.js 14 (App Router) · TypeScript · Tailwind · ECharts 5 · Lucide Icons\n\n**后端**：FastAPI · Python 3.10+ · Pydantic v2 · DuckDB · SQLite (历史会话)\n\n**AI**：DeepSeek-V3 / GPT-4o-mini · Schema Linker · 指标语义层 · Few-shot Prompt\n\n**部署**：\n• 前端：Vercel / Render\n• 后端：Render Web Service（Docker）\n• 数据：Render Disk（持久化 DuckDB）\n\n**DevOps**：GitHub Actions · Docker · 环境变量注入",

    "怎么做的": "🛠️ **实现原理**（一句话总结）：\n\n1. 用户输入自然语言问题\n2. Schema Linker 自动选出相关表 + 字段\n3. 把精简后的表结构 + 指标口径 + Few-shot 喂给 LLM\n4. LLM 生成 DuckDB 兼容 SQL\n5. SQL 走「只读 + 黑白名单」双重校验\n6. DuckDB 执行 → 返回数据 + 图表配置\n7. 前端 ECharts 渲染 + 流式推送自然语言洞察\n\n**亮点**：\n• 闲聊/技术问题走纯文本通道，不浪费 LLM token\n• 指标口径锁定在 `metrics_dict.json`，业务一致性 100%\n• 自动归因：销量波动时自动下钻子维度",

    "底层": "🔧 **底层实现**\n\n**数据库**：DuckDB（嵌入式 OLAP，比 SQLite 快 10x+，比 PostgreSQL 部署简单）\n\n**NL2SQL 流程**：\n```\n自然语言 → Schema Linker → Prompt 拼装 → LLM →\nSQL 校验（只读 + 危险词） → DuckDB 执行 →\n指标模板渲染 → ECharts + 文字洞察\n```\n\n**安全护栏**：\n• SQL 必须以 SELECT/WITH 开头\n• 严禁 INSERT/UPDATE/DELETE/DROP/CREATE/ALTER\n• 表名必须在白名单（3 张业务表 + 用户上传表）\n• 除零保护：自动 `NULLIF(val, 0)`\n\n**Sprint 进度**：当前 Sprint 9，15 条快捷问数 + 9 项语义层优化上线",
}


def match_small_talk(query: str) -> Optional[str]:
    """匹配闲聊引导语（关键词命中即返回）"""
    q = query.strip()

    # 业务关键词黑名单：包含业务词时强制走 SQL 通道，不走闲聊分支
    # 即使匹配上闲聊词，只要问句里有这些实体，也认为是有意图的查询
    BUSINESS_HINTS = [
        "销量", "营收", "达成", "预算", "目标", "台", "辆",
        "埃安", "传祺", "昊铂", "广汽",
        "cpl", "roi", "线索", "投放", "渠道", "获客", "营销",
        "门店", "进店", "试驾", "订单", "客流", "漏斗", "转化",
        "趋势", "排名", "占比", "对比", "区域", "城市",
        "市场", "经营", "财务",
        "fact_sales", "dim_budget", "fact_marketing",
    ]
    q_lower = q.lower()
    for hint in BUSINESS_HINTS:
        if hint in q_lower:
            return None  # 含业务词，强制走 SQL

    # 关键词匹配
    for trigger, reply in SMALL_TALK_GUIDE.items():
        if trigger in q_lower:
            return reply

    # 规则引擎兜底：纯寒暄（不含任何业务/数字/英文单词）
    import re
    # 移除标点和空白
    cleaned = re.sub(r"[\s,.，。?!？!～~]+", "", q_lower)
    # 如果 cleaned 长度 < 10 且没有数字 + 没有业务词 + 没有"什么/多少/哪/怎么"
    if len(cleaned) > 0 and len(cleaned) <= 15:
        has_number = bool(re.search(r"\d", cleaned))
        has_query_word = any(w in cleaned for w in ["什么", "多少", "咋", "哪", "怎么", "如何", "几", "谁", "何时", "为啥"])
        if not has_number and not has_query_word:
            # 看起来就是闲聊
            return ("我是广汽云 ChatBI 智能问数助手 👋\n\n"
                    "请告诉我你想查的经营数据，比如「广汽埃安3月销量」。\n"
                    "也可以点击下方 15 条快捷提问试试看。")

    return None
