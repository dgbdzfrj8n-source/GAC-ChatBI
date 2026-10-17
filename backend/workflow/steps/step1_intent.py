"""
Step1: 意图识别
谁做：大模型（LLM）
输入：用户原始问题
输出：intent + confidence + reasoning
"""

import json
import re
from typing import Optional
from workflow.context import WorkflowContext


# 支持的查询类型定义
QUERY_TYPES = {
    "指标查询": "询问某个具体指标的数值，如'3月埃安销量多少'",
    "对比查询": "比较两个或多个对象，如'埃安和传祺哪个销量高'",
    "趋势查询": "询问随时间变化，如'近半年销量走势'",
    "归因查询": "询问原因，如'销量为什么下降'",
    "非业务查询": "与汽车经营分析无关，如'今天天气'"
}

SYSTEM_PROMPT = """你是广汽集团经营分析系统的意图识别器。请判断用户问题属于以下哪种类型：
- 指标查询：询问某个具体指标的数值，如"3月埃安销量多少"
- 对比查询：比较两个或多个对象，如"埃安和传祺哪个销量高"
- 趋势查询：询问随时间变化，如"近半年销量走势"
- 归因查询：询问原因，如"销量为什么下降"
- 非业务查询：与汽车经营分析无关，如"今天天气"

只返回JSON：{"intent":"指标查询","confidence":0.95,"reasoning":"用户询问具体数值"}
"""


def recognize_intent(question: str, llm_client=None) -> dict:
    """
    意图识别主函数
    
    Args:
        question: 用户问题
        llm_client: LLM客户端，可选
    
    Returns:
        {"intent": str, "confidence": float, "reasoning": str}
    """
    # 非业务查询关键词快速检测
    non_business_keywords = [
        "天气", "新闻", "股票", "今天多少号", "现在几点",
        "你是谁", "你好", "hi", "hello",
        "怎么用", "帮助", "功能"
    ]
    
    # 业务关键词
    business_keywords = [
        "销量", "营收", "达成", "预算", "目标", "交付",
        "埃安", "传祺", "昊铂", "品牌",
        "cpl", "roi", "线索", "投放", "渠道", "营销",
        "客流", "漏斗", "转化", "库存", "周转",
        "单车", "均价", "毛利", "成本", "费用"
    ]
    
    question_lower = question.lower()
    
    # 检查是否包含业务关键词
    has_business = any(kw in question_lower for kw in business_keywords)
    has_non_business = any(kw in question_lower for kw in non_business_keywords)
    
    # 判断意图
    if "为什么" in question or "原因" in question or "归因" in question:
        intent = "归因查询"
        confidence = 0.9
        reasoning = "用户询问原因或归因分析"
    elif "对比" in question or "哪个高" in question or "比较" in question or "vs" in question_lower:
        intent = "对比查询"
        confidence = 0.85
        reasoning = "用户进行对比分析"
    elif any(kw in question for kw in ["走势", "趋势", "变化", "趋势", "近", "环比", "同比"]):
        intent = "趋势查询"
        confidence = 0.85
        reasoning = "用户询问时间趋势变化"
    elif has_business:
        intent = "指标查询"
        confidence = 0.95
        reasoning = "用户询问具体业务指标"
    elif has_non_business and not has_business:
        intent = "非业务查询"
        confidence = 0.95
        reasoning = "用户问题与业务无关"
    else:
        # 尝试使用 LLM
        if llm_client:
            try:
                result = llm_client.call([
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ])
                
                # 解析 JSON
                match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                    return {
                        "intent": parsed.get("intent", "指标查询"),
                        "confidence": float(parsed.get("confidence", 0.5)),
                        "reasoning": parsed.get("reasoning", "")
                    }
            except Exception:
                pass
        
        # 兜底：默认指标查询
        intent = "指标查询"
        confidence = 0.5
        reasoning = "未能明确识别，默认按指标查询处理"
    
    return {
        "intent": intent,
        "confidence": confidence,
        "reasoning": reasoning
    }


def execute(context: WorkflowContext, llm_client=None) -> bool:
    """
    执行意图识别步骤
    
    Returns:
        True: 成功，继续下一步
        False: 失败或拒答
    """
    import time
    start_time = time.time()
    
    # 执行意图识别
    result = recognize_intent(context.question, llm_client)
    
    context.intent = result["intent"]
    context.intent_confidence = result["confidence"]
    context.intent_reasoning = result["reasoning"]
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    # 记录思考链
    content = f"检测到查询类型：{result['intent']}。{result['reasoning']}"
    if context.matched_metric:
        content += f" 核心指标：{context.matched_metric.metric_name}。"
    
    context.add_thinking_step(
        step=1,
        name="意图识别",
        content=content,
        status="done",
        duration_ms=duration_ms
    )
    
    # 判断是否拒答
    if result["intent"] == "非业务查询" or result["confidence"] < 0.3:
        context.set_reject(
            reason=f"当前问题属于「{result['intent']}」，与广汽集团经营分析无关。",
            supported_domains=["整车销售", "经营财务", "市场营销", "渠道经营", "库存管理"]
        )
        return False
    
    return True
