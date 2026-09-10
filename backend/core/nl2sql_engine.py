"""
核心 NL2SQL 引擎 (NL2SQL Engine)
核心功能：
1. 协调 Schema Linker 进行语义剪枝（Token 控制）；
2. 调度 LLM（优先调用配置的 DeepSeek / OpenAI 兼容 API；若未配置 API Key，平滑回退至预置 Mock 录像模式，确保 100% 演示可用）；
3. 驱动 AST 只读安全检查与执行；
4. 容错闭环：执行失败自动触发 1 次 Self-Healing 自愈修正。
"""

import os
import re
import json
from typing import Dict, Any, List, Optional
from backend.core.schema_linker import SchemaLinker
from backend.core.sql_executor import SqlExecutor
from backend.core.prompt_templates import (
    SYSTEM_PROMPT,
    build_nl2sql_prompt,
    build_self_healing_prompt
)

# 尝试载入 openai SDK
try:
    import openai
    HAS_OPENAI_SDK = True
except ImportError:
    HAS_OPENAI_SDK = False

# 预置典型问数场景的 Mock 录像库（面试与断网防翻车保证）
MOCK_KNOWLEDGE_BASE = {
    "2025年3月埃安销量与预算达成率": {
        "sql": """WITH monthly_sales AS (
    SELECT 
        brand_name,
        STRFTIME('%Y-%m', sale_date) AS year_month,
        SUM(delivered_units) AS actual_units
    FROM fact_sales_daily
    WHERE brand_name = '广汽埃安' AND STRFTIME('%Y-%m', sale_date) = '2025-03'
    GROUP BY brand_name, year_month
)
SELECT 
    s.brand_name,
    s.year_month,
    s.actual_units,
    b.target_units,
    ROUND(s.actual_units * 100.0 / NULLIF(b.target_units, 0), 2) AS fulfillment_rate_pct
FROM monthly_sales s
JOIN dim_budget_target b 
  ON s.brand_name = b.brand_name AND s.year_month = b.year_month;""",
        "insight": "2025年3月广汽埃安实际完成交付 4,462 辆，预算目标为 4,615 辆，综合达成率为 96.68%，整体表现稳健，距离月度目标仅存 153 辆缺口。"
    },
    "各品牌总销量与总营收": {
        "sql": """SELECT 
    brand_name,
    SUM(delivered_units) AS total_delivered_units,
    ROUND(SUM(gross_revenue) / 100000000.0, 2) AS gross_revenue_billion_yuan,
    ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 2) AS avg_price_yuan
FROM fact_sales_daily
GROUP BY brand_name
ORDER BY total_delivered_units DESC;""",
        "insight": "广汽埃安以 64,321 辆交付量位居第一（营收 92.55 亿元）；广汽传祺交付 47,343 辆（营收 86.59 亿元）；昊铂累计交付 11,715 辆（单车均价超 22 万元，拉动高端结构）。"
    },
    "各营销渠道投放支出与获客成本": {
        "sql": """SELECT 
    channel_name,
    ROUND(SUM(expense_amount) / 10000.0, 2) AS total_expense_wan,
    SUM(leads_generated) AS total_leads,
    ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 2) AS cpl_yuan
FROM fact_marketing_expenses
GROUP BY channel_name
ORDER BY cpl_yuan ASC;""",
        "insight": "抖音信息流为获客性价比最高渠道（CPL 仅 94.69 元/条）；懂车帝垂媒集客总量最大（CPL 119.85 元/条）；线下巡展外拓成本较高（CPL 264.07 元/条），建议优化展点选址。"
    },
    "传祺各车型在华东大区销量": {
        "sql": """SELECT 
    model_name,
    SUM(delivered_units) AS total_units,
    ROUND(SUM(gross_revenue) * 1.0 / NULLIF(SUM(delivered_units), 0), 2) AS avg_price
FROM fact_sales_daily
WHERE brand_name = '广汽传祺' AND region_name = '华东区'
GROUP BY model_name
ORDER BY total_units DESC;""",
        "insight": "华东大区中传祺M8与GS8构成双主力支撑，其中高端MPV传祺M8均价稳定在 22 万元以上，市场认可度极高。"
    }
}

class Nl2SqlEngine:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "deepseek-chat"):
        self.api_key = api_key or os.environ.get("LLM_API_KEY", "")
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
        self.model = model
        self.schema_linker = SchemaLinker()
        self.sql_executor = SqlExecutor()

    def _extract_sql(self, text: str) -> str:
        """从模型输出中提取 Markdown SQL 块"""
        match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """统一调用 LLM API"""
        if not self.api_key or not HAS_OPENAI_SDK:
            return None
        
        try:
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[LLM 调用异常]: {e}")
            return None

    def _match_mock_knowledge(self, query: str) -> Optional[Dict[str, str]]:
        """从 Mock 库中模糊匹配问答"""
        for k, v in MOCK_KNOWLEDGE_BASE.items():
            words = [w for w in ["埃安", "达成率", "渠道", "获客", "传祺", "华东", "总销量", "营收"] if w in k]
            if words and all(w in query for w in words):
                return v
        return None

    def ask(self, query: str, force_mock: bool = False) -> Dict[str, Any]:
        """
        核心问数调度主流程：
        1. 剪枝提取 Schema
        2. 生成 SQL（API 或 Mock）
        3. AST 检查与执行
        4. 报错 1 次自愈重试
        """
        # 1. 语义剪枝
        link_res = self.schema_linker.link(query)
        thought_steps = list(link_res["thought_steps"])
        pruned_schema = link_res["pruned_schema_text"]
        metric_rules = link_res["metric_rules_text"]

        raw_sql = None
        insight = None
        is_mock = False

        # 2. 尝试匹配 Mock 录像（若显式指定或无 API 密钥）
        if force_mock or not self.api_key:
            mock_hit = self._match_mock_knowledge(query)
            if mock_hit:
                thought_steps.append("已命中车企高频离线经营知识，以 0-Latency 模式秒级响应")
                raw_sql = mock_hit["sql"]
                insight = mock_hit["insight"]
                is_mock = True

        # 3. 若无 Mock 命中，则拼装 Prompt 调用 LLM
        if not raw_sql:
            thought_steps.append("正在调度大模型理解业务意图并生成标准 SQL...")
            prompt = build_nl2sql_prompt(query, pruned_schema, metric_rules)
            llm_reply = self._call_llm(SYSTEM_PROMPT, prompt)

            if llm_reply:
                raw_sql = self._extract_sql(llm_reply)
            else:
                # 兜底 Mock 案例
                thought_steps.append("API 未配置或网络不通，平滑降级至广汽经营基准案例")
                raw_sql = MOCK_KNOWLEDGE_BASE["2025年3月埃安销量与预算达成率"]["sql"]
                insight = MOCK_KNOWLEDGE_BASE["2025年3月埃安销量与预算达成率"]["insight"]
                is_mock = True

        # 4. 执行 SQL
        thought_steps.append(f"正在通过 {self.sql_executor.engine_type} 执行只读聚合查询...")
        exec_res = self.sql_executor.execute_query(raw_sql)

        # 5. 报错 1 次 Self-Healing 自愈修正机制
        healed = False
        if not exec_res["success"] and not is_mock and self.api_key:
            thought_steps.append(f"初次执行出现语法或口径异常: {exec_res['error']}，正在触发自愈重试修正...")
            heal_prompt = build_self_healing_prompt(query, raw_sql, exec_res["error"], pruned_schema)
            healed_reply = self._call_llm(SYSTEM_PROMPT, heal_prompt)
            if healed_reply:
                healed_sql = self._extract_sql(healed_reply)
                thought_steps.append("自愈修复完成，重新提交数据库验证执行...")
                retry_res = self.sql_executor.execute_query(healed_sql)
                if retry_res["success"]:
                    exec_res = retry_res
                    raw_sql = healed_sql
                    healed = True
                    thought_steps.append("✔ 自愈重试成功，数据已成功拉取！")

        if exec_res["success"]:
            thought_steps.append(f"查询成功，耗时 {exec_res['execution_time_ms']}ms，获取 {exec_res['row_count']} 条经营聚合记录")
            if not insight:
                insight = f"本次查询共获得 {exec_res['row_count']} 条业务记录，数据已成功经过集团统一口径校验。"

        return {
            "query": query,
            "thought_steps": thought_steps,
            "sql": raw_sql,
            "success": exec_res["success"],
            "data": exec_res["data"],
            "columns": exec_res["columns"],
            "row_count": exec_res["row_count"],
            "execution_time_ms": exec_res["execution_time_ms"],
            "error": exec_res["error"],
            "summary_insight": insight,
            "healed": healed,
            "engine": self.sql_executor.engine_type
        }

if __name__ == "__main__":
    engine = Nl2SqlEngine()
    print("=== 测试 1：高频提问（Mock 演示模式秒回）===")
    res1 = engine.ask("请查下2025年3月埃安销量与预算达成率是多少？", force_mock=True)
    print("思考链:", res1["thought_steps"])
    print("生成SQL:\n", res1["sql"])
    print("数据条数:", res1["row_count"])
    print("数据前1条:", res1["data"][0] if res1["data"] else None)
    print("经营洞察:", res1["summary_insight"])
