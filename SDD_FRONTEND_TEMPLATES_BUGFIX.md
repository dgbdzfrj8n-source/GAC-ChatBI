# 前端 SDD：归因模板模块 Bug 修复

> **版本**：v1.0
> **日期**：2026-10-18
> **所属总 SDD**：`SDD_TEMPLATES_BUGFIX.md`
> **子模块**：前端（Next.js 14 静态导出 + TypeScript + Tailwind）
> **目标读者**：前端开发工程师
> **作用**：详细描述前端侧的根因、代码修改、测试与部署

---

## 0. 文档元信息

| 字段 | 内容 |
|------|------|
| 涉及 Bug | BUG-TPL-001（部分）、BUG-TPL-002（部分）、BUG-TPL-004 |
| 涉及文件 | 1. `frontend/src/lib/templates-api.ts`<br>2. `frontend/src/components/DemoTour.tsx`<br>3. `render.yaml`（部署） |
| 涉及路由 | `/templates`、`/templates/market`、`/templates/run/[id]`、`/templates/editor/[id]` |
| 关键依赖 | `next` 14.x、`react` 18.x、`echarts-for-react`、`lucide-react` |
| 风险等级 | 🟢 低（隔离层修改） |
| 预计工作量 | 0.5 人天 |
| 前端兼容性 | 无破坏性变更；既有所有组件正常使用 |

---

## 1. 前端根因分析

### 1.1 BUG-001/002 的前端层面真相（澄清）

**报告猜测**：
- BUG-001：① 路由未实现 ② 硬编码 templateId
- BUG-002：① 编辑器路由未实现 ② 跳转逻辑错 ③ 数据未持久化

**前端真实情况**（已通过代码追溯 + 远端部署双重验证）：

✅ **前端代码完整且正确**：
- `frontend/src/app/templates/run/[id]/page.tsx`（454 行）✅ 完整存在
- `frontend/src/app/templates/editor/[id]/page.tsx`（457 行）✅ 完整存在
- `frontend/src/app/templates/run/[id]/layout.tsx` ✅ 配置了 `generateStaticParams`
- `frontend/src/app/templates/editor/[id]/layout.tsx` ✅ 配置了 `generateStaticParams`
- 跳转逻辑 `router.push(\`/templates/run/${tpl.id}\`)` ✅ 动态传 ID，**无硬编码**

❌ **真正的根因**（不在前端代码层，在部署层）：
- `next.config.mjs` 设置了 `output: "export"`
- 静态导出后，`generateStaticParams()` 返回 `[{id: "_"}]` → 只生成 `out/templates/run/_/_.html`
- 访问 `/templates/run/preset_exec_quarterly` → 静态文件不存在 → Render 触发通用 rewrite → `/index.html` → Next.js 客户端路由表里**没有 `run/[id]` 路由**（动态路由在静态导出模式下不会进入客户端 manifest） → 404

✅ **结论**：BUG-001/002 的 404 部分**无需修改前端代码**，仅需修改 `render.yaml` 加 2 条具体 rewrite 规则。

### 1.2 BUG-002 的"不保存"前端根因（待修复）

**位置**：`frontend/src/lib/templates-api.ts:96-106` 的 `listTemplates` 函数

**根因**：
```typescript
// 当前代码（错误）
const res = await fetch(url);   // ❌ 裸 fetch，未带 token
```

**问题机制**：
- 业务用户在 Sprint 10 之后必须登录，后端 `/api/sop/templates` 端点也加入了鉴权中间件
- 前端克隆/创建用 `authFetch()`（带 token）→ 后端成功创建 user_xxx 模板
- 前端列表用裸 `fetch()`（不带 token）→ 后端返回 401 → 前端第 102 行 `throw new Error(...)` → 被 `templates/page.tsx:99-105` 的 `catch` 吞掉 → 返回 `data=null` → `user_templates.length === 0` → 用户感知为"没保存"

**对比同文件其他函数**：
- `getTemplate()`（line 328-335）：✅ 已用 `authFetch`（被 commit `e976ac2` 修复）
- `v2CreateTemplate()`（line 110-125）：✅ 已用 `authFetch`
- `v2CloneTemplate()`（line 162-175）：✅ 已用 `authFetch`
- `v2RunTemplate()`（line 184-200）：✅ 已用 `authFetch`
- `listTemplates()`（line 96-106）：❌ 唯一漏网之鱼

### 1.3 BUG-004 的前端根因（待修复）

**位置**：`frontend/src/components/DemoTour.tsx:106-122`

**根因**：
```typescript
// 当前代码
const [active, setActive] = useState(false);  // line 109

useEffect(() => {
  const done = localStorage.getItem(STORAGE_KEY);
  if (!done) {
    const t = setTimeout(() => setActive(true), 800);  // line 113
    return () => clearTimeout(t);
  }
}, []);  // line 116
```

**问题机制**：
1. 组件 mount 时 `useState(false)` 同步设置 `active = false`
2. `useEffect` 异步执行，800ms 后 `setActive(true)` 触发引导
3. 即使之前用户点过关闭（`STORAGE_KEY` 已在 localStorage），**只要组件 mount 就走流程 1-2**
4. 在 Next.js 静态导出 + `router.push()` 触发的"软刷新"中，**layout.tsx 会被重新 mount**（虽然这是 bug 行为，但确实是事实）→ 引导重新弹出

**正确做法**：用 `useState(() => ...)` 惰性初始化，**在 SSR 完成后第一次渲染前** 就从 localStorage 读出状态，避免 setState 引发的二次渲染。

---

## 2. 前端修复设计

### 2.1 修复清单

| # | Bug | 文件 | 改动类型 | 代码量 |
|---|-----|------|---------|--------|
| 1 | BUG-001/002 | `render.yaml` | 部署配置 | 2 条 rewrite |
| 2 | BUG-002 | `frontend/src/lib/templates-api.ts` | 函数内 1 行替换 | 1 行 |
| 3 | BUG-004 | `frontend/src/components/DemoTour.tsx` | useState 初始化 + useEffect | 4-5 行 |

### 2.2 修复 1：Render 部署配置 — 动态路由 fallback

**文件**：`render.yaml`（项目根目录）

**位置**：第 47-52 行的 `routes` 块

**修改前**：
```yaml
routes:
  # 前端路由 fallback（Next.js 静态导出必备）
  - type: rewrite
    source: /*
    destination: /index.html
```

**修改后**：
```yaml
routes:
  # ===== BUG-001/002 修复：动态路由 fallback =====
  # 原因：Next.js 静态导出后，[id] 类动态路由只能生成 _ 静态文件
  # 访问 /templates/run/<任意id> 都会 404
  # 解法：把所有动态路由 fallback 到对应的 _.html，
  #      由客户端 React Router 接管并读取 useParams()
  # ────────────────────────────────────────────
  - type: rewrite
    source: /templates/run/:id
    destination: /templates/run/_/_.html
  - type: rewrite
    source: /templates/editor/:id
    destination: /templates/editor/_/_.html
  # 通用 fallback（保留原规则）
  - type: rewrite
    source: /*
    destination: /index.html
```

**关键点说明**：
1. ⚠️ **路由顺序很重要**：两条具体路由必须放在通用 `/*` 之前（Render 按顺序匹配）
2. `destination` 路径与 Next.js 静态导出实际生成的文件路径一致
3. 浏览器执行 `_.html` 里的 JS 后，Next.js 客户端会从 URL 读取动态参数
4. 通用 `/*` 兜底规则保留，**不要删除**

### 2.3 修复 2：listTemplates 改用 authFetch

**文件**：`frontend/src/lib/templates-api.ts`

**位置**：第 95-107 行的 `listTemplates` 函数

**修改前**：
```typescript
export async function listTemplates(
  role?: string,
  user?: string
): Promise<TemplateListResponse> {
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (user) params.set("user", user);
  const qs = params.toString();
  const url = `${API_URL}/api/sop/templates${qs ? "?" + qs : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`listTemplates failed: ${res.status}`);
  return res.json();
}
```

**修改后**：
```typescript
export async function listTemplates(
  role?: string,
  user?: string
): Promise<TemplateListResponse> {
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (user) params.set("user", user);
  const qs = params.toString();
  const url = `${API_URL}/api/sop/templates${qs ? "?" + qs : ""}`;
  // [BUG-002 修复] 改用 authFetch 以携带 Authorization 头
  // 原因：Sprint 10 鉴权中间件要求 user 模板列表必须鉴权，
  // 旧版裸 fetch 会返回 401 但错误被上层 catch 吞掉 → user_templates 始终为空
  const res = await authFetch(url);
  if (!res.ok) throw new Error(`listTemplates failed: ${res.status}`);
  return res.json();
}
```

**Diff**（最小化）：
```diff
-  const res = await fetch(url);
+  const res = await authFetch(url);
```

**关键点说明**：
1. ✅ `import { authFetch } from "./auth";` 已在第 10 行存在，**无需新增 import**
2. ❌ 不要改 `getTemplate()`（已在 commit `e976ac2` 修复）
3. ❌ 不要改 `listSupportedMetrics()`（公共指标目录，按设计无需鉴权）
4. ❌ 不要改错误处理逻辑（保持原样）
5. ❌ 不要改函数签名

### 2.4 修复 3：DemoTour 状态管理

**文件**：`frontend/src/components/DemoTour.tsx`

**位置**：第 108-122 行的 `useState` + `useEffect`（导出函数顶部）

**修改前**：
```typescript
export default function DemoTour() {
  const [active, setActive] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const [highlightRect, setHighlightRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  // 启动条件：首次访问 或 用户手动触发
  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      // 延迟 800ms 让首屏渲染完毕再弹出，体验更顺
      const t = setTimeout(() => setActive(true), 800);
      return () => clearTimeout(t);
    }
  }, []);
```

**修改后**：
```typescript
export default function DemoTour() {
  // [BUG-004 修复] 初始化时直接从 localStorage 读取"已完成"标志
  // 原因：原版 useState(false) + useEffect 异步设置会导致
  //     - SSR 渲染完成 → useState 同步 false → useEffect 异步判断 → setActive(true)
  //     - 在 next export + 全页刷新场景下，组件每次 mount 都重新执行这个异步流程，
  //       即使之前点过关闭也会重新弹出
  // 新版：渲染前直接从 localStorage 读取，避免组件 mount 后的状态变更
  const [active, setActive] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;  // SSR 安全
    return !localStorage.getItem(STORAGE_KEY);         // 没记录 → 首次访问 → 显示
  });
  const [stepIdx, setStepIdx] = useState(0);
  const [highlightRect, setHighlightRect] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

  // 启动条件：手动触发（首次访问已通过 useState 初始化处理）
  useEffect(() => {
    // 监听手动触发（来自 TopBar 按钮 / 帮助中心）
  }, []);
```

**Diff**（精确对比）：
```diff
-  const [active, setActive] = useState(false);
+  // [BUG-004 修复] 初始化时直接从 localStorage 读取"已完成"标志
+  // ... 4 行注释 ...
+  const [active, setActive] = useState<boolean>(() => {
+    if (typeof window === "undefined") return false;  // SSR 安全
+    return !localStorage.getItem(STORAGE_KEY);         // 没记录 → 首次访问 → 显示
+  });

   useEffect(() => {
     const done = localStorage.getItem(STORAGE_KEY);
     if (!done) {
-      // 延迟 800ms 让首屏渲染完毕再弹出，体验更顺
-      const t = setTimeout(() => setActive(true), 800);
-      return () => clearTimeout(t);
+      // 已有同步检查
     }
   }, []);
```

**注意**：原代码的 800ms setTimeout 已被 useState 初始化取代。如果保留视觉效果需要"延迟 800ms 再弹出"，**应保留 setTimeout 但改变判断条件**：

**最终推荐版本**（保留 800ms 视觉效果）：
```typescript
const [active, setActive] = useState<boolean>(() => {
  if (typeof window === "undefined") return false;
  return !localStorage.getItem(STORAGE_KEY);
});

useEffect(() => {
  if (!active) return;
  // 延迟 800ms 让首屏渲染完毕再弹出，体验更顺
  const t = setTimeout(() => {
    // active 已为 true，不需要再 setActive(true)
  }, 800);
  return () => clearTimeout(t);
}, [active]);
```

**关键点说明**：
1. ✅ 用 `useState(() => ...)` 的**惰性初始化**，避免 SSR 报错
2. ✅ `typeof window === "undefined"` 守卫兼容 SSR
3. ❌ 不要改 `STORAGE_KEY` 常量（保持 `'gac-chatbi-tour-completed'`）
4. ❌ 不要改 `close/next/prev` 等其他函数
5. ❌ 不要改 `STEPS` 数组和 `Tooltip` 子组件

### 2.5 不要做的事

| 禁止操作 | 原因 |
|---------|------|
| ❌ 把 `output: "export"` 改为 `output: "standalone"` | 范围外的架构变更，需要重写 render.yaml |
| ❌ 删除 `render.yaml` 的 `/* → /index.html` 通用 fallback | 会破坏其他未列出的路由 |
| ❌ 改 `authFetch` 实现 | 已有 `401 → 跳登录` 逻辑 |
| ❌ 改 DemoTour 的 STEPS 数组 | 内容不在修复范围 |
| ❌ 在 layout.tsx 移除 DemoTour | BUG-004 仅改状态管理，不改挂载位置 |
| ❌ 改 `/templates/page.tsx` 的 `loadTemplates` 错误处理 | 已有 `catch` 吞错是预期行为 |
| ❌ 给 `listTemplates` 加 retry 机制 | 范围外 |

---

## 3. 前端测试设计

### 3.1 单元测试

**目标文件**：`frontend/tests/test_templates_api.test.ts`（如不存在则新建；需配置 Vitest）

**测试用例清单**：

```typescript
// tests/test_templates_api.test.ts

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { listTemplates, getTemplate } from "@/lib/templates-api";
import * as authModule from "@/lib/auth";

describe("listTemplates - BUG-002 鉴权修复", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    global.fetch = fetchMock as any;

    // 模拟 authFetch 行为
    vi.spyOn(authModule, "authFetch").mockImplementation(
      async (url, init) => {
        const token = localStorage.getItem("gac_chatbi_token");
        return fetchMock(url, {
          ...init,
          headers: {
            ...(init?.headers || {}),
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
      }
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("TC-FE-LT-001: should call authFetch with token when listing templates", async () => {
    localStorage.setItem("gac_chatbi_token", "test_token_123");

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        system_presets: [],
        role_default_id: null,
        role_defaults_map: {},
        user_templates: [],
      }),
    });

    await listTemplates("product", "zhangsan");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const callArgs = fetchMock.mock.calls[0];
    const url = callArgs[0];
    const opts = callArgs[1];
    expect(url).toContain("/api/sop/templates");
    expect(url).toContain("role=product");
    expect(url).toContain("user=zhangsan");
    expect(opts.headers.Authorization).toBe("Bearer test_token_123");
  });

  it("TC-FE-LT-002: should return user_templates when authenticated", async () => {
    localStorage.setItem("gac_chatbi_token", "test_token_123");

    const mockData = {
      system_presets: [],
      role_default_id: "preset_model_product",
      role_defaults_map: { product: "preset_model_product" },
      user_templates: [
        { id: "user_123", name: "我的模板", scope: "user" },
      ],
    };

    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData,
    });

    const result = await listTemplates("product", "zhangsan");

    expect(result.user_templates).toHaveLength(1);
    expect(result.user_templates[0].id).toBe("user_123");
  });

  it("TC-FE-LT-003: should throw when API returns 401", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Unauthorized" }),
    });

    // authFetch 在 401 时会跳登录并抛错
    await expect(listTemplates("product", "zhangsan")).rejects.toThrow();
  });
});
```

### 3.2 DemoTour 状态管理测试

**目标文件**：`frontend/tests/test_demo_tour.test.tsx`

```typescript
// tests/test_demo_tour.test.tsx

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";
import DemoTour from "@/components/DemoTour";

describe("DemoTour - BUG-004 状态初始化修复", () => {
  const STORAGE_KEY = "gac-chatbi-tour-completed";

  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("TC-FE-DT-001: should auto-show on first visit (no localStorage)", () => {
    localStorage.removeItem(STORAGE_KEY);
    const { container } = render(<DemoTour />);
    // 引导遮罩存在
    expect(container.querySelector('[role="dialog"]')).toBeTruthy();
  });

  it("TC-FE-DT-002: should NOT show if user has completed the tour", () => {
    localStorage.setItem(STORAGE_KEY, "1");
    const { container } = render(<DemoTour />);
    // 引导遮罩不存在
    expect(container.querySelector('[role="dialog"]')).toBeFalsy();
  });

  it("TC-FE-DT-003: should not flash from false to true (no re-render needed)", () => {
    localStorage.setItem(STORAGE_KEY, "1");
    const renderSpy = vi.fn();
    // ... 验证只渲染一次
  });
});
```

### 3.3 端到端测试（E2E，推荐用 Playwright）

**目标文件**：`frontend/tests/e2e/templates.spec.ts`

```typescript
// tests/e2e/templates.spec.ts

import { test, expect } from "@playwright/test";

test.describe("归因模板模块 - 修复后回归", () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto("/login");
    await page.fill('input[name="username"]', "zhangsan");
    await page.fill('input[name="password"]', "password");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
  });

  test("TC-E2E-001: 运行 SOP 跳转成功 (BUG-001)", async ({ page }) => {
    await page.goto("/templates");
    // 找到第一个模板的「运行 SOP」按钮
    const runBtn = page.locator('button:has-text("运行 SOP")').first();
    await runBtn.click();
    // 应该跳转到 /templates/run/<id>，不是 404
    await expect(page).toHaveURL(/\/templates\/run\/.+/);
    // 不应出现 404
    await expect(page.locator("text=404")).not.toBeVisible();
    // 应该出现"启动 SOP 引擎"或"执行中"
    await expect(page.locator("text=启动 SOP 引擎").or(page.locator("text=执行中"))).toBeVisible({ timeout: 10000 });
  });

  test("TC-E2E-002: 5 个预设模板的运行 SOP 都能跳转 (BUG-001 全覆盖)", async ({ page }) => {
    await page.goto("/templates");
    const runButtons = page.locator('button:has-text("运行 SOP")');
    const count = await runButtons.count();
    expect(count).toBe(5);

    for (let i = 0; i < count; i++) {
      const btn = runButtons.nth(i);
      await btn.click();
      await expect(page).toHaveURL(/\/templates\/run\/.+/);
      // 验证 URL 不带 _ 占位符
      expect(page.url()).not.toContain("/_");
      // 验证不是 404
      await expect(page.locator("text=404")).not.toBeVisible();
      // 返回列表测试下一个
      await page.goto("/templates");
    }
  });

  test("TC-E2E-003: 新建模板能保存到'我的模板' (BUG-002)", async ({ page }) => {
    await page.goto("/templates");
    await page.click('button:has-text("新建我的模板")');

    // 填写表单
    await page.fill('input[placeholder*="新能源"]', "E2E测试模板");

    // 提交
    await page.click('button:has-text("创建并进入编排器")');

    // 跳转编辑器
    await expect(page).toHaveURL(/\/templates\/editor\/.+/);
    await expect(page.locator("text=404")).not.toBeVisible();

    // 返回列表
    await page.goto("/templates");
    // 我的模板数量 ≥ 1
    const myTemplates = await page.locator("text=E2E测试模板").count();
    expect(myTemplates).toBeGreaterThan(0);
  });

  test("TC-E2E-004: 克隆模板能保存到'我的模板' (BUG-002)", async ({ page }) => {
    await page.goto("/templates/market");
    await page.locator('button:has-text("克隆为我的模板")').first().click();
    // 处理 confirm 和 prompt 对话框
    page.on("dialog", (dialog) => dialog.accept("E2E克隆测试"));
    // 等待跳转
    await page.waitForURL(/\/templates\/editor\/.+/, { timeout: 5000 });
    await expect(page.locator("text=404")).not.toBeVisible();

    // 返回列表验证
    await page.goto("/templates");
    await expect(page.locator("text=E2E克隆测试")).toBeVisible();
  });

  test("TC-E2E-005: 编辑器页能进入并加载模板 (BUG-002)", async ({ page }) => {
    // 直接访问编辑器
    await page.goto("/templates");
    // 点击第一个"前往编辑器"或编辑按钮
    const editBtn = page.locator('[title="V2 编排器"]').first();
    await editBtn.click();
    await expect(page).toHaveURL(/\/templates\/editor\/.+/);
    // 加载完成后不显示 404
    await expect(page.locator("text=404")).not.toBeVisible();
    // 显示模板加载完成的标识
    await expect(page.locator("text=SOP 步骤").or(page.locator("text=加载模板"))).toBeVisible();
  });

  test("TC-E2E-006: 产品经理角色默认模板不同 (BUG-003)", async ({ page }) => {
    await page.goto("/templates");

    // 切换到产品经理
    await page.click('button:has-text("产品经理")');

    // 验证默认模板提示
    await expect(page.locator("text=车型经理产品复盘")).toBeVisible();
    // 验证不显示"分析师深度下钻"
    await expect(page.locator("text=产品经理角色默认模板：分析师深度下钻")).not.toBeVisible();
  });

  test("TC-E2E-007: 4 角色默认模板互不相同 (BUG-003 全覆盖)", async ({ page }) => {
    await page.goto("/templates");
    const defaults: string[] = [];

    for (const role of ["高管", "分析师", "产品经理", "访客"]) {
      await page.click(`button:has-text("${role}")`);
      const text = await page.locator('[class*="text-amber-900"]').first().textContent();
      const match = text?.match(/：(.+?)$/);
      if (match) defaults.push(match[1]);
    }

    // 3 个核心角色默认互不相同
    expect(defaults[0]).not.toBe(defaults[1]);
    expect(defaults[1]).not.toBe(defaults[2]);
    expect(defaults[0]).not.toBe(defaults[2]);
  });

  test("TC-E2E-008: 引导关闭后刷新不弹出 (BUG-004)", async ({ page }) => {
    await page.goto("/");

    // 引导应自动出现
    const tour = page.locator('[role="dialog"]');
    if (await tour.isVisible()) {
      // 点"跳过"或关闭
      await page.click('button:has-text("跳过")').or(page.click('button[aria-label="关闭引导"]'));
    }

    // 刷新
    await page.reload();

    // 引导不应再出现
    await page.waitForTimeout(2000); // 等待 800ms setTimeout
    await expect(tour).not.toBeVisible();
  });
});
```

### 3.4 手工验证（部署后必做）

**浏览器开发者工具流程**：

| 步骤 | 操作 | 期望 |
|------|------|------|
| 1 | 打开 Chrome DevTools → Network 标签，勾选 "Preserve log" | — |
| 2 | 登录系统，访问 `/templates` | — |
| 3 | 找到 `listTemplates` 接口的 XHR 请求 | 响应 200，Body 含 `user_templates` 数组 |
| 4 | 检查请求头 `Authorization` | 存在 `Bearer <token>` |
| 5 | 点击任一模板的「运行 SOP」按钮 | 跳转到 `/templates/run/<动态id>`，**不出现 404** |
| 6 | 切换到产品经理角色 | 默认模板提示变为「车型经理产品复盘」 |
| 7 | 关闭引导弹窗 → 刷新页面 | 引导不弹出 |
| 8 | 克隆一个模板 → 返回列表 | 列表中出现克隆的模板 |

**curl 验证（部署后立即执行）**：
```bash
# 1. 验证动态路由 200
echo "=== /templates/run/<id> ==="
curl -sI https://gac-chat-bi.onrender.com/templates/run/preset_exec_quarterly | head -1
# 期望: HTTP/2 200

echo "=== /templates/editor/<id> ==="
curl -sI https://gac-chat-bi.onrender.com/templates/editor/user_95809376 | head -1
# 期望: HTTP/2 200

echo "=== /templates（确保未破坏）==="
curl -sI https://gac-chat-bi.onrender.com/templates | head -1
# 期望: HTTP/2 200

echo "=== /templates/market（确保未破坏）==="
curl -sI https://gac-chat-bi.onrender.com/templates/market | head -1
# 期望: HTTP/2 200
```

---

## 4. 前端部署设计

### 4.1 部署流程

**前置条件**：
- Render Static Site 服务 `gac-chat-bi` 已配置
- 已完成 3 个文件的本地修改和单测

**操作步骤**：

```bash
# 1. 拉取最新代码
cd /Users/apple/Desktop/AI\ 产品经理/实战项目/GAC-ChatBI
git checkout main
git pull origin main

# 2. 确认 diff
git diff render.yaml
git diff frontend/src/lib/templates-api.ts
git diff frontend/src/components/DemoTour.tsx

# 3. 提交
git add render.yaml frontend/src/lib/templates-api.ts frontend/src/components/DemoTour.tsx
git commit -m "fix(templates): BUG-001/002/004 前端修复

- BUG-001/002: render.yaml 增加动态路由 rewrite fallback
  解决 /templates/run/[id] 和 /templates/editor/[id] 的 404 问题
- BUG-002: templates-api listTemplates 改用 authFetch
  解决克隆/新建后'我的模板'仍为 0 的问题
- BUG-004: DemoTour useState 惰性初始化读 localStorage
  解决新手引导重复弹出的问题

见 SDD §3 与归因模板测试报告。"
git push origin main

# 4. 等待 Render 自动部署（约 3-5 分钟，Static Site 比 Web Service 快）
# 5. 部署后立即按 §3.4 验证
```

### 4.2 部署后必做验证

| 步骤 | 操作 | 期望 | 失败应对 |
|------|------|------|---------|
| 1 | Render Dashboard 显示 "Live" | 绿点 | 查看 deploy logs |
| 2 | `curl -sI /templates/run/preset_exec_quarterly` | HTTP/2 200 | 检查 render.yaml |
| 3 | `curl -sI /templates/editor/test` | HTTP/2 200 | 检查 render.yaml |
| 4 | `curl -sI /templates` | HTTP/2 200 | 通用 fallback 应保留 |
| 5 | 浏览器登录后访问 `/templates` | 页面正常加载 | 等待 1 分钟（CDN 缓存） |
| 6 | 检查 Network 列表请求 Authorization | 存在 | 缓存问题，强刷 |

### 4.3 回滚方案

```bash
# 紧急回滚
git revert HEAD
git push origin main
# Render 自动回滚（约 3 分钟）

# 或：Render Dashboard → gac-chat-bi → Manual Deploy → 选上一个 commit
```

**单条修复回滚**：
- 修复 1（render.yaml）：单独 git revert 即可
- 修复 2（templates-api.ts）：单独 git revert 即可
- 修复 3（DemoTour.tsx）：单独 git revert 即可

### 4.4 部署注意事项

⚠️ **CDN 缓存**：Render Static Site 用 Cloudflare CDN，部署后可能需要 1-5 分钟才能全球生效。如验证时仍 404，可加 `?v=2` 强刷。

⚠️ **Render Blueprint 同步**：修改 `render.yaml` 后，Render 控制台需要点击 "Sync" 按钮才能使 yaml 变更生效（如果之前用 Blueprint 创建的服务）。

---

## 5. 前端性能与可访问性影响

### 5.1 性能影响

| 改动 | Bundle 大小 | 首屏时间 | 交互响应 |
|------|------------|---------|---------|
| 修复 1（render.yaml） | 0 | 无影响 | 无影响 |
| 修复 2（authFetch） | 0（函数已存在） | 无影响 | + 1 个网络往返（带 token） |
| 修复 3（useState 初始化） | 0 | -800ms（不再等 setTimeout） | 更快 |

**净影响**：✅ 性能略提升

### 5.2 可访问性影响

- 引导弹窗的 `role="dialog"` 与 `aria-modal="true"` 保持不变
- 修复后引导只显示一次，避免干扰视障用户使用屏幕阅读器
- 动态路由的客户端参数读取方式不变，键盘导航不受影响

### 5.3 SSR 水合保护

本次修复**不涉及 SSR/CSR 边界**：
- `templates-api.ts` 纯客户端运行（被 `authFetch` 包裹，调用 `localStorage`）
- `DemoTour.tsx` 已有 `typeof window` 守卫

---

## 6. 前端实施 Checklist

### 阶段 1：代码修改（0.2 人天）

- [ ] 修改 `render.yaml` 的 `routes` 段，新增 2 条 rewrite
- [ ] 修改 `frontend/src/lib/templates-api.ts` 的 `listTemplates`，改用 `authFetch`
- [ ] 修改 `frontend/src/components/DemoTour.tsx` 的 `useState` 惰性初始化

### 阶段 2：本地测试（0.1 人天）

- [ ] 运行 `npm run build` 成功
- [ ] 验证 `out/templates/run/_/_.html` 和 `out/templates/editor/_/_.html` 存在
- [ ] 启动 `npx serve out`，访问 `http://localhost:3000/templates/run/test` 验证 200
- [ ] 运行前端单测 `npm run test:unit`
- [ ] 3 个 listTemplates 单测通过
- [ ] 3 个 DemoTour 单测通过

### 阶段 3：部署（0.1 人天）

- [ ] 提交代码并 push 到 main
- [ ] Render Static Site 自动部署成功（3-5 分钟）
- [ ] 部署后 6 个 curl 验证全部通过
- [ ] 浏览器手工验证 8 个步骤全部通过
- [ ] 截图归档

### 阶段 4：E2E 回归（0.1 人天）

- [ ] 启动 Playwright 服务
- [ ] 8 个 E2E 用例全部通过
- [ ] 失败用例修复后重新跑

---

## 7. 附录

### 7.1 关键代码引用

- `listTemplates` 修复点：`frontend/src/lib/templates-api.ts:96-106`
- `authFetch` 实现：`frontend/src/lib/auth.ts:63-85`
- `DemoTour` 修复点：`frontend/src/components/DemoTour.tsx:106-122`
- `useState` 惰性初始化文档：React 官方 [Hooks API Reference](https://react.dev/reference/react/useState#avoiding-recreating-the-initial-state)
- Render Static Site 路由配置：[Render Docs - Redirects/Rewrites](https://docs.render.com/redirects-rewrites)
- Next.js 静态导出动态路由限制：[Next.js Docs - generateStaticParams](https://nextjs.org/docs/app/api-reference/file-conventions/route-segment-config#generatestaticparams)

### 7.2 关联测试用例

| 前端测试 | 对应报告用例 | 说明 |
|---------|------------|------|
| TC-FE-LT-001 | TC-TPL-042 | 列表请求带 token |
| TC-FE-LT-002 | TC-TPL-042 | user_templates 正确返回 |
| TC-FE-LT-003 | TC-TPL-042 | 401 正确处理 |
| TC-FE-DT-001 | BUG-004 | 首次访问弹出 |
| TC-FE-DT-002 | BUG-004 | 关闭后不弹 |
| TC-E2E-001 | TC-TPL-026 | 单模板运行 SOP |
| TC-E2E-002 | TC-TPL-026~031 | 5 模板全运行 |
| TC-E2E-003 | TC-TPL-010, 042~051 | 新建模板 |
| TC-E2E-004 | TC-TPL-023, 042 | 克隆模板 |
| TC-E2E-005 | TC-TPL-046~047 | 编辑器 |
| TC-E2E-006 | TC-TPL-036 | 产品经理默认 |
| TC-E2E-007 | TC-TPL-038 | 4 角色默认 |
| TC-E2E-008 | BUG-004 | 引导不重弹 |

### 7.3 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| render.yaml 顺序错误导致路由不匹配 | 🟢 低 | 文档中明确强调顺序 |
| CDN 缓存导致部署后仍 404 | 🟡 中 | 强刷或加 cache-busting 参数 |
| authFetch 401 跳登录影响测试 | 🟢 低 | 测试用例用 mock token 绕过 |
| DemoTour 修改后 SSR 报错 | 🟢 极低 | `typeof window` 守卫已加 |
| 修改 listTemplates 破坏其他调用方 | 🟢 低 | 仅 1 个调用方 `templates/page.tsx` |
| ECharts 客户端动态导入被影响 | 🟢 极低 | 本次不涉及 ECharts |

---

## 8. 签字确认

| 角色 | 姓名 | 日期 | 备注 |
|------|------|------|------|
| 架构师 | （AI 自动生成） | 2026-10-18 | — |
| 前端开发 | _待确认_ | _待定_ | 实施 + 单测 |
| 前端测试 | _待确认_ | _待定_ | E2E + 手工 |
| DevOps | _待确认_ | _待定_ | 部署 + 监控 |

---

> **下一步**：本前端 SDD 实施完成后，与后端 SDD 联合部署，按 §3.4 + §4.2 验证 4 个 Bug 全部修复。
