"""
Step3: 维度解析
谁做：大模型（LLM）+ 规则（时间表达式解析）
输入：用户问题、指标支持的维度
输出：dimensions + missing_dimensions + confidence
"""

import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from workflow.context import WorkflowContext


# 品牌列表
BRANDS = ["广汽埃安", "广汽传祺", "昊铂", "埃安", "传祺", "昊铂"]
BRAND_MAPPING = {
    "广汽埃安": "广汽埃安",
    "埃安": "广汽埃安",
    "广汽传祺": "广汽传祺",
    "传祺": "广汽传祺",
}

# 区域列表
REGIONS = ["华东", "华南", "华北", "华中", "西南", "华东区", "华南区", "华北区", "华中区", "西南区"]
REGION_MAPPING = {
    "华东": "华东区",
    "华东区": "华东区",
    "华南": "华南区",
    "华南区": "华南区",
    "华北": "华北区",
    "华北区": "华北区",
    "华中": "华中区",
    "华中区": "华中区",
    "西南": "西南区",
    "西南区": "西南区",
}

# 车型列表（部分）
MODELS = ["AION Y", "AION S", "AION V", "AION LX", "传祺GS8", "传祺M8", "传祺影豹", "昊铂GT", "昊铂HT", "昊铂SSR"]

# 渠道列表
CHANNELS = ["抖音", "懂车帝", "汽车之家", "自然到店", "老客转介绍", "商圈巡展"]


def parse_absolute_time(text: str) -> Optional[str]:
    """解析绝对时间表达式"""
    # 2025年3月 -> 2025-03
    match = re.search(r'(\d{4})年(\d{1,2})月', text)
    if match:
        year, month = match.groups()
        return f"{year}-{int(month):02d}"
    
    # 2025-03 或 2025/03
    match = re.search(r'(\d{4})[/-](\d{1,2})', text)
    if match:
        year, month = match.groups()
        return f"{year}-{int(month):02d}"
    
    # 2025年Q1
    match = re.search(r'(\d{4})年Q([1-4])', text)
    if match:
        year, quarter = match.groups()
        quarter_starts = {"1": "01", "2": "04", "3": "07", "4": "10"}
        return f"{year}-{quarter_starts.get(quarter, '01')}"
    
    return None


def parse_relative_time(text: str) -> Optional[Dict[str, str]]:
    """解析相对时间表达式"""
    now = datetime.now()
    
    # 上个月
    if "上个月" in text:
        if now.month == 1:
            return {"start": f"{now.year-1}-12", "end": f"{now.year-1}-12"}
        return {"start": f"{now.year}-{now.month-1:02d}", "end": f"{now.year}-{now.month-1:02d}"}
    
    # 这个月
    if "这个月" in text or "本月" in text:
        return {"start": f"{now.year}-{now.month:02d}", "end": f"{now.year}-{now.month:02d}"}
    
    # 下个月
    if "下个月" in text:
        if now.month == 12:
            return {"start": f"{now.year+1}-01", "end": f"{now.year+1}-01"}
        return {"start": f"{now.year}-{now.month+1:02d}", "end": f"{now.year}-{now.month+1:02d}"}
    
    # 最近N天
    match = re.search(r'近(\d+)天', text)
    if match:
        days = int(match.group(1))
        # 简化处理，返回起始日期
        return {"days": str(days)}
    
    # 最近N个月
    match = re.search(r'近(\d+)个?月', text)
    if match:
        months = int(match.group(1))
        return {"months": str(months)}
    
    # Q1/Q2/Q3/Q4
    match = re.search(r'Q([1-4])', text)
    if match:
        quarter = int(match.group(1))
        starts = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
        sm, em = starts.get(quarter, (1, 3))
        return {"start": f"{now.year}-{sm:02d}", "end": f"{now.year}-{em:02d}"}
    
    return None


def parse_brand(text: str) -> Optional[str]:
    """解析品牌维度"""
    text_lower = text.lower()
    
    for brand in BRANDS:
        if brand in text:
            return BRAND_MAPPING.get(brand, brand)
    
    return None


def parse_region(text: str) -> Optional[str]:
    """解析区域维度"""
    for region in REGIONS:
        if region in text:
            return REGION_MAPPING.get(region, region)
    
    return None


def parse_model(text: str) -> Optional[str]:
    """解析车型维度"""
    for model in MODELS:
        if model in text:
            return model
    
    # 模糊匹配
    if "昊铂GT" in text or "GT" in text:
        return "昊铂GT"
    if "昊铂HT" in text or "HT" in text:
        return "昊铂HT"
    if "AION" in text or "埃安" in text:
        # 返回列表
        return None  # 需要更复杂的解析
    
    return None


def parse_channel(text: str) -> Optional[str]:
    """解析渠道维度"""
    for channel in CHANNELS:
        if channel in text:
            return channel
    
    return None


def parse_dimensions(question: str, required_dimensions: List[str] = None) -> Dict[str, Any]:
    """
    解析维度主函数
    
    Args:
        question: 用户问题
        required_dimensions: 该指标支持的维度列表
    
    Returns:
        {
            "brand": "广汽埃安" | None,
            "time": "2025-03" | None,
            "region": "华东区" | None,
            "model": "AION Y" | None,
            "channel": "抖音" | None,
            "confidence": 0.9,
            "missing": ["brand", "time"]
        }
    """
    dimensions = {}
    missing = []
    
    # 品牌解析
    brand = parse_brand(question)
    dimensions["brand"] = brand
    if "brand" in (required_dimensions or []) and not brand:
        missing.append("brand")
    
    # 时间解析
    time_dim = parse_absolute_time(question)
    if not time_dim:
        rel_time = parse_relative_time(question)
        if rel_time:
            time_dim = rel_time.get("start") or rel_time.get("months")
    
    dimensions["time"] = time_dim
    if "time" in (required_dimensions or []) and not time_dim:
        missing.append("time")
    
    # 区域解析
    region = parse_region(question)
    dimensions["region"] = region
    if "region" in (required_dimensions or []) and not region:
        missing.append("region")
    
    # 车型解析
    model = parse_model(question)
    dimensions["model"] = model
    if "model" in (required_dimensions or []) and not model:
        missing.append("model")
    
    # 渠道解析
    channel = parse_channel(question)
    dimensions["channel"] = channel
    if "channel" in (required_dimensions or []) and not channel:
        missing.append("channel")
    
    # 计算置信度
    filled_count = sum(1 for v in dimensions.values() if v is not None)
    total_count = len([v for v in dimensions.values() if v is not None or True])
    confidence = filled_count / total_count if total_count > 0 else 0.5
    
    return {
        **dimensions,
        "confidence": confidence,
        "missing": missing
    }


def execute(context: WorkflowContext, llm_client=None) -> bool:
    """
    执行维度解析步骤
    
    Returns:
        True: 成功，继续下一步
        False: 需要澄清或失败
    """
    import time
    start_time = time.time()
    
    # 获取指标支持的维度
    required_dimensions = []
    if context.matched_metric:
        required_dimensions = context.matched_metric.related_dimensions
    
    # 解析维度
    parsed = parse_dimensions(context.question, required_dimensions)
    
    context.dimensions = {
        "brand": parsed.get("brand") or context.brand_filter,
        "time": parsed.get("time"),
        "region": parsed.get("region"),
        "model": parsed.get("model"),
        "channel": parsed.get("channel")
    }
    context.missing_dimensions = parsed.get("missing", [])
    context.dimension_confidence = parsed.get("confidence", 0.5)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # 记录思考链
    dim_parts = []
    if context.dimensions.get("brand"):
        dim_parts.append(f"品牌={context.dimensions['brand']}")
    if context.dimensions.get("time"):
        dim_parts.append(f"时间={context.dimensions['time']}")
    if context.dimensions.get("region"):
        dim_parts.append(f"区域={context.dimensions['region']}")
    if context.dimensions.get("model"):
        dim_parts.append(f"车型={context.dimensions['model']}")
    
    content = "维度解析结果："
    if dim_parts:
        content += "，".join(dim_parts)
    else:
        content += "未明确指定维度，使用全量聚合"
    
    if context.missing_dimensions:
        content += f"。缺失维度：{', '.join(context.missing_dimensions)}"
    
    context.add_thinking_step(
        step=3,
        name="维度解析",
        content=content,
        status="done",
        duration_ms=duration_ms
    )
    
    # 判断是否需要澄清
    # 关键维度（品牌+时间）缺失且置信度低
    key_missing = "brand" in context.missing_dimensions or "time" in context.missing_dimensions
    low_confidence = context.dimension_confidence < 0.6
    
    if key_missing and low_confidence:
        # 生成澄清问题
        clarify_question = f"您想查询哪个品牌、哪个时间段的"
        if context.matched_metric:
            clarify_question += context.matched_metric.metric_name
        clarify_question += "？"
        
        # 生成选项
        brand_options = [
            {"label": "广汽埃安", "value": "广汽埃安"},
            {"label": "广汽传祺", "value": "广汽传祺"},
            {"label": "昊铂", "value": "昊铂"},
            {"label": "全部品牌", "value": "全部"}
        ]
        
        # 简化时间选项
        now = datetime.now()
        time_options = [
            {"label": f"{now.year}年{now.month}月（本月）", "value": f"{now.year}-{now.month:02d}"},
            {"label": f"{now.year}年{now.month-1 if now.month > 1 else 12}月（上月）", "value": f"{now.year if now.month > 1 else now.year-1}-{now.month-1 if now.month > 1 else 12:02d}"},
            {"label": f"{now.year}年第1季度", "value": f"{now.year}-01"},
            {"label": "全部时间", "value": "全部"}
        ]
        
        context.set_clarify(
            question=clarify_question,
            options=[
                {"type": "brand", "options": brand_options},
                {"type": "time", "options": time_options}
            ]
        )
        return False
    
    return True
