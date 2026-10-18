# 测试用例文档：归因模板模块 Bug 修复回归测试

> **版本**：v1.0
> **日期**：2026-10-18
> **所属总 SDD**：`SDD_TEMPLATES_BUGFIX.md`
> **子模块**：测试用例（覆盖前端 + 后端 + 部署 3 个修复点）
> **目标读者**：测试工程师 / QA / 自动化测试开发
> **作用**：基于测试报告中的 4 个 P0/P1/P2 Bug，输出可执行的回归测试用例

---

## 0. 文档元信息

| 字段 | 内容 |
|------|------|
| 测试目标 | 验证 SDD 中的 4 处修复（render.yaml / templates-api.ts / attribution_templates.py / DemoTour.tsx） |
| 测试范围 | 单元测试 + 集成测试 + E2E 测试 + 手工验证 |
| 测试环境 | 1. 本地（开发自测）<br>2. Staging（Render 测试服务）<br>3. Production（Render 生产服务） |
| 测试账号 | zhangsan（业务用户）、admin（管理员） |
| 预计测试工时 | 1.0 人天（含执行 + 报告） |
| 通过率目标 | ≥ 90%（≥ 36/40），P0 通过率 100%（8/8） |

---

## 1. 测试策略总览

### 1.1 测试金字塔

```
        ╱╲
       ╱  ╲          E2E 测试 (Playwright)
      ╱ 8条 ╲        → 覆盖完整用户旅程
     ╱──────╲
    ╱ 集成测试 ╲      API + 鉴权 + 跨服务
   ╱  12 条   ╲     → 验证 SDD 修复契约
  ╱────────────╲
 ╱  单元测试     ╲    Vitest + Pytest
╱  18 条         ╲   → 验证函数级逻辑
────────────────────
```

### 1.2 测试覆盖矩阵

| Bug | 单元测试 | 集成测试 | E2E 测试 | 手工验证 | 报告原用例 |
|-----|---------|---------|---------|---------|-----------|
| **BUG-001** | 0 | 0 | 2 | 1 | TC-TPL-026~031 |
| **BUG-002** | 3 | 3 | 4 | 1 | TC-TPL-010, 023, 042~051 |
| **BUG-003** | 6 | 2 | 2 | 1 | TC-TPL-036, 038 |
| **BUG-004** | 3 | 0 | 1 | 1 | 全局体验 |
| **合计** | **12** | **5** | **9** | **4** | — |

### 1.3 优先级与执行顺序

| 优先级 | 测试类型 | 必须通过的 Bug | 阻塞后续测试 |
|--------|---------|--------------|------------|
| 🔴 P0 | 后端单测 + 前端单测 | BUG-002, BUG-003 | 是 |
| 🔴 P0 | E2E 运行 SOP | BUG-001 | 是 |
| 🟡 P1 | E2E 自定义模板 | BUG-002 | 是 |
| 🟡 P1 | E2E 角色默认 | BUG-003 | 否 |
| 🟢 P2 | E2E 引导 | BUG-004 | 否 |

---

## 2. 单元测试用例

### 2.1 后端单测：ROLE_DEFAULTS（BUG-003）

**文件**：`backend/tests/test_role_defaults.py`（新建）

**前置条件**：pytest 已安装，`AttributionTemplateManager` 可导入

#### TC-BE-RD-001：高管角色默认模板

| 项 | 内容 |
|----|------|
| **测试点** | `ROLE_DEFAULTS["executive"]` 返回 `preset_exec_quarterly` |
| **优先级** | P0 |
| **类型** | 单元测试 |
| **自动化** | ✅ |

**测试代码**：
```python
def test_executive_default_is_quarterly():
    from core.attribution_templates import ROLE_DEFAULTS
    assert ROLE_DEFAULTS["executive"] == "preset_exec_quarterly"
```

**通过标准**：断言通过，无异常

---

#### TC-BE-RD-002：分析师角色默认模板

| 项 | 内容 |
|----|------|
| **测试点** | `ROLE_DEFAULTS["analyst"]` 返回 `preset_analyst_deep` |
| **优先级** | P0 |
| **类型** | 单元测试 |

**测试代码**：
```python
def test_analyst_default_is_deep_drill():
    from core.attribution_templates import ROLE_DEFAULTS
    assert ROLE_DEFAULTS["analyst"] == "preset_analyst_deep"
```

---

#### TC-BE-RD-003：产品经理角色默认模板（BUG-003 核心验证）

| 项 | 内容 |
|----|------|
| **测试点** | `ROLE_DEFAULTS["product"]` **必须**等于 `preset_model_product`（不再是 `preset_analyst_deep`） |
| **优先级** | 🔴 P0 |
| **类型** | 单元测试 |
| **关联报告** | TC-TPL-038 |

**测试代码**：
```python
def test_product_default_is_product_model():
    from core.attribution_templates import ROLE_DEFAULTS
    # 关键断言：产品经理必须有自己专属的默认模板
    assert ROLE_DEFAULTS["product"] == "preset_model_product"
    # 防御性检查：不应等于分析师的默认
    assert ROLE_DEFAULTS["product"] != ROLE_DEFAULTS["analyst"]
```

**通过标准**：
1. ✅ `ROLE_DEFAULTS["product"] == "preset_model_product"`
2. ✅ `ROLE_DEFAULTS["product"] != ROLE_DEFAULTS["analyst"]`

**失败信号**：修复未生效或回退到旧值

---

#### TC-BE-RD-004：访客角色默认模板

| 项 | 内容 |
|----|------|
| **测试点** | `ROLE_DEFAULTS["visitor"]` 返回 `preset_exec_quarterly` |
| **优先级** | P0 |
| **类型** | 单元测试 |

**测试代码**：
```python
def test_visitor_default_is_quarterly():
    from core.attribution_templates import ROLE_DEFAULTS
    assert ROLE_DEFAULTS["visitor"] == "preset_exec_quarterly"
```

---

#### TC-BE-RD-005：3 个核心角色默认互不相同

| 项 | 内容 |
|----|------|
| **测试点** | executive / analyst / product 三个角色的默认模板 ID 互不相同 |
| **优先级** | 🔴 P0 |
| **类型** | 单元测试 |
| **关联报告** | TC-TPL-038（核心验收） |

**测试代码**：
```python
def test_core_roles_have_distinct_defaults():
    from core.attribution_templates import ROLE_DEFAULTS
    core = ["executive", "analyst", "product"]
    defaults = [ROLE_DEFAULTS[r] for r in core]
    # 3 个值必须互不相同
    assert len(set(defaults)) == 3, \
        f"3 个核心角色默认模板必须互不相同，实际: {dict(zip(core, defaults))}"
```

**通过标准**：`len(set(defaults)) == 3`

**失败信号**：角色映射仍然有重复（BUG-003 未修复）

---

#### TC-BE-RD-006：所有默认模板 ID 真实存在

| 项 | 内容 |
|----|------|
| **测试点** | 4 个角色的默认模板 ID 在系统中真实存在 |
| **优先级** | P0 |
| **类型** | 单元测试 |

**测试代码**：
```python
def test_all_default_template_ids_exist(tmp_path):
    from core.attribution_templates import (
        AttributionTemplateManager, ROLE_DEFAULTS
    )
    mgr = AttributionTemplateManager(db_path=str(tmp_path / "test.duckdb"))
    mgr.init_presets()
    for role, tpl_id in ROLE_DEFAULTS.items():
        if tpl_id is None:
            continue
        tpl = mgr.get_template(tpl_id)
        assert tpl is not None, f"角色 {role} 默认模板 {tpl_id} 不存在"
```

---

### 2.2 前端单测：listTemplates 鉴权（BUG-002）

**文件**：`frontend/tests/test_templates_api.test.ts`（新建或追加）

**前置条件**：Vitest 已配置，`@/lib/auth` 可 mock

#### TC-FE-LT-001：列表请求携带 Authorization

| 项 | 内容 |
|----|------|
| **测试点** | `listTemplates()` 调用时，`authFetch` 注入 Authorization 头 |
| **优先级** | 🔴 P0 |
| **类型** | 单元测试 |
| **关联报告** | TC-TPL-042 |

**测试代码**：
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import * as authModule from "@/lib/auth";

describe("listTemplates - BUG-002", () => {
  beforeEach(() => {
    localStorage.setItem("gac_chatbi_token", "test_token_123");
  });

  it("TC-FE-LT-001: should call authFetch with token", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ system_presets: [], user_templates: [] }),
    });
    vi.spyOn(authModule, "authFetch").mockImplementation(fetchMock);

    const { listTemplates } = await import("@/lib/templates-api");
    await listTemplates("product", "zhangsan");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = fetchMock.mock.calls[0][0];
    expect(url).toContain("/api/sop/templates");
    expect(url).toContain("role=product");
  });
});
```

**通过标准**：`fetchMock` 被调用 1 次，URL 含 `/api/sop/templates` 和 `role=product`

---

#### TC-FE-LT-002：user_templates 正确返回

| 项 | 内容 |
|----|------|
| **测试点** | 鉴权后调用 listTemplates 能正确返回 user_templates 数组 |
| **优先级** | 🔴 P0 |
| **类型** | 单元测试 |
| **关联报告** | TC-TPL-042 |

**测试代码**：
```typescript
it("TC-FE-LT-002: should return user_templates when authenticated", async () => {
  const mockData = {
    system_presets: [],
    role_default_id: "preset_model_product",
    role_defaults_map: { product: "preset_model_product" },
    user_templates: [{ id: "user_123", name: "我的模板" }],
  };
  vi.spyOn(authModule, "authFetch").mockResolvedValue({
    ok: true,
    json: async () => mockData,
  } as any);

  const { listTemplates } = await import("@/lib/templates-api");
  const result = await listTemplates("product", "zhangsan");

  expect(result.user_templates).toHaveLength(1);
  expect(result.user_templates[0].id).toBe("user_123");
});
```

---

#### TC-FE-LT-003：401 正确处理

| 项 | 内容 |
|----|------|
| **测试点** | API 返回 401 时，listTemplates 抛错（不静默吞错） |
| **优先级** | P1 |
| **类型** | 单元测试 |

**测试代码**：
```typescript
it("TC-FE-LT-003: should throw on 401", async () => {
  vi.spyOn(authModule, "authFetch").mockResolvedValue({
    ok: false,
    status: 401,
  } as any);

  const { listTemplates } = await import("@/lib/templates-api");
  await expect(listTemplates("product", "zhangsan"))
    .rejects.toThrow("listTemplates failed: 401");
});
```

---

### 2.3 前端单测：DemoTour 状态（BUG-004）

**文件**：`frontend/tests/test_demo_tour.test.tsx`（新建）

#### TC-FE-DT-001：首次访问自动弹出

| 项 | 内容 |
|----|------|
| **测试点** | localStorage 无记录时，DemoTour 渲染后引导遮罩存在 |
| **优先级** | 🟢 P2 |
| **类型** | 单元测试 |

**测试代码**：
```typescript
import { render } from "@testing-library/react";
import DemoTour from "@/components/DemoTour";

it("TC-FE-DT-001: shows on first visit (no localStorage)", () => {
  localStorage.removeItem("gac-chatbi-tour-completed");
  const { container } = render(<DemoTour />);
  expect(container.querySelector('[role="dialog"]')).toBeTruthy();
});
```

---

#### TC-FE-DT-002：完成引导后不弹出

| 项 | 内容 |
|----|------|
| **测试点** | localStorage 存在 `tour-completed` 记录时，DemoTour 不渲染引导 |
| **优先级** | 🟢 P2 |
| **类型** | 单元测试 |
| **关联报告** | BUG-004 |

**测试代码**：
```typescript
it("TC-FE-DT-002: doesn't show after completion", () => {
  localStorage.setItem("gac-chatbi-tour-completed", "1");
  const { container } = render(<DemoTour />);
  expect(container.querySelector('[role="dialog"]')).toBeFalsy();
});
```

---

#### TC-FE-DT-003：组件 mount 不重置已读状态

| 项 | 内容 |
|----|------|
| **测试点** | 模拟"组件被重新 mount"（如 React Strict Mode），状态不丢失 |
| **优先级** | 🟢 P2 |
| **类型** | 单元测试 |

**测试代码**：
```typescript
it("TC-FE-DT-003: state persists across remount", () => {
  localStorage.setItem("gac-chatbi-tour-completed", "1");
  const { unmount, container } = render(<DemoTour />);
  expect(container.querySelector('[role="dialog"]')).toBeFalsy();

  unmount();

  // 重新 mount（模拟 React Strict Mode 或 layout 重 mount）
  const { container: container2 } = render(<DemoTour />);
  expect(container2.querySelector('[role="dialog"]')).toBeFalsy();
});
```

---

## 3. 集成测试用例（API + 鉴权）

### 3.1 后端集成：list_templates 返回正确默认

#### TC-BE-LT-001：产品经理角色默认模板

| 项 | 内容 |
|----|------|
| **测试点** | `template_manager.list_templates(role="product")` 返回 `role_default_id="preset_model_product"` |
| **优先级** | 🔴 P0 |
| **类型** | 集成测试 |
| **关联报告** | TC-TPL-038 |

**测试代码**：
```python
def test_list_templates_product_role_default(tmp_path):
    from core.attribution_templates import AttributionTemplateManager
    mgr = AttributionTemplateManager(db_path=str(tmp_path / "test.duckdb"))
    mgr.init_presets()
    result = mgr.list_templates(role="product", user="zhangsan")
    assert result["role_default_id"] == "preset_model_product"
```

---

#### TC-BE-LT-002：分析师角色默认模板

| 项 | 内容 |
|----|------|
| **测试点** | `list_templates(role="analyst")` 返回 `role_default_id="preset_analyst_deep"` |
| **优先级** | P0 |
| **类型** | 集成测试 |

```python
def test_list_templates_analyst_role_default(tmp_path):
    mgr = AttributionTemplateManager(db_path=str(tmp_path / "test.duckdb"))
    mgr.init_presets()
    result = mgr.list_templates(role="analyst", user="zhangsan")
    assert result["role_default_id"] == "preset_analyst_deep"
```

---

#### TC-BE-LT-003：4 角色默认值互不相同

| 项 | 内容 |
|----|------|
| **测试点** | 4 角色调用 list_templates，3 个核心角色返回值互不相同 |
| **优先级** | 🔴 P0 |
| **类型** | 集成测试 |
| **关联报告** | TC-TPL-038 |

```python
def test_list_templates_4_roles_distinct(tmp_path):
    mgr = AttributionTemplateManager(db_path=str(tmp_path / "test.duckdb"))
    mgr.init_presets()
    defaults = {}
    for role in ["executive", "analyst", "product"]:
        result = mgr.list_templates(role=role, user="zhangsan")
        defaults[role] = result["role_default_id"]
    assert len(set(defaults.values())) == 3
```

---

### 3.2 API 端到端测试（HTTP）

#### TC-API-001：GET /api/sop/templates?role=product

| 项 | 内容 |
|----|------|
| **测试点** | API 端点返回的 `role_default_id` 正确 |
| **优先级** | 🔴 P0 |
| **类型** | 集成测试（HTTP） |
| **关联报告** | TC-TPL-036 |

**测试代码**：
```python
def test_api_list_templates_product_role(client, auth_headers_product):
    resp = client.get(
        "/api/sop/templates",
        params={"role": "product", "user": "zhangsan"},
        headers=auth_headers_product,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["role_default_id"] == "preset_model_product"
    assert data["role_defaults_map"]["product"] == "preset_model_product"
```

---

#### TC-API-002：listTemplates 不带 token 应返回 401

| 项 | 内容 |
|----|------|
| **测试点** | 不带 Authorization 头调用 API，应返回 401（验证后端鉴权正确） |
| **优先级** | P1 |
| **类型** | 集成测试 |
| **关联报告** | TC-TPL-042（验证根因二） |

```python
def test_api_list_templates_without_token_returns_401(client):
    resp = client.get("/api/sop/templates?user=zhangsan")
    # 后端鉴权中间件应拒绝
    assert resp.status_code == 401
```

---

## 4. E2E 测试用例（Playwright）

**文件**：`frontend/tests/e2e/templates.spec.ts`

### 4.1 BUG-001 验证用例

#### TC-E2E-001：单个预设模板运行 SOP

| 项 | 内容 |
|----|------|
| **测试点** | 点击「高管季度复盘」的「运行 SOP」按钮，跳转到执行报告页（**不出现 404**） |
| **优先级** | 🔴 P0 |
| **类型** | E2E |
| **关联报告** | TC-TPL-026 |

**前置条件**：
- 登录 zhangsan 账号
- 5 个预设模板已加载

**测试步骤**：
1. 访问 `/templates`
2. 点击「高管季度复盘」卡片的「运行 SOP」按钮
3. 等待页面跳转
4. 检查 URL 是否为 `/templates/run/<id>`（不含 `_`）
5. 检查页面不显示 404
6. 等待 SOP 执行完成（loading 消失）

**通过标准**：
- ✅ URL 匹配 `/templates/run/(?!_)` 模式
- ✅ 页面不显示 404
- ✅ 出现"启动 SOP 引擎"或"执行中"或步骤详情

**失败信号**：
- ❌ 仍跳转 404
- ❌ 跳转到 `/templates/run/_`（说明 fallback 不正确）

---

#### TC-E2E-002：5 个预设模板运行 SOP 全覆盖

| 项 | 内容 |
|----|------|
| **测试点** | 5 个预设模板的「运行 SOP」按钮都能跳转成功 |
| **优先级** | 🔴 P0 |
| **类型** | E2E |
| **关联报告** | TC-TPL-026~031 |

**测试步骤**：
1. 访问 `/templates`
2. 遍历所有「运行 SOP」按钮（应为 5 个）
3. 对每个按钮：点击 → 验证 URL 跳转 → 验证非 404 → 返回

**通过标准**：5 个按钮全部成功跳转

**Playwright 代码**：
```typescript
test("TC-E2E-002: all 5 preset templates can run SOP", async ({ page }) => {
  await page.goto("/templates");
  const buttons = page.locator('button:has-text("运行 SOP")');
  const count = await buttons.count();
  expect(count).toBe(5);

  for (let i = 0; i < count; i++) {
    const btn = buttons.nth(i);
    await btn.click();
    await expect(page).toHaveURL(/\/templates\/run\/.+/);
    expect(page.url()).not.toContain("/_");
    await expect(page.locator("text=404")).not.toBeVisible();
    await page.goto("/templates");
  }
});
```

---

### 4.2 BUG-002 验证用例

#### TC-E2E-003：新建模板能保存到"我的模板"

| 项 | 内容 |
|----|------|
| **测试点** | 新建弹窗 → 填写名称 → 创建 → 跳编辑器 → 返回列表 → 新模板可见 |
| **优先级** | 🔴 P0 |
| **类型** | E2E |
| **关联报告** | TC-TPL-010, TC-TPL-042~051 |

**测试步骤**：
1. 访问 `/templates`
2. 点击「新建我的模板」按钮
3. 填写模板名称"E2E新建测试"
4. 点击「创建并进入编排器」
5. 验证跳转到 `/templates/editor/<id>`，无 404
6. 返回 `/templates`
7. 验证"我的模板"区域出现"E2E新建测试"

**通过标准**：
- ✅ 跳转到编辑器（非 404）
- ✅ 列表中显示新模板
- ✅ 新模板可点击编辑/运行

**Playwright 代码**：
```typescript
test("TC-E2E-003: new template appears in My Templates", async ({ page }) => {
  const testName = `E2E新建测试_${Date.now()}`;

  await page.goto("/templates");
  await page.click('button:has-text("新建我的模板")');
  await page.fill('input[placeholder*="新能源"]', testName);
  await page.click('button:has-text("创建并进入编排器")');

  await expect(page).toHaveURL(/\/templates\/editor\/.+/);
  expect(page.url()).not.toContain("/_");
  await expect(page.locator("text=404")).not.toBeVisible();

  await page.goto("/templates");
  await expect(page.locator(`text=${testName}`)).toBeVisible();
});
```

---

#### TC-E2E-004：克隆模板能保存到"我的模板"

| 项 | 内容 |
|----|------|
| **测试点** | 模板市场 → 克隆 → 跳编辑器 → 返回列表 → 克隆模板可见 |
| **优先级** | 🔴 P0 |
| **类型** | E2E |
| **关联报告** | TC-TPL-023, TC-TPL-042 |

**测试步骤**：
1. 访问 `/templates/market`
2. 点击第一个模板的「克隆为我的模板」按钮
3. 处理 confirm / prompt 弹窗（输入新名称）
4. 验证跳转到 `/templates/editor/<id>`，无 404
5. 返回 `/templates`
6. 验证"我的模板"区域出现克隆的模板

**Playwright 代码**：
```typescript
test("TC-E2E-004: cloned template appears in My Templates", async ({ page }) => {
  const cloneName = `E2E克隆_${Date.now()}`;

  page.on("dialog", (dialog) => dialog.accept(cloneName));

  await page.goto("/templates/market");
  await page.locator('button:has-text("克隆为我的模板")').first().click();
  await page.waitForURL(/\/templates\/editor\/.+/);
  expect(page.url()).not.toContain("/_");
  await expect(page.locator("text=404")).not.toBeVisible();

  await page.goto("/templates");
  await expect(page.locator(`text=${cloneName}`)).toBeVisible();
});
```

---

#### TC-E2E-005：编辑器页能加载模板

| 项 | 内容 |
|----|------|
| **测试点** | 直接访问 `/templates/editor/<id>` 能正常加载，显示模板内容 |
| **优先级** | 🔴 P0 |
| **类型** | E2E |
| **关联报告** | TC-TPL-046, TC-TPL-047 |

**测试步骤**：
1. 访问 `/templates`
2. 点击任一模板的编辑按钮（V2 编排器）
3. 验证跳转到 `/templates/editor/<id>`
4. 验证页面加载完成（"SOP 步骤" 或 "加载模板" 出现）
5. 验证左侧步骤列表、右侧预览面板出现

**Playwright 代码**：
```typescript
test("TC-E2E-005: editor page loads template", async ({ page }) => {
  await page.goto("/templates");
  await page.locator('[title="V2 编排器"]').first().click();
  await expect(page).toHaveURL(/\/templates\/editor\/.+/);
  await expect(page.locator("text=404")).not.toBeVisible();
  await expect(page.locator("text=SOP 步骤").or(page.locator("text=加载模板"))).toBeVisible();
});
```

---

#### TC-E2E-006：编辑后保存能成功

| 项 | 内容 |
|----|------|
| **测试点** | 在编辑器修改名称 → 点保存 → 重新加载能看到新名称 |
| **优先级** | P1 |
| **类型** | E2E |
| **关联报告** | TC-TPL-046 |

```typescript
test("TC-E2E-006: edit and save template", async ({ page }) => {
  await page.goto("/templates");
  await page.locator('[title="V2 编排器"]').first().click();
  await page.waitForURL(/\/templates\/editor\/.+/);

  const newName = `编辑测试_${Date.now()}`;
  const nameInput = page.locator('input[type="text"]').first();
  await nameInput.fill(newName);
  await page.click('button:has-text("保存")');

  await page.goto("/templates");
  await expect(page.locator(`text=${newName}`)).toBeVisible();
});
```

---

### 4.3 BUG-003 验证用例

#### TC-E2E-007：产品经理角色默认模板

| 项 | 内容 |
|----|------|
| **测试点** | 切换到"产品经理"角色，默认提示显示「车型经理产品复盘」 |
| **优先级** | 🟡 P1 |
| **类型** | E2E |
| **关联报告** | TC-TPL-036 |

**Playwright 代码**：
```typescript
test("TC-E2E-007: product role default is model_product", async ({ page }) => {
  await page.goto("/templates");
  await page.click('button:has-text("产品经理")');
  await expect(page.locator("text=车型经理产品复盘")).toBeVisible();
});
```

---

#### TC-E2E-008：4 角色默认模板互不相同

| 项 | 内容 |
|----|------|
| **测试点** | 高管/分析师/产品经理 3 角色默认模板互不相同 |
| **优先级** | 🟡 P1 |
| **类型** | E2E |
| **关联报告** | TC-TPL-038 |

**Playwright 代码**：
```typescript
test("TC-E2E-008: 4 roles have distinct default templates", async ({ page }) => {
  await page.goto("/templates");
  const defaults: string[] = [];

  for (const role of ["高管", "分析师", "产品经理"]) {
    await page.click(`button:has-text("${role}")`);
    const banner = await page.locator(".bg-amber-50").first().textContent();
    const match = banner?.match(/：(.+)$/);
    if (match) defaults.push(match[1].trim());
  }

  expect(new Set(defaults).size).toBe(3);
});
```

---

### 4.4 BUG-004 验证用例

#### TC-E2E-009：引导关闭后刷新不弹出

| 项 | 内容 |
|----|------|
| **测试点** | 关闭引导后 F5 刷新，引导不再弹出 |
| **优先级** | 🟢 P2 |
| **类型** | E2E |
| **关联报告** | BUG-004 |

**Playwright 代码**：
```typescript
test("TC-E2E-009: tour doesn't reappear after close + reload", async ({ page }) => {
  // 首次访问清空 localStorage
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());

  // 重新加载让引导自动弹出
  await page.reload();
  await page.waitForTimeout(1500);  // 等 800ms 延迟

  const tour = page.locator('[role="dialog"]');
  await expect(tour).toBeVisible();

  // 关闭引导
  await page.click('button:has-text("跳过")').or(page.click('button[aria-label="关闭引导"]'));
  await expect(tour).not.toBeVisible();

  // 刷新
  await page.reload();
  await page.waitForTimeout(1500);
  await expect(tour).not.toBeVisible();
});
```

---

## 5. 手工验证用例

### 5.1 部署后立即验证（DevOps 必做）

#### TC-MANUAL-001：动态路由 200

| 项 | 内容 |
|----|------|
| **测试点** | `curl -sI /templates/run/<id>` 返回 200 |
| **优先级** | 🔴 P0 |
| **类型** | 手工（curl） |

**命令**：
```bash
echo "=== /templates/run/preset_exec_quarterly ==="
curl -sI https://gac-chat-bi.onrender.com/templates/run/preset_exec_quarterly | head -1
echo "=== /templates/editor/user_test ==="
curl -sI https://gac-chat-bi.onrender.com/templates/editor/user_test | head -1
echo "=== /templates（应保持 200）==="
curl -sI https://gac-chat-bi.onrender.com/templates | head -1
```

**通过标准**：
- `/templates/run/preset_exec_quarterly` → HTTP/2 200
- `/templates/editor/user_test` → HTTP/2 200
- `/templates` → HTTP/2 200

**失败应对**：
- 仍 404 → 检查 render.yaml 是否提交 + Render 部署是否成功
- 500 → 检查 Render 部署日志

---

#### TC-MANUAL-002：后端 API 返回 200

| 项 | 内容 |
|----|------|
| **测试点** | `/api/sop/templates?role=product` 返回 200 且 role_default_id 正确 |
| **优先级** | 🔴 P0 |
| **类型** | 手工（curl） |

**命令**：
```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST https://gac-chatbi-api.onrender.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"zhangsan","password":"password"}' \
  | python -c "import json,sys; print(json.load(sys.stdin).get('access_token',''))")

# 2. 调用列表接口
curl -s "https://gac-chatbi-api.onrender.com/api/sop/templates?role=product&user=zhangsan" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool | grep -E "role_default_id|role_defaults_map"
```

**通过标准**：
- 返回 200
- `role_default_id` = `preset_model_product`
- `role_defaults_map.product` = `preset_model_product`

---

#### TC-MANUAL-003：浏览器端验证

| 项 | 内容 |
|----|------|
| **测试点** | 浏览器完整流程，验证 4 个 Bug 全修复 |
| **优先级** | 🔴 P0 |
| **类型** | 手工（浏览器） |

**步骤清单**：
1. 打开 Chrome DevTools，Network 标签，勾选 "Preserve log"
2. 访问 `https://gac-chat-bi.onrender.com/login`
3. 用 zhangsan 账号登录
4. 访问 `/templates`
5. 检查 Network 中的 `/api/sop/templates` 请求：
   - 状态码 200
   - 请求头含 `Authorization: Bearer ...`
   - 响应 Body 含 `user_templates: []` 或更多
6. 点击「高管季度复盘」的「运行 SOP」按钮
7. 验证 URL 变为 `/templates/run/preset_exec_quarterly`
8. 验证页面**不显示 404**
9. 验证页面出现"启动 SOP 引擎..."或步骤详情
10. 返回 `/templates`
11. 切换到「产品经理」角色
12. 验证默认模板提示变为「车型经理产品复盘」
13. 关闭引导弹窗
14. 刷新页面（F5）
15. 验证引导不弹出
16. 截图归档

**通过标准**：所有 16 步全部通过

---

## 6. 回归测试清单（来自原始测试报告）

### 6.1 必须通过的核心用例

| 用例 | 修复前 | 修复后期望 | 验证方式 |
|------|--------|-----------|---------|
| TC-TPL-001 | ✅ | ✅ | 手工 |
| TC-TPL-002 | ✅ | ✅ | 手工 |
| TC-TPL-003 | ✅ | ✅ | 手工 |
| TC-TPL-004 | ✅ | ✅ | 手工 |
| TC-TPL-005 | ✅ | ✅ | 手工 |
| TC-TPL-006 | ✅ | ✅ | 手工 |
| TC-TPL-007 | ✅ | ✅ | 手工 |
| TC-TPL-008 | ✅ | ✅ | 手工 |
| TC-TPL-009 | ✅ | ✅ | 手工 |
| TC-TPL-010 | ❌ | ✅ | E2E（TC-E2E-003） |
| TC-TPL-011 | ✅ | ✅ | 手工 |
| TC-TPL-016 | ✅ | ✅ | 手工 |
| TC-TPL-017 | ✅ | ✅ | 手工 |
| TC-TPL-018 | ✅ | ✅ | 手工 |
| TC-TPL-019 | ✅ | ✅ | 手工 |
| TC-TPL-020 | ✅ | ✅ | 手工 |
| TC-TPL-021 | ✅ | ✅ | 手工 |
| TC-TPL-022 | ✅ | ✅ | 手工 |
| TC-TPL-023 | ❌ | ✅ | E2E（TC-E2E-004） |
| TC-TPL-026 | ❌ | ✅ | E2E（TC-E2E-001） |
| TC-TPL-027 | ❌ | ✅ | E2E（TC-E2E-002） |
| TC-TPL-028 | ❌ | ✅ | E2E（TC-E2E-002） |
| TC-TPL-029 | ❌ | ✅ | E2E（TC-E2E-002） |
| TC-TPL-030 | ❌ | ✅ | E2E（TC-E2E-002） |
| TC-TPL-031 | ❌ | ✅ | 手工（直接访问 URL） |
| TC-TPL-032 | ✅ | ✅ | 手工 |
| TC-TPL-034 | ✅ | ✅ | 手工 |
| TC-TPL-035 | ✅ | ✅ | 手工 |
| TC-TPL-036 | ✅（错配） | ✅ | E2E（TC-E2E-007） |
| TC-TPL-037 | ✅ | ✅ | 手工 |
| TC-TPL-038 | ⚠️ 部分 | ✅ | E2E（TC-E2E-008） |
| TC-TPL-039 | ✅ | ✅ | 手工 |
| TC-TPL-042 | ❌ | ✅ | E2E（TC-E2E-003/004） |
| TC-TPL-043 | ⛔ | ✅ | E2E |
| TC-TPL-044 | ⛔ | ✅ | E2E |
| TC-TPL-045 | ⛔ | ✅ | E2E |
| TC-TPL-046 | ⛔ | ✅ | E2E（TC-E2E-006） |
| TC-TPL-047 | ⛔ | ✅ | E2E |
| TC-TPL-048 | ⛔ | ✅ | E2E |
| TC-TPL-049 | ⛔ | ✅ | E2E |

**修复前**：26 通过 / 9 失败 / 5 阻塞 = 65%  
**修复后目标**：≥ 36 通过 / ≤ 4 失败 / 0 阻塞 = **≥ 90%**

### 6.2 仍然未执行的用例（不在本次范围）

- TC-TPL-012, TC-TPL-013, TC-TPL-015（功能重复）
- TC-TPL-024, TC-TPL-025（依赖 TC-TPL-023 修复）
- TC-TPL-033（依赖 TC-TPL-026 修复）
- TC-TPL-040, TC-TPL-041（刷新保持）
- TC-TPL-050, TC-TPL-051（依赖 TC-TPL-023 修复）
- TC-TPL-052~057（兼容性，6 条全未执行）

**说明**：这些用例在修复后可继续执行，但本次修复目标不强制要求。

---

## 7. 测试执行计划

### 7.1 执行时间表

| 阶段 | 任务 | 预计工时 | 执行人 |
|------|------|---------|--------|
| T+0 | 部署前：本地单测（TC-BE-RD-001~006 + TC-FE-LT-001~003 + TC-FE-DT-001~003） | 0.3 人天 | 开发自测 |
| T+0 | 部署前：本地构建验证（`npm run build` + `npx serve out`） | 0.1 人天 | 前端 |
| T+1 | 部署中：提交代码 → Render 自动部署 | 等待 5-8 分钟 | DevOps |
| T+1 | 部署后：手工验证（TC-MANUAL-001/002/003） | 0.1 人天 | 测试 |
| T+1 | 部署后：集成测试（TC-BE-LT-001~003 + TC-API-001/002） | 0.2 人天 | 测试 |
| T+2 | 部署后：E2E 测试（TC-E2E-001~009） | 0.3 人天 | 测试 |
| T+2 | 回归测试：报告 40 条用例全部回归 | 0.3 人天 | 测试 |
| T+3 | 报告输出：测试报告 + 截图归档 | 0.1 人天 | 测试 |
| **合计** | — | **1.4 人天** | — |

### 7.2 准入准出标准

**准入**（开始测试的前置条件）：
- ✅ 4 个文件修复已提交到 main
- ✅ Render 部署状态显示 "Live"
- ✅ 本地单测全部通过

**准出**（测试完成的标志）：
- ✅ P0 用例 100% 通过
- ✅ P1 用例 ≥ 90% 通过
- ✅ 总通过率 ≥ 90%
- ✅ 无 P0 阻断性 Bug
- ✅ 测试报告已输出

### 7.3 缺陷升级流程

| 严重程度 | 处理时长 | 升级路径 |
|---------|---------|---------|
| 🔴 P0 阻断 | < 1 小时 | 测试 → 开发负责人 → 架构师 |
| 🟡 P1 一般 | < 4 小时 | 测试 → 开发负责人 |
| 🟢 P2 轻微 | < 1 天 | 测试 → 下个 Sprint |

---

## 8. 测试报告模板

### 8.1 报告输出要求

测试完成后，输出 Markdown 报告，包含以下内容：

```markdown
# 归因模板模块 v2.0.1 回归测试报告

## 测试摘要
- 测试时间：2026-10-XX
- 测试环境：Production (https://gac-chat-bi.onrender.com)
- 测试人：XXX
- 通过率：XX% (XX/40)
- P0 通过率：100% (8/8)

## Bug 修复验证
| Bug | 状态 | 验证方式 | 备注 |
|-----|------|---------|------|
| BUG-001 | ✅ 已修复 | E2E TC-E2E-001/002 | 5 模板全通过 |
| BUG-002 | ✅ 已修复 | E2E TC-E2E-003/004/005 | 我的模板正常显示 |
| BUG-003 | ✅ 已修复 | E2E TC-E2E-007/008 | 4 角色默认全不同 |
| BUG-004 | ✅ 已修复 | E2E TC-E2E-009 | 引导不重复弹 |

## 用例结果
- 单元测试：XX / XX 通过
- 集成测试：XX / XX 通过
- E2E 测试：XX / XX 通过
- 手工验证：XX / XX 通过

## 失败用例（如有）
### TC-XXX-XXX: XXX
- 现象：
- 截图：
- 根因：
- 修复建议：

## 截图归档
- [BUG-001 修复证据]（link）
- [BUG-002 修复证据]（link）
- ...

## 结论
- 修复质量：优秀 / 良好 / 一般
- 是否可以发布：是 / 否
- 建议：XXX
```

### 8.2 截图清单

| 截图编号 | 内容 | 用途 |
|---------|------|------|
| SC-01 | 5 个模板的"运行 SOP"执行报告页 | BUG-001 修复证据 |
| SC-02 | 新建模板后"我的模板"列表显示 | BUG-002 修复证据 |
| SC-03 | 克隆模板后编辑器页 + 列表显示 | BUG-002 修复证据 |
| SC-04 | 4 角色默认模板提示（含产品经理） | BUG-003 修复证据 |
| SC-05 | 关闭引导后刷新不弹出 | BUG-004 修复证据 |
| SC-06 | Network 请求中 Authorization 头 | BUG-002 修复证据 |
| SC-07 | curl 输出 HTTP/2 200 | BUG-001 修复证据 |

---

## 9. 附录

### 9.1 测试用例 → 报告用例映射表

| 本文档测试用例 | 测试报告原始用例 | 修复 Bug |
|-------------|----------------|---------|
| TC-E2E-001 | TC-TPL-026 | BUG-001 |
| TC-E2E-002 | TC-TPL-026~031 | BUG-001 |
| TC-E2E-003 | TC-TPL-010, 042~051 | BUG-002 |
| TC-E2E-004 | TC-TPL-023, 042 | BUG-002 |
| TC-E2E-005 | TC-TPL-046~047 | BUG-002 |
| TC-E2E-006 | TC-TPL-046 | BUG-002 |
| TC-E2E-007 | TC-TPL-036 | BUG-003 |
| TC-E2E-008 | TC-TPL-038 | BUG-003 |
| TC-E2E-009 | BUG-004 | BUG-004 |
| TC-MANUAL-001 | TC-TPL-031 | BUG-001 |
| TC-MANUAL-002 | TC-TPL-042 | BUG-002 |
| TC-MANUAL-003 | 全局 | 全部 |
| TC-BE-RD-003 | TC-TPL-038 | BUG-003 |
| TC-BE-LT-001~003 | TC-TPL-038 | BUG-003 |
| TC-API-001 | TC-TPL-036 | BUG-003 |
| TC-API-002 | TC-TPL-042 | BUG-002（根因验证） |
| TC-FE-LT-001~002 | TC-TPL-042 | BUG-002 |
| TC-FE-DT-002 | BUG-004 | BUG-004 |

### 9.2 测试工具栈

| 工具 | 用途 | 配置 |
|------|------|------|
| pytest | Python 后端单测 | `backend/tests/` |
| Vitest | TypeScript 前端单测 | `frontend/tests/` |
| Playwright | E2E 浏览器测试 | `frontend/tests/e2e/` |
| curl | HTTP 手工验证 | 系统自带 |
| Chrome DevTools | 浏览器端手工验证 | Chrome 100+ |

### 9.3 关键配置参考

**Playwright 配置**（`playwright.config.ts`）：
```typescript
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  use: {
    baseURL: process.env.BASE_URL || "https://gac-chat-bi.onrender.com",
    headless: true,
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
});
```

**pytest 配置**（`backend/pytest.ini`）：
```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
```

**Vitest 配置**（`frontend/vitest.config.ts`）：
```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
  },
});
```

---

## 10. 签字确认

| 角色 | 姓名 | 日期 | 备注 |
|------|------|------|------|
| 架构师 | （AI 自动生成） | 2026-10-18 | — |
| 测试负责人 | _待确认_ | _待定_ | 负责 E2E + 手工 |
| 开发代表 | _待确认_ | _待定_ | 负责单测 |
| QA Lead | _待确认_ | _待定_ | 负责报告签字 |

---

> **下一步**：本测试用例文档应与后端 SDD、前端 SDD 同步实施。开发完成后，按 §7.1 顺序执行测试。
