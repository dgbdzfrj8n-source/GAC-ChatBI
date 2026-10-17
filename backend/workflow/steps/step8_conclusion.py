"""
Step8: 业务解读
谁做：大模型（LLM）
输入：用户问题 + 指标 + 维度 + result + chart_type
输出：conclusion + key_numbers
"""

import json
from typing import Dict, Any, List, Optional
from workflow.context import WorkflowContext


def format_number(value: Any, unit: str = "") -> str:
    """格式化数字显示"""
    if value is None:
        return "—"
    
    try:
        val = float(value)
        if abs(val) >= 10000:
            return f"{val/10000:.2f}万{unit}"
        elif abs(val) >= 100:
            return f"{val:,.0f}{unit}"
        else:
            return f"{val:.2f}{unit}"
    except (ValueError, TypeError):
        return str(value)


def generate_conclusion_template(context: WorkflowContext) -> str:
    """
    使用模板生成结论（当 LLM 不可用时）
    """
    if not context.result or not context.result.rows:
        return "当前条件下暂无数据，请尝试调整查询条件。"
    
    result = context.result
    columns = result.columns
    rows = result.rows
    
    # 提取关键数字
    key_numbers = []
    conclusion_parts = []
    
    # 尝试从结果中提取关键信息
    for row_idx, row in enumerate(rows):
        for col_idx, col_name in enumerate(columns):
            value = row[col_idx] if col_idx < len(row) else None
            
            # 数值列
            if value is not None and isinstance(value, (int, float)):
                # 单位检测
                unit = ""
                if "率" in col_name or "pct" in col_name.lower():
                    unit = "%"
                elif "辆" in col_name or "台" in col_name:
                    unit = "辆"
                elif "元" in col_name:
                    unit = "元"
                
                # 添加到关键数字
                key_numbers.append({
                    "label": col_name,
                    "value": format_number(value, unit)
                })
    
    # 根据指标类型生成不同结论
    if context.matched_metric:
        metric_name = context.matched_metric.metric_name
        
        # 达成率
        if "达成率" in metric_name:
            if rows and len(rows[0]) >= 3:
                brand = rows[0][0] if rows[0] else ""
                actual = rows[0][2] if len(rows[0]) > 2 else None
                target = rows[0][3] if len(rows[0]) > 3 else None
                rate = rows[0][4] if len(rows[0]) > 4 else None
                
                if rate:
                    conclusion_parts.append(f"{brand}达成率为 {rate}%")
                    if target and actual:
                        diff = float(target) - float(actual) if actual else 0
                        if diff > 0:
                            conclusion_parts.append(f"距目标还差 {format_number(diff, '辆')}")
                        else:
                            conclusion_parts.append("已超额完成")
        
        # 交付量
        elif "交付量" in metric_name or "交付" in metric_name:
            total = 0
            brands = []
            for row in rows[:3]:  # 取前3个
                if row:
                    brand = row[0] if len(row) > 0 else ""
                    units = row[1] if len(row) > 1 else 0
                    if brand and units:
                        brands.append(f"{brand} {format_number(units, '辆')}")
                        total += float(units) if units else 0
            
            if brands:
                conclusion_parts.append(f"集团总交付 {format_number(total, '辆')}")
                if len(brands) == 1:
                    conclusion_parts.append(f"其中 {brands[0]}")
                else:
                    conclusion_parts.append(f"主要品牌：{', '.join(brands)}")
        
        # 营收
        elif "营收" in metric_name or "收入" in metric_name:
            total = 0
            for row in rows[:3]:
                if row and len(row) > 1:
                    val = row[1] if isinstance(row[1], (int, float)) else 0
                    total += val
            
            if total > 0:
                conclusion_parts.append(f"总营收约 {format_number(total, '元')} ({format_number(total/10000, '万元')})")
        
        # CPL
        elif "CPL" in metric_name or "获客成本" in metric_name:
            if rows:
                best = rows[0] if rows[0] else []
                worst = rows[-1] if rows[-1] else []
                
                if len(best) >= 2 and len(worst) >= 2:
                    best_channel = best[0]
                    best_cpl = best[1]
                    worst_channel = worst[0]
                    worst_cpl = worst[1]
                    
                    conclusion_parts.append(f"CPL最优渠道：{best_channel} ({format_number(best_cpl, '元/条')})")
                    conclusion_parts.append(f"CPL最高渠道：{worst_channel} ({format_number(worst_cpl, '元/条')})")
        
        # 库存
        elif "库存" in metric_name:
            if rows:
                high_stock = [row for row in rows if len(row) > 5 and row[5] and float(row[5]) > 2.0]
                if high_stock:
                    conclusion_parts.append(f"发现 {len(high_stock)} 个高库存预警车型（库存系数>2.0）")
                    for row in high_stock[:2]:
                        if row and len(row) >= 2:
                            conclusion_parts.append(f"• {row[0]} {row[1] if len(row) > 1 else ''}")
                else:
                    conclusion_parts.append("各车型库存系数正常，无预警")
    
    # 通用结论
    if not conclusion_parts:
        if len(rows) == 1:
            conclusion_parts.append("查询完成，详情如下表")
        else:
            conclusion_parts.append(f"共查询到 {len(rows)} 条记录")
    
    return "。".join(conclusion_parts), key_numbers[:5]


def render_insight_template(insight_template: str, context: WorkflowContext) -> str:
    """
    渲染 insight 模板中的占位符
    """
    if not insight_template or not context.result:
        return insight_template
    
    result = context.result
    columns = result.columns
    rows = result.rows
    
    if not rows:
        return insight_template
    
    first_row = rows[0]
    
    # 尝试提取值
    def get_value(*names):
        for name in names:
            for idx, col in enumerate(columns):
                if name.lower() in col.lower():
                    if idx < len(first_row):
                        return first_row[idx]
        return None
    
    def format_val(val):
        if val is None:
            return "—"
        if isinstance(val, float):
            if abs(val) > 100:
                return f"{val:,.2f}"
            return f"{val:.2f}"
        return str(val)
    
    # 替换占位符
    replacements = {
        "{actual}": format_val(get_value("实际", "actual", "交付量")),
        "{target}": format_val(get_value("预算", "target")),
        "{rate}": format_val(get_value("达成率", "rate", "率")),
        "{total}": format_val(get_value("总", "total")),
        "{revenue}": format_val(get_value("营收", "revenue")),
        "{ym}": get_value("月份", "month", "ym") or "2025-03",
        "{diff}": format_val(get_value("差额", "gap", "diff")),
    }
    
    for key, value in replacements.items():
        insight_template = insight_template.replace(key, str(value))
    
    return insight_template


def execute(context: WorkflowContext, llm_client=None) -> bool:
    """
    执行业务解读步骤
    
    Returns:
        True: 成功
    """
    import time
    start_time = time.time()
    
    conclusion = ""
    key_numbers = []
    
    # 尝试使用 LLM 生成
    if llm_client and context.result:
        try:
            prompt = f"""你是广汽集团经营分析师。根据查询结果，用1-2句中文给出业务结论。

## 用户问题
{context.question}

## 指标
{context.matched_metric.metric_name if context.matched_metric else '通用指标'}

## 维度
{json.dumps(context.dimensions, ensure_ascii=False)}

## 查询结果
列名：{', '.join(context.result.columns)}
行数：{context.result.row_count}
前3行：{str(context.result.rows[:3])}

## 要求
1. 结论中必须包含关键数字
2. 如果有目标/预算对比，说明达成情况和差距
3. 如果是趋势，说明上升/下降方向
4. 不要编造数据中没有的信息
5. 同时提取关键数字列表，格式为[{{"label":"标签","value":"数值"}}]
6. 只返回JSON：{{"conclusion":"结论文本","key_numbers":[{{"label":"标签","value":"数值"}}]}}
"""
            
            response = llm_client.call([
                {"role": "user", "content": prompt}
            ])
            
            # 解析 JSON
            import re
            match = re.search(r'\{[^{}]*"conclusion"[^{}]*\}', response, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                conclusion = parsed.get("conclusion", "")
                key_numbers = parsed.get("key_numbers", [])
        except Exception as e:
            pass
    
    # 兜底：使用模板生成
    if not conclusion:
        conclusion, key_numbers = generate_conclusion_template(context)
    
    context.conclusion = conclusion
    context.key_numbers = key_numbers
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # 记录思考链
    content = f"生成业务结论：{conclusion[:50]}..." if len(conclusion) > 50 else f"生成业务结论：{conclusion}"
    if key_numbers:
        content += f"。提取关键数字 {len(key_numbers)} 个"
    
    context.add_thinking_step(
        step=8,
        name="业务解读",
        content=content,
        status="done",
        duration_ms=duration_ms
    )
    
    return True
