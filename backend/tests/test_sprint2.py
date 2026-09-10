"""
Sprint 2 单元与集成测试套件
验证项目：
1. Chart Recommender 图表自适应推荐（双轴复合图、时间折线图、类别柱状图、环形占比图）；
2. 后端服务核心处理函数（get_health_data, get_metrics_data, process_chat_query, process_feedback）；
3. HTTP 服务通信连通性。
"""

import sys
import os
import json
import threading
import time
import urllib.request

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from backend.core.chart_recommender import ChartRecommender
from backend.api.server import (
    get_health_data,
    get_metrics_data,
    process_chat_query,
    process_feedback,
    run_server
)

def test_chart_recommender():
    print("--- [测试 1: ECharts 图表自适应推荐器] ---")
    recommender = ChartRecommender()

    # 1.1 双轴图测试（柱状交付量 + 折线达成率）
    dual_data = [
        {"brand_name": "广汽埃安", "delivered_units": 4462, "fulfillment_rate_pct": 96.68},
        {"brand_name": "广汽传祺", "delivered_units": 3223, "fulfillment_rate_pct": 102.58}
    ]
    res_dual = recommender.recommend("各品牌销量与达成率", ["brand_name", "delivered_units", "fulfillment_rate_pct"], dual_data)
    assert res_dual["chart_type"] == "dual_axis", f"双轴图推荐错误，实际为 {res_dual['chart_type']}"
    assert len(res_dual["echarts_option"]["yAxis"]) == 2
    print("✔ 成功推断双轴复合图 (柱状交付量 + 折线达成率)")

    # 1.2 时间折线趋势图测试
    trend_data = [
        {"year_month": "2025-01", "delivered_units": 3800},
        {"year_month": "2025-02", "delivered_units": 2400},
        {"year_month": "2025-03", "delivered_units": 4462}
    ]
    res_trend = recommender.recommend("埃安月度交付趋势", ["year_month", "delivered_units"], trend_data)
    assert res_trend["chart_type"] == "line", f"折线图推荐错误，实际为 {res_trend['chart_type']}"
    print("✔ 成功推断月度趋势折线图")

    # 1.3 渠道占比饼图测试
    pie_data = [
        {"channel_name": "懂车帝", "spend": 1455},
        {"channel_name": "抖音", "spend": 1243},
        {"channel_name": "巡展", "spend": 828}
    ]
    res_pie = recommender.recommend("各渠道投放支出占比分布", ["channel_name", "spend"], pie_data)
    assert res_pie["chart_type"] == "pie", f"饼图推荐错误，实际为 {res_pie['chart_type']}"
    print("✔ 成功推断环形占比分布饼图")

def test_api_handlers():
    print("\n--- [测试 2: API 业务处理器与数据契约] ---")
    
    # 2.1 健康状态
    health = get_health_data()
    assert health["status"] == "healthy"
    print(f"✔ get_health_data() 正常，当前底层数仓引擎: {health['engine']}")

    # 2.2 经营指标字典
    metrics = get_metrics_data()
    assert "metrics" in metrics
    assert len(metrics["metrics"]) >= 5
    print(f"✔ get_metrics_data() 正常，已装载 {len(metrics['metrics'])} 项集团经营指标")

    # 2.3 问数核心处理
    chat_res = process_chat_query({"query": "2025年3月埃安销量与预算达成率是多少？", "force_mock": True})
    assert chat_res["success"] is True
    assert chat_res["row_count"] > 0
    assert chat_res["echarts_option"] is not None
    print(f"✔ process_chat_query() 正常，输出图表: {chat_res['chart_type']}, 思考步数: {len(chat_res['thought_steps'])}")

    # 2.4 Bad Case 收集反馈
    fb_res = process_feedback({
        "query": "测试提问",
        "sql": "SELECT 1",
        "feedback_type": "图表不适配",
        "user_comment": "建议使用双轴图"
    })
    assert fb_res["status"] == "success"
    print(f"✔ process_feedback() 正常，累计收集 Bad Case: {fb_res['total_cases']} 例")

def test_http_server_live():
    print("\n--- [测试 3: HTTP 网络服务真实端到端连通性] ---")
    test_port = 8899
    # 启动后台测试服务器
    server_thread = threading.Thread(target=run_server, args=(test_port,), daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # 3.1 真实 GET 请求
    url_health = f"http://127.0.0.1:{test_port}/api/health"
    with urllib.request.urlopen(url_health) as resp:
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))
        assert body["status"] == "healthy"
    print(f"✔ GET  /api/health 端到端请求成功 [HTTP 200]")

    # 3.2 真实 POST 问数请求
    url_chat = f"http://127.0.0.1:{test_port}/api/chat"
    payload = json.dumps({"query": "各品牌总销量与总营收", "force_mock": True}).encode("utf-8")
    req = urllib.request.Request(url_chat, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        chat_body = json.loads(resp.read().decode("utf-8"))
        assert chat_body["success"] is True
        assert chat_body["row_count"] == 3
    print(f"✔ POST /api/chat 端到端请求成功 [HTTP 200], 获取 {chat_body['row_count']} 条经营汇总记录")

if __name__ == "__main__":
    print("==========================================")
    print("      广汽云 ChatBI Sprint 2 验收测试      ")
    print("==========================================")
    test_chart_recommender()
    test_api_handlers()
    test_http_server_live()
    print("\n🎉 Sprint 2 所有测试用例 100% 验证通过！")
