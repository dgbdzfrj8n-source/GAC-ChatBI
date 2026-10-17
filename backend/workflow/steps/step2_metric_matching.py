"""
Step2: 指标匹配
谁做：规则（同义词精确匹配）+ 大模型（模糊匹配）混合
输入：用户问题、语义层30个指标
输出：matched_metric + confidence + synonym_mapping
"""

import json
import re
from typing import Optional, List, Dict, Any
from workflow.context import WorkflowContext, Metric


# 同义词映射表
SYNONYM_MAPPINGS = {
    # 销量相关
    "销量": "delivered_units",
    "交付量": "delivered_units",
    "交付": "delivered_units",
    "卖了多少": "delivered_units",
    "卖了": "delivered_units",
    
    # 营收相关
    "营收": "gross_revenue",
    "收入": "gross_revenue",
    "营业额": "gross_revenue",
    
    # 达成率相关
    "达成率": "fulfillment_rate",
    "完成率": "fulfillment_rate",
    "目标达成": "fulfillment_rate",
    "完成情况": "fulfillment_rate",
    
    # CPL相关
    "cpl": "cpl",
    "获客成本": "cpl",
    "单渠道获客成本": "cpl",
    
    # ROI相关
    "roi": "roi",
    "投资回报": "roi",
    
    # 客流相关
    "客流": "store_visits",
    "进店": "store_visits",
    "客流": "store_visits",
    
    # 转化率相关
    "转化率": "conversion_rate",
    "转化": "conversion_rate",
    
    # 库存相关
    "库存": "stock_units",
    "库存周转": "avg_stock_days",
    
    # 留资相关
    "留资": "leads_count",
    "线索": "leads_generated",
}


def match_synonyms(question: str) -> Dict[str, str]:
    """
    规则匹配同义词
    返回: {"销量": "delivered_units", ...}
    """
    mappings = {}
    question_lower = question.lower()
    
    for keyword, field in SYNONYM_MAPPINGS.items():
        if keyword in question_lower:
            mappings[keyword] = field
    
    return mappings


def load_metrics() -> List[Metric]:
    """从 metrics_dict.json 加载指标"""
    import os
    
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    metrics_path = os.path.join(current_dir, "core", "metrics_dict.json")
    
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        metrics = []
        for m in data.get("metrics", []):
            metrics.append(Metric.from_dict(m))
        return metrics
    except Exception:
        return []


def calculate_similarity(text1: str, text2: str) -> float:
    """
    简单的语义相似度计算（基于关键词重叠）
    后续可替换为 embedding 模型
    """
    if not text1 or not text2:
        return 0.0
    
    # 标准化
    t1 = text1.lower().replace("(", "（").replace(")", "）")
    t2 = text2.lower().replace("(", "（").replace(")", "）")
    
    # 关键词集合
    words1 = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', t1))
    words2 = set(re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', t2))
    
    # Jaccard 相似度
    intersection = words1 & words2
    union = words1 | words2
    
    if not union:
        return 0.0
    
    return len(intersection) / len(union)


def match_metric(question: str, metrics: List[Metric], 
                 llm_client=None) -> tuple[Optional[Metric], float]:
    """
    指标匹配主函数
    
    两级匹配：
    1. 同义词精确匹配（规则，快）
    2. 语义相似度匹配（兜底）
    
    Returns:
        (matched_metric, confidence)
    """
    question_lower = question.lower()
    
    # 第一级：检查指标名称是否直接出现
    for metric in metrics:
        metric_name = metric.metric_name.lower()
        
        # 完全包含
        if metric_name in question_lower:
            return metric, 0.95
        
        # 核心词匹配（如"达成率"匹配"销售达成率"）
        core_words = ["达成率", "交付量", "营收", "CPL", "客流", "转化率", "库存", "周转"]
        for word in core_words:
            if word in metric_name and word in question_lower:
                return metric, 0.90
    
    # 第二级：语义相似度匹配
    best_metric = None
    best_score = 0.0
    
    for metric in metrics:
        # 计算与指标名称的相似度
        name_score = calculate_similarity(question, metric.metric_name)
        
        # 计算与定义文本的相似度
        def_score = calculate_similarity(question, metric.definition)
        
        # 取平均
        avg_score = (name_score + def_score) / 2
        
        if avg_score > best_score:
            best_score = avg_score
            best_metric = metric
    
    # 阈值判断
    if best_score >= 0.2:
        return best_metric, min(best_score + 0.3, 0.95)
    
    # 第三级：LLM 匹配（如果有）
    if llm_client and best_score < 0.3:
        try:
            prompt = f"""用户问题：{question}

可选指标列表：
"""
            for m in metrics[:10]:  # 限制数量
                prompt += f"- {m.metric_name}: {m.definition}\n"
            
            prompt += """
请判断用户最可能想查询哪个指标，返回JSON格式：
{"metric_name": "指标名称", "confidence": 0.85, "reasoning": "判断理由"}
"""
            
            result = llm_client.call([
                {"role": "user", "content": prompt}
            ])
            
            # 解析结果
            match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
                metric_name = parsed.get("metric_name", "")
                confidence = float(parsed.get("confidence", 0.5))
                
                for m in metrics:
                    if m.metric_name == metric_name:
                        return m, confidence
        except Exception:
            pass
    
    # 兜底：返回"总交付量"指标
    for metric in metrics:
        if "交付量" in metric.metric_name or "总交付" in metric.metric_name:
            return metric, 0.5
    
    return None, 0.0


def execute(context: WorkflowContext, metrics: List[Metric] = None, 
            llm_client=None) -> bool:
    """
    执行指标匹配步骤
    
    Returns:
        True: 成功，继续下一步
        False: 失败或拒答
    """
    import time
    start_time = time.time()
    
    # 加载指标库（如果未提供）
    if metrics is None:
        metrics = load_metrics()
    
    # 执行同义词匹配
    synonym_mapping = match_synonyms(context.question)
    context.synonym_mapping = synonym_mapping
    
    # 执行指标匹配
    matched_metric, confidence = match_metric(context.question, metrics, llm_client)
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    if matched_metric:
        context.matched_metric = matched_metric
        context.metric_confidence = confidence
        
        # 记录思考链
        content = f"语义层命中指标 {matched_metric.metric_id}（{matched_metric.metric_name}），"
        content += f"匹配置信度 {confidence:.2f}。"
        
        if synonym_mapping:
            content += f" 同义词映射：{', '.join(synonym_mapping.keys())}。"
        
        context.add_thinking_step(
            step=2,
            name="指标匹配",
            content=content,
            status="done",
            duration_ms=duration_ms
        )
        
        # 判断置信度
        if confidence < 0.3:
            context.set_reject(
                reason="未能在语义层找到匹配的经营指标",
                supported_domains=["整车销售", "经营财务", "市场营销", "渠道经营", "库存管理"]
            )
            return False
        
        return True
    else:
        # 没有匹配到指标，拒答
        context.set_reject(
            reason="未能在语义层找到匹配的经营指标",
            supported_domains=["整车销售", "经营财务", "市场营销", "渠道经营", "库存管理"]
        )
        return False
