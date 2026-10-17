"""
Step4: 表定位
谁做：规则（指标-维度-数据表三角映射，纯查表，不用LLM）
输入：指标涉及的表、维度
输出：table_list + compact_schema + join_hints
"""

import os
import json
from typing import List, Dict, Any
from workflow.context import WorkflowContext


# 表元数据定义
TABLE_METADATA = {
    "fact_sales_daily": {
        "description": "整车销售交付事实表（日/车型/大区粒度）",
        "grain": "日粒度，按品牌×车型×大区",
        "columns": [
            {"name": "sale_date", "type": "DATE", "description": "销售日期"},
            {"name": "brand_name", "type": "VARCHAR", "description": "品牌名称"},
            {"name": "model_name", "type": "VARCHAR", "description": "车型名称"},
            {"name": "region_name", "type": "VARCHAR", "description": "大区名称"},
            {"name": "dealer_id", "type": "VARCHAR", "description": "门店ID"},
            {"name": "delivered_units", "type": "INTEGER", "description": "实际交付量（辆）"},
            {"name": "gross_revenue", "type": "DECIMAL", "description": "开票营收（元）"},
            {"name": "order_units", "type": "INTEGER", "description": "订单量"},
            {"name": "customer_leads", "type": "INTEGER", "description": "进店客流（组）"},
            {"name": "test_drives", "type": "INTEGER", "description": "试驾次数"},
            {"name": "energy_type", "type": "VARCHAR", "description": "能源类型"},
            {"name": "price_segment", "type": "VARCHAR", "description": "价格段"}
        ]
    },
    "dim_budget_target": {
        "description": "集团经营预算与销量目标表（月度/品牌粒度）",
        "grain": "月粒度，按品牌",
        "columns": [
            {"name": "year_month", "type": "VARCHAR", "description": "月份（YYYY-MM）"},
            {"name": "brand_name", "type": "VARCHAR", "description": "品牌名称"},
            {"name": "target_units", "type": "INTEGER", "description": "预算目标交付量"},
            {"name": "target_revenue", "type": "DECIMAL", "description": "预算目标营收"},
            {"name": "region_name", "type": "VARCHAR", "description": "大区名称"}
        ]
    },
    "fact_marketing_expenses": {
        "description": "市场营销获客支出事实表（日/渠道/品牌粒度）",
        "grain": "日粒度，按渠道×品牌",
        "columns": [
            {"name": "expense_date", "type": "DATE", "description": "投放日期"},
            {"name": "brand_name", "type": "VARCHAR", "description": "品牌名称"},
            {"name": "channel_name", "type": "VARCHAR", "description": "渠道名称"},
            {"name": "expense_amount", "type": "DECIMAL", "description": "实际支出金额（元）"},
            {"name": "leads_generated", "type": "INTEGER", "description": "带来线索量"},
            {"name": "impressions", "type": "INTEGER", "description": "曝光量"}
        ]
    },
    # v2.0 新增表
    "fact_dealer_traffic": {
        "description": "渠道客流事实表（日/门店/渠道粒度）",
        "grain": "日粒度，按门店×渠道",
        "columns": [
            {"name": "traffic_date", "type": "DATE", "description": "统计日期"},
            {"name": "brand_name", "type": "VARCHAR", "description": "品牌名称"},
            {"name": "region_name", "type": "VARCHAR", "description": "大区名称"},
            {"name": "dealer_id", "type": "VARCHAR", "description": "门店ID"},
            {"name": "dealer_name", "type": "VARCHAR", "description": "门店名称"},
            {"name": "channel_source", "type": "VARCHAR", "description": "客流来源渠道"},
            {"name": "store_visits", "type": "INTEGER", "description": "进店客流（人次）"},
            {"name": "leads_count", "type": "INTEGER", "description": "留资线索数"},
            {"name": "test_drives", "type": "INTEGER", "description": "试驾数"},
            {"name": "deals_closed", "type": "INTEGER", "description": "成交数"},
            {"name": "avg_dwell_minutes", "type": "DECIMAL", "description": "平均停留时长（分钟）"}
        ]
    },
    "fact_inventory": {
        "description": "经销商库存事实表（月快照粒度）",
        "grain": "月粒度，按车型×大区",
        "columns": [
            {"name": "snapshot_month", "type": "VARCHAR", "description": "快照月份（YYYY-MM）"},
            {"name": "brand_name", "type": "VARCHAR", "description": "品牌名称"},
            {"name": "model_name", "type": "VARCHAR", "description": "车型名称"},
            {"name": "region_name", "type": "VARCHAR", "description": "大区名称"},
            {"name": "stock_units", "type": "INTEGER", "description": "在库车辆数"},
            {"name": "in_transit_units", "type": "INTEGER", "description": "在途车辆数"},
            {"name": "avg_stock_days", "type": "DECIMAL", "description": "库存周转天数"},
            {"name": "stock_coefficient", "type": "DECIMAL", "description": "库存系数"},
            {"name": "aging_over_90d_units", "type": "INTEGER", "description": "库龄超90天车辆数"},
            {"name": "shortage_flag", "type": "BOOLEAN", "description": "是否缺货预警"}
        ]
    }
}

# 维度字段映射（哪个维度在哪个表中）
DIMENSION_TABLE_MAP = {
    "brand_name": ["fact_sales_daily", "dim_budget_target", "fact_marketing_expenses", 
                   "fact_dealer_traffic", "fact_inventory"],
    "region_name": ["fact_sales_daily", "dim_budget_target", "fact_dealer_traffic", "fact_inventory"],
    "model_name": ["fact_sales_daily", "fact_inventory"],
    "channel_name": ["fact_marketing_expenses"],
    "channel_source": ["fact_dealer_traffic"],
}


def get_table_join_hints(table_list: List[str]) -> List[str]:
    """生成表间关联提示"""
    hints = []
    
    # 事实表与预算表：粒度不同，需要先聚合再JOIN
    if "fact_sales_daily" in table_list and "dim_budget_target" in table_list:
        hints.append("fact_sales_daily 为日粒度，dim_budget_target 为月粒度，需先按月聚合 fact_sales_daily 再 JOIN")
    
    # 事实表与营销表：通过 brand_name + 时间关联
    if "fact_sales_daily" in table_list and "fact_marketing_expenses" in table_list:
        hints.append("fact_sales_daily 和 fact_marketing_expenses 通过 brand_name + 月份关联，注意两表粒度不同")
    
    # 客流表：通过 brand_name + 时间关联
    if "fact_sales_daily" in table_list and "fact_dealer_traffic" in table_list:
        hints.append("fact_sales_daily 和 fact_dealer_traffic 通过 brand_name + 月份关联")
    
    return hints


def get_compact_schema(table_list: List[str]) -> str:
    """生成精简的 schema 文本（注入 Prompt 用）"""
    parts = []
    
    for table_name in table_list:
        if table_name in TABLE_METADATA:
            meta = TABLE_METADATA[table_name]
            cols = ", ".join(f"{c['name']}({c['type']})" for c in meta["columns"])
            parts.append(f"{table_name}: {cols}")
    
    return "\n".join(parts)


def execute(context: WorkflowContext) -> bool:
    """
    执行表定位步骤
    
    Returns:
        True: 成功，继续下一步
    """
    import time
    start_time = time.time()
    
    # 从指标定义中获取涉及的表
    required_tables = []
    if context.matched_metric:
        required_tables = context.matched_metric.required_tables
    
    # 如果指标没有定义表，根据维度推断
    if not required_tables:
        for dim_name in context.dimensions:
            if context.dimensions[dim_name] and dim_name in DIMENSION_TABLE_MAP:
                for table in DIMENSION_TABLE_MAP[dim_name]:
                    if table not in required_tables:
                        required_tables.append(table)
    
    # 默认至少包含销售事实表
    if not required_tables:
        required_tables = ["fact_sales_daily"]
    
    context.table_list = required_tables
    
    # 生成精简 schema
    context.compact_schema = get_compact_schema(required_tables)
    
    # 生成关联提示
    context.join_hints = get_table_join_hints(required_tables)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # 记录思考链
    content = f"通过指标-维度-表三角映射，定位到 {len(required_tables)} 张数据表："
    content += "、".join(required_tables)
    
    context.add_thinking_step(
        step=4,
        name="表定位",
        content=content,
        status="done",
        duration_ms=duration_ms
    )
    
    return True
