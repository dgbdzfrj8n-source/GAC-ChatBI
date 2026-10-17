"""
Step5: SQL生成
谁做：大模型（LLM）
输入：用户问题、指标定义、维度、schema、关联提示
输出：sql + token_count
"""

import re
import json
from typing import Optional
from workflow.context import WorkflowContext


# DuckDB SQL 生成 Prompt 模板
SQL_GENERATION_PROMPT = """你是 DuckDB SQL 生成专家。根据以下信息生成高质量 SQL，只返回 SQL，不要解释。

## 用户问题
{question}

## 指标定义
指标名称：{metric_name}
计算公式：{calculation_rule}
注意事项：{notes}

## 解析出的维度
{dimensions_json}

## 可用表结构
{compact_schema}

## 关联提示
{join_hints_text}

## 要求
1. 使用 DuckDB 语法
2. 时间过滤用 STRFTIME('%Y-%m', date_column) = 'YYYY-MM'
3. 除法必须用 NULLIF(分母, 0) 防止除零
4. 多表关联时注意粒度差异，先聚合再JOIN
5. 数值结果保留2位小数用 ROUND(x, 2)
6. 只返回 SELECT 或 WITH 语句，不要其他内容
7. 中文别名用 AS 命名，如 "品牌" AS brand_name
"""


def extract_sql(text: str) -> Optional[str]:
    """从模型输出中提取 SQL"""
    # 匹配 ```sql ... ``` 或 ``` ... ```
    patterns = [
        r"```sql\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            # 去除可能的首尾空白和反引号
            sql = sql.strip('` \n')
            if sql:
                return sql
    
    # 如果没有代码块，尝试直接返回非空内容
    lines = text.strip().split('\n')
    sql_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('--'):
            sql_lines.append(line)
    
    if sql_lines:
        return '\n'.join(sql_lines)
    
    return None


def build_dimensions_json(dimensions: dict) -> str:
    """将维度字典转换为 JSON 格式"""
    # 过滤掉 None 值
    filtered = {k: v for k, v in dimensions.items() if v is not None}
    return json.dumps(filtered, ensure_ascii=False, indent=2)


def generate_sql_prompt(context: WorkflowContext) -> str:
    """生成 SQL 生成的 Prompt"""
    dimensions_text = build_dimensions_json(context.dimensions)
    
    # 关联提示
    join_hints_text = "\n".join(f"- {hint}" for hint in context.join_hints) if context.join_hints else "无特殊关联要求"
    
    # 指标信息
    metric_name = context.matched_metric.metric_name if context.matched_metric else "通用指标"
    calculation_rule = context.matched_metric.calculation_rule if context.matched_metric else ""
    notes = context.matched_metric.notes if context.matched_metric else ""
    
    return SQL_GENERATION_PROMPT.format(
        question=context.question,
        metric_name=metric_name,
        calculation_rule=calculation_rule,
        notes=notes,
        dimensions_json=dimensions_text,
        compact_schema=context.compact_schema,
        join_hints_text=join_hints_text
    )


def execute(context: WorkflowContext, llm_client=None) -> bool:
    """
    执行 SQL 生成步骤
    
    Returns:
        True: 成功，继续下一步
        False: 失败
    """
    import time
    start_time = time.time()
    
    # 生成 Prompt
    prompt = generate_sql_prompt(context)
    
    # 调用 LLM
    sql = None
    if llm_client:
        try:
            response = llm_client.call([
                {"role": "user", "content": prompt}
            ])
            sql = extract_sql(response)
        except Exception as e:
            context.sql_attempts += 1
    
    # 如果 LLM 调用失败，尝试使用模板生成
    if not sql:
        sql = _generate_fallback_sql(context)
    
    context.sql = sql
    context.sql_token_count = len(prompt) // 4  # 粗略估算 token 数
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # 记录思考链
    content = f"生成 DuckDB SQL"
    if context.matched_metric:
        content += f"，基于指标 {context.matched_metric.metric_name}"
    content += f"，Token 消耗约 {context.sql_token_count}"
    
    context.add_thinking_step(
        step=5,
        name="SQL生成",
        content=content,
        status="done",
        duration_ms=duration_ms
    )
    
    return sql is not None


def _generate_fallback_sql(context: WorkflowContext) -> Optional[str]:
    """
    兜底 SQL 生成（当 LLM 不可用时）
    根据指标和维度生成简单的 SQL
    """
    if not context.matched_metric:
        return None
    
    metric = context.matched_metric
    dims = context.dimensions
    
    # 基本 SELECT
    select_parts = []
    where_parts = []
    
    # 品牌过滤
    if dims.get("brand") and dims["brand"] != "全部":
        where_parts.append(f"brand_name = '{dims['brand']}'")
    
    # 时间过滤
    if dims.get("time"):
        time_val = dims["time"]
        if len(time_val) == 7:  # YYYY-MM
            where_parts.append(f"STRFTIME('%Y-%m', sale_date) = '{time_val}'")
        else:
            where_parts.append(f"sale_date = '{time_val}'")
    
    # 区域过滤
    if dims.get("region"):
        where_parts.append(f"region_name = '{dims['region']}'")
    
    # 车型过滤
    if dims.get("model"):
        where_parts.append(f"model_name = '{dims['model']}'")
    
    # 根据指标生成 SQL
    if metric.metric_id == "M01" or "达成率" in metric.metric_name:
        # 达成率需要 JOIN 预算表
        sql = f"""WITH sales_agg AS (
    SELECT 
        brand_name,
        STRFTIME('%Y-%m', sale_date) AS year_month,
        SUM(delivered_units) AS actual_units
    FROM fact_sales_daily
    {"WHERE " + " AND ".join(where_parts) if where_parts else ""}
    GROUP BY brand_name, year_month
)
SELECT 
    s.brand_name AS 品牌,
    s.year_month AS 月份,
    s.actual_units AS 实际交付量,
    b.target_units AS 预算目标量,
    ROUND(s.actual_units * 100.0 / NULLIF(b.target_units, 0), 2) AS 达成率_pct,
    (b.target_units - s.actual_units) AS 差额_辆
FROM sales_agg s
JOIN dim_budget_target b ON s.brand_name = b.brand_name AND s.year_month = b.year_month"""
        return sql
    
    elif metric.metric_id == "M02" or "交付量" in metric.metric_name:
        # 总交付量
        sql = f"""SELECT 
    brand_name AS 品牌,"""
        if dims.get("model"):
            sql += "\n    model_name AS 车型,"
        if dims.get("region"):
            sql += "\n    region_name AS 大区,"
        sql += f"""
    SUM(delivered_units) AS 总交付量
FROM fact_sales_daily
{"WHERE " + " AND ".join(where_parts) if where_parts else ""}
GROUP BY brand_name"""
        if dims.get("model"):
            sql += ", model_name"
        if dims.get("region"):
            sql += ", region_name"
        sql += "\nORDER BY 总交付量 DESC"
        return sql
    
    elif metric.metric_id == "M03" or "均价" in metric.metric_name:
        # 单车成交均价
        sql = f"""SELECT 
    brand_name AS 品牌,"""
        if dims.get("model"):
            sql += "\n    model_name AS 车型,"
        sql += f"""
    SUM(gross_revenue) AS 总营收,
    SUM(delivered_units) AS 总交付量,
    ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 2) AS 单车均价
FROM fact_sales_daily
{"WHERE " + " AND ".join(where_parts) if where_parts else ""}
GROUP BY brand_name"""
        if dims.get("model"):
            sql += ", model_name"
        sql += "\nORDER BY 单车均价 DESC"
        return sql
    
    elif metric.metric_id == "M05" or "CPL" in metric.metric_name or "获客成本" in metric.metric_name:
        # CPL
        sql = f"""SELECT 
    channel_name AS 渠道,
    SUM(expense_amount) AS 总投放_元,
    SUM(leads_generated) AS 总线索量,
    ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 2) AS CPL_元
FROM fact_marketing_expenses"""
        if where_parts:
            # 过滤可能不适用于营销表
            pass
        sql += """
GROUP BY channel_name
ORDER BY CPL_元 ASC"""
        return sql
    
    elif metric.metric_id == "M18" or "进店客流" in metric.metric_name:
        # 进店客流
        sql = f"""SELECT 
    brand_name AS 品牌,
    region_name AS 大区,
    channel_source AS 渠道,
    SUM(store_visits) AS 进店客流
FROM fact_dealer_traffic"""
        if where_parts:
            # 过滤可能不适用于客流表
            pass
        sql += """
GROUP BY brand_name, region_name, channel_source
ORDER BY 进店客流 DESC"""
        return sql
    
    elif metric.metric_id == "M21" or "成交转化" in metric.metric_name:
        # 客流成交转化率
        sql = f"""SELECT 
    brand_name AS 品牌,
    region_name AS 大区,
    SUM(store_visits) AS 进店客流,
    SUM(leads_count) AS 留资数,
    SUM(test_drives) AS 试驾数,
    SUM(deals_closed) AS 成交数,
    ROUND(SUM(deals_closed) * 100.0 / NULLIF(SUM(store_visits), 0), 2) AS 客流成交转化率
FROM fact_dealer_traffic
GROUP BY brand_name, region_name
ORDER BY 客流成交转化率 DESC"""
        return sql
    
    elif metric.metric_id == "M23" or "在库" in metric.metric_name or "库存" in metric.metric_name:
        # 在库车辆数
        sql = f"""SELECT 
    brand_name AS 品牌,
    model_name AS 车型,
    region_name AS 大区,
    SUM(stock_units) AS 在库车辆数,
    ROUND(AVG(avg_stock_days), 1) AS 平均周转天数,
    ROUND(AVG(stock_coefficient), 2) AS 库存系数
FROM fact_inventory
GROUP BY brand_name, model_name, region_name
ORDER BY 在库车辆数 DESC"""
        return sql
    
    # 默认：总交付量
    sql = f"""SELECT 
    brand_name AS 品牌,"""
    if dims.get("model"):
        sql += "\n    model_name AS 车型,"
    sql += f"""
    SUM(delivered_units) AS 总交付量
FROM fact_sales_daily
{"WHERE " + " AND ".join(where_parts) if where_parts else ""}
GROUP BY brand_name"""
    if dims.get("model"):
        sql += ", model_name"
    sql += "\nORDER BY 总交付量 DESC"
    
    return sql
