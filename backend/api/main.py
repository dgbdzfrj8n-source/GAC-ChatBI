"""
广汽云 ChatBI 后端智能服务入口 (FastAPI)
功能清单：
1. GET /api/health: 服务健康检查与数据库引擎状态；
2. GET /api/metrics: 指标语义字典查询（供给前端指标侧边栏）；
3. POST /api/chat: 核心问数端点（集成 Schema 剪枝 + SQL 生成 + 执行 + ECharts 自适应推荐 + 经营洞察）；
4. POST /api/feedback: Bad Case 回收与闭环沉淀接口。
"""

import os
import sys

# Render/Docker 部署兼容：无论 Root Directory 是仓库根目录还是 backend，
# 都把 backend 目录注入到 sys.path，让相对导入 `from api.xxx` 生效
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_CURRENT_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import json
import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.schemas import (
    ChatQueryRequest,
    ChatQueryResponse,
    MetricListResponse,
    BadCaseFeedbackRequest,
    SopAnalysisRequest,
    SopAnalysisResponse
)
from core.nl2sql_engine import Nl2SqlEngine
from core.chart_recommender import ChartRecommender
from core.sop_analyzer import SopAnalyzer

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
METRICS_PATH = os.path.join(BACKEND_DIR, "core", "metrics_dict.json")
BAD_CASES_PATH = os.path.join(BACKEND_DIR, "eval", "bad_cases.json")

# 初始化 FastAPI 应用
app = FastAPI(
    title="广汽云 ChatBI 智能问数服务 API",
    description="面向大型车企集团的全链路经营决策问数 Agent 服务端",
    version="1.0.0"
)

# 配置 CORS 跨域支持（支持 Netlify 与本地 Next.js 访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 实例化单例 Agent 引擎与图表推荐器
nl2sql_engine = Nl2SqlEngine()
chart_recommender = ChartRecommender()
sop_analyzer = SopAnalyzer()

# Render 平台健康检查端点（默认 GET /，不依赖业务初始化）
@app.get("/", tags=["基础监控"])
def root():
    return {
        "status": "ok",
        "service": "GAC-ChatBI API",
        "version": "1.1.0",
        "endpoints": [
            "/api/health",
            "/api/metrics",
            "/api/chat",
            "/api/chat/stream",
            "/api/feedback",
            "/api/sop/analyze",
            "/api/dashboard/snapshot",
            "/docs"
        ]
    }

@app.get("/api/health", tags=["基础监控"])
def health_check():
    """健康检查与引擎探测"""
    return {
        "status": "healthy",
        "service": "GAC-ChatBI API",
        "engine": nl2sql_engine.sql_executor.engine_type,
        "database_file": nl2sql_engine.sql_executor.db_path,
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.get("/api/metrics", response_model=MetricListResponse, tags=["指标资产"])
def get_metrics_dict():
    """获取集团标准经营分析指标体系字典"""
    if not os.path.exists(METRICS_PATH):
        raise HTTPException(status_code=404, detail="指标字典文件未找到")
    
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

@app.post("/api/chat", response_model=ChatQueryResponse, tags=["智能问数"])
def chat_query(req: ChatQueryRequest):
    """
    核心智能问数端点：
    自然语言提问 -> 剪枝 -> SQL生成 -> 数据库执行 -> 自适应ECharts推断 -> 经营分析洞察
    """
    # 1. 运行问数主引擎
    result = nl2sql_engine.ask(req.query, force_mock=req.force_mock)

    # 2. 生成自适应 ECharts 图表配置
    chart_info = chart_recommender.recommend(
        query=req.query,
        columns=result.get("columns", []),
        data=result.get("data", [])
    )

    # 3. 构造统一响应体
    return ChatQueryResponse(
        query=req.query,
        thought_steps=result["thought_steps"],
        sql=result["sql"] or "",
        success=result["success"],
        data=result["data"],
        columns=result["columns"],
        row_count=result["row_count"],
        execution_time_ms=result["execution_time_ms"],
        chart_type=chart_info["chart_type"],
        echarts_option=chart_info["echarts_option"],
        summary_insight=result["summary_insight"] or "查询完成，已生成最新经营视图。",
        healed=result.get("healed", False),
        engine=result.get("engine", "DuckDB"),
        error=result.get("error")
    )

@app.post("/api/feedback", tags=["运营治理"])
def collect_bad_case(req: BadCaseFeedbackRequest):
    """Bad Case 反馈收集池"""
    os.makedirs(os.path.dirname(BAD_CASES_PATH), exist_ok=True)

    cases = []
    if os.path.exists(BAD_CASES_PATH):
        try:
            raw = json.load(open(BAD_CASES_PATH, "r", encoding="utf-8"))
            cases = raw.get("cases", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        except Exception:
            cases = []

    case_record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": req.query,
        "sql": req.sql,
        "feedback_type": req.feedback_type,
        "user_comment": req.user_comment
    }
    cases.append(case_record)

    with open(BAD_CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    return {"status": "success", "message": "Bad Case 反馈已成功记录至运营池", "total_cases": len(cases)}


# ─── Sprint 5.3 SOP 高频归因引擎 ──────────────────────────────────────
@app.post("/api/sop/analyze", response_model=SopAnalysisResponse, tags=["SOP 归因引擎"])
def sop_analyze(req: SopAnalysisRequest):
    """
    Sprint 5.3: 高频归因 SOP（销量达成异常 / 预算偏差 / 费用异常波动）

    执行四步下钻 SOP：
      Step 1 大盘对标 —— 目标 vs 实际，达成率评级
      Step 2 维度下钻 —— 车型 × 大区双维度定位最大缺口贡献者
      Step 3 跨域归因 —— 关联营销投放 / 终端客流 / 折扣力度
      Step 4 策略建议 —— 生成可执行经营策略（带预算影响估算）
    """
    import time
    start = time.time()
    try:
        result = sop_analyzer.analyze_fulfillment_gap(
            brand_name=req.brand_name,
            year_month=req.year_month,
            threshold_pct=req.threshold_pct or 95.0
        )

        # 提取第 1 步的评级原因
        steps = result.get("steps", [])
        step1 = steps[0] if steps else {}

        # 提取第 4 步的建议
        step4 = steps[3] if len(steps) >= 4 else {}
        recommendations = step4.get("recommendations", []) if step4 else []

        elapsed_ms = (time.time() - start) * 1000

        return SopAnalysisResponse(
            success=True,
            brand=result.get("brand", req.brand_name),
            year_month=result.get("year_month", req.year_month),
            fulfillment_rate_pct=result.get("fulfillment_rate_pct", 0) or 0,
            gap_units=result.get("gap_units", 0) or 0,
            gap_grade=step1.get("grade", "未知") if step1 else "未知",
            gap_reason=step1.get("gap_reason", "") if step1 else "",
            steps=steps,
            recommendations=recommendations,
            executive_summary=result.get("executive_summary", ""),
            execution_time_ms=round(elapsed_ms, 1)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SOP 引擎执行异常: {str(e)}")


# ─── Sprint 5.1 SSE 流式问数端点 ──────────────────────────────────────
@app.post("/api/chat/stream", tags=["智能问数"])
async def chat_stream(req: ChatQueryRequest):
    """
    Sprint 5.1: SSE 流式问数端点

    流式事件类型：
      - thought  : Agent 思考链路（剪枝/表关联/SQL 计划）
      - sql      : 生成的 SQL
      - data     : 查询结果数据
      - chart    : ECharts 图表配置
      - insight  : 经营分析师核心洞察（逐字流式）
      - done     : 完成事件（含耗时统计）
    """
    from fastapi.responses import StreamingResponse
    import asyncio

    async def event_generator():
        try:
            # Step 1: 流式输出思考链（伪流式，模拟 Agent 推理过程）
            yield f"event: thought\ndata: {json.dumps({'step': 1, 'text': '🔍 正在解析提问语义...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            yield f"event: thought\ndata: {json.dumps({'step': 2, 'text': '📊 动态 Schema 剪枝中...'}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.05)

            # Step 2: 同步执行 NL2SQL 主链路（最耗时的部分）
            result = nl2sql_engine.ask(req.query, force_mock=req.force_mock)

            # Step 2.1: 如果是闲聊/元问题，直接发 meta_answer 事件，跳过 SQL 生成
            if result.get("is_meta_answer"):
                meta_text = result.get("summary_insight") or "你好！我是广汽云 ChatBI。"
                # 按标点分块流式推送
                chunks = []
                current = ""
                for char in meta_text:
                    current += char
                    if char in "。！？；\n" or len(current) >= 10:
                        chunks.append(current)
                        current = ""
                if current:
                    chunks.append(current)
                for chunk in chunks:
                    yield f"event: meta_answer\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.05)
                yield f"event: done\ndata: {json.dumps({'success': True, 'healed': False, 'engine': 'meta'}, ensure_ascii=False)}\n\n"
                return

            # Step 3: 推送 SQL
            sql_text = (result.get("sql") or "").replace("\n", " ")
            yield f"event: sql\ndata: {json.dumps({'sql': sql_text}, ensure_ascii=False)}\n\n"

            # Step 4: 推送思考步骤明细
            for step_text in (result.get("thought_steps") or []):
                clean_step = step_text.replace("\n", " ")
                yield f"event: thought\ndata: {json.dumps({'step': 99, 'text': clean_step}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)

            # Step 5: 推送查询结果数据
            data_payload = {
                "columns": result.get("columns", []),
                "rows": result.get("data", []),
                "row_count": result.get("row_count", 0),
                "execution_time_ms": result.get("execution_time_ms", 0)
            }
            yield f"event: data\ndata: {json.dumps(data_payload, ensure_ascii=False)}\n\n"

            # Step 6: 推送图表配置
            chart_info = chart_recommender.recommend(
                query=req.query,
                columns=result.get("columns", []),
                data=result.get("data", [])
            )
            chart_payload = {
                "chart_type": chart_info.get("chart_type", "table"),
                "echarts_option": chart_info.get("echarts_option") or {}
            }
            yield f"event: chart\ndata: {json.dumps(chart_payload, ensure_ascii=False)}\n\n"

            # Step 7: 流式推送经营洞察（逐字）
            insight_text = result.get("summary_insight") or "查询完成，已生成最新经营视图。"
            # 按中文标点和空格分块，避免截断词组
            chunks = []
            current = ""
            for char in insight_text:
                current += char
                if char in "。！？；\n" or len(current) >= 8:
                    chunks.append(current)
                    current = ""
            if current:
                chunks.append(current)

            for chunk in chunks:
                yield f"event: insight\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.08)

            # Step 8: 完成事件
            done_payload = {
                "success": True,
                "healed": result.get("healed", False),
                "engine": result.get("engine", "DuckDB")
            }
            yield f"event: done\ndata: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

        except Exception as e:
            err_msg = str(e).replace("\n", " ")
            yield f"event: error\ndata: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ─── Sprint 5.2 驾驶舱大屏数据聚合端点 ────────────────────────────────
@app.get("/api/dashboard/snapshot", tags=["驾驶舱大屏"])
def dashboard_snapshot(latest_month: str = "2025-04"):
    """
    Sprint 5.2: 一次拉取大屏所需的全部数据（4 个 KPI + 趋势 + 排名 + 预警）

    通过 latest_month 控制要分析的月份，避免对账期硬编码。
    """
    try:
        prev_month_calculator = sop_analyzer._prev_month(latest_month)

        snapshot = {
            "meta": {
                "latest_month": latest_month,
                "prev_month": prev_month_calculator,
                "generated_at": datetime.datetime.now().isoformat()
            },
            "kpis": {},
            "trend": {},
            "ranking": {},
            "alerts": []
        }

        # 1. KPI 卡片组：整体达成率 / 总交付 / 总营收 / 平均 CPL
        kpi_sql = f"""
        WITH sales AS (
            SELECT
                SUM(delivered_units) AS total_units,
                SUM(gross_revenue) / 10000.0 AS total_revenue_wan
            FROM fact_sales_daily
            WHERE STRFTIME('%Y-%m', sale_date) = '{latest_month}'
        ),
        budget AS (
            SELECT SUM(target_units) AS total_target
            FROM dim_budget_target
            WHERE year_month = '{latest_month}'
        ),
        mkt AS (
            SELECT
                ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 2) AS cpl
            FROM fact_marketing_expenses
            WHERE STRFTIME('%Y-%m', expense_date) = '{latest_month}'
        )
        SELECT
            sales.total_units,
            sales.total_revenue_wan,
            budget.total_target,
            ROUND(sales.total_units * 100.0 / NULLIF(budget.total_target, 0), 2) AS fulfillment_rate,
            mkt.cpl
        FROM sales, budget, mkt
        """
        kpi_res = nl2sql_engine.sql_executor.execute_query(kpi_sql)
        if kpi_res["success"] and kpi_res["data"]:
            row = kpi_res["data"][0]
            snapshot["kpis"] = {
                "fulfillment_rate_pct": row.get("fulfillment_rate") or 0,
                "total_units": int(row.get("total_units") or 0),
                "total_revenue_wan": round(row.get("total_revenue_wan") or 0, 1),
                "avg_cpl": row.get("cpl") or 0
            }

        # 2. 趋势：近 12 个月各品牌月交付量（按数据最大月份倒推）
        trend_sql = """
        SELECT
            STRFTIME('%Y-%m', sale_date) AS month,
            brand_name,
            SUM(delivered_units) AS units
        FROM fact_sales_daily
        WHERE sale_date >= (
            SELECT DATE_TRUNC('month', MAX(sale_date)) - INTERVAL '11 months'
            FROM fact_sales_daily
        )
        GROUP BY month, brand_name
        ORDER BY month
        """
        trend_res = nl2sql_engine.sql_executor.execute_query(trend_sql)
        if trend_res["success"]:
            snapshot["trend"] = {"data": trend_res["data"], "columns": trend_res.get("columns", [])}

        # 3. 品牌排名：本期各品牌达成率
        rank_sql = f"""
        WITH s AS (
            SELECT brand_name, SUM(delivered_units) AS actual
            FROM fact_sales_daily
            WHERE STRFTIME('%Y-%m', sale_date) = '{latest_month}'
            GROUP BY brand_name
        ),
        b AS (
            SELECT brand_name, SUM(target_units) AS target
            FROM dim_budget_target
            WHERE year_month = '{latest_month}'
            GROUP BY brand_name
        )
        SELECT
            s.brand_name,
            s.actual,
            b.target,
            ROUND(s.actual * 100.0 / NULLIF(b.target, 0), 2) AS fulfillment_rate
        FROM s
        JOIN b ON s.brand_name = b.brand_name
        ORDER BY fulfillment_rate DESC
        """
        rank_res = nl2sql_engine.sql_executor.execute_query(rank_sql)
        if rank_res["success"]:
            snapshot["ranking"] = {"data": rank_res["data"], "columns": rank_res.get("columns", [])}

        # 4. 异常预警：达成率 < 95% 的品牌自动跑 SOP
        for r in (rank_res.get("data") or []):
            if r.get("fulfillment_rate") is not None and r["fulfillment_rate"] < 95:
                try:
                    sop_report = sop_analyzer.analyze_fulfillment_gap(
                        brand_name=r["brand_name"],
                        year_month=latest_month,
                        threshold_pct=95.0
                    )
                    snapshot["alerts"].append({
                        "brand": r["brand_name"],
                        "fulfillment_rate": r["fulfillment_rate"],
                        "gap_units": sop_report.get("gap_units", 0),
                        "executive_summary": sop_report.get("executive_summary", ""),
                        "top_recommendation": (sop_report["steps"][3].get("recommendations", [{}])[0]
                                              if len(sop_report.get("steps", [])) >= 4
                                                 and sop_report["steps"][3].get("recommendations")
                                              else None)
                    })
                except Exception as sop_err:
                    # 单品牌 SOP 失败不影响整体快照
                    snapshot["alerts"].append({
                        "brand": r["brand_name"],
                        "fulfillment_rate": r["fulfillment_rate"],
                        "error": str(sop_err)
                    })

        return snapshot

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"驾驶舱大屏数据聚合异常: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
