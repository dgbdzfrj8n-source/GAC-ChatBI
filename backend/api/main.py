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
    BadCaseFeedbackRequest
)
from core.nl2sql_engine import Nl2SqlEngine
from core.chart_recommender import ChartRecommender

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
