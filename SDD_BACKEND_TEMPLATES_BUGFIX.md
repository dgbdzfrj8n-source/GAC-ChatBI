# 后端 SDD：归因模板模块 Bug 修复

> **版本**：v1.0
> **日期**：2026-10-18
> **所属总 SDD**：`SDD_TEMPLATES_BUGFIX.md`
> **子模块**：后端（FastAPI + DuckDB）
> **目标读者**：后端开发工程师
> **作用**：详细描述后端侧的根因、代码修改、测试与部署

---

## 0. 文档元信息

| 字段 | 内容 |
|------|------|
| 涉及 Bug | BUG-TPL-002（部分）、BUG-TPL-003 |
| 涉及文件 | `backend/core/attribution_templates.py`（1 个文件 1 行修改） |
| 涉及 API 端点 | `GET /api/sop/templates`、`POST /api/templates/v2/clone`、`POST /api/templates/v2/create` |
| 数据库 | DuckDB（无需 schema 变更） |
| 风险等级 | 🟢 极低（仅修改模块级常量） |
| 预计工作量 | 0.2 人天 |
| 后端兼容性 | 无破坏性变更；接口契约不变 |

---

## 1. 后端根因分析

### 1.1 BUG-002 的后端层面真相（澄清）

**报告猜测**：「数据未持久化：模板可能只在前端 state 中生成了 ID，未调用保存 API 或保存失败无提示」

**后端真实情况**（已通过代码追溯验证）：

✅ **后端 `/api/templates/v2/clone` 与 `/api/templates/v2/create` 工作正常**：

- `backend/api/main.py:518-538` 的 `v2_clone_template` 端点：
  - 调用 `template_manager.clone_template(source_template_id=..., target_scope="user", owner_user=user.username, ...)`
  - 返回 `{success: true, template: {...}}`
  - **鉴权检查**：通过 `Depends(get_current_user)` 注入 `CurrentUser`，确保克隆归属当前用户
  - **唯一校验**：`owner_user=user.username` 写入模板，确保 `user_templates` 能被列表接口正确过滤

- `backend/api/main.py:446-475` 的 `v2_create_template` 端点：
  - 调用 `template_manager.create_template(..., scope="user", owner_user=user.username, ...)`
  - 自动写入 audit 初始快照
  - 鉴权机制同上

**结论**：BUG-002 的"不保存"**与后端无关**，是**前端鉴权缺失**导致列表查询失败、用户感知为"未保存"。

### 1.2 BUG-003 的后端根因（待修复）

**位置**：`backend/core/attribution_templates.py:158`（`ROLE_DEFAULTS` 字典）

**当前错误配置**：
```python
ROLE_DEFAULTS = {
    "executive": "preset_exec_quarterly",   # 高管 → 高管季度复盘
    "analyst":   "preset_analyst_deep",     # 分析师 → 深度下钻
    "product":   "preset_analyst_deep",     # ❌ 产品经理 → 深度下钻（与分析师重复）
    "visitor":   "preset_exec_quarterly",   # 访客 → 高管季度复盘
}
```

**根因**：开发时复用 analyst 默认模板而忘记单独配置 product 角色的默认值。

**验证目标模板存在性**（line 104）：
```python
"preset_model_product": {
    "name": "车型经理产品复盘",
    "description": "面向车型经理的产品线归因复盘 SOP",
    "scope": "system",
    ...
}
```
✅ 模板已存在，仅是字典映射值错误。

---

## 2. 后端修复设计

### 2.1 修复清单

| # | Bug | 文件 | 改动类型 | 代码量 |
|---|-----|------|---------|--------|
| 1 | BUG-003 | `backend/core/attribution_templates.py` | 常量值修改 | 1 行 |

### 2.2 修复 1：产品经理默认模板

**文件路径**：`backend/core/attribution_templates.py`

**搜索锚点**：定位 `ROLE_DEFAULTS` 字典（约 line 155-160）

**修改前**：
```python
ROLE_DEFAULTS = {
    "executive": "preset_exec_quarterly",
    "analyst":   "preset_analyst_deep",
    "product":   "preset_analyst_deep",     # ❌ 错配
    "visitor":   "preset_exec_quarterly",
}
```

**修改后**：
```python
ROLE_DEFAULTS = {
    "executive": "preset_exec_quarterly",
    "analyst":   "preset_analyst_deep",
    "product":   "preset_model_product",    # ✅ 改为产品经理专属模板
    "visitor":   "preset_exec_quarterly",
}
```

**代码 Diff（最小化）**：
```diff
- "product":   "preset_analyst_deep",
+ "product":   "preset_model_product",
```

### 2.3 不要做的事

| 禁止操作 | 原因 |
|---------|------|
| ❌ 修改 `product` 为 `product_manager` | 后端 role 枚举已固定为 `product`，前端 `ROLE_LABELS` 也是 `product` |
| ❌ 调整 `executive` / `analyst` / `visitor` 的值 | 这三个角色的映射均正确，测试已通过 |
| ❌ 把 `ROLE_DEFAULTS` 改为从数据库加载 | 范围外的架构变更，会引入新 bug |
| ❌ 修改 `template_manager.get_template()` 或 `list_templates()` 逻辑 | 报告未指出后端列表逻辑有 bug |
| ❌ 修改 `AttributionTemplateManager` 任何方法签名 | 接口契约必须保持稳定 |

### 2.4 后端接口契约（无变更说明）

本次修复**不修改任何 API 端点的请求/响应格式**。下表列出与本次修复相关的接口，仅做澄清说明：

| 端点 | 用途 | 鉴权 | 与修复关系 |
|------|------|------|-----------|
| `GET /api/sop/templates?role=xxx` | 列出模板（含 role_default_id） | 可选（推荐带） | 返回的 `role_default_id` 将正确反映 product 角色 |
| `POST /api/sop/templates/create` | 老接口创建 | 无 | 与本次修复无关 |
| `POST /api/templates/v2/create` | V2 创建 | 必须 | 业务用户创建 user 模板 |
| `POST /api/templates/v2/clone` | V2 克隆 | 必须 | 业务用户克隆到 user scope |
| `POST /api/templates/v2/{id}/run` | V2 执行 SOP | 必须 | 核心执行端点 |
| `POST /api/templates/v2/{id}/preview` | V2 预览 | 必须 | 编辑器实时预览 |
| `GET /api/templates/v2/{id}/audit` | V2 审计历史 | 必须 | 变更历史 |
| `PUT /api/templates/v2/{id}` | V2 更新 | 必须 | 编辑器保存 |
| `DELETE /api/templates/v2/{id}` | V2 删除 | 必须 | 用户删除自己的模板 |

**所有接口契约保持不变**，前端无需调整任何 API 调用代码（鉴权修复属于前端责任，详见前端 SDD）。

---

## 3. 后端测试设计

### 3.1 单元测试

**目标文件**：`backend/tests/test_attribution_templates.py`（如不存在则新建）

**测试用例清单**：

```python
# tests/test_attribution_templates.py

import pytest
from core.attribution_templates import (
    AttributionTemplateManager,
    ROLE_DEFAULTS,
)


class TestRoleDefaults:
    """验证 4 角色默认模板配置（BUG-003 修复）"""

    def test_executive_default_is_quarterly(self):
        """TC-RD-001: 高管默认 = 高管季度复盘"""
        assert ROLE_DEFAULTS.get("executive") == "preset_exec_quarterly"

    def test_analyst_default_is_deep_drill(self):
        """TC-RD-002: 分析师默认 = 深度下钻"""
        assert ROLE_DEFAULTS.get("analyst") == "preset_analyst_deep"

    def test_product_default_is_product_model(self):
        """TC-RD-003: 产品经理默认 = 车型经理产品复盘（BUG-003 修复验证）"""
        assert ROLE_DEFAULTS.get("product") == "preset_model_product"
        # 关键：必须不等于 analyst 的默认
        assert ROLE_DEFAULTS.get("product") != ROLE_DEFAULTS.get("analyst")

    def test_visitor_default_is_quarterly(self):
        """TC-RD-004: 访客默认 = 高管季度复盘"""
        assert ROLE_DEFAULTS.get("visitor") == "preset_exec_quarterly"

    def test_all_role_defaults_are_unique_except_visitor(self):
        """TC-RD-005: 4 角色默认值，3 个核心角色（executive/analyst/product）必须互不相同"""
        core = ["executive", "analyst", "product"]
        defaults = [ROLE_DEFAULTS[r] for r in core]
        assert len(set(defaults)) == len(defaults), \
            f"核心角色默认模板必须互不相同，实际: {dict(zip(core, defaults))}"

    def test_all_default_template_ids_exist(self):
        """TC-RD-006: 所有默认模板 ID 必须真实存在（防止 typo）"""
        mgr = AttributionTemplateManager()
        for role, tpl_id in ROLE_DEFAULTS.items():
            if tpl_id is None:
                continue
            tpl = mgr.get_template(tpl_id)
            assert tpl is not None, f"角色 {role} 默认模板 {tpl_id} 不存在"
            assert tpl.get("scope") in ("system", "role_default"), \
                f"角色 {role} 默认模板 {tpl_id} 必须是 system 或 role_default scope"


class TestListTemplatesRoleDefault:
    """验证 list_templates 返回正确的 role_default_id（BUG-003 集成验证）"""

    def test_list_templates_product_role_default(self, tmp_path):
        """TC-LT-001: role=product 返回的 role_default_id 必须是 preset_model_product"""
        mgr = AttributionTemplateManager(db_path=str(tmp_path / "test.duckdb"))
        # 初始化 5 个预设模板（fixture 已有）
        mgr.init_presets()
        result = mgr.list_templates(role="product", user="test_user")
        assert result["role_default_id"] == "preset_model_product"

    def test_list_templates_analyst_role_default(self, tmp_path):
        """TC-LT-002: role=analyst 返回的 role_default_id 必须是 preset_analyst_deep"""
        mgr = AttributionTemplateManager(db_path=str(tmp_path / "test.duckdb"))
        mgr.init_presets()
        result = mgr.list_templates(role="analyst", user="test_user")
        assert result["role_default_id"] == "preset_analyst_deep"

    def test_list_templates_4_roles_different_defaults(self, tmp_path):
        """TC-LT-003: 4 角色调用 list_templates，3 个核心角色返回的 role_default_id 互不相同"""
        mgr = AttributionTemplateManager(db_path=str(tmp_path / "test.duckdb"))
        mgr.init_presets()
        defaults = {}
        for role in ["executive", "analyst", "product"]:
            result = mgr.list_templates(role=role, user="test_user")
            defaults[role] = result["role_default_id"]
        assert defaults["executive"] != defaults["analyst"]
        assert defaults["analyst"] != defaults["product"]
        assert defaults["executive"] != defaults["product"]
```

### 3.2 集成测试（API 端点）

**目标文件**：`backend/tests/test_role_permissions.py`（如不存在则新建）

**测试用例清单**：

```python
# tests/test_role_permissions.py

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers_product():
    """产品经理角色登录态的 Authorization header"""
    # 实际项目中的 mock 登录 token
    return {"Authorization": "Bearer mock_token_product_role"}


class TestRoleDefaultMappingAPI:
    """通过 API 端点验证 BUG-003 修复"""

    def test_api_list_templates_product_role_default(
        self, client, auth_headers_product
    ):
        """TC-API-001: GET /api/sop/templates?role=product 返回正确默认模板"""
        resp = client.get(
            "/api/sop/templates",
            params={"role": "product", "user": "zhangsan"},
            headers=auth_headers_product,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role_default_id"] == "preset_model_product"
        # 防御性检查：role_defaults_map 也应正确
        assert data["role_defaults_map"]["product"] == "preset_model_product"

    def test_api_list_templates_4_roles_all_distinct(
        self, client
    ):
        """TC-API-002: 4 角色调用 API，3 个核心角色默认模板互不相同"""
        defaults = {}
        for role in ["executive", "analyst", "product", "visitor"]:
            resp = client.get(
                "/api/sop/templates",
                params={"role": role, "user": "test_user"},
            )
            if resp.status_code == 200:
                defaults[role] = resp.json().get("role_default_id")
        # 3 个核心角色必须互不相同
        assert defaults.get("executive") != defaults.get("analyst")
        assert defaults.get("analyst") != defaults.get("product")
        assert defaults.get("executive") != defaults.get("product")
```

### 3.3 手工验证步骤（Postman / curl）

**前置条件**：本地启动后端 `uvicorn api.main:app --port 8000`

**验证 1：产品经理默认模板**
```bash
curl -s "http://localhost:8000/api/sop/templates?role=product&user=test_user" \
  -H "Authorization: Bearer <your_token>" | python -m json.tool | grep role_default_id
```
**期望输出**：`"role_default_id": "preset_model_product"`

**验证 2：其他 3 角色未受影响**
```bash
for role in executive analyst visitor; do
  echo "=== $role ==="
  curl -s "http://localhost:8000/api/sop/templates?role=$role&user=test_user" \
    -H "Authorization: Bearer <your_token>" | python -c "import json,sys; print(json.load(sys.stdin)['role_default_id'])"
done
```
**期望输出**：
```
=== executive ===
preset_exec_quarterly
=== analyst ===
preset_analyst_deep
=== visitor ===
preset_exec_quarterly
```

**验证 3：创建/克隆/运行流程**
```bash
# 1. 创建一个 user 模板
TID=$(curl -s -X POST "http://localhost:8000/api/templates/v2/create" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试模板","steps":[{"step_id":"s1","title":"测试","step_type":"horizontal_compare","metric_key":"delivered_units","group_by":["brand_name"],"compare_mode":"plan","order":1}]}' \
  | python -c "import json,sys; print(json.load(sys.stdin)['template']['id'])")
echo "Created: $TID"

# 2. 列表里能看到
curl -s "http://localhost:8000/api/sop/templates?user=test_user" \
  -H "Authorization: Bearer <your_token>" | python -c "import json,sys; d=json.load(sys.stdin); print('user_templates count:', len(d.get('user_templates', [])))"
```
**期望输出**：`user_templates count: 1`（或大于 0）

# 3. 能成功运行
curl -s -X POST "http://localhost:8000/api/templates/v2/$TID/run" \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{}' | python -c "import json,sys; d=json.load(sys.stdin); print('steps_executed:', d.get('steps_executed'))"
```
**期望输出**：`steps_executed: 1`

### 3.4 回归测试清单

| 用例 | 状态 | 说明 |
|------|------|------|
| 5 个预设模板的 `GET /api/sop/templates/{id}` 仍 200 | 必须通过 | 不可破坏现有模板 |
| `POST /api/templates/v2/create` 业务用户创建 | 必须通过 | 不修改此端点 |
| `POST /api/templates/v2/clone` 业务用户克隆 | 必须通过 | 不修改此端点 |
| `POST /api/templates/v2/{id}/run` 执行 SOP | 必须通过 | 不修改此端点 |
| `GET /api/templates/v2/{id}/audit` 审计历史 | 必须通过 | 不修改此端点 |
| admin 端点 `POST /api/admin/templates` 创建/更新 | 必须通过 | 不修改此端点 |
| `existing test_role_permissions.py` 全部用例 | 必须通过 | 不修改既有权限测试 |

---

## 4. 后端部署设计

### 4.1 部署步骤

**前置条件**：
- 已有 Render Web Service 服务 `gac-chatbi-api`（Docker 部署）
- 仓库已 push 到 `origin/main`

**操作流程**：

```bash
# 1. 拉取最新代码
cd /Users/apple/Desktop/AI\ 产品经理/实战项目/GAC-ChatBI
git checkout main
git pull origin main

# 2. 确认 diff
git diff backend/core/attribution_templates.py
# 期望：1 行修改
# - "product":   "preset_analyst_deep",
# + "product":   "preset_model_product",

# 3. 提交并推送
git add backend/core/attribution_templates.py
git commit -m "fix(templates): BUG-003 产品经理默认模板改为 preset_model_product

产品经理角色之前复用分析师的 preset_analyst_deep，
根据产品设计应为专属模板 preset_model_product。
见 SDD §3.4 与归因模板测试报告 TC-TPL-038。"
git push origin main

# 4. Render Web Service 自动部署（约 5-8 分钟，因为 Docker build）
# 5. 部署完成后**硬重启**服务（重要！模块级常量需要进程重启才生效）
#    Render 控制台 → gac-chatbi-api → Manual Deploy → Clear build cache & deploy
```

### 4.2 部署后验证（按顺序执行）

| 步骤 | 操作 | 期望 |
|------|------|------|
| 1 | 访问 `https://gac-chatbi-api.onrender.com/api/health` | `{"status":"ok"}` |
| 2 | 等待部署完成（Render Dashboard 显示 "Live"） | — |
| 3 | curl 测试 4 角色 role_default_id | 3 个核心角色互不相同 |
| 4 | 创建 → 列表 → 运行 一个 user 模板 | 完整流程通 |
| 5 | 通知前端测试团队开始联调 | — |

### 4.3 回滚方案

```bash
# 如果修复引入问题：
git revert HEAD
git push origin main
# Render 自动回滚（需 5-8 分钟）

# 紧急硬回滚（Render 控制台）：
# → gac-chatbi-api → Manual Deploy → 选择上一个成功 commit → Deploy
```

**风险评估**：
- 1 行常量值修改，几乎无引入 bug 风险
- 即使改错，回滚不影响用户数据（DuckDB 模板表不受影响）

---

## 5. 监控与告警建议（可选）

修复上线后，建议在 Render Dashboard 配置以下告警（不属于本次代码修复范围）：

| 告警指标 | 阈值 | 告警渠道 |
|---------|------|---------|
| 5xx 错误率 | > 1% 持续 5 分钟 | 邮件 |
| `/api/sop/templates` P99 延迟 | > 2s | 邮件 |
| `/api/templates/v2/{id}/run` P99 延迟 | > 30s | 邮件 |
| 模板创建成功率 | < 99% | Slack |

---

## 6. 后端实施 Checklist

### 阶段 1：代码修改（0.1 人天）

- [ ] 打开 `backend/core/attribution_templates.py`
- [ ] 定位 `ROLE_DEFAULTS` 字典（约 line 155-160）
- [ ] 修改 `"product"` 值为 `"preset_model_product"`
- [ ] 保存文件

### 阶段 2：本地测试（0.05 人天）

- [ ] 运行 `pytest backend/tests/test_attribution_templates.py::TestRoleDefaults -v`
- [ ] 6 个单测全部通过
- [ ] 运行 `pytest backend/tests/ -v` 全量回归
- [ ] 全部既有测试通过

### 阶段 3：部署（0.05 人天）

- [ ] 提交代码并 push 到 main
- [ ] Render 自动部署完成（5-8 分钟）
- [ ] 硬重启 Render 服务（Clear build cache & deploy）
- [ ] 部署后验证 4 角色 role_default_id 互不相同
- [ ] 通知前端联调

### 阶段 4：交付（0 工时）

- [ ] 更新 CHANGELOG.md
- [ ] 通知测试团队回归
- [ ] 归档实施记录

---

## 7. 附录

### 7.1 关键代码引用

- `ROLE_DEFAULTS` 定义：`backend/core/attribution_templates.py:155-160`
- `preset_model_product` 模板定义：`backend/core/attribution_templates.py:104-115`
- `list_templates` 方法：`backend/core/attribution_templates.py`（具体行号见 `list_templates` 方法）
- `list_attribution_templates` API 端点：`backend/api/main.py:373-384`
- `v2_create_template` API 端点：`backend/api/main.py:446-475`
- `v2_clone_template` API 端点：`backend/api/main.py:518-538`
- `v2_template_run` API 端点：`backend/api/main.py:567-595`

### 7.2 关联测试用例

| 后端测试 | 对应报告用例 | 说明 |
|---------|------------|------|
| TC-RD-001 ~ TC-RD-006 | TC-TPL-038 | 4 角色默认模板互不相同 |
| TC-LT-001 ~ TC-LT-003 | TC-TPL-038 | 列表接口返回正确默认 |
| TC-API-001 ~ TC-API-002 | TC-TPL-036, TC-TPL-038 | API 层验证 |
| 手工验证 1-3 | TC-TPL-042, TC-TPL-023, TC-TPL-026 | 完整流程验证 |

### 7.3 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| 修改常量值后忘记硬重启 | 🟢 低 | 部署步骤明确要求 Clear build cache |
| `preset_model_product` 模板定义缺失 | 🟢 极低 | 已验证 line 104 存在 |
| DuckDB 数据迁移问题 | 🟢 极低 | 本次不修改 schema |
| 其他模块依赖 ROLE_DEFAULTS 的值 | 🟢 低 | 全局搜索确认无外部引用 |

---

## 8. 签字确认

| 角色 | 姓名 | 日期 | 备注 |
|------|------|------|------|
| 架构师 | （AI 自动生成） | 2026-10-18 | — |
| 后端开发 | _待确认_ | _待定_ | 实施 + 单测 |
| 后端测试 | _待确认_ | _待定_ | 回归测试 |
| DevOps | _待确认_ | _待定_ | 部署 + 监控 |

---

> **下一步**：本后端 SDD 实施完成后，等待前端 SDD 实施完成，再进行联调。
