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
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.auth import CurrentUser
from core.schema_linker import SchemaLinker
from core.sql_executor import SqlExecutor
from core.prompt_templates import (
    SYSTEM_PROMPT,
    build_nl2sql_prompt,
    build_self_healing_prompt
)
from core.query_templates import (
    QUERY_TEMPLATES,
    match_query_template,
    match_small_talk,
)

# 尝试载入 openai SDK
try:
    import openai
    HAS_OPENAI_SDK = True
except ImportError:
    HAS_OPENAI_SDK = False


def _call_llm_direct() -> Dict[str, Any]:
    """诊断用：直接打 DeepSeek API，绕过 SDK，返回完整诊断结果"""
    import json, urllib.request, urllib.error, os as _os

    api_key = _os.environ.get("LLM_API_KEY", "")
    base_url = _os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
    model = "deepseek-chat"

    result: Dict[str, Any] = {
        "env_key_set": bool(api_key),
        "env_key_prefix": api_key[:8] + "..." if api_key else "(empty)",
        "env_key_len": len(api_key),
        "base_url": base_url,
        "has_openai_sdk": HAS_OPENAI_SDK,
        "deepseek_http_status": None,
        "deepseek_response": None,
        "error": None,
    }

    if not api_key:
        result["error"] = "LLM_API_KEY not set in environment"
        return result

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Say 'OK' in one word."}],
        "max_tokens": 10,
        "temperature": 0.0,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            result["deepseek_http_status"] = resp.status
            parsed = json.loads(body)
            result["deepseek_response"] = parsed.get("choices", [{}])[0].get("message", {}).get("content", "")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        result["deepseek_http_status"] = e.code
        try:
            err_body = json.loads(body)
            result["error"] = f"HTTP {e.code}: {err_body.get('error', {}).get('message', body[:200])}"
        except Exception:
            result["error"] = f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        result["error"] = str(e)

    return result

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
    ROUND(s.actual_units * 100.0 / NULLIF(b.target_units, 0), 2) AS fulfillment_rate_pct,
    (b.target_units - s.actual_units) AS gap_units
FROM monthly_sales s
JOIN dim_budget_target b 
  ON s.brand_name = b.brand_name AND s.year_month = b.year_month;""",
        "insight": "2025年3月广汽埃安实际完成交付 {actual} 辆，预算目标为 {target} 辆，综合达成率为 {rate}%。距离月度目标还差 **{diff} 辆**，整体表现稳健。"
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
        """优先匹配 15 条精确问数模板库（覆盖前端 SuggestionPills）"""
        tmpl = match_query_template(query)
        if tmpl:
            sql = tmpl["sql"].replace("{ym}", "2025-03")  # 默认月份
            return {"sql": sql, "insight": tmpl["insight"], "template_id": tmpl["id"]}
        # 兼容老的 mock 库（兜底）
        for k, v in MOCK_KNOWLEDGE_BASE.items():
            words = [w for w in ["埃安", "达成率", "渠道", "获客", "传祺", "华东", "总销量", "营收"] if w in k]
            if words and all(w in query for w in words):
                return v
        return None

    # 闲聊/元问题触发词（增强版：覆盖寒暄、反馈、验证码、跑题）
    # [P1 修复] 移除"今天/昨天/明天"等纯时间词——这些经常跟业务词组合
    #          （如"昨天埃安卖了多少车"），让 _detect_unsupported_entity
    #          通过 LLM/模板路径处理，截走会导致静默失败
    SMART_TALK_TRIGGERS = [
        "你是谁", "你叫什么", "介绍一下", "关于你", "你是ai吗",
        "怎么用", "如何使用", "帮助", "功能介绍",
        "你能做什么", "what can you do", "who are you",
        "hello", "hi", "你好", "您好", "请问", "在吗",
        "这个系统", "这个平台", "chatbi",
        # 新增：反馈/投诉/测试
        "不好用", "答错", "答错了", "错误", "测试", "怎么啦",
        # 新增：跑题识别（不含业务关键词）
        "天气", "新闻",
        "开心", "高兴", "难过", "郁闷", "累", "忙",
        "吃饭", "睡觉", "下班", "休息", "开会",
        # 时间元问题（"今天星期几"这类没业务意图的）
        "几月", "几号", "几月了", "几月份", "几个月",
        "几点了", "什么时候",
        "现在几点", "今天几号", "今天星期几", "现在几月", "现在第几",
    ]

    META_ANSWER = """我是**广汽云 ChatBI**，由谢志锋主导构建的智能经营分析助手。

**我能帮你做什么：**
• 📊 查询各品牌（埃安/传祺/昊铂）的销量、营收、达成率
• 💰 分析营销渠道投放与 CPL（获客成本）
• 🚗 查看客流转化率与漏斗分析
• 📈 生成趋势图与对比报表
• 🔍 深度归因：定位销量波动的根因

**快捷提问示例（点击下方 15 条直达）：**
• "2025年3月埃安销量与预算达成率"
• "各品牌总交付量与总营收"
• "抖音渠道 CPL 排名"
• "昊铂 GT 与 HT 客流转化率对比"

直接输入您想了解的问题，或点击下方快捷提问按钮！😊"""

    def _is_meta_question(self, query: str) -> bool:
        """判断是否为闲聊/元问题"""
        q = query.strip().lower()
        if match_small_talk(query):
            return True
        return any(t in q for t in self.SMART_TALK_TRIGGERS)

    # 时间元问题关键词
    TIME_TRIGGERS = {
        # 现在/今天 + 第几月/几月/几月了/几月份 => 给当前月份
        "month": ["现在第几月份", "现在第几月", "现在是几月", "现在几月", "这个月", "现在是几月份",
                  "几月了", "几月份", "几月", "几月份了", "当前月份"],
        # 现在/今天 + 几号/几号了 => 给当前日期
        "day": ["今天几号", "现在几号", "几号了", "今天是几号", "今天几号了", "今天日期", "今天日期是"],
        # 现在/今天/几点了 => 给当前时间
        "now": ["现在几点", "几点了", "现在时间", "现在时间几点"],
        # 星期几
        "weekday": ["今天星期几", "今天是星期几", "现在星期几", "今天礼拜几", "礼拜几"],
        # 今年/哪一年
        "year": ["今年是哪一年", "今年是哪年", "今年几年", "今年多少年", "今年"],
    }

    def _answer_time_question(self, query: str) -> Optional[str]:
        """对命中时间元问题的查询返回精确短答案；不命中则返回 None 走默认 META_ANSWER。"""
        from datetime import datetime
        try:
            now = datetime.now()
            q = query.strip()
            # 按优先级匹配
            for kind, triggers in self.TIME_TRIGGERS.items():
                for t in triggers:
                    if t in q:
                        if kind == "month":
                            return f"📅 现在是 **{now.year} 年 {now.month} 月**（本月共 30 天，今天是 {now.day} 号）。"
                        if kind == "day":
                            return f"📅 今天日期是 **{now.year}-{now.month:02d}-{now.day:02d}**。"
                        if kind == "now":
                            return f"⏰ 现在是 **{now.strftime('%H:%M')}**（{now.year}-{now.month:02d}-{now.day:02d}）。"
                        if kind == "weekday":
                            names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
                            return f"📅 今天是 **{names[now.weekday()]}**。"
                        if kind == "year":
                            return f"📅 今年是 **{now.year} 年**。"
        except Exception:
            pass
        return None

    def _render_insight_template(self, insight: str, exec_res: Dict[str, Any], query: str) -> str:
        """渲染 insight 模板里的占位符，把 {actual}, {target}, {rate} 等替换为真实值。

        data 可能是 list[dict] 或 list[tuple]（取决于 sql_executor 行为）
        """
        try:
            data = exec_res.get("data", [])
            cols = exec_res.get("columns", [])

            if not data:
                return insight.replace("{ym}", "2025-03").replace("{total}", "0").replace("{count}", "0")

            first = data[0]
            col_idx = {c: i for i, c in enumerate(cols)}

            def get_val(*names):
                """按列名取值（兼容 list[dict] 和 list[tuple]）"""
                # 优先作为 dict
                if isinstance(first, dict):
                    for n in names:
                        if n in first and first[n] is not None:
                            return first[n]
                    # 模糊匹配
                    for n in names:
                        for col in cols:
                            if n.lower() in col.lower() or col.lower() in n.lower():
                                if first.get(col) is not None:
                                    return first[col]
                    return None
                # list[tuple] 形式
                for n in names:
                    if n in col_idx:
                        v = first[col_idx[n]]
                        if v is not None:
                            return v
                    # 模糊
                    for col in cols:
                        if n.lower() in col.lower() or col.lower() in n.lower():
                            v = first[col_idx[col]]
                            if v is not None:
                                return v
                return None

            def gv(*names) -> str:
                v = get_val(*names)
                if v is None:
                    return "—"
                if isinstance(v, float):
                    return f"{v:,.2f}" if abs(v) < 100 else f"{int(v):,}"
                return str(v)

            ym = "2025-03"
            for k in ["月份", "ym", "year_month"]:
                v = get_val(k)
                if v:
                    ym = str(v)
                    break

            actual_val = gv("实际交付量", "units", "总交付量", "delivered_units")
            target_val = gv("预算目标量", "target_units")
            rate_val = gv("达成率_pct", "rate", "fulfillment_rate_pct")
            if "{rate}" in insight and rate_val == "—" and actual_val != "—" and target_val != "—":
                try:
                    a = float(actual_val.replace(",", ""))
                    t = float(target_val.replace(",", ""))
                    if t > 0:
                        rate_val = f"{(a/t*100):.2f}"
                except Exception:
                    pass

            replacements = {
                "{ym}": ym,
                "{actual}": actual_val,
                "{target}": target_val,
                "{rate}": rate_val,
                "{total}": gv("总交付量", "总营收_亿元", "total_delivered_units"),
                "{revenue}": gv("总营收_亿元", "营收_万元", "gross_revenue_billion_yuan"),
                "{top_model}": gv("车型", "model_name"),
                "{top_price}": gv("单车均价_元", "avg_price_yuan"),
                "{gq_price}": gv("单车均价_元", "avg_price_yuan"),
                "{ht_rate}": gv("试驾转化率_pct"),
                "{gt_rate}": gv("试驾转化率_pct"),
                "{diff}": gv("差额_辆", "差额", "gap_units", "diff_units"),
                "{top_channel}": gv("渠道", "channel_name"),
                "{top_pct}": gv("占比_pct"),
                "{model}": gv("车型", "model_name"),
                "{profit}": gv("估算毛利_元"),
                "{best}": gv("渠道", "channel_name"),
                "{best_cpl}": gv("CPL_元"),
                "{worst}": gv("渠道", "channel_name"),
                "{worst_cpl}": gv("CPL_元"),
                "{pct}": gv("抖音占比_pct"),
                "{best_roi}": gv("ROI_倍数"),
                "{top_region}": gv("门店大区", "region_name"),
                "{top_rate}": gv("客流成交转化率_pct"),
                "{step1}": gv("进店→试驾_pct"),
                "{step2}": gv("试驾→成交_pct"),
                "{count}": str(len(data)),
                "{lowest}": gv("转化率_pct"),
                # [P1 修复] Q06 环比下降最多 / 通用 品牌+环比 字段
                "{brand}": gv("品牌", "brand_name"),
                "{rate}": rate_val if rate_val != "—" else gv("环比_pct"),
            }

            for k, v in replacements.items():
                insight = insight.replace(k, v)

            return insight
        except Exception as e:
            print(f"[渲染 insight 异常]: {e}")
            return insight

    # 当前数仓可分析的实体粒度白名单（用于拦截"答非所问"幻觉）
    SUPPORTED_DIMENSIONS = {
        "品牌": ["广汽埃安", "广汽传祺", "昊铂", "brand_name"],
        "车型": ["AION Y", "AION S", "传祺GS8", "传祺M8", "传祺影豹", "昊铂GT", "昊铂HT", "model_name"],
        "大区": ["华南区", "华东区", "华北区", "华中区", "西南区", "region_name"],
        "省份": ["province_name"],
        "月份": ["2025-01", "2025-02", "2025-03", "2025-04"],
    }
    
    # 数仓暂不支持的实体粒度（用户提问命中这些关键词时，直接告知"无法分析"）
    UNSUPPORTED_ENTITIES = {
        "门店": {
            "reply": (
                "抱歉 😅 当前数仓没有门店（经销商）粒度数据。\n\n"
                "✅ 当前可分析粒度：\n"
                "• **品牌**：广汽埃安 / 广汽传祺 / 昊铂\n"
                "• **车型**：AION Y / AION S / 传祺GS8 / 传祺M8 / 传祺影豹 / 昊铂GT / 昊铂HT\n"
                "• **大区**：华南 / 华东 / 华北 / 华中 / 西南\n"
                "• **省份**：根据大区级联展开\n\n"
                "💡 **建议**：试试这类问题：\n"
                "• 「华东区广汽埃安3月销量」\n"
                "• 「各大区客流转化率排名」\n"
                "• 「广东省广汽传祺3月销量」\n\n"
                "📌 真实门店级分析需对接 DMS（经销商管理系统）数据"
            ),
            "keywords": ["门店", "4s店", "4S", "经销商", "dealer", "store"],
        },
        "客户个体": {
            "reply": (
                "抱歉 😅 当前 ChatBI 是**聚合级经营分析**，不支持到客户个体粒度。\n\n"
                "✅ 我们能提供：\n"
                "• 品牌 × 车型 × 大区的销量聚合\n"
                "• 渠道 × 月份的营销投放聚合\n"
                "• 大区间的客流转化对比\n\n"
                "📌 个体级分析受《数据安全法》与集团隐私合规要求限制，需走审批流程"
            ),
            "keywords": ["客户", "车主", "潜客", "用户id", "客户名", "姓名"],
        },
        "未来预测": {
            "reply": (
                "抱歉 😅 当前 ChatBI 是**历史经营分析** BI，不做未来预测。\n\n"
                "✅ 我们能提供：\n"
                "• 历史与当期数据复盘\n"
                "• 当期 vs 预算达成率\n"
                "• 跨期同比/环比\n\n"
                "💡 如需预测模型（销量预测 / 客流预测），需对接时间序列模型（Prophet/ARIMA）"
            ),
            "keywords": ["预测", "明年", "下个月", "未来", "forecast", "predict"],
        },
        # [P1 修复] 新增：竞品数据不在数仓范围（避免 LLM 幻觉写"比亚迪"等）
        "竞品对比": {
            "reply": (
                "抱歉 😅 当前 ChatBI 数据源是广汽集团内部经营主库，**不含外部竞品数据**。\n\n"
                "✅ 我们能提供的对比：\n"
                "• **集团内部 3 大品牌**：广汽埃安 / 广汽传祺 / 昊铂 的销量、营收、CPL 互比\n"
                "• **跨大区/跨车型/跨渠道** 的内部对比\n\n"
                "💡 **建议试试这些**：\n"
                "• 「埃安和传祺各车型销量对比」\n"
                "• 「各大区广汽埃安达成率对比」\n"
                "• 「抖音渠道与懂车帝 CPL 对比」\n\n"
                "📌 外部竞品分析需对接行业第三方数据（如乘联会、懂车帝榜单）"
            ),
            "keywords": ["比亚迪", "特斯拉", "tesla", "byd", "蔚来", "小鹏", "理想", "li", "xpeng", "nio",
                         "上汽", "东风", "一汽", "长安", "吉利", "奇瑞", "领克", "wey", "红旗",
                         "广丰", "广本", "丰田", "本田", "大众", "奔驰", "宝马", "奥迪", "外部", "竞品", "对手"],
        },
        # [P1 修复] 新增：利润/成本字段数仓没有，避免 LLM 把"利润"误读为"营收"
        "利润成本": {
            "reply": (
                "抱歉 😅 当前数仓**没有成本/利润字段**，无法直接计算利润。\n\n"
                "✅ 我们能提供的财务指标：\n"
                "• **总营收 / 单车均价**（基于 gross_revenue 字段）\n"
                "• **单车毛利率估算** = 1 - 折扣率（仅供经营参考，非真实毛利率）\n"
                "• **单车毛利贡献 Top 车型**：试试快捷提问「单车毛利贡献最高的车型」\n\n"
                "💡 **建议**：\n"
                "• 「各品牌单车成交均价」→ 看营收端\n"
                "• 「单车毛利贡献最高的车型」→ 看毛利贡献排序\n"
                "• 「各营销渠道 ROI」→ 看投放端效率\n\n"
                "📌 真实成本/净利率数据需对接财务系统（如 SAP、金蝶、用友）"
            ),
            "keywords": ["净利润", "利润率", "净利率", "毛利率", "总成本", "成本率", "净利", "利润", "毛利额", "毛利润"],
        },
    }
    
    def _detect_unsupported_entity(self, query: str) -> Optional[str]:
        """检测用户提问中是否包含数仓暂不支持的实体粒度。返回对应的引导文案。"""
        for entity_name, entity_cfg in self.UNSUPPORTED_ENTITIES.items():
            for kw in entity_cfg["keywords"]:
                if kw.lower() in query.lower():
                    return entity_cfg["reply"]
        return None

    def ask(self, query: str, force_mock: bool = False, current_user: Optional["CurrentUser"] = None) -> Dict[str, Any]:
        """
        核心问数调度主流程：
        1. 闲聊/元问题引导
        2. 不可达维度拦截（门店/客户个体/未来预测等）
        3. 15 条精确模板匹配
        4. LLM 生成
        5. AST 检查与执行
        6. 报错 1 次自愈重试
        """
        # 0. 闲聊/元问题兜底（精准引导）
        small_talk_reply = match_small_talk(query)
        if small_talk_reply:
            return {
                "query": query,
                "thought_steps": ["命中闲聊引导，返回智能引导语"],
                "sql": None,
                "success": True,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "error": None,
                "summary_insight": small_talk_reply,
                "healed": False,
                "engine": "guide",
                "is_meta_answer": True,
            }

        # 0.5 不可达维度拦截（防止 LLM 幻觉"门店"返回品牌交付量）
        unsupported_reply = self._detect_unsupported_entity(query)
        if unsupported_reply:
            return {
                "query": query,
                "thought_steps": [
                    "识别到用户提问涉及数仓暂不支持的实体粒度",
                    "诚实告知当前可分析维度，避免答非所问",
                ],
                "sql": None,
                "success": True,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "error": None,
                "summary_insight": unsupported_reply,
                "healed": False,
                "engine": "dimension_guard",
                "is_unsupported_entity": True,
            }

        if self._is_meta_question(query):
            # 对于"现在第几月"这类时间元问题，返回真实时间而不是默认 META_ANSWER 长版介绍
            time_reply = self._answer_time_question(query)
            insight_text = time_reply if time_reply else self.META_ANSWER
            return {
                "query": query,
                "thought_steps": ["命中闲聊/元问题，跳过 SQL 生成"],
                "sql": None,
                "success": True,
                "data": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
                "error": None,
                "summary_insight": insight_text,
                "healed": False,
                "engine": "meta",
                "is_meta_answer": True,
            }

        # 1. 语义剪枝（为 LLM 路径准备 schema）
        link_res = self.schema_linker.link(query)
        thought_steps = list(link_res["thought_steps"])
        pruned_schema = link_res["pruned_schema_text"]
        metric_rules = link_res["metric_rules_text"]

        raw_sql = None
        insight = None
        is_mock = False

        # ── [P0 修复] 精确模板匹配优先级最高，不依赖 force_mock ──
        # 原因：15 条快捷提问已全部在 DuckDB 验证，生产全走 LLM 会导致
        #       Q09 误判闲聊、Q12 ROI 错、Q15 缺过滤；改为：有 API key 时
        #       也优先走模板，模板无命中才走 LLM。
        tmpl = match_query_template(query)
        if tmpl:
            raw_sql = tmpl["sql"]
            # 占位符默认替换（{ym} 默认 2025-03；其他参数 SQL 里没用到）
            raw_sql = raw_sql.replace("{ym}", "2025-03")
            insight = tmpl["insight"]
            is_mock = False
            thought_steps.append(f"已命中 15 条精确问数模板（{tmpl['id']}），跳过 LLM 直接执行验证 SQL")
            # [P1 修复] 把模板的 chart_hint 透传到 chart_recommender，避免被自动推断覆盖
            self._last_template_chart_hint = tmpl.get("chart_hint")

        # 2. 兼容旧 Mock 兜底（仅在 force_mock=true 或无 API key 时触发）
        elif force_mock or not self.api_key:
            mock_hit = self._match_mock_knowledge(query)
            if mock_hit:
                thought_steps.append("已命中车企高频离线经营知识，以 0-Latency 模式秒级响应")
                raw_sql = mock_hit["sql"]
                insight = mock_hit["insight"]
                is_mock = True

        # 3. 若模板和 Mock 都无命中，则拼装 Prompt 调用 LLM
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
            # 渲染 insight 中的占位符（如 {actual}, {target}, {rate}, {ym} 等）
            if insight:
                insight = self._render_insight_template(insight, exec_res, query)
            if not insight:
                # [P2 修复] 根据行数给不同文案，避免套话
                row_count = exec_res['row_count']
                if row_count == 0:
                    insight = "📭 当前查询条件在数仓中未匹配到数据，请尝试调整查询条件或参考 15 条快捷提问。"
                elif row_count == 1:
                    insight = "✓ 已返回唯一匹配记录，请查看左侧数据卡片。"
                else:
                    insight = f"✓ 已返回 {row_count} 条记录，数据按当前维度自动聚合排序。"

            # [Sprint 10] 应用行级权限过滤 + 字段级脱敏
            if current_user:
                from core.permission import apply_full_permission, check_table_access
                # 1. 表级权限校验
                sql_lower = (raw_sql or "").lower()
                # 简单检测 SQL 里出现的 fact_/dim_ 表名
                import re as _re
                tables_in_sql = _re.findall(r'\b(fact_\w+|dim_\w+)\b', sql_lower)
                for tbl in set(tables_in_sql):
                    if not check_table_access(current_user, tbl):
                        return {
                            "query": query,
                            "thought_steps": thought_steps + [f"⛔ 权限不足：角色 {current_user.role} 无权访问表 {tbl}"],
                            "sql": raw_sql,
                            "success": False,
                            "data": [],
                            "columns": [],
                            "row_count": 0,
                            "execution_time_ms": exec_res["execution_time_ms"],
                            "error": f"权限不足：当前角色无访问表 {tbl} 的权限。请联系管理员申请。",
                            "summary_insight": f"⛔ 您的角色（{current_user.role}）无权访问表 {tbl}。\n\n请联系系统管理员申请权限，或切换到具备权限的账号。",
                            "healed": healed,
                            "engine": self.sql_executor.engine_type,
                            "is_meta_answer": False,
                            "permission_denied": True,
                        }

                # 2. 行级过滤 + 字段级脱敏（统一入口）
                perm_result = apply_full_permission(
                    sql=raw_sql,
                    user=current_user,
                    data=exec_res["data"],
                    columns=exec_res["columns"],
                )
                exec_res["data"] = perm_result["data"]
                exec_res["columns"] = perm_result["columns"]
                # 注意：行级过滤 SQL 已应用到 raw_sql（业务用户看起来"明明查询全集团但只看到自己区域"是预期行为）
                if perm_result["permission"]["row_filtered"]:
                    thought_steps.append(f"🔒 已应用行级权限：{current_user.department} + {current_user.region}")
                if perm_result["permission"]["masked_columns"]:
                    thought_steps.append(f"🎭 已脱敏敏感字段：{', '.join(perm_result['permission']['masked_columns'])}")
                # 把权限信息附加到返回 dict
                perm_info = perm_result["permission"]

        if not exec_res["success"]:
            perm_info = None

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
            "engine": self.sql_executor.engine_type,
            "permission": perm_info if current_user and exec_res["success"] else None,
            "is_empty_result": exec_res["success"] and (not exec_res["data"] or len(exec_res["data"]) == 0),
            "_chart_hint": getattr(self, "_last_template_chart_hint", None),
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
