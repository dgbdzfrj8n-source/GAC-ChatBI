"""
归因模板中心 v3 - 端到端测试
按"全链路"思路：DB 初始化 → CRUD → 执行 → 历史 → 归档
"""
import sys
import os

# 注入 backend 到 sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import json
import time
import duckdb
import urllib.request, urllib.error
import urllib.parse as urlparse

class _Resp:
    def __init__(self, code, body):
        self.status_code = code
        self.text = body
        self._body = body
    def json(self):
        import json
        return json.loads(self._body)
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}: {self._body[:200]}")

class requests:
    @staticmethod
    def get(url, headers=None):
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return _Resp(resp.status, resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return _Resp(e.code, e.read().decode("utf-8"))

    @staticmethod
    def post(url, headers=None, data=None, json=None):
        import json as _json
        body = (data if data is not None else (_json.dumps(json) if json else "")).encode("utf-8")
        h = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(url, data=body, method="POST", headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return _Resp(resp.status, resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return _Resp(e.code, e.read().decode("utf-8"))

    @staticmethod
    def patch(url, headers=None, data=None, json=None):
        import json as _json
        body = (data if data is not None else (_json.dumps(json) if json else "")).encode("utf-8")
        h = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(url, data=body, method="PATCH", headers=h)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return _Resp(resp.status, resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return _Resp(e.code, e.read().decode("utf-8"))

    @staticmethod
    def delete(url, headers=None):
        req = urllib.request.Request(url, method="DELETE", headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return _Resp(resp.status, resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return _Resp(e.code, e.read().decode("utf-8"))

API = os.environ.get("API_BASE", "http://127.0.0.1:8766")
DB_PATH = os.path.join(BACKEND_DIR, "data", "gac_bi.duckdb")

# ANSI 颜色
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def step(msg):
    print(f"\n{YELLOW}▶ {msg}{RESET}")


def ok(msg):
    print(f"  {GREEN}✅ {msg}{RESET}")


def fail(msg, exc=None):
    print(f"  {RED}❌ {msg}{RESET}")
    if exc:
        print(f"      {exc}")


# ============================================================
# 准备：拿 token
# ============================================================
def get_token():
    r = requests.post(f"{API}/api/auth/login", json={"username": "admin", "password": "x"})
    r.raise_for_status()
    return r.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ============================================================
# 测试 1: Health（无需 token）
# ============================================================
def test_health():
    step("Test 1: GET /api/template-center/health")
    r = requests.get(f"{API}/api/template-center/health")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    d = r.json()
    assert d["status"] == "healthy", f"Status not healthy: {d['status']}"
    assert len(d["v3_tables_present"]) == 4, f"Expected 4 tables, got {len(d['v3_tables_present'])}"
    ok(f"healthy, all 4 v3 tables present: {d['v3_tables_present']}")


# ============================================================
# 测试 2: 数据库 schema 验证
# ============================================================
def test_db_schema():
    step("Test 2: DuckDB 4 张 v3 表结构")
    con = duckdb.connect(DB_PATH, read_only=True)
    expected = {
        "attribution_template": [
            "template_id", "name", "code", "description", "category", "tags",
            "current_version", "is_archived", "is_builtin",
            "created_by", "created_at", "updated_at",
        ],
        "attribution_template_version": [
            "template_id", "version", "steps_json", "status", "changelog",
            "created_by", "created_at",
        ],
        "attribution_template_run": [
            "run_id", "template_id", "template_version", "user_query", "params_json",
            "status", "total_steps", "completed_steps", "summary_json", "error_message",
            "started_at", "finished_at", "duration_ms", "created_by", "created_at",
        ],
        "attribution_step_execution": [
            "step_execution_id", "run_id", "step_index", "step_name", "step_type",
            "input_json", "output_json", "status", "error_message", "duration_ms", "created_at",
        ],
    }
    for table, expected_cols in expected.items():
        cols = [row[0] for row in con.execute(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_name = '{table}' ORDER BY ordinal_position"
        ).fetchall()]
        assert cols == expected_cols, f"{table} columns mismatch:\n  expected: {expected_cols}\n  actual:   {cols}"
        ok(f"{table}: {len(cols)} 列结构正确")
    con.close()


# ============================================================
# 测试 3: 5 个 seed 已写入
# ============================================================
def test_seeds():
    step("Test 3: 5 个 seed 模板已初始化")
    con = duckdb.connect(DB_PATH, read_only=True)
    rows = con.execute(
        "SELECT code, name, current_version, is_builtin FROM attribution_template "
        "WHERE is_archived = FALSE ORDER BY code"
    ).fetchall()
    assert len(rows) == 5, f"Expected 5 templates, got {len(rows)}"
    expected_codes = {"sales_attr_qoq", "sales_attr_yoy", "sales_topn", "marketing_roi", "inventory_attr"}
    actual_codes = {r[0] for r in rows}
    assert actual_codes == expected_codes, f"Codes mismatch:\n  expected: {expected_codes}\n  actual:   {actual_codes}"
    for code, name, ver, is_builtin in rows:
        ok(f"  {code} v{ver} (内置={is_builtin}): {name}")
    con.close()


# ============================================================
# 测试 4: 模板列表 API
# ============================================================
def test_list_templates(token):
    step("Test 4: GET /api/template-center/templates")
    r = requests.get(f"{API}/api/template-center/templates", headers=auth_headers(token))
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    d = r.json()
    assert d["total"] >= 5, f"Expected >=5, got {d['total']}"
    ok(f"total={d['total']}, items={len(d['items'])}")
    return d["items"]


# ============================================================
# 测试 5: 关键词搜索
# ============================================================
def test_search(token):
    import urllib.parse
    step("Test 5: 关键词搜索 '销售'")
    r = requests.get(
        f"{API}/api/template-center/templates?keyword={urllib.parse.quote("销售")}",
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 3, f"Expected >=3 matches for '销售', got {d['total']}"
    ok(f"找到 {d['total']} 个匹配")


# ============================================================
# 测试 6: 分类筛选
# ============================================================
def test_category_filter(token):
    import urllib.parse
    step("Test 6: 分类筛选 '销售归因'")
    r = requests.get(
        f"{API}/api/template-center/templates?category={urllib.parse.quote("销售归因")}",
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2, f"Expected >=2 sales templates, got {d['total']}"
    for t in d["items"]:
        assert t["category"] == "销售归因", f"Category wrong: {t['category']}"
    ok(f"找到 {d['total']} 个 '销售归因' 模板")


# ============================================================
# 测试 7: 元数据 API
# ============================================================
def test_meta(token):
    step("Test 7: 元数据 API（categories + step-types）")
    cats = requests.get(f"{API}/api/template-center/categories", headers=auth_headers(token)).json()
    assert len(cats["items"]) >= 5
    ok(f"categories: {len(cats['items'])} 类")

    types = requests.get(f"{API}/api/template-center/step-types", headers=auth_headers(token)).json()
    assert len(types["items"]) >= 5
    ok(f"step-types: {len(types['items'])} 类型")
    for t in types["items"]:
        assert "label" in t and "description" in t


# ============================================================
# 测试 8: 创建 + 查询 + PATCH + 发布 v2
# ============================================================
def test_full_crud(token):
    step("Test 8: 完整 CRUD 流程（创建 → PATCH → publish v2 → 归档）")
    # 8.1 创建
    import time as _t
    _uniq = f"{int(_t.time())}_{_t.monotonic_ns() % 1000000}"
    create_body = {
        "name": "E2E 测试模板",
        "code": f"e2e_{_uniq}",
        "description": "端到端测试",
        "category": "自定义",
        "tags": ["e2e", "test"],
        "steps": [
            {
                "name": "查询销量",
                "type": "nl2sql",
                "description": "测试 NL2SQL 步骤",
                "question": "查询 {brand} {month} 销量",
                "metrics": ["delivered_units"],
                "dimensions": ["model_name"],
                "variables": [
                    {"name": "brand", "label": "品牌", "type": "string", "required": True, "default": "广汽埃安"},
                    {"name": "month", "label": "月份", "type": "string", "required": True, "default": "2025-09"},
                ],
            },
            {
                "name": "归因结论",
                "type": "conclusion",
                "description": "输出归因",
                "prompt": "基于上一步数据输出结论",
                "variables": [],
            },
        ],
    }
    r = requests.post(
        f"{API}/api/template-center/templates",
        headers=auth_headers(token),
        data=json.dumps(create_body),
    )
    assert r.status_code == 201, f"Create failed: {r.status_code} {r.text}"
    tpl = r.json()
    tid = tpl["template_id"]
    assert tpl["code"] == f"e2e_{_uniq}"
    assert tpl["current_version"] == 1
    ok(f"创建: {tpl['code']} v1 id={tid}")

    # 8.2 GET 详情
    r = requests.get(f"{API}/api/template-center/templates/{tid}", headers=auth_headers(token))
    assert r.status_code == 200
    t = r.json()
    assert t["name"] == "E2E 测试模板"
    ok(f"详情: name={t['name']}, tags={t['tags']}")

    # 8.3 PATCH
    r = requests.patch(
        f"{API}/api/template-center/templates/{tid}",
        headers=auth_headers(token),
        data=json.dumps({"description": "已更新", "tags": ["e2e", "test", "updated"]}),
    )
    assert r.status_code == 200
    t = r.json()
    assert t["description"] == "已更新"
    assert "updated" in t["tags"]
    ok(f"更新: desc='{t['description']}', tags={t['tags']}")

    # 8.4 发布 v2
    r = requests.post(
        f"{API}/api/template-center/templates/{tid}/publish",
        headers=auth_headers(token),
        data=json.dumps({
            "steps": [
                {"name": "v2 step", "type": "aggregation", "aggregation": "sum", "variables": []}
            ],
            "changelog": "E2E test v2",
        }),
    )
    assert r.status_code == 200
    assert r.json()["new_version"] == 2
    ok(f"发布 v2 成功")

    # 8.5 版本列表
    r = requests.get(
        f"{API}/api/template-center/templates/{tid}/versions",
        headers=auth_headers(token),
    )
    versions = r.json()["items"]
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[1]["version"] == 1
    ok(f"版本列表: {len(versions)} 个版本（v{versions[0]['version']}, v{versions[1]['version']}）")

    # 8.6 归档
    r = requests.delete(f"{API}/api/template-center/templates/{tid}", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["archived"] == True
    ok(f"归档成功")

    return tid

# ============================================================
# 测试 9: 同步执行 run
# ============================================================
def test_run_template(token, tpl_id):
    step("Test 9: POST 同步执行 run")
    run_body = {
        "user_query": "E2E 测试 QoQ 归因",
        "params": {"brand": "广汽埃安", "cur_month": "2025-09", "prev_month": "2025-08"},
    }
    r = requests.post(
        f"{API}/api/template-center/templates/{tpl_id}/runs",
        headers=auth_headers(token),
        data=json.dumps(run_body),
    )
    assert r.status_code == 201, f"Run failed: {r.status_code} {r.text}"
    d = r.json()
    run = d["run"]
    steps = d["steps"]
    assert run["status"] == "success", f"Run status: {run['status']}, error: {run.get('error_message')}"
    assert run["completed_steps"] == run["total_steps"], \
        f"Not all steps completed: {run['completed_steps']}/{run['total_steps']}"
    assert len(steps) == run["total_steps"]
    for s in steps:
        assert s["status"] == "success", f"Step {s['step_index']} status: {s['status']}"
    ok(f"run {run['run_id']}: {run['completed_steps']}/{run['total_steps']} steps, "
       f"{run['duration_ms']}ms")
    return run["run_id"]


# ============================================================
# 测试 10: run 详情 + 步骤输出
# ============================================================
def test_run_detail(token, run_id):
    step("Test 10: GET /api/template-center/runs/{id}")
    r = requests.get(f"{API}/api/template-center/runs/{run_id}", headers=auth_headers(token))
    assert r.status_code == 200
    d = r.json()
    run = d["run"]
    steps = d["steps"]
    assert run["status"] == "success"
    assert len(steps) >= 2
    # 验证步骤有 input/output
    for s in steps:
        assert "input_data" in s
        assert s["output_data"] is not None, f"Step {s['step_index']} has no output"
    ok(f"详情 OK: {len(steps)} 步全部有输出")


# ============================================================
# 测试 11: run 列表 + 过滤
# ============================================================
def test_run_list(token):
    step("Test 11: GET /api/template-center/runs（列表）")
    r = requests.get(f"{API}/api/template-center/runs?limit=10", headers=auth_headers(token))
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    ok(f"列表: {d['total']} 条 run 记录")

    # 状态过滤
    r2 = requests.get(
        f"{API}/api/template-center/runs?status=success",
        headers=auth_headers(token),
    )
    d2 = r2.json()
    assert all(r["status"] == "success" for r in d2["items"])
    ok(f"成功状态过滤: {d2['total']} 条")


# ============================================================
# 测试 12: 错误路径 - 重复 code
# ============================================================
def test_duplicate_code(token):
    step("Test 12: 错误路径 — 重复 code 应 409")
    body = {
        "name": "重复测试",
        "code": "sales_attr_qoq",  # 已存在
        "description": "",
        "category": "自定义",
        "tags": [],
        "steps": [{"name": "s", "type": "nl2sql", "variables": []}],
    }
    r = requests.post(
        f"{API}/api/template-center/templates",
        headers=auth_headers(token),
        data=json.dumps(body),
    )
    assert r.status_code == 409, f"Expected 409, got {r.status_code}"
    ok(f"重复 code 正确返回 409: {r.json()['detail']}")


# ============================================================
# 测试 13: 错误路径 - 不存在的模板
# ============================================================
def test_not_found(token):
    step("Test 13: 错误路径 — 不存在的 ID 应 404")
    r = requests.get(
        f"{API}/api/template-center/templates/tpl_nonexistent_xxxxx",
        headers=auth_headers(token),
    )
    assert r.status_code == 404
    ok("404 OK")


# ============================================================
# 测试 14: 未鉴权访问
# ============================================================
def test_unauth():
    step("Test 14: 未鉴权应 401/403")
    r = requests.get(f"{API}/api/template-center/templates")
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"
    ok(f"未鉴权正确返回 {r.status_code}")


# ============================================================
# 主流程
# ============================================================
def main():
    print(f"\n{'='*60}")
    print(f"归因模板中心 v3 - 端到端测试")
    print(f"API: {API}")
    print(f"DB:  {DB_PATH}")
    print(f"{'='*60}")

    passed = 0
    failed = 0
    start = time.time()

    def run_test(name, fn, *args):
        nonlocal passed, failed
        try:
            fn(*args)
            passed += 1
        except Exception as e:
            failed += 1
            fail(f"{name} 失败", e)

    # 基础
    run_test("Test 1: health", test_health)
    run_test("Test 2: schema", test_db_schema)
    run_test("Test 3: seeds", test_seeds)

    # 拿 token
    token = get_token()
    ok(f"登录成功，token 长度 {len(token)}")

    # API
    run_test("Test 4: list templates", test_list_templates, token)
    run_test("Test 5: search", test_search, token)
    run_test("Test 6: category filter", test_category_filter, token)
    run_test("Test 7: meta", test_meta, token)
    run_test("Test 8: full CRUD", test_full_crud, token)

    # 拿到第一个 seed 模板 ID
    items = test_list_templates(token)
    seed_tpl_id = items[0]["template_id"]
    ok(f"用 seed 模板测试: {items[0]['code']}")

    run_test("Test 9: run template", test_run_template, token, seed_tpl_id)
    # 取最新 run id
    runs = requests.get(
        f"{API}/api/template-center/runs?template_id={seed_tpl_id}&limit=1",
        headers=auth_headers(token),
    ).json()
    latest_run_id = runs["items"][0]["run_id"]
    run_test("Test 10: run detail", test_run_detail, token, latest_run_id)
    run_test("Test 11: run list", test_run_list, token)

    # 错误路径
    run_test("Test 12: duplicate code", test_duplicate_code, token)
    run_test("Test 13: not found", test_not_found, token)
    run_test("Test 14: unauth", test_unauth)

    # 总结
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"测试结果: {GREEN}{passed} 通过{RESET} / {RED if failed else ''}{failed} 失败{RESET}")
    print(f"耗时: {elapsed:.2f}s")
    print(f"{'='*60}\n")

    return failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
