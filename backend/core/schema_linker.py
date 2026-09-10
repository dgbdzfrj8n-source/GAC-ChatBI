"""
Schema Linker 动态字段与指标剪枝器
作用：实现代价架构中的【Token 预算控制（降低 85% Token 消耗）】
逻辑：
1. 扫描业务提问，提取时间维度、品牌名称、指标关键词；
2. 匹配 metrics_dict.json 中最相关的指标计算规则；
3. 动态裁剪相关数据表与核心字段，只将必要的 Schema 注入 Prompt，杜绝全量表结构输入带来的幻觉与 Token 浪费。
"""

import os
import json
import re
from typing import Dict, Any, List, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_PATH = os.path.join(CURRENT_DIR, "metrics_dict.json")

# 广汽经营数据表元数据定义（精简版，用于定向剪枝）
TABLE_DEFINITIONS = {
    "fact_sales_daily": {
        "description": "整车销售交付事实表（日/车型/大区粒度）",
        "columns": [
            "sale_date DATE (销售交付日期，格式 'YYYY-MM-DD')",
            "brand_name VARCHAR (品牌：广汽埃安、广汽传祺、昊铂)",
            "model_name VARCHAR (车型：AION Y, AION S, 传祺GS8, 传祺M8, 昊铂GT等)",
            "region_name VARCHAR (大区：华南区、华东区、华北区、华中区、西南区)",
            "province_name VARCHAR (省份)",
            "delivered_units INTEGER (当日实际交付量/辆)",
            "gross_revenue DOUBLE (开票总营收/元)",
            "discount_rate DOUBLE (终端平均折扣率，如0.08代表8%)",
            "customer_leads INTEGER (进店意向客流量/组)",
            "test_drives INTEGER (试乘试驾次数/次)"
        ]
    },
    "dim_budget_target": {
        "description": "集团经营预算与销量目标表（月度/品牌粒度）",
        "columns": [
            "year_month VARCHAR (年月标识，格式 'YYYY-MM')",
            "brand_name VARCHAR (品牌：广汽埃安、广汽传祺、昊铂)",
            "target_units INTEGER (预算交付目标/辆)",
            "target_revenue DOUBLE (预算营收目标/元)",
            "expense_limit DOUBLE (营销与运营费用预算限额/元)"
        ]
    },
    "fact_marketing_expenses": {
        "description": "市场营销获客支出事实表（日/渠道/品牌粒度）",
        "columns": [
            "expense_date DATE (投放日期，格式 'YYYY-MM-DD')",
            "brand_name VARCHAR (品牌：广汽埃安、广汽传祺、昊铂)",
            "channel_name VARCHAR (投放渠道：懂车帝垂直类、抖音信息流、商圈巡展外拓、区域广播与电梯屏)",
            "expense_category VARCHAR (费用类别：线上公域投放、线下巡展体验、终端促销补贴)",
            "expense_amount DOUBLE (实际支出金额/元)",
            "leads_generated INTEGER (集客线索总量/条)"
        ]
    }
}

# 关键词触发规则
KEYWORD_MAPPING = {
    "dim_budget_target": ["预算", "目标", "达成", "完成率", "达成率", "进度", "计划"],
    "fact_marketing_expenses": ["营销", "费用", "支出", "成本", "投入", "渠道", "广告", "cpl", "ROI", "懂车帝", "抖音", "巡展"],
    "fact_sales_daily": ["销量", "交付", "卖了", "营收", "收入", "均价", "价格", "折扣", "客流", "试驾", "转化率", "车型", "大区"]
}

class SchemaLinker:
    def __init__(self, metrics_path: str = METRICS_PATH):
        with open(metrics_path, "r", encoding="utf-8") as f:
            self.metrics_data = json.load(f)
        self.metrics = self.metrics_data.get("metrics", [])

    def link(self, query: str) -> Dict[str, Any]:
        """
        对提问进行语义剪枝，提取命中的指标、数据表和最小上下文
        """
        query_lower = query.lower()
        thought_steps: List[str] = []

        # 1. 匹配指标（基于完整指标名或精确别名，杜绝单字符误匹配）
        matched_metrics = []
        for m in self.metrics:
            m_name = m["metric_name"]
            # 完整匹配，或者提取括号内外的核心词
            clean_names = [m_name]
            if "(" in m_name:
                clean_names.append(m_name.split("(")[0])
            if "（" in m_name:
                clean_names.append(m_name.split("（")[0])
            
            # 检查是否有实质性词汇命中（词长>=2）
            if any(name in query for name in clean_names if len(name) >= 2):
                matched_metrics.append(m)

        # 特殊模糊匹配（如提到“达成”或“完成”时强制命中“销售达成率”）
        if any(w in query for w in ["达成", "完成率", "目标"]) and not any(m["metric_name"] == "销售达成率" for m in matched_metrics):
            for m in self.metrics:
                if m["metric_name"] == "销售达成率":
                    matched_metrics.append(m)

        if matched_metrics:
            m_names = [m["metric_name"] for m in matched_metrics]
            thought_steps.append(f"命中集团经营指标：{', '.join(m_names)}")
        else:
            thought_steps.append("未直接命中预设聚合指标，启用通用多维聚合推断")

        # 2. 识别所需数据表
        selected_tables = set()
        # 从命中的指标中提取依赖表
        for m in matched_metrics:
            for t in m.get("required_tables", []):
                selected_tables.add(t)

        # 从关键词补充表匹配
        for table_name, keywords in KEYWORD_MAPPING.items():
            if any(kw in query_lower for kw in keywords):
                selected_tables.add(table_name)

        # 默认保底兜底：若没有任何表命中，则加载销售事实表
        if not selected_tables:
            selected_tables.add("fact_sales_daily")

        thought_steps.append(f"经过 Schema 剪枝，锁定关联业务表：{list(selected_tables)}")

        # 3. 构造剪枝后的紧凑 Prompt Schema 说明
        schema_lines = []
        for table in sorted(selected_tables):
            meta = TABLE_DEFINITIONS.get(table, {})
            schema_lines.append(f"### 表名：`{table}`（{meta.get('description', '')}）")
            schema_lines.append("字段清单：")
            for col in meta.get("columns", []):
                schema_lines.append(f"  - {col}")
            schema_lines.append("")

        # 4. 构造指标计算规范约束说明
        metric_constraint_lines = []
        if matched_metrics:
            metric_constraint_lines.append("### 集团指标强制计算口径与示例：")
            for m in matched_metrics:
                metric_constraint_lines.append(f"• **{m['metric_name']}** ({m.get('unit', '')}):")
                metric_constraint_lines.append(f"  - 口径说明：{m.get('definition', '')}")
                metric_constraint_lines.append(f"  - 计算公式：`{m.get('calculation_rule', '')}`")
                if "join_condition" in m:
                    metric_constraint_lines.append(f"  - 关联规则：`{m.get('join_condition')}`")
                if "example_query" in m:
                    metric_constraint_lines.append(f"  - 参考标准SQL：`{m.get('example_query')}`")
                metric_constraint_lines.append("")

        return {
            "query": query,
            "matched_metrics": matched_metrics,
            "selected_tables": list(selected_tables),
            "thought_steps": thought_steps,
            "pruned_schema_text": "\n".join(schema_lines).strip(),
            "metric_rules_text": "\n".join(metric_constraint_lines).strip()
        }

if __name__ == "__main__":
    linker = SchemaLinker()
    res = linker.link("请问2025年3月埃安销量与预算达成率是多少？")
    print("=== 剪枝结果验证 ===")
    print("思考链:", res["thought_steps"])
    print("锁定表:", res["selected_tables"])
    print("\n剪枝后 Schema:\n", res["pruned_schema_text"])
    print("\n指标约束:\n", res["metric_rules_text"])
