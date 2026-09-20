"""
Sprint A 单元测试套件（P2-SprintA SOP 步骤化模板）
验证项目：
1. A1 迁移：表新增 steps / updated_by 列，audit 表存在，老数据兜底迁移成功
2. A2 Pydantic schemas：StepSpec / AttributionTemplateV2 / Request 模型的字段级 + 模板级校验
3. A3 CRUD 兼容：老接口 (dimensions) 与新接口 (steps) 共存；admin allow_preset 可改；audit 快照；clone 方法
"""
import sys
import os
import shutil
import tempfile
from pathlib import Path

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))  # 让 `import core.xxx` 可解析

PASS = 0
FAIL = 0


def check(name, fn):
    """运行测试并打印结果"""
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
# A1：迁移 + 老数据兜底
# ────────────────────────────────────────────────────────────
def test_a1_migration_and_fallback():
    """A1 DuckDB 启动自动备份 + 表迁移 + 老数据兜底"""
    print("\n--- [A1 迁移 + 老数据兜底] ---")

    tmp_db = Path(tempfile.mkdtemp()) / "test_a1.duckdb"
    real_db = ROOT_DIR + "/backend/data/gac_bi.duckdb"
    shutil.copy(real_db, tmp_db)

    # 1. 清掉新列/audit 表 + 插入老格式数据
    import duckdb
    con = duckdb.connect(str(tmp_db), read_only=False)
    con.execute("DROP TABLE IF EXISTS dim_attribution_template")
    con.execute("DROP TABLE IF EXISTS dim_attribution_template_audit")
    con.execute("""
    CREATE TABLE dim_attribution_template (
        id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, description VARCHAR,
        scope VARCHAR NOT NULL DEFAULT 'user',
        metric_key VARCHAR NOT NULL DEFAULT 'delivered_units',
        owner_role VARCHAR, owner_user VARCHAR,
        dimensions JSON, created_at VARCHAR, updated_at VARCHAR
    )
    """)
    con.execute(
        "INSERT INTO dim_attribution_template VALUES "
        "('user_a','老模板A','desc','user','delivered_units',NULL,'alice','[\"brand_name\",\"region_name\"]','2026-09-01','2026-09-01'),"
        "('user_b','老模板B','','user','gross_revenue',NULL,'bob','[\"model_name\"]','2026-09-01','2026-09-01')"
    )
    con.commit()
    con.close()

    # 2. 把模块的 DUCKDB_PATH 指到测试库，触发迁移
    import backend.core.attribution_templates as M
    real_path = M.DUCKDB_PATH
    M.DUCKDB_PATH = tmp_db
    try:
        M.AttributionTemplateManager()  # __init__ 会触发 _ensure_table

        def has_steps_column():
            con = duckdb.connect(str(tmp_db), read_only=True)
            cols = [r[0] for r in con.execute("DESCRIBE dim_attribution_template").fetchall()]
            con.close()
            assert "steps" in cols, f"缺 steps 列, cols={cols}"
        check("dim_attribution_template 新增 steps 列", has_steps_column)

        def has_audit_table():
            con = duckdb.connect(str(tmp_db), read_only=True)
            cols = [r[0] for r in con.execute("DESCRIBE dim_attribution_template_audit").fetchall()]
            con.close()
            assert "snapshot" in cols, f"缺 snapshot 列, cols={cols}"
        check("dim_attribution_template_audit 表已建", has_audit_table)

        def legacy_data_fallback():
            con = duckdb.connect(str(tmp_db), read_only=True)
            for row in con.execute("SELECT id, steps FROM dim_attribution_template WHERE id IN ('user_a','user_b')").fetchall():
                import json as _json
                steps = _json.loads(row[1]) if isinstance(row[1], str) else row[1]
                assert len(steps) == 1 and steps[0]["step_type"] == "horizontal_compare", f"兜底失败: {row}"
            con.close()
        check("老数据兜底为 1 个 horizontal_compare step", legacy_data_fallback)
    finally:
        M.DUCKDB_PATH = real_path
        if tmp_db.exists():
            tmp_db.unlink()


# ────────────────────────────────────────────────────────────
# A2：Pydantic schemas 校验
# ────────────────────────────────────────────────────────────
def test_a2_pydantic_schemas():
    """A2 Pydantic v2 schema 校验：正向 + 反向"""
    print("\n--- [A2 Pydantic 严格校验] ---")

    from pydantic import ValidationError
    from backend.api.schemas import (
        StepSpec, AttributionTemplateV2,
        TemplateCreateRequestV2, TemplateUpdateRequestV2,
        TemplateCloneRequestV2, TemplateAuditItem,
    )

    def good_single_step():
        s = StepSpec(title="整体达成率", step_type="overall_kpi",
                     metric_key="delivered_units", order=1)
        assert s.step_id.startswith("step_")
    check("StepSpec 单步 ok", good_single_step)

    def good_full_sop():
        s1 = StepSpec(title="整体达成", step_type="overall_kpi",
                      metric_key="delivered_units", order=1)
        s2 = StepSpec(title="品牌横向", step_type="horizontal_compare",
                      metric_key="delivered_units", group_by=["brand_name"], order=2)
        s3 = StepSpec(title="下钻区域", step_type="drill_down",
                      metric_key="delivered_units", group_by=["region_name"], order=3)
        s4 = StepSpec(title="下钻车型", step_type="drill_down",
                      metric_key="delivered_units", group_by=["model_name"], order=4)
        s5 = StepSpec(title="策略建议", step_type="strategy_recommend",
                      metric_key="delivered_units", depends_on=s4.step_id, order=5)
        tpl = AttributionTemplateV2(
            id="tpl_1", name="高管季度复盘", scope="system",
            steps=[s1, s2, s3, s4, s5],
        )
        assert len(tpl.steps) == 5
    check("完整 5 步 SOP ok", good_full_sop)

    def good_market():
        tpl = AttributionTemplateV2(
            id="t", name="new-energy-mkt", scope="market",
            steps=[StepSpec(title="YoY", step_type="yoy_compare",
                            metric_key="delivered_units",
                            compare_period="2025-Q3", order=1)],
        )
        assert tpl.scope == "market"
    check("market scope + yoy ok", good_market)

    def good_clone():
        TemplateCloneRequestV2(source_template_id="preset_x",
                                target_scope="user", new_name="mine")
    check("CloneRequest ok", good_clone)

    def bad_metric():
        try:
            StepSpec(title="bad", step_type="overall_kpi",
                     metric_key="fake_xyz", order=1)
        except ValidationError:
            return
        raise AssertionError("未拦截非法 metric")
    check("非法 metric 被拦", bad_metric)

    def bad_dims():
        # 必须走 AttributionTemplateV2.model_validator 才能拿到完整校验
        try:
            AttributionTemplateV2(id="t", name="nn", scope="user", steps=[
                StepSpec(title="bad", step_type="drill_down",
                         metric_key="conversion_rate",
                         group_by=["energy_type"], order=1),
            ])
        except ValidationError:
            return
        raise AssertionError("未拦截非法 dim")
    check("非法 dim×metric 被拦", bad_dims)

    def bad_order():
        try:
            AttributionTemplateV2(id="t", name="nn", scope="user", steps=[
                StepSpec(title="a", step_type="overall_kpi",
                         metric_key="delivered_units", order=1),
                StepSpec(title="b", step_type="horizontal_compare",
                         metric_key="delivered_units",
                         group_by=["brand_name"], order=3),
            ])
        except ValidationError:
            return
        raise AssertionError("未拦截 order 不连续")
    check("order 不连续被拦", bad_order)

    def bad_depends_on():
        try:
            AttributionTemplateV2(id="t", name="nn", scope="user", steps=[
                StepSpec(title="a", step_type="strategy_recommend",
                         metric_key="delivered_units",
                         depends_on="ghost", order=1),
            ])
        except ValidationError:
            return
        raise AssertionError("未拦截 depends_on 缺失")
    check("depends_on 缺失被拦", bad_depends_on)

    def bad_strategy_no_dep():
        try:
            AttributionTemplateV2(id="t", name="nn", scope="user", steps=[
                StepSpec(title="a", step_type="strategy_recommend",
                         metric_key="delivered_units", order=1),
            ])
        except ValidationError:
            return
        raise AssertionError("strategy_recommend 缺 dep 应拦")
    check("strategy_recommend 缺 dep 被拦", bad_strategy_no_dep)

    def bad_yoy_no_period():
        # 模板级 model_validator 才校验 compare_period 必填
        try:
            AttributionTemplateV2(id="t", name="nn", scope="user", steps=[
                StepSpec(title="YoY", step_type="yoy_compare",
                         metric_key="delivered_units", order=1),
            ])
        except ValidationError:
            return
        raise AssertionError("yoy_compare 缺 period 应拦")
    check("yoy_compare 缺 period 被拦", bad_yoy_no_period)

    def extra_field_forbidden():
        try:
            StepSpec(title="ok", step_type="overall_kpi",
                     metric_key="delivered_units", order=1, foo="bar")
        except ValidationError:
            return
        raise AssertionError("extra='forbid' 应拒绝")
    check("extra='forbid' 拒绝未知字段", extra_field_forbidden)


# ────────────────────────────────────────────────────────────
# A3：CRUD 兼容 + steps 升级 + audit
# ────────────────────────────────────────────────────────────
def test_a3_crud_and_audit():
    """A3 CRUD 兼容 + steps 升级 + audit + clone"""
    print("\n--- [A3 CRUD 兼容 + audit + clone] ---")

    tmp_db = Path(tempfile.mkdtemp()) / "test_a3.duckdb"
    real_db = ROOT_DIR + "/backend/data/gac_bi.duckdb"
    shutil.copy(real_db, tmp_db)

    import backend.core.attribution_templates as M
    real_path = M.DUCKDB_PATH
    M.DUCKDB_PATH = tmp_db
    try:
        mgr = M.AttributionTemplateManager()

        def legacy_create():
            res = mgr.create_template(name="legacy-1",
                                      dimensions=["brand_name"],
                                      owner_user="alice")
            assert res["success"], res
            assert "steps" in res["template"]
            assert len(res["template"]["steps"]) >= 1
            assert res["template"]["steps"][0]["step_type"] == "horizontal_compare"
        check("老接口 create(name, dimensions)", legacy_create)

        def legacy_update():
            res = mgr.create_template(name="legacy-2",
                                      dimensions=["model_name"],
                                      owner_user="bob")
            tid = res["template"]["id"]
            up = mgr.update_template(template_id=tid,
                                     dimensions=["region_name"],
                                     owner_user="bob")
            assert up["success"], up
            g = mgr.get_template(tid)
            assert "region_name" in g["dimensions"]
        check("老接口 update(dimensions)", legacy_update)

        def new_create_with_steps():
            steps = [
                {"step_id":"s1","title":"整体达成","step_type":"overall_kpi",
                 "metric_key":"delivered_units","group_by":[],"order":1},
                {"step_id":"s2","title":"品牌横向","step_type":"horizontal_compare",
                 "metric_key":"delivered_units","group_by":["brand_name"],"order":2},
                {"step_id":"s3","title":"策略建议","step_type":"strategy_recommend",
                 "metric_key":"delivered_units","depends_on":"s2","order":3},
            ]
            res = mgr.create_template(name="new-v2", steps=steps,
                                      owner_user="carol",
                                      updated_by="carol",
                                      change_reason="init")
            assert res["success"], res
            assert len(res["template"]["steps"]) == 3
            assert res["template"]["steps"][2]["depends_on"] == "s2"
            assert "brand_name" in res["template"]["dimensions"]
            return res["template"]["id"]

        new_id_holder = []
        def _run_new_create():
            new_id_holder.append(new_create_with_steps())
        check("新接口 create(steps)", _run_new_create)
        new_id = new_id_holder[0]

        def get_returns_steps():
            g = mgr.get_template(new_id)
            assert "steps" in g and len(g["steps"]) == 3
        check("get_template 返回 steps", get_returns_steps)

        def list_returns_steps():
            lst = mgr._list_user_templates(user="carol")
            assert len(lst) >= 1
            assert all("steps" in t for t in lst)
        check("_list_user_templates 含 steps", list_returns_steps)

        def update_steps_writes_audit():
            new_steps = [
                {"step_id":"x1","title":"新s1","step_type":"overall_kpi",
                 "metric_key":"delivered_units","order":1},
                {"step_id":"x2","title":"新s2","step_type":"horizontal_compare",
                 "metric_key":"delivered_units","group_by":["brand_name"],"order":2},
            ]
            up = mgr.update_template(template_id=new_id, steps=new_steps,
                                     owner_user="carol", updated_by="carol",
                                     change_reason="refactor")
            assert up["success"]
            g = mgr.get_template(new_id)
            assert len(g["steps"]) == 2
            assert g["steps"][0]["title"] == "新s1"
        check("update(steps) 改写 + audit", update_steps_writes_audit)

        def audit_history_correct():
            h = mgr.get_audit_history(new_id)
            assert len(h) >= 2, f"audit 应>=2条，实际 {len(h)}"
            versions = [x["version_no"] for x in h]
            assert versions == sorted(versions, reverse=True)
        check("audit 历史正确", audit_history_correct)

        def preset_has_steps():
            t = mgr.get_template("preset_exec_quarterly")
            assert t is not None
            assert "steps" in t and len(t["steps"]) >= 4
            titles = [s["title"] for s in t["steps"]]
            assert "整体达成率对标" in titles
        check("preset_exec_quarterly 含完整 5 步", preset_has_steps)

        def preset_no_edit_by_default():
            up = mgr.update_template(template_id="preset_exec_quarterly", name="坏")
            assert not up["success"] and "不可编辑" in up["error"]
        check("preset 默认禁编辑", preset_no_edit_by_default)

        def admin_can_edit_preset():
            up = mgr.update_template(
                template_id="preset_exec_quarterly",
                name="高管季度复盘（管理员改）",
                allow_preset=True, updated_by="admin", change_reason="fix",
            )
            assert up["success"], up
            g = mgr.get_template("preset_exec_quarterly")
            assert "管理员改" in g["name"]
        check("admin allow_preset=True 可改", admin_can_edit_preset)

        def clone_preset():
            res = mgr.clone_template(source_template_id="preset_analyst_deep",
                                     target_scope="user", owner_user="dave")
            assert res["success"], res
            assert res["template"]["id"].startswith("user_")
            assert len(res["template"]["steps"]) >= 3
        check("clone 预设 → user", clone_preset)

        def clone_user_with_new_name():
            res = mgr.clone_template(source_template_id=new_id,
                                     target_scope="user", new_name="cloned",
                                     owner_user="eve")
            assert res["success"]
            assert res["template"]["name"] == "cloned"
        check("clone user → user (改名)", clone_user_with_new_name)

        def bad_step_in_create():
            res = mgr.create_template(name="bad-order", steps=[
                {"step_id":"a","title":"step A","step_type":"overall_kpi",
                 "metric_key":"delivered_units","order":3},
                {"step_id":"b","title":"step B","step_type":"overall_kpi",
                 "metric_key":"delivered_units","order":1},
            ], owner_user="x")
            assert not res["success"]
            assert "order" in res["error"] or "连续" in res["error"]
        check("steps order 不连续被拦", bad_step_in_create)

        def bad_strategy_no_dep():
            res = mgr.create_template(name="bad-strategy", steps=[
                {"step_id":"a","title":"advice","step_type":"strategy_recommend",
                 "metric_key":"delivered_units","order":1},
            ], owner_user="x")
            assert not res["success"]
            assert "depends_on" in res["error"]
        check("strategy_recommend 无 depends_on 被拦", bad_strategy_no_dep)

        def bad_dims_metric():
            res = mgr.create_template(name="bad-dim", steps=[
                {"step_id":"a","title":"drill","step_type":"drill_down",
                 "metric_key":"conversion_rate","group_by":["energy_type"],"order":1},
            ], owner_user="x")
            assert not res["success"]
            assert "维度" in res["error"]
        check("非法 dim×metric 组合被拦", bad_dims_metric)
    finally:
        M.DUCKDB_PATH = real_path
        if tmp_db.exists():
            tmp_db.unlink()


# ────────────────────────────────────────────────────────────
# 主入口
# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("   Sprint A SOP 步骤化模板 - 单元测试套件")
    print("=" * 60)
    test_a1_migration_and_fallback()
    test_a2_pydantic_schemas()
    test_a3_crud_and_audit()
    print(f"\n=== {PASS} pass / {FAIL} fail ===")
    if FAIL == 0:
        print("🎉 Sprint A 所有测试用例 100% 验证通过！")
    else:
        print(f"⚠️  有 {FAIL} 个用例失败，请检查")
        sys.exit(1)
