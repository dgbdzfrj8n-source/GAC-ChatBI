"""
Prompt 工程调优与 Few-Shot 样本库
角色：资深广汽集团经营分析师人设
设计要点：
1. 注入结构化约束规范：严格只能输出符合语法标准的 SQL；
2. 注入车企经营术语 Few-Shot（涵盖季度/月度时间转换、达成率防扇出 CTE、各品牌下钻维度）；
3. 严格禁止除零异常（强制使用 NULLIF(..., 0)）；
4. 输出格式标准化：只返回 ```sql ... ``` 代码块，不产生其他冗余废话。
"""

SYSTEM_PROMPT = """你是由广汽集团数字化运营中心打造的“广汽云 ChatBI 资深经营分析专家”。
你的任务是：根据业务用户提问，结合给定的【精简数据表结构】与【集团指标强制口径】，生成高精度、完全符合标准 SQL 语法（兼容 DuckDB 与 SQLite）的只读分析 SQL。

### 核心规则与红线：
1. **只读安全**：严禁生成任何写操作（INSERT/UPDATE/DELETE/DROP/ALTER/CREATE），必须且只能以 `SELECT` 或 `WITH` 开头。
2. **防扇出计算规范**：
   - 当同时涉及【日粒度销售事实表 `fact_sales_daily`】与【月粒度预算表 `dim_budget_target`】时，严禁直接通过 brand_name 暴力 JOIN！
   - 必须使用 CTE（WITH 子句）先将 `fact_sales_daily` 按照 brand_name 和 `STRFTIME('%Y-%m', sale_date)` 聚合为月度颗粒度，再与预算表关联，否则将导致成百上千倍的数据扇出错误！
3. **除零安全**：凡涉及除法运算（如达成率、均价、CPL、占比），分母必须包裹 `NULLIF(..., 0)`，防止出现 ZeroDivisionError。
4. **时间函数规范**：
   - 提取年月统一使用 `STRFTIME('%Y-%m', 日期字段)`。
   - 提取年份统一使用 `STRFTIME('%Y', 日期字段)`。
5. **数值美化**：比率指标保留两位小数（使用 `ROUND(..., 2)`）。
6. **输出格式**：仅输出标准的 Markdown SQL 代码块，不得包含任何问候语或外部说明：
```sql
SELECT ...
```

7. **差量问题必须返回 gap（缺口/还差）字段**：
   - 当用户提问包含「还差」「差多少」「缺口」「未达成」「还差几」「差几」「未完成」「不足」「差多少辆」等关键词时，必须额外返回 `target_units - actual_units AS gap_units`（或 `收入差、预算差、成交差` 等）。
   - 缺口/还差类问法的标准 SQL 必须包含减法字段，否则视为答非所问。
```sql
-- 范例：还差多少？
SELECT 
    s.actual_units,
    b.target_units,
    (b.target_units - s.actual_units) AS gap_units
FROM ...
```
"""

FEW_SHOT_EXAMPLES = [
    {
        "user_query": "2025年第一季度广汽埃安每个月的总交付量是多少？",
        "thought": "按月聚合埃安销量，过滤时间范围 2025-01-01 至 2025-03-31",
        "sql": """SELECT 
    STRFTIME('%Y-%m', sale_date) AS year_month,
    SUM(delivered_units) AS total_delivered_units
FROM fact_sales_daily
WHERE brand_name = '广汽埃安' 
  AND sale_date >= '2025-01-01' 
  AND sale_date <= '2025-03-31'
GROUP BY 1
ORDER BY 1 ASC;"""
    },
    {
        "user_query": "2025年3月广汽埃安、传祺各品牌的销售预算达成率是多少？",
        "thought": "两表粒度不同，必须使用 CTE 先对事实表聚合至月粒度，再关联预算表计算达成率",
        "sql": """WITH monthly_sales AS (
    SELECT 
        brand_name,
        STRFTIME('%Y-%m', sale_date) AS year_month,
        SUM(delivered_units) AS actual_units
    FROM fact_sales_daily
    WHERE STRFTIME('%Y-%m', sale_date) = '2025-03'
    GROUP BY brand_name, year_month
)
SELECT 
    s.brand_name,
    s.actual_units,
    b.target_units,
    ROUND(s.actual_units * 100.0 / NULLIF(b.target_units, 0), 2) AS fulfillment_rate_pct
FROM monthly_sales s
JOIN dim_budget_target b 
  ON s.brand_name = b.brand_name 
 AND s.year_month = b.year_month
ORDER BY fulfillment_rate_pct DESC;"""
    },
    {
        "user_query": "传祺各车型在华东大区的总交付量和平均成交均价是多少？",
        "thought": "过滤品牌为广汽传祺与大区为华东区，按车型汇总",
        "sql": """SELECT 
    model_name,
    SUM(delivered_units) AS total_units,
    ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 2) AS avg_transaction_price
FROM fact_sales_daily
WHERE brand_name = '广汽传祺' 
  AND region_name = '华东区'
GROUP BY model_name
ORDER BY total_units DESC;"""
    },
    {
        "user_query": "各营销渠道在2025年的投放总支出和单条线索获客成本(CPL)排名",
        "thought": "聚合营销费用表，计算 CPL 并按成本升序排列",
        "sql": """SELECT 
    channel_name,
    ROUND(SUM(expense_amount), 2) AS total_spend,
    SUM(leads_generated) AS total_leads,
    ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 2) AS cpl
FROM fact_marketing_expenses
WHERE expense_date >= '2025-01-01'
GROUP BY channel_name
ORDER BY cpl ASC;"""
    }
]

def build_nl2sql_prompt(query: str, pruned_schema: str, metric_rules: str) -> str:
    """
    动态拼装最终注入 LLM 的紧凑 Prompt
    """
    few_shot_texts = []
    for idx, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        few_shot_texts.append(f"【示例 {idx}】\n业务提问：{ex['user_query']}\n生成 SQL：\n```sql\n{ex['sql']}\n```")

    prompt = f"""### 当前业务提问：
"{query}"

### 剪枝后的数据表结构上下文：
{pruned_schema}

### 集团指标强制口径规则：
{metric_rules if metric_rules else "按业务标准通用聚合计算"}

### 经典车企经营分析 Few-Shot 参考：
{chr(10).join(few_shot_texts)}

请严格基于上述表结构与指标规则，生成回答当前提问的只读 SQL（用 ```sql 包裹）："""
    return prompt

def build_self_healing_prompt(query: str, failed_sql: str, error_message: str, pruned_schema: str) -> str:
    """
    自愈重试 Prompt：将执行报错反哺给大模型进行定向纠错
    """
    prompt = f"""你之前为业务问题：“{query}” 生成的 SQL 在数据库中执行报错！

### 失败的 SQL：
```sql
{failed_sql}
```

### 数据库执行错误信息：
{error_message}

### 参考表结构：
{pruned_schema}

请针对报错原因（例如字段拼写错误、聚合分组遗漏、除零或缺少 CTE），重新生成一份修正后 100% 能够成功执行的只读 SQL（只输出 ```sql ... ``` 代码块）："""
    return prompt
