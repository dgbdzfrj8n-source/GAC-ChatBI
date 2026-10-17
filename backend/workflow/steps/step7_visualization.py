"""
Step7: 可视化决策
谁做：大模型（LLM）决策 + 后端函数生成配置
输入：result + matched_metric + dimensions
输出：chart_type + field_mapping + chart_config
"""

import json
from typing import Dict, Any, Optional, List
from workflow.context import WorkflowContext, ChartConfig


# 图表类型定义
CHART_TYPES = {
    "single_kpi": {
        "description": "单个指标值，适用于1行1个主要数值",
        "examples": ["达成率", "总交付量", "CPL"]
    },
    "bar": {
        "description": "类别对比，适用于多个类别比较数值",
        "examples": ["各品牌销量", "各渠道CPL", "各车型营收"]
    },
    "line": {
        "description": "时间趋势，适用于时间序列",
        "examples": ["近6月走势", "Q1各月趋势", "同比变化"]
    },
    "pie": {
        "description": "占比分布，适用于类别占比",
        "examples": ["渠道占比", "品牌占比", "车型占比"]
    },
    "funnel": {
        "description": "转化漏斗，适用于逐级收窄的转化数据",
        "examples": ["客流漏斗", "转化漏斗"]
    },
    "rank": {
        "description": "排名，适用于按数值排序的类别对比",
        "examples": ["CPL排名", "达成率排名", "转化率排名"]
    },
    "table": {
        "description": "明细数据，适用于多列多行明细",
        "examples": ["各车型明细", "各区域明细"]
    }
}


def infer_chart_type(question: str, columns: List[str], row_count: int) -> str:
    """
    根据问题特征和结果特征推断图表类型
    
    规则：
    1. 单行数据 → single_kpi
    2. 问题包含"走势""趋势""变化" → line
    3. 问题包含"排名""排序" → rank
    4. 问题包含"漏斗""转化" → funnel
    5. 问题包含"占比""比例""多少" → pie
    6. 多行数据 → bar
    7. 默认 → table
    """
    question_lower = question.lower()
    
    # 单行数据 → KPI
    if row_count == 1:
        return "single_kpi"
    
    # 时间序列检测
    time_columns = [col for col in columns if any(kw in col.lower() for kw in ["月", "日期", "date", "month", "time", "期"])]
    if time_columns and row_count > 1:
        if any(kw in question_lower for kw in ["走势", "趋势", "变化", "时间"]):
            return "line"
    
    # 漏斗检测
    funnel_keywords = ["漏斗", "转化", "funnel", "stage"]
    if any(kw in question_lower for kw in funnel_keywords):
        return "funnel"
    
    # 排名检测
    rank_keywords = ["排名", "排序", "rank", "top", "best"]
    if any(kw in question_lower for kw in rank_keywords):
        return "rank"
    
    # 占比检测
    pct_keywords = ["占比", "比例", "percent", "%", "占比"]
    if any(kw in question_lower for kw in pct_keywords):
        return "pie"
    
    # 对比检测
    compare_keywords = ["对比", "比较", "compare"]
    if any(kw in question_lower for kw in compare_keywords):
        return "bar"
    
    # 默认：根据行数判断
    if row_count <= 5:
        return "bar"
    elif row_count <= 10:
        return "table"
    else:
        return "table"


def infer_field_mapping(columns: List[str], chart_type: str) -> Dict[str, str]:
    """
    根据列名推断字段映射
    """
    mapping = {}
    
    # 常见列名模式
    for col in columns:
        col_lower = col.lower()
        
        # X轴/类别
        if any(kw in col_lower for kw in ["品牌", "brand", "车型", "model", "渠道", "channel", "区域", "region", "大区"]):
            mapping["x"] = col
        
        # Y轴/数值
        if any(kw in col_lower for kw in ["量", "额", "units", "revenue", "amount", "cost", "rate", "率"]):
            mapping["y"] = col
        
        # 主指标值
        if any(kw in col_lower for kw in ["交付量", "销量", "总", "total", "达成率"]):
            mapping["value"] = col
        
        # 占比/百分比
        if any(kw in col_lower for kw in ["占比", "percent", "pct", "率"]):
            mapping["percent"] = col
    
    # 单 KPI 类型特殊处理
    if chart_type == "single_kpi" and columns:
        mapping["value"] = columns[-1]  # 通常最后一列是主要指标
    
    # 饼图需要 category
    if chart_type == "pie":
        for col in columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in ["品牌", "brand", "渠道", "channel", "车型", "model"]):
                mapping["category"] = col
                break
        if "value" not in mapping and "y" in mapping:
            mapping["value"] = mapping.pop("y")
    
    # 折线图需要 series
    if chart_type == "line":
        if "x" not in mapping and columns:
            mapping["x"] = columns[0]
        if "y" not in mapping:
            for col in columns[1:]:
                mapping["y"] = col
                break
    
    return mapping


def generate_chart_config(chart_type: str, field_mapping: Dict[str, str], 
                        result: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据图表类型和字段映射生成 ECharts 配置
    """
    columns = result.get("columns", [])
    rows = result.get("rows", [])
    
    config = {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True}
    }
    
    if chart_type == "single_kpi":
        # 单值 KPI 卡片
        value_col = field_mapping.get("value", columns[-1] if columns else "")
        value = rows[0][columns.index(value_col)] if rows and columns else 0
        
        config = {
            "type": "single_kpi",
            "value": value,
            "label": value_col,
            "title": ""
        }
    
    elif chart_type == "bar":
        # 柱状图
        x_data = []
        y_data = []
        
        x_col = field_mapping.get("x", columns[0] if columns else "")
        y_col = field_mapping.get("y", columns[1] if len(columns) > 1 else "")
        
        for row in rows:
            if x_col in columns:
                x_data.append(row[columns.index(x_col)])
            if y_col in columns:
                y_data.append(row[columns.index(y_col)])
        
        config.update({
            "xAxis": {"type": "category", "data": x_data, "axisLabel": {"rotate": 15}},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "data": y_data}]
        })
    
    elif chart_type == "line":
        # 折线图
        x_data = []
        series_data = []
        
        x_col = field_mapping.get("x", columns[0] if columns else "")
        y_col = field_mapping.get("y", columns[1] if len(columns) > 1 else "")
        
        for row in rows:
            if x_col in columns:
                x_data.append(row[columns.index(x_col)])
            if y_col in columns:
                series_data.append(row[columns.index(y_col)])
        
        config.update({
            "xAxis": {"type": "category", "data": x_data},
            "yAxis": {"type": "value"},
            "series": [{"type": "line", "data": series_data, "smooth": True}]
        })
    
    elif chart_type == "pie":
        # 饼图
        data = []
        
        name_col = field_mapping.get("category", columns[0] if columns else "")
        value_col = field_mapping.get("value", columns[1] if len(columns) > 1 else "")
        
        for row in rows:
            name = row[columns.index(name_col)] if name_col in columns else ""
            value = row[columns.index(value_col)] if value_col in columns else 0
            data.append({"name": name, "value": value})
        
        config = {
            "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
            "legend": {"orient": "vertical", "left": "left"},
            "series": [{"type": "pie", "radius": "55%", "data": data, "label": {"formatter": "{b}: {d}%"}}]
        }
    
    elif chart_type == "funnel":
        # 漏斗图
        data = []
        
        for row in rows:
            if columns:
                name = row[0] if len(row) > 0 else ""
                value = row[1] if len(row) > 1 else 0
                data.append({"name": name, "value": value})
        
        config = {
            "tooltip": {"trigger": "item", "formatter": "{b}: {c}"},
            "series": [{
                "type": "funnel",
                "data": data
            }]
        }
    
    elif chart_type == "rank":
        # 排名条形图（横向柱状图）
        y_data = []
        series_data = []
        
        x_col = field_mapping.get("x", columns[0] if columns else "")
        y_col = field_mapping.get("y", columns[1] if len(columns) > 1 else "")
        
        for row in rows:
            if x_col in columns:
                y_data.append(row[columns.index(x_col)])
            if y_col in columns:
                series_data.append(row[columns.index(y_col)])
        
        config.update({
            "yAxis": {"type": "category", "data": y_data[::-1], "axisLabel": {"rotate": 0}},
            "xAxis": {"type": "value"},
            "series": [{"type": "bar", "data": series_data[::-1]}]
        })
    
    else:
        # table: 返回空配置，前端直接渲染表格
        config = {"type": "table", "columns": columns, "rows": rows}
    
    return config


def decide_chart(llm_client=None) -> callable:
    """
    返回图表决策函数
    （支持 LLM 决策，暂用规则）
    """
    def decide(context: WorkflowContext) -> ChartConfig:
        columns = context.result.columns if context.result else []
        rows = context.result.rows if context.result else []
        row_count = len(rows)
        
        # 推断图表类型
        chart_type = infer_chart_type(context.question, columns, row_count)
        
        # 推断字段映射
        field_mapping = infer_field_mapping(columns, chart_type)
        
        # 生成 ECharts 配置
        chart_config = generate_chart_config(
            chart_type, 
            field_mapping,
            {"columns": columns, "rows": rows}
        )
        
        return ChartConfig(
            chart_type=chart_type,
            field_mapping=field_mapping,
            config=chart_config
        )
    
    return decide


def execute(context: WorkflowContext, llm_client=None) -> bool:
    """
    执行可视化决策步骤
    
    Returns:
        True: 成功
    """
    import time
    start_time = time.time()
    
    if not context.result or not context.result.rows:
        # 空结果，设置为表格类型
        context.chart_config = ChartConfig(
            chart_type="table",
            field_mapping={},
            config={"type": "table", "columns": [], "rows": []}
        )
    else:
        # 使用规则推断图表类型
        chart_decider = decide_chart(llm_client)
        context.chart_config = chart_decider(context)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # 记录思考链
    chart_type = context.chart_config.chart_type if context.chart_config else "table"
    chart_desc = CHART_TYPES.get(chart_type, {}).get("description", "")
    
    content = f"数据特征：{context.result.row_count} 行 {len(context.result.columns)} 列。"
    content += f" 决策选择「{chart_type}」({chart_desc})。"
    
    context.add_thinking_step(
        step=7,
        name="可视化决策",
        content=content,
        status="done",
        duration_ms=duration_ms
    )
    
    return True
