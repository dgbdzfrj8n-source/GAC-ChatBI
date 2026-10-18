"""
5 个归因模板 Seed 数据
涵盖：销售归因（QoQ/YoY/TopN/差值）+ 市场归因（漏斗）
"""
from __future__ import annotations

import sys
import os

# 注入 backend 到 sys.path
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from services.sop.template_db import TemplateDB

DB_PATH = os.path.join(_BACKEND_DIR, "data", "gac_bi.db")

SEEDS = [
    {
        "name": "销售环比下降归因",
        "code": "sales_attr_qoq",
        "description": "对比本月 vs 上月销售下滑原因，覆盖品牌/车型/区域维度",
        "category": "销售归因",
        "tags": ["销售", "环比", "下滑"],
        "steps": [
            {
                "name": "查询本月销量",
                "type": "nl2sql",
                "description": "聚合本月的交付量/营收/客单价",
                "question": "查询 {brand} 本月（{cur_month}）各车型交付量、总营收、折扣率",
                "metrics": ["delivered_units", "gross_revenue", "discount_rate"],
                "dimensions": ["model_name"],
                "variables": [
                    {"name": "brand", "label": "品牌", "type": "string", "required": True, "default": "广汽埃安"},
                    {"name": "cur_month", "label": "当前月份", "type": "string", "required": True, "default": "2025-09"},
                ],
            },
            {
                "name": "查询上月销量",
                "type": "nl2sql",
                "description": "聚合上月的交付量/营收/折扣率",
                "question": "查询 {brand} 上月（{prev_month}）各车型交付量、总营收、折扣率",
                "metrics": ["delivered_units", "gross_revenue", "discount_rate"],
                "dimensions": ["model_name"],
                "variables": [
                    {"name": "prev_month", "label": "对比月份", "type": "string", "required": True, "default": "2025-08"},
                ],
            },
            {
                "name": "环比差值计算",
                "type": "aggregation",
                "description": "按车型计算环比变化量与变化率",
                "aggregation": "diff",
                "group_by": ["model_name"],
                "variables": [],
            },
            {
                "name": "TopN 下滑车型",
                "type": "strategy",
                "description": "取环比下滑最严重的 Top5 车型",
                "strategy": "topn",
                "variables": [],
            },
            {
                "name": "经营结论",
                "type": "conclusion",
                "description": "LLM 基于 TopN 下滑车型输出归因结论",
                "prompt": "基于以下下滑车型数据，输出 3 条核心归因结论：\n{prev_step_output}\n要求：1)聚焦主因；2)量化影响；3)给出建议。",
                "variables": [],
            },
        ],
    },
    {
        "name": "销售同比下降归因",
        "code": "sales_attr_yoy",
        "description": "对比今年 vs 去年同月销售下滑原因",
        "category": "销售归因",
        "tags": ["销售", "同比", "下滑"],
        "steps": [
            {
                "name": "查询今年累计",
                "type": "nl2sql",
                "description": "今年 YTD 销量/营收",
                "question": "查询 {brand} {cur_year} 年至今各月交付量、总营收",
                "metrics": ["delivered_units", "gross_revenue"],
                "dimensions": ["sale_date"],
                "variables": [
                    {"name": "brand", "label": "品牌", "type": "string", "required": True, "default": "广汽传祺"},
                    {"name": "cur_year", "label": "年份", "type": "string", "required": True, "default": "2025"},
                ],
            },
            {
                "name": "查询去年累计",
                "type": "nl2sql",
                "description": "去年 YTD 销量/营收",
                "question": "查询 {brand} {prev_year} 年同期各月交付量、总营收",
                "metrics": ["delivered_units", "gross_revenue"],
                "dimensions": ["sale_date"],
                "variables": [
                    {"name": "prev_year", "label": "去年年份", "type": "string", "required": True, "default": "2024"},
                ],
            },
            {
                "name": "同比差值",
                "type": "aggregation",
                "description": "按月聚合同比差值与同比率",
                "aggregation": "diff",
                "group_by": ["sale_date"],
            },
            {
                "name": "趋势总结",
                "type": "conclusion",
                "description": "总结同比下滑的核心月份和累计影响",
                "prompt": "基于以下同比数据，输出 3 条核心归因结论",
            },
        ],
    },
    {
        "name": "TopN 销售车型归因",
        "code": "sales_topn",
        "description": "找出销量/营收 Top 10 车型并分析共同特征",
        "category": "销售归因",
        "tags": ["TopN", "畅销"],
        "steps": [
            {
                "name": "查询全量销售",
                "type": "nl2sql",
                "description": "本月所有车型销量/营收",
                "question": "查询 {month} 各车型交付量、总营收、折扣率、能源类型、价格段",
                "metrics": ["delivered_units", "gross_revenue", "discount_rate"],
                "dimensions": ["model_name", "energy_type", "price_segment"],
                "variables": [
                    {"name": "month", "label": "月份", "type": "string", "required": True, "default": "2025-09"},
                ],
            },
            {
                "name": "Top10 排序",
                "type": "strategy",
                "description": "按交付量倒序取 Top10",
                "strategy": "topn",
            },
            {
                "name": "特征聚合",
                "type": "aggregation",
                "description": "统计 Top10 中能源类型/价格段分布",
                "aggregation": "count",
                "group_by": ["energy_type", "price_segment"],
            },
            {
                "name": "畅销归因",
                "type": "conclusion",
                "description": "总结畅销车型的共性",
                "prompt": "基于以下 Top10 数据，归纳畅销车型的 3 个共性特征",
            },
        ],
    },
    {
        "name": "市场获客 ROI 归因",
        "code": "marketing_roi",
        "description": "分析各渠道获客成本与线索转化",
        "category": "市场归因",
        "tags": ["营销", "ROI", "渠道"],
        "steps": [
            {
                "name": "查询各渠道投放",
                "type": "nl2sql",
                "description": "各渠道支出/线索/曝光",
                "question": "查询 {brand} {month} 各渠道支出、线索量、曝光量",
                "metrics": ["expense_amount", "leads_generated", "impressions"],
                "dimensions": ["channel_name"],
                "variables": [
                    {"name": "brand", "label": "品牌", "type": "string", "required": True, "default": "广汽埃安"},
                    {"name": "month", "label": "月份", "type": "string", "required": True, "default": "2025-09"},
                ],
            },
            {
                "name": "计算 ROI",
                "type": "aggregation",
                "description": "线索单价 = expense / leads",
                "aggregation": "custom_roi",
            },
            {
                "name": "排序",
                "type": "strategy",
                "description": "按线索单价升序（最优渠道在前）",
                "strategy": "topn",
            },
            {
                "name": "ROI 结论",
                "type": "conclusion",
                "description": "总结最优/最差渠道",
                "prompt": "基于各渠道 ROI 数据，输出 Top3 高效渠道 + Bottom3 低效渠道",
            },
        ],
    },
    {
        "name": "库存周转归因",
        "code": "inventory_attr",
        "description": "分析库存周转天数与滞销车型分布",
        "category": "库存归因",
        "tags": ["库存", "周转"],
        "steps": [
            {
                "name": "查询当前库存",
                "type": "nl2sql",
                "description": "各车型当前库存量与库龄",
                "question": "查询 {brand} 当前各车型库存量、平均库龄",
                "metrics": ["stock_units", "avg_age_days"],
                "dimensions": ["model_name"],
                "variables": [
                    {"name": "brand", "label": "品牌", "type": "string", "required": True, "default": "广汽传祺"},
                ],
            },
            {
                "name": "查询近期销售",
                "type": "nl2sql",
                "description": "近 30 天各车型销量",
                "question": "查询 {brand} 近 30 天各车型交付量",
                "metrics": ["delivered_units"],
                "dimensions": ["model_name"],
            },
            {
                "name": "周转天数",
                "type": "aggregation",
                "description": "周转天数 ≈ 库存量 / 日均销量",
                "aggregation": "turnover_days",
            },
            {
                "name": "滞销归因",
                "type": "conclusion",
                "description": "总结高滞销车型",
                "prompt": "基于周转天数数据，输出 Top3 滞销车型 + 建议",
            },
        ],
    },
]


def seed():
    db = TemplateDB(DB_PATH)
    created = 0
    skipped = 0
    for s in SEEDS:
        if db.get_template_by_code(s["code"]):
            print(f"⏭  Skip: {s['code']} (已存在)")
            skipped += 1
            continue
        tpl = db.create_template(
            name=s["name"],
            code=s["code"],
            description=s["description"],
            category=s["category"],
            tags=s["tags"],
            steps=s["steps"],
            created_by="system",
            is_builtin=True,
            status="published",
        )
        print(f"✅ Created: {s['code']} (id={tpl.template_id}, v{tpl.current_version})")
        created += 1
    print(f"\nTotal: created={created}, skipped={skipped}")


if __name__ == "__main__":
    seed()
