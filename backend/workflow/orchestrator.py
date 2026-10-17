"""
Workflow Orchestrator - 编排器
核心：驱动 Text2SQL 8 步链路按顺序执行
"""

import time
import json
from typing import AsyncIterator, Optional, Dict, Any, List
from dataclasses import asdict

from workflow.context import WorkflowContext, ClarifySlot
from workflow.steps import (
    execute_step1,
    execute_step2,
    execute_step3,
    execute_step4,
    execute_step5,
    execute_step6,
    execute_step7,
    execute_step8,
    load_metrics
)


class ChatEvent:
    """SSE 事件类型"""
    
    @staticmethod
    def thinking_step(step_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"event": "thinking_step", "data": step_data}
    
    @staticmethod
    def sql(sql: str, ast_check_passed: bool = True) -> Dict[str, Any]:
        return {"event": "sql", "data": {"sql": sql, "ast_check_passed": ast_check_passed}}
    
    @staticmethod
    def result(columns: list, rows: list) -> Dict[str, Any]:
        return {"event": "result", "data": {"columns": columns, "rows": rows}}
    
    @staticmethod
    def chart(chart_type: str, field_mapping: Dict[str, str], config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "event": "chart",
            "data": {
                "chart_type": chart_type,
                "field_mapping": field_mapping,
                "config": config
            }
        }
    
    @staticmethod
    def conclusion(text: str, key_numbers: list) -> Dict[str, Any]:
        return {"event": "conclusion", "data": {"text": text, "key_numbers": key_numbers}}
    
    @staticmethod
    def clarify(question: str, options: list) -> Dict[str, Any]:
        return {"event": "clarify", "data": {"question": question, "options": options}}
    
    @staticmethod
    def reject(reason: str, supported_domains: list) -> Dict[str, Any]:
        return {
            "event": "reject",
            "data": {"reason": reason, "supported_domains": supported_domains}
        }
    
    @staticmethod
    def error(code: str, message: str, suggestion: str = "") -> Dict[str, Any]:
        return {
            "event": "error",
            "data": {"code": code, "message": message, "suggestion": suggestion}
        }
    
    @staticmethod
    def done(session_id: str, total_duration_ms: int) -> Dict[str, Any]:
        return {"event": "done", "data": {"session_id": session_id, "total_duration_ms": total_duration_ms}}


def _generate_final_events(context: WorkflowContext, start_time: float) -> List[Dict[str, Any]]:
    """生成最终事件列表（用于同步调用）"""
    context.total_duration_ms = int((time.time() - start_time) * 1000)
    events = []
    
    if context.status == "reject":
        events.append(ChatEvent.reject(
            reason=context.error.message if context.error else "问题超出业务范围",
            supported_domains=["整车销售", "经营财务", "市场营销", "渠道经营", "库存管理"]
        ))
    elif context.status == "clarify":
        events.append(ChatEvent.clarify(
            question=context.error.message if context.error else "",
            options=getattr(context, "clarify_options", [])
        ))
    else:
        events.append(ChatEvent.error(
            code=context.error.code if context.error else "UNKNOWN_ERROR",
            message=context.error.message if context.error else "未知错误",
            suggestion=context.error.suggestion if context.error else ""
        ))
    
    events.append(ChatEvent.done(context.session_id, context.total_duration_ms))
    return events


class Text2SQLWorkflow:
    """
    Text2SQL Workflow 编排器
    
    执行 8 步链路：
    1. 意图识别
    2. 指标匹配
    3. 维度解析
    4. 表定位
    5. SQL生成
    6. 执行校验
    7. 可视化决策
    8. 业务解读
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.metrics = load_metrics()
    
    def run(self, context: WorkflowContext) -> List[Dict[str, Any]]:
        """
        执行完整链路（同步版本，用于测试）
        
        Returns:
            事件列表
        """
        start_time = time.time()
        context.status = "running"
        
        # 加载指标库
        if not self.metrics:
            self.metrics = load_metrics()
        
        try:
            # ========== Step 1: 意图识别 ==========
            success = execute_step1(context, self.llm_client)
            
            if context.status in ["reject", "clarify", "failed"]:
                return _generate_final_events(context, start_time)
            
            if not success:
                context.set_error("INTENT_RECOGNITION_ERROR", "意图识别失败")
                return _generate_final_events(context, start_time)
            
            # ========== Step 2: 指标匹配 ==========
            success = execute_step2(context, self.metrics, self.llm_client)
            
            if context.status in ["reject", "clarify", "failed"]:
                return _generate_final_events(context, start_time)
            
            if not success:
                context.set_error("METRIC_MATCH_ERROR", "指标匹配失败")
                return _generate_final_events(context, start_time)
            
            # ========== Step 3: 维度解析 ==========
            success = execute_step3(context, self.llm_client)
            
            if context.status == "clarify":
                events = [
                    ChatEvent.clarify(
                        question=context.error.message if context.error else "",
                        options=getattr(context, "clarify_options", [])
                    )
                ]
                events.extend(_generate_final_events(context, start_time))
                return events
            
            if not success:
                context.set_error("DIMENSION_PARSE_ERROR", "维度解析失败")
                return _generate_final_events(context, start_time)
            
            # ========== Step 4: 表定位 ==========
            success = execute_step4(context)
            
            if not success:
                context.set_error("TABLE_LOCATION_ERROR", "表定位失败")
                return _generate_final_events(context, start_time)
            
            # ========== Step 5: SQL生成 ==========
            success = execute_step5(context, self.llm_client)
            
            if not success or not context.sql:
                context.set_error("SQL_GENERATION_ERROR", "SQL生成失败")
                return _generate_final_events(context, start_time)
            
            # ========== Step 6: 执行校验 ==========
            success = execute_step6(context)
            
            if not success:
                # 尝试重试
                if context.sql_attempts < 3:
                    context.sql_attempts += 1
                    success = execute_step6(context)
                    
                    if not success:
                        context.set_error("SQL_EXECUTION_ERROR", "SQL执行失败")
                        return _generate_final_events(context, start_time)
                else:
                    context.set_error("SQL_EXECUTION_ERROR", "SQL执行失败")
                    return _generate_final_events(context, start_time)
            
            # ========== Step 7: 可视化决策 ==========
            success = execute_step7(context, self.llm_client)
            
            if not success:
                context.chart_config = None
            
            # ========== Step 8: 业务解读 ==========
            success = execute_step8(context, self.llm_client)
            
            # ========== 成功：输出结果 ==========
            context.status = "success"
            context.total_duration_ms = int((time.time() - start_time) * 1000)
            
            events = []
            
            # 输出 SQL
            events.append(ChatEvent.sql(context.sql, ast_check_passed=True))
            
            # 输出结果
            if context.result:
                events.append(ChatEvent.result(context.result.columns, context.result.rows))
            
            # 输出图表
            if context.chart_config:
                events.append(ChatEvent.chart(
                    context.chart_config.chart_type,
                    context.chart_config.field_mapping,
                    context.chart_config.config
                ))
            
            # 输出结论
            events.append(ChatEvent.conclusion(
                context.conclusion or "查询完成",
                context.key_numbers
            ))
            
            # 完成
            events.append(ChatEvent.done(context.session_id, context.total_duration_ms))
            
            return events
            
        except Exception as e:
            context.status = "failed"
            context.set_error(
                code="INTERNAL_ERROR",
                message=f"系统内部错误: {str(e)}",
                suggestion="请稍后重试或联系管理员"
            )
            return _generate_final_events(context, start_time)


def run_workflow_sync(question: str, brand_filter: str = "全部", 
                      session_id: str = "", llm_client=None) -> Dict[str, Any]:
    """
    同步运行 Workflow（用于测试）
    """
    context = WorkflowContext(
        question=question,
        brand_filter=brand_filter,
        session_id=session_id or f"sess_{int(time.time())}"
    )
    
    workflow = Text2SQLWorkflow(llm_client)
    
    # 收集所有事件
    events = workflow.run(context)
    
    return {
        "context": context,
        "events": events
    }


if __name__ == "__main__":
    # 测试
    result = run_workflow_sync("2025年3月埃安销量与预算达成率是多少？")
    print("状态:", result["context"].status)
    print("意图:", result["context"].intent)
    print("指标:", result["context"].matched_metric.metric_name if result["context"].matched_metric else None)
    print("SQL:", result["context"].sql)
    print("行数:", result["context"].result.row_count if result["context"].result else 0)
    print("图表:", result["context"].chart_config.chart_type if result["context"].chart_config else None)
    print("结论:", result["context"].conclusion)
    print("思考链:")
    for step in result["context"].thinking_steps:
        print(f"  {step.step}. {step.name}: {step.content[:50]}...")
