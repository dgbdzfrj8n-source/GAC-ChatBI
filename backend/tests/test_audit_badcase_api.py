"""P2-4 + P2-7 后端 API 集成测试"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def run():
    print("=== P2-4 审计日志 API ===")
    # 1. 写入审计
    r = client.post("/api/audit/log", json={
        "actor": "test-user",
        "action": "create",
        "resource": "semantic_term",
        "resource_id": "term-001",
        "payload": {"key": "value"},
        "note": "集成测试"
    })
    assert r.status_code == 200
    audit_id = r.json()["audit_id"]
    print(f"  ✅ 写入审计: {audit_id}")

    # 2. 列表
    r = client.get("/api/audit/list", params={"actor": "test-user", "limit": 10})
    assert r.status_code == 200
    items = r.json()["items"]
    assert any(i["id"] == audit_id for i in items)
    print(f"  ✅ 列表查询: 命中 {len(items)} 条")

    # 3. 统计
    r = client.get("/api/audit/stats")
    assert r.status_code == 200
    stats = r.json()
    assert "total" in stats and "by_actor" in stats
    print(f"  ✅ 统计: total={stats['total']} today={stats['today']}")

    print("\n=== P2-7 Bad Case API ===")
    # 4. 提交负面反馈
    r = client.post("/api/bad-case/submit", json={
        "actor": "test-user",
        "query": "广汽埃安 3 月销量",
        "sql_text": "SELECT * FROM sales WHERE brand='广汽埃安'",
        "feedback_type": "negative",
        "feedback_label": "口径偏差",
        "correction": "应该是 3 月新能源销量，不含燃油"
    })
    assert r.status_code == 200
    case_id = r.json()["case_id"]
    print(f"  ✅ 提交反馈: {case_id}")

    # 5. 列表
    r = client.get("/api/bad-case/list", params={"feedback_type": "negative"})
    items = r.json()["items"]
    assert any(i["id"] == case_id for i in items)
    print(f"  ✅ 列表: 命中 {len(items)} 条 negative")

    # 6. 闭环
    r = client.post("/api/bad-case/resolve", json={
        "case_id": case_id,
        "resolved_by": "ai-pm",
        "semantic_term_id": "term-新能源销量"
    })
    assert r.status_code == 200
    print(f"  ✅ 闭环: success")

    # 7. 已解决列表
    r = client.get("/api/bad-case/list", params={"resolved": True})
    items = r.json()["items"]
    assert any(i["id"] == case_id for i in items)
    print(f"  ✅ 已解决列表: 命中 {len(items)} 条")

    # 8. 统计
    r = client.get("/api/bad-case/stats")
    stats = r.json()
    print(f"  ✅ Bad Case 统计: total={stats['total']} resolved={stats['resolved']} open={stats['open']}")

    # 9. 校验：resolve 后 audit 也应有 update 记录
    r = client.get("/api/audit/list", params={"resource": "bad_case", "limit": 50})
    items = r.json()["items"]
    resolve_audit = [i for i in items if i["resource_id"] == case_id and i["action"] == "update"]
    assert len(resolve_audit) >= 1, "应有 resolve 的审计记录"
    print(f"  ✅ resolve 同时写入审计: {len(resolve_audit)} 条")

    print("\n🎉 P2-4 + P2-7 全链路通过\n")


if __name__ == "__main__":
    run()
