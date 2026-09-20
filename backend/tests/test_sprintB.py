"""
Sprint B 单元测试套件（P2-SprintB SOP 执行引擎 + API 路由）
验证项目：
1. B2 sop_executor：8 种 step_type SQL 构造 + 结论生成 + strategy_recommend + 阈值判定
2. B3 API 路由（业务用户 + admin）：鉴权门禁 / CRUD / clone / audit
3. B4 /api/templates/v2/{id}/run 主端点：5 步 SOP 完整跑通 + 报告组装
4. B5 /api/templates/v2/{id}/preview 预览端点：仅前 2 步
"""
import sys
import os
import shutil
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))

PASS = 0
FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  ✔ {name}")
        PASS += 1
    except AssertionError as e:
        print(f"  ✘ {name}: {e}")
        FAIL += 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  ✘ {name}: {type(e).__name__}: {e}")
        FAIL += 1


# ────────────────────────────────────────────────────────────
# B2：sop_executor 引擎
# ────────────────────────────────────────────────────────────
def test_b2_sop_executor():
    """B2 sop_executor 引擎：8 种 step_type 都能跑通"""
    print("\n--- [B2 sop_executor 引擎] ---")
    from backend.core.sop_executor import SopExecutor, DEFAULT_TIME_WINDOW
    from backend.core.attribution_templates import AttributionTemplateManager

    def init_ok():
        ex = SopExecutor()
        assert ex.sql_executor.engine_type == "DuckDB"
    check("SopExecutor init", init_ok)

    def make_step(step_type, **kw):
        base = {
            "step_id": kw.get("step_id", f"s_{step_type[:3]}"),
            "title": kw.get("title", f"测试 {step_type}"),
            "step_type": step_type,
            "metric_key": kw.get("metric_key", "delivered_units"),
            "group_by": kw.get("group_by", []),
            "order": kw.get("order", 1),
        }
        base.update(kw)
        return base

    def run_step(step):
        ex = SopExecutor()
        tpl = {"id": "test", "name": "test", "metric_key": "delivered_units", "steps": [step]}
        return ex.run(tpl, time_window=DEFAULT_TIME_WINDOW)

    def test_overall_kpi():
        step = make_step("overall_kpi", compare_mode="plan",
                         threshold={"warn": 0.95, "bad": 0.85})
        r = run_step(step)
        s = r["report"][0]
        assert s["step_type"] == "overall_kpi"
        assert s["data"], "无数据"
        assert "conclusion" in s and len(s["conclusion"]) > 0
    check("overall_kpi + plan 对比", test_overall_kpi)

    def test_horizontal_compare():
        step = make_step("horizontal_compare", group_by=["brand_name"], order=1)
        r = run_step(step)
        s = r["report"][0]
        assert len(s["data"]) >= 2
        assert "横向对比" in s["conclusion"]
        actuals = [row["actual"] for row in s["data"]]
        assert actuals == sorted(actuals, reverse=True), "应按 actual DESC"
    check("horizontal_compare 按 brand", test_horizontal_compare)

    def test_drill_down():
        step = make_step("drill_down", group_by=["region_name"], order=1, top_n=5)
        r = run_step(step)
        s = r["report"][0]
        assert s["data"]
        assert "最薄弱" in s["conclusion"] or "未发现" in s["conclusion"]
    check("drill_down 按 region", test_drill_down)

    def test_cross_attribution():
        step = make_step("cross_attribution", group_by=["model_name"], order=1)
        r = run_step(step)
        s = r["report"][0]
        assert s["data"]
        assert "贡献" in s["conclusion"]
    check("cross_attribution 按 model", test_cross_attribution)

    def test_anomaly_alert():
        step = make_step("anomaly_alert", group_by=["model_name"], order=1, top_n=5)
        r = run_step(step)
        s = r["report"][0]
        assert s["data"]
        assert "异常" in s["conclusion"]
    check("anomaly_alert 按 model", test_anomaly_alert)

    def test_yoy_compare():
        step = make_step("yoy_compare", compare_mode="yoy",
                         compare_period="2025-Q3", order=1)
        r = run_step(step)
        s = r["report"][0]
        assert s["data"]
        assert "本期" in s["conclusion"] and "上期" in s["conclusion"]
    check("yoy_compare", test_yoy_compare)

    def test_period_compare():
        step = make_step("period_compare", compare_mode="mom",
                         compare_period="month", order=1)
        r = run_step(step)
        s = r["report"][0]
        assert s["data"]
    check("period_compare", test_period_compare)

    def test_strategy_recommend():
        upstream = make_step("drill_down", step_id="d1",
                             group_by=["region_name"], order=1)
        strategy = make_step("strategy_recommend", step_id="s1",
                             depends_on="d1", order=2)
        tpl = {"id": "test", "name": "test", "metric_key": "delivered_units",
               "steps": [upstream, strategy]}
        ex = SopExecutor()
        r = ex.run(tpl, time_window=DEFAULT_TIME_WINDOW)
        assert len(r["report"]) == 2
        assert r["report"][1]["step_type"] == "strategy_recommend"
        assert "建议" in r["report"][1]["conclusion"]
    check("strategy_recommend 依赖 drill_down", test_strategy_recommend)

    def full_5_step_sop():
        mgr = AttributionTemplateManager()
        tpl = mgr.get_template("preset_exec_quarterly")
        assert tpl and len(tpl["steps"]) == 5
        ex = SopExecutor()
        r = ex.run(tpl, time_window=DEFAULT_TIME_WINDOW)
        assert r["steps_executed"] == 5
        assert r["executive_summary"]
        assert "达成率" in r["report"][0]["conclusion"]
    check("完整 5 步 SOP（preset_exec_quarterly）", full_5_step_sop)


# ────────────────────────────────────────────────────────────
# B3+B4+B5：API 路由（用 FastAPI TestClient）
# ────────────────────────────────────────────────────────────
def test_b345_api_routes():
    """B3+B4+B5 API 路由端到端测试"""
    print("\n--- [B3+B4+B5 API 路由] ---")

    tmp_db = Path("/tmp/gac_sprintB_test.duckdb")
    if tmp_db.exists():
        tmp_db.unlink()
    shutil.copy("backend/data/gac_bi.duckdb", tmp_db)

    import backend.core.attribution_templates as M
    import backend.core.sql_executor as S
    real_db = M.DUCKDB_PATH
    M.DUCKDB_PATH = tmp_db
    S.DUCKDB_PATH = str(tmp_db)

    try:
        M.AttributionTemplateManager()  # 触发迁移

        # 重载 main 用测试 DB
        import importlib
        if "backend.api.main" in sys.modules:
            importlib.reload(sys.modules["backend.api.main"])
        from fastapi.testclient import TestClient
        from backend.api.main import app
        client = TestClient(app)

        def login(username, password):
            r = client.post("/api/auth/login", json={"username": username, "password": password})
            assert r.status_code == 200, r.text
            return r.json()["access_token"]

        admin_token = login("admin", "demo")
        business_token = login("zhangsan", "demo")
        admin_h = {"Authorization": f"Bearer {admin_token}"}
        business_h = {"Authorization": f"Bearer {business_token}"}

        # ── 1. 鉴权门禁 ──
        def no_token_401():
            r = client.post("/api/templates/v2/create", json={
                "name": "xx-test", "scope": "user", "steps": [
                    {"title": "step A", "step_type": "overall_kpi",
                     "metric_key": "delivered_units", "order": 1}
                ]
            })
            assert r.status_code == 401
        check("无 token 应 401", no_token_401)

        def business_create_v2():
            r = client.post("/api/templates/v2/create",
                headers=business_h,
                json={"name": "business-v2-test", "scope": "user", "steps": [
                    {"title": "step A", "step_type": "overall_kpi",
                     "metric_key": "delivered_units", "order": 1}
                ]},
            )
            assert r.status_code == 200, r.text
            j = r.json()
            assert j["success"]
            assert j["template"]["steps"][0]["step_type"] == "overall_kpi"
            return j["template"]["id"]
        BIZ_ID = business_create_v2()
        check("业务用户 v2/create 200", lambda: None)  # 已通过

        # ── 2. Admin 系统模板 ──
        def admin_create_system():
            r = client.post("/api/admin/templates", headers=admin_h,
                json={"name": "admin-sys-v2", "scope": "system", "steps": [
                    {"title": "step A", "step_type": "overall_kpi",
                     "metric_key": "delivered_units", "order": 1},
                    {"title": "step B", "step_type": "horizontal_compare",
                     "metric_key": "delivered_units",
                     "group_by": ["brand_name"], "order": 2},
                ], "change_reason": "init"},
            )
            assert r.status_code == 200, r.text
            return r.json()["template"]["id"]
        ADMIN_SYS_ID = admin_create_system()
        check("admin POST /api/admin/templates (system)", lambda: None)

        def business_cannot_admin_create():
            r = client.post("/api/admin/templates", headers=business_h,
                json={"name": "bad-intent", "scope": "system", "steps": [
                    {"title": "step A", "step_type": "overall_kpi",
                     "metric_key": "delivered_units", "order": 1}
                ]},
            )
            assert r.status_code == 403, r.text
        check("业务用户调 admin 接口应 403", business_cannot_admin_create)

        def admin_update_preset():
            r = client.put("/api/admin/templates/preset_exec_quarterly",
                headers=admin_h,
                json={"name": "高管季度复盘（admin改）", "change_reason": "fix"},
            )
            assert r.status_code == 200, r.text
        check("admin 可改 preset_*", admin_update_preset)

        def business_cannot_update_preset():
            r = client.put("/api/templates/v2/preset_exec_quarterly",
                headers=business_h,
                json={"name": "business hack", "change_reason": "hack"},
            )
            assert r.status_code == 403, r.text
        check("业务用户改 preset_* 应 403", business_cannot_update_preset)

        # ── 3. Clone ──
        def business_clone_preset():
            r = client.post("/api/templates/v2/clone", headers=business_h,
                json={"source_template_id": "preset_analyst_deep",
                      "target_scope": "user", "new_name": "我的克隆"},
            )
            assert r.status_code == 200, r.text
            j = r.json()
            assert j["success"]
            assert j["template"]["name"] == "我的克隆"
            assert j["template"]["scope"] == "user"
        check("业务用户 clone preset → user", business_clone_preset)

        # ── 4. Run / Preview ──
        def run_preset():
            r = client.post("/api/templates/v2/preset_exec_quarterly/run",
                headers=business_h, json={},
            )
            assert r.status_code == 200, r.text
            j = r.json()
            assert j["steps_executed"] == 5
            assert j["executive_summary"]
            assert len(j["report"]) == 5
            for s in j["report"]:
                assert "conclusion" in s and len(s["conclusion"]) > 0
                assert "step_id" in s and "status" in s
            assert [s["step_type"] for s in j["report"]] == [
                "overall_kpi", "horizontal_compare", "drill_down",
                "drill_down", "strategy_recommend",
            ]
        check("POST /run (5 步 SOP)", run_preset)

        def preview_preset():
            r = client.post("/api/templates/v2/preset_exec_quarterly/preview",
                headers=admin_h, json={},
            )
            assert r.status_code == 200, r.text
            j = r.json()
            assert j["is_preview"] is True
            assert j["steps_executed"] == 2
        check("POST /preview (2 步)", preview_preset)

        def run_user_template():
            r = client.post(f"/api/templates/v2/{BIZ_ID}/run",
                headers=business_h, json={},
            )
            assert r.status_code == 200, r.text
            assert r.json()["steps_executed"] == 1
        check("POST /run user 模板", run_user_template)

        def run_nonexistent():
            r = client.post("/api/templates/v2/nonexistent_xxx/run",
                headers=business_h, json={},
            )
            assert r.status_code == 404
        check("Run 不存在模板应 404", run_nonexistent)

        def run_with_time_window():
            r = client.post("/api/templates/v2/preset_exec_quarterly/run",
                headers=admin_h,
                json={"time_window": {"start": "2024-01-01", "end": "2024-03-31"}},
            )
            assert r.status_code == 200, r.text
        check("Run 自定义 time_window", run_with_time_window)

        # ── 5. Audit ──
        def audit_has_history():
            r = client.get(f"/api/admin/templates/{ADMIN_SYS_ID}/audit?limit=5",
                headers=admin_h,
            )
            assert r.status_code == 200, r.text
            j = r.json()
            assert len(j["history"]) >= 1
            assert j["history"][0]["version_no"] == 1
        check("admin 查 audit 历史", audit_has_history)

        def audit_after_update():
            client.put(f"/api/admin/templates/{ADMIN_SYS_ID}",
                headers=admin_h,
                json={"name": "改了 1 次", "change_reason": "first"})
            client.put(f"/api/admin/templates/{ADMIN_SYS_ID}",
                headers=admin_h,
                json={"name": "改了 2 次", "change_reason": "second"})
            r = client.get(f"/api/admin/templates/{ADMIN_SYS_ID}/audit?limit=10",
                headers=admin_h,
            )
            j = r.json()
            assert len(j["history"]) >= 3, f"应有 3 条，实际 {len(j['history'])}"
            versions = [h["version_no"] for h in j["history"]]
            assert versions == sorted(versions, reverse=True)
        check("audit 自动累积", audit_after_update)

        def admin_can_run_user_template():
            r = client.post(f"/api/templates/v2/{BIZ_ID}/run",
                headers=admin_h, json={},
            )
            assert r.status_code == 200, r.text
        check("admin 可跑 user 模板", admin_can_run_user_template)
    finally:
        M.DUCKDB_PATH = real_db
        S.DUCKDB_PATH = real_db
        if tmp_db.exists():
            tmp_db.unlink()


# ────────────────────────────────────────────────────────────
# 主入口
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("   Sprint B SOP 步骤化执行引擎 + API 路由 - 单元测试套件")
    print("=" * 60)
    test_b2_sop_executor()
    test_b345_api_routes()
    print(f"\n=== {PASS} pass / {FAIL} fail ===")
    if FAIL == 0:
        print("🎉 Sprint B 所有测试用例 100% 验证通过！")
    else:
        print(f"⚠️  有 {FAIL} 个用例失败，请检查")
        sys.exit(1)
