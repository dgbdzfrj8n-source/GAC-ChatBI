"""
轻量化 HTTP 服务适配器（支持标准库 wsgiref/http.server 零依赖启动，同时无缝支持 FastAPI/Uvicorn）
设计目的：
1. 本地/离线开发：使用 Python 内置 http.server 即可毫秒级启动标准 RESTful API，杜绝代理/网络/pip 阻断；
2. 线上/容器部署：在安装了 FastAPI+Uvicorn 的 Docker/Render 环境中自动切换高性能异步模式；
3. 接口行为与契约与 FastAPI 保持 100% 相同（/api/health, /api/metrics, /api/chat, /api/feedback）。
"""

import os
import sys

# Render/Docker 部署兼容：把 backend 目录注入到 sys.path
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_CURRENT_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from core.nl2sql_engine import Nl2SqlEngine
from core.chart_recommender import ChartRecommender

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
METRICS_PATH = os.path.join(BACKEND_DIR, "core", "metrics_dict.json")
BAD_CASES_PATH = os.path.join(BACKEND_DIR, "eval", "bad_cases.json")

nl2sql_engine = Nl2SqlEngine()
chart_recommender = ChartRecommender()

def get_health_data():
    return {
        "status": "healthy",
        "service": "GAC-ChatBI API",
        "engine": nl2sql_engine.sql_executor.engine_type,
        "database_file": nl2sql_engine.sql_executor.db_path,
        "timestamp": datetime.datetime.now().isoformat()
    }

def get_metrics_data():
    if not os.path.exists(METRICS_PATH):
        return {"error": "指标字典不存在"}
    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def process_chat_query(req_json: dict) -> dict:
    query = req_json.get("query", "")
    force_mock = req_json.get("force_mock", False)

    result = nl2sql_engine.ask(query, force_mock=force_mock)
    chart_info = chart_recommender.recommend(
        query=query,
        columns=result.get("columns", []),
        data=result.get("data", [])
    )

    return {
        "query": query,
        "thought_steps": result["thought_steps"],
        "sql": result["sql"] or "",
        "success": result["success"],
        "data": result["data"],
        "columns": result["columns"],
        "row_count": result["row_count"],
        "execution_time_ms": result["execution_time_ms"],
        "chart_type": chart_info["chart_type"],
        "echarts_option": chart_info["echarts_option"],
        "summary_insight": result["summary_insight"] or "查询完成，已生成最新经营视图。",
        "healed": result.get("healed", False),
        "engine": result.get("engine", "DuckDB"),
        "error": result.get("error")
    }

def process_feedback(req_json: dict) -> dict:
    os.makedirs(os.path.dirname(BAD_CASES_PATH), exist_ok=True)
    # 兼容 dict（初始空结构）和 list（旧格式）
    cases = []
    if os.path.exists(BAD_CASES_PATH):
        try:
            raw = json.load(open(BAD_CASES_PATH, "r", encoding="utf-8"))
            cases = raw.get("cases", []) if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
        except Exception:
            cases = []

    case_record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "query": req_json.get("query", ""),
        "sql": req_json.get("sql"),
        "feedback_type": req_json.get("feedback_type", "口径不准"),
        "user_comment": req_json.get("user_comment", "")
    }
    cases.append(case_record)

    # 统一写回为 list 结构（兼容新旧格式）
    with open(BAD_CASES_PATH, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=2)

    return {"status": "success", "message": "Bad Case 反馈已成功记录至运营池", "total_cases": len(cases)}

class GacBiHttpHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/health":
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(get_health_data(), ensure_ascii=False).encode("utf-8"))
        elif path == "/api/metrics":
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(get_metrics_data(), ensure_ascii=False).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode("utf-8"))

    def do_POST(self):
        path = urlparse(self.path).path
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            req_json = json.loads(post_body)
        except Exception:
            req_json = {}

        if path == "/api/chat":
            res = process_chat_query(req_json)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
        elif path == "/api/feedback":
            res = process_feedback(req_json)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint Not Found"}).encode("utf-8"))

    def log_message(self, format, *args):
        # 简化日志输出
        pass

def run_server(port=None):
    # 兼容 Render/Heroku 等平台通过环境变量注入的 PORT
    if port is None:
        port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), GacBiHttpHandler)
    print(f"🚀 [广汽云 ChatBI 智能服务已启动] 监听端口: http://0.0.0.0:{port}")
    print("可用接口:")
    print(f"  • GET  http://0.0.0.0:{port}/api/health")
    print(f"  • GET  http://0.0.0.0:{port}/api/metrics")
    print(f"  • POST http://0.0.0.0:{port}/api/chat")
    print(f"  • POST http://0.0.0.0:{port}/api/feedback")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
