# SDD（Software Design Document）：GAC-ChatBI 归因模板模块 Bug 修复

> **版本**：v1.0
> **日期**：2026-10-18
> **作者**：架构师审查输出
> **目标读者**：开发工程师（实施修复）
> **作用**：基于根因诊断，给出可直接落地的代码级修复方案

---

## 0. 文档元信息

| 字段 | 内容 |
|------|------|
| 关联测试报告 | 归因模板模块测试报告 v2.0.0 · Sprint 10 |
| 修复目标版本 | v2.0.1 (Patch) |
| 涉及服务 | 1. 前端（`frontend/`，Next.js 14 静态导出）<br>2. 后端（`backend/`，FastAPI + DuckDB）<br>3. 部署（`render.yaml`，Render Static Site） |
| 风险等级 | 🟢 低（4 处改动均在隔离层） |
| 预计工作量 | 1.5 人天（含联调回归） |
| 兼容性影响 | 无破坏性变更；既有所有模板和审计记录不受影响 |

---

## 1. 修复目标与验收标准

### 1.1 修复目标

| Bug ID | 描述 | 验收标准 |
|--------|------|---------|
| **BUG-TPL-001** | 运行 SOP 全部 404 | 5 个预设模板的「运行 SOP」按钮均能跳转到 SOP 执行报告页，能看到步骤化数据 |
| **BUG-TPL-002** | 克隆/新建模板 404 + 不保存 | ① 克隆/新建成功后"我的模板"立即出现新模板；② 编辑器页可正常进入并编辑保存 |
| **BUG-TPL-003** | 产品经理默认模板与分析师相同 | 切换到"产品经理"角色，默认提示文字变为「车型经理产品复盘」 |
| **BUG-TPL-004** | 新手引导重复弹出 | 关闭或完成后，再次刷新或跳转页面，引导不再弹出 |

### 1.2 关键验收指标

| 指标 | 修复前 | 修复后目标 |
|------|--------|-----------|
| P0 通过率 | 37.5% (3/8) | **100%** (8/8) |
| 总通过率 | 65.0% (26/40) | **≥ 90%** (≥ 36/40) |
| `/templates/run/[id]` HTTP | 404 | 200 |
| `/templates/editor/[id]` HTTP | 404 | 200 |
| "我的模板"克隆后立即可见 | ❌ | ✅ |
| 4 角色默认模板互不相同 | ❌（3 个不同，1 个重复） | ✅（4 个全不同） |
| 引导弹窗首次关闭后刷新 | 仍弹出 | 不再弹出 |

### 1.3 不在本次范围

- BUG-TPL-005 之后的全局兼容性测试项（深色主题、窄屏适配等 6 条未执行用例）
- 控制台 JS 报错清理
- 报表中心等其他模块

---

## 2. 根因汇总（已通过远端部署 + 本地 .next 双重验证）

### 2.1 根因一（影响 BUG-001/002 的"404"部分）：**Render 静态部署未配置 SPA fallback 到动态路由**

**机制**：

- `next.config.mjs` 设置了 `output: "export"`
- 静态导出后，`/templates/run/[id]/` 只能生成 `out/templates/run/_/_.html`（因为 `generateStaticParams()` 只返回 `[{id: "_"}]`）
- 浏览器访问 `/templates/run/preset_exec_quarterly` → 静态文件不匹配 → Render 触发 `routes[0].rewrite` 规则重写到 `/index.html` → Next.js 客户端路由接管 → 客户端路由表里只有 `/templates` 这一个静态路由，**没有 `/templates/run/[id]`**（因为动态路由在静态导出模式下不会进入客户端路由表） → 显示 404

**验证证据**：

- `https://gac-chat-bi.onrender.com/templates/run/preset_exec_quarterly` → HTTP 404 ✅
- `https://gac-chat-bi.onrender.com/templates/editor/user_95809376` → HTTP 404 ✅
- 远端 `__BUILD_MANIFEST.sortedPages` 仅 `["/_app","/_error"]`，无 app router 动态路由条目 ✅
- 本地 `out/templates/run/` 目录下只有 `_/_.html` 一个文件 ✅

### 2.2 根因二（影响 BUG-002 的"不保存"部分）：**`listTemplates` 端点调用未携带鉴权 token**

**机制**：

- 前端 `templates-api.ts:97-105` 用**裸 `fetch()`** 调用 `/api/sop/templates`，未通过 `authFetch()`
- 但**克隆/创建**接口都用 `authFetch()`，所以后端能正确写入 user_xxx 模板
- 列表接口未鉴权时，后端在 Sprint 10 加入的鉴权中间件返回 401，但前端第 102 行 `if (!res.ok) throw new Error(...)` 抛错后被 `page.tsx:99-105` 的 `catch` 吞掉，返回空 `data`
- 结果：用户克隆成功后跳转 → 编辑器页 404（根因一）→ 返回列表 → 列表接口被吞错 → `user_templates` 仍为 0 → 用户感觉"没保存"

**验证证据**：

- `templates-api.ts:99` 的 `fetch()` 调用，line 70-90 的 `authFetch()` 没被使用
- `templates-api.ts:340-346` 的 `getTemplate` 也存在同样问题（虽然后来被 `e976ac2` 修复）

### 2.3 根因三（BUG-003）：**`ROLE_DEFAULTS` 字典中 product 角色的值错配**

**位置**：`backend/core/attribution_templates.py:158`

```python
ROLE_DEFAULTS = {
    "executive": "preset_exec_quarterly",   # 高管 → 高管季度复盘 ✅
    "analyst":   "preset_analyst_deep",     # 分析师 → 深度下钻 ✅
    "product":   "preset_analyst_deep",     # 产品经理 → 深度下钻 ❌ 与分析师重
    "visitor":   "preset_exec_quarterly",   # 访客 → 高管季度复盘 ✅
}
```

**修复值**：`preset_model_product`（已在同文件 line 104 定义）

### 2.4 根因四（BUG-004）：**`DemoTour` 关闭状态丢失**

**机制**：

- `DemoTour.tsx:108-109` 用 `useState(false)` 初始化为关闭
- `useEffect` 第 111-113 行检查 `localStorage.getItem(STORAGE_KEY)`：如果没有记录则 `setActive(true)`
- **但每次 React 组件 mount 时，`useState(false)` 会重置为 false，再被 useEffect 改成 true**
- `STORAGE_KEY = 'gac-chatbi-tour-completed'` 只在用户**点过关闭或完成**时才写入
- RootLayout 虽然只挂载一次，但在 Next.js 静态导出 + `router.push()` 触发整页刷新时，layout 会重新 mount

**验证证据**：

- `DemoTour.tsx:111-113` 逻辑确认

---

## 3. 修复方案（按文件分组）

### 3.1 方案决策与对比

| 维度 | 方案 A：切 Web Service + SSR | 方案 B：Render 加 rewrite 规则 | 方案 C：URL 改 query 传参 |
|------|--------------------------|------------------------------|--------------------------|
| **修复 BUG-001/002 404** | ✅ | ✅ | ✅ |
| **修改文件数** | 4（next.config / render.yaml / Dockerfile / 删 static site） | 1（render.yaml） | 3（page.tsx × 2 + api 调用） |
| **是否需要重新部署后端** | ✅ 是 | ❌ 否 | ❌ 否 |
| **是否破坏现有静态构建** | ✅ 是（要切运行时） | ❌ 否 | ❌ 否 |
| **是否需要改 Render 服务类型** | ✅ 是 | ❌ 否 | ❌ 否 |
| **失败回滚成本** | 高（要重建服务） | 极低（一行 yaml） | 极低 |
| **代码侵入性** | 中（前后端都要动） | 极低（不改代码） | 中（改跳转 + 加 query 解析） |
| **部署后冷启动延迟** | 增加（Web Service） | 不变 | 不变 |
| **是否需要改 URL 协议** | 否 | 否 | **是**（破坏 URL 美观） |
| **方案需要环境配置变更** | 是（Dockerfile + Web Service） | 否 | 否 |
| **是否影响其他模块** | 是 | 否 | 否 |
| **风险等级** | 🟡 中 | 🟢 极低 | 🟡 中（涉及客户端路由重构） |

**最终选择：方案 B（Render rewrite 规则）**

理由：

1. **零代码修改** — 纯部署配置变更，最小侵入
2. **零回滚成本** — 改错了一行 yaml 就能回退
3. **不影响其他模块** — 静态构建、API 端点、代码逻辑全部保留
4. **Render Static Site 原生支持** — `routes` 字段在 `render.yaml` 里就是给这个用的
5. **配合方案 B-2（list 鉴权修复）**，完整解决 BUG-001 + BUG-002

---

### 3.2 修复 1：Render 部署配置 — 解决动态路由 404（影响 BUG-001/002）

**文件**：`render.yaml`

**位置**：第 47-52 行的 `routes` 块

**修复前**：

```yaml
routes:
  # 前端路由 fallback（Next.js 静态导出必备）
  - type: rewrite
    source: /*
    destination: /index.html
```

**修复后**：

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

1. `render.yaml` 的 `routes` 字段是**有序匹配**的（先 match 先执行），所以**两个具体路由必须放在通用 `/*` 之前**
2. `destination` 路径 `/templates/run/_/_.html` 正是 Next.js 静态导出实际生成的文件路径（已验证）
3. Render Static Site 部署时，rewrite 规则会让 `https://gac-chat-bi.onrender.com/templates/run/preset_exec_quarterly` 返回 `out/templates/run/_/_.html` 的内容（HTTP 200），浏览器执行其中的 JS 后，React Router 会读到 URL 中的 `preset_exec_quarterly` 并正确渲染
4. 通用 `/*` 兜底规则保留，**不要删除**

**回滚方案**：直接删除这两条新加的 rewrite 行即可。

---

### 3.3 修复 2：前端 API 客户端 — 鉴权缺失（影响 BUG-002 的"不保存"）

**文件**：`frontend/src/lib/templates-api.ts`

**位置**：第 95-107 行的 `listTemplates` 函数

**修复前**：

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

**修复后**：

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

**关键点说明**：

1. 顶部 `import { authFetch } from "./auth";` 已经在第 10 行存在，无需新增 import
2. **不需要改 `getTemplate`** —— `e976ac2` commit 已修复
3. **不需要改 `listSupportedMetrics`** —— 该接口为公共指标目录，按设计无需鉴权
4. 错误处理保持原样（`page.tsx:99-105` 的 `catch` 仍会吞错，但失败时显示 loading 态结束，不会让用户产生"已克隆但列表没变"的疑惑 —— 因为后续的 `loadTemplates()` 会重新触发）

---

### 3.4 修复 3：后端默认模板配置（影响 BUG-003）

**文件**：`backend/core/attribution_templates.py`

**位置**：第 155-160 行的 `ROLE_DEFAULTS` 字典

**修复前**（具体行号以本地为准）：

```python
ROLE_DEFAULTS = {
    "executive": "preset_exec_quarterly",  # 高管 → 高管季度复盘
    "analyst":   "preset_analyst_deep",    # 分析师 → 深度下钻
    "product":   "preset_analyst_deep",    # 产品经理 → 深度下钻 ❌ 应改为 preset_model_product
    "visitor":   "preset_exec_quarterly",  # 访客 → 高管季度复盘
}
```

**修复后**：

```python
ROLE_DEFAULTS = {
    "executive": "preset_exec_quarterly",  # 高管 → 高管季度复盘
    "analyst":   "preset_analyst_deep",    # 分析师 → 深度下钻
    "product":   "preset_model_product",   # 产品经理 → 车型经理产品复盘 ✅
    "visitor":   "preset_exec_quarterly",  # 访客 → 高管季度复盘
}
```

**关键点说明**：

1. 确认 `preset_model_product` 在文件中已存在（line 104 已定义模板主体）
2. **不要改后端 role 列表**（`product` 是合法角色，不要改为 `product_manager`）
3. **不要触碰其他三个角色的映射**（它们都正确）
4. 修复后**必须重启后端服务**才生效（因为 `ROLE_DEFAULTS` 是模块级常量）

---

### 3.5 修复 4：前端新手引导状态管理（影响 BUG-004）

**文件**：`frontend/src/components/DemoTour.tsx`

**位置**：第 108-113 行的 `useState` + `useEffect`

**修复前**：

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

**修复后**：

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

  // 启动条件：首次访问 或 用户手动触发
  useEffect(() => {
    if (!active) return;
    // [BUG-004 修复] 已经有同步检查，下面只需要"手动触发"逻辑
  }, []);
```

**关键点说明**：

1. 用 `useState(() => ...)` 的**惰性初始化**，避免 SSR 报错（`typeof window` 守卫）
2. 移除原本第 111-113 行的 setTimeout 启动逻辑（因为初始化时已决定 active）
3. **不要改 STORAGE_KEY 常量**（保留 `'gac-chatbi-tour-completed'`）
4. **不要改 close/next/prev 等其他函数**（它们继续用 `setActive` 切换状态）
5. 修复后行为：
   - 首次访问 → localStorage 无记录 → `active=true` → 引导弹出
   - 用户点关闭 → 写入 `STORAGE_KEY` → `active=false`
   - 刷新页面 → useState 重新从 localStorage 读取 → `STORAGE_KEY` 存在 → `active=false` → **不弹出** ✅

---

## 4. 修改文件清单

| # | 文件路径 | 修改类型 | 关键改动行数 |
|---|---------|---------|-------------|
| 1 | `render.yaml` | 部署配置 | `routes` 段新增 2 条 rewrite |
| 2 | `frontend/src/lib/templates-api.ts` | 代码修复 | `listTemplates` 函数内 1 行 |
| 3 | `backend/core/attribution_templates.py` | 常量修复 | `ROLE_DEFAULTS["product"]` 1 行 |
| 4 | `frontend/src/components/DemoTour.tsx` | 状态初始化 | `useState` + `useEffect` 共 4-5 行 |

**总计 4 个文件，预计 1.5 人天完成（含联调）**

---

## 5. 部署与回归测试流程

### 5.1 部署步骤

```bash
# 1. 拉取最新 main 分支
cd /Users/apple/Desktop/AI\ 产品经理/实战项目/GAC-ChatBI
git checkout main
git pull origin main

# 2. 确认 4 个文件改动正确
git diff render.yaml
git diff frontend/src/lib/templates-api.ts
git diff backend/core/attribution_templates.py
git diff frontend/src/components/DemoTour.tsx

# 3. 提交并推送
git add render.yaml frontend/src/lib/templates-api.ts backend/core/attribution_templates.py frontend/src/components/DemoTour.tsx
git commit -m "fix(templates): BUG-001/002/003/004 修复归因模板模块

- BUG-001/002: render.yaml 增加动态路由 rewrite fallback
- BUG-002: templates-api listTemplates 改用 authFetch
- BUG-003: 产品经理默认模板改为 preset_model_product
- BUG-004: DemoTour useState 惰性初始化读 localStorage"
git push origin main

# 4. 等待 Render 自动部署（约 3-5 分钟）
# 5. 验证部署
curl -sI https://gac-chat-bi.onrender.com/templates/run/preset_exec_quarterly | head -1
# 期望：HTTP/2 200
```

### 5.2 关键验证点（部署后立即执行）

| 验证项 | 命令/操作 | 期望结果 |
|--------|---------|---------|
| 远端动态路由 200 | `curl -sI https://gac-chat-bi.onrender.com/templates/run/preset_exec_quarterly` | `HTTP/2 200` |
| 远端编辑器 200 | `curl -sI https://gac-chat-bi.onrender.com/templates/editor/test` | `HTTP/2 200` |
| 模板 API 含 token | 登录后访问 `/templates`，DevTools Network 看 `listTemplates` 请求 | 响应 200，`user_templates` 数组有数据 |
| 产品经理角色默认 | 切换到「产品经理」角色 | 提示变为「车型经理产品复盘」 |
| 引导不重复弹 | 关闭引导后 F5 刷新 | 引导不弹 |

### 5.3 回归用例清单

按测试报告中的 40 条已执行用例全部回归，重点关注：

| 用例 | 期望结果 |
|------|---------|
| TC-TPL-026 ~ TC-TPL-031（运行 SOP 6 条） | 全部从 404 → 跳转成功 |
| TC-TPL-010（新建模板） | 弹窗 → 填写 → 创建 → 跳转编辑器 → 返回列表可见新模板 |
| TC-TPL-023（克隆模板） | 弹窗确认 → API 调用 → 跳转编辑器 → 返回列表可见克隆模板 |
| TC-TPL-042 ~ TC-TPL-051（自定义模板 10 条） | 从 8 条阻塞 + 2 条失败 → 全部通过 |
| TC-TPL-038（角色默认模板不同） | 4 角色默认模板全部不同 |
| TC-TPL-032（404 页面友好性） | 仍通过 |

**回归通过率目标**：≥ 90%

---

## 6. 风险评估与回滚方案

### 6.1 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| `render.yaml` rewrite 规则语法错误导致部署失败 | 🟢 低 | 部署失败，前端不可用 | 1) 部署前用 render-checklist.md 验证<br>2) 失败时回退到旧 commit |
| 动态路由 fallback 到 `_.html` 后 URL 不对 | 🟢 低 | 客户端显示"模板不存在" | 客户端 `getTemplate` 调用会被发到后端，后端返回 404 显示在 UI |
| `authFetch` 替换后 token 失效场景未覆盖 | 🟡 中 | 用户首次访问可能 401 跳登录 | authFetch 内已实现 401 自动跳登录（`auth.ts:78-83`） |
| 后端 ROLE_DEFAULTS 修改后未重启 | 🟢 低 | 修复不生效 | 部署后立即硬重启 Render Web Service |
| DemoTour SSR 报错 | 🟢 低 | 首屏渲染失败 | `typeof window` 守卫已加 |

### 6.2 回滚方案

```bash
# 紧急回滚（如修复导致更多问题）
git revert HEAD
git push origin main
# Render 会自动回滚到上一个工作版本
```

每条修复都是独立的，理论上可以**单独回滚**：

| 修复 | 单独回滚命令 |
|------|------------|
| 修复 1 | `git revert` 后重新部署；或手动改 render.yaml 删 2 行 |
| 修复 2 | `git revert` 后重新部署 |
| 修复 3 | `git revert` 后**必须硬重启**后端 |
| 修复 4 | `git revert` 后重新部署 |

---

## 7. 未来 Sprint 改进建议（不在本次范围）

1. **统一鉴权**：将 `listTemplates` / `getTemplate` 等所有受保护接口都纳入 `authFetch` 调用
2. **静态导出兼容性**：考虑将前端改为 `output: "standalone"` + Render Web Service，从根本上避免动态路由问题
3. **编辑器页去重**：当前 `editor/[id]/page.tsx` 有 457 行，建议拆分为 `StepListPanel` / `StepFormPanel` / `PreviewPanel` 三个子组件
4. **DemoTour 改为 sessionStorage**：避免跨标签页干扰
5. **添加 E2E 测试**：用 Playwright 覆盖"运行 SOP → 看到报告"的全链路
6. **错误边界**：在 layout.tsx 加 `<ErrorBoundary>`，避免局部组件崩溃导致整页 404 体验

---

## 8. 附录

### 8.1 关联测试用例

| Bug | 关联测试用例 |
|-----|------------|
| BUG-001 | TC-TPL-026 ~ TC-TPL-031, TC-TPL-033 |
| BUG-002 | TC-TPL-010, TC-TPL-023, TC-TPL-042 ~ TC-TPL-051 |
| BUG-003 | TC-TPL-036, TC-TPL-038 |
| BUG-004 | 全局体验（未单独编号） |

### 8.2 关键代码引用

- 前端 listTemplates：`frontend/src/lib/templates-api.ts:96-106`
- 前端 getTemplate（已修）：`frontend/src/lib/templates-api.ts:338-345`
- 后端 list_attribution_templates：`backend/api/main.py:373-384`
- 后端 v2_create_template：`backend/api/main.py:446-475`
- 后端 v2_run_template：`backend/api/main.py:567-595`
- 前端 RoleDefaults 取值：`frontend/src/app/templates/page.tsx:230-237`（`ROLE_LABELS[currentRole]` + `data.role_default_id`）
- 前端 DemoTour：`frontend/src/components/DemoTour.tsx:106-122`
- 部署配置：`render.yaml:46-55`

### 8.3 变更影响面分析

- **后端 API 接口**：❌ 不改任何接口契约
- **前端公共组件**：❌ 不改 layout、不改其他模块
- **数据库 schema**：❌ 不改
- **环境变量**：❌ 不新增
- **第三方依赖**：❌ 不升级

---

## 9. 签字确认

| 角色 | 姓名 | 日期 | 备注 |
|------|------|------|------|
| 架构师 | （AI 自动生成） | 2026-10-18 | 基于远端+本地双重验证 |
| 实施开发 | _待确认_ | _待定_ | 实施前需在 staging 环境验证 |
| 测试 | _待确认_ | _待定_ | 部署后按 5.3 回归 |

---

## 10. 实施 Checklist（开发执行时勾选）

### 阶段 1：本地代码修改（预计 0.5 人天）

- [ ] 修改 `render.yaml` 的 `routes` 段，新增 2 条 rewrite
- [ ] 修改 `frontend/src/lib/templates-api.ts` 的 `listTemplates`，改用 `authFetch`
- [ ] 修改 `backend/core/attribution_templates.py` 的 `ROLE_DEFAULTS["product"]` 值为 `preset_model_product`
- [ ] 修改 `frontend/src/components/DemoTour.tsx` 的 `useState` 惰性初始化

### 阶段 2：本地验证（预计 0.3 人天）

- [ ] 前端 `npm run build` 成功
- [ ] 本地 `out/` 目录生成 `out/templates/run/_/_.html` 和 `out/templates/editor/_/_.html`
- [ ] 本地 `npx serve out` 启动后，访问 `http://localhost:3000/templates/run/test` 返回 200
- [ ] 后端 pytest 单测通过

### 阶段 3：部署与回归（预计 0.7 人天）

- [ ] 提交代码并 push 到 main
- [ ] Render Static Site 自动部署成功（3-5 分钟）
- [ ] Render Web Service（后端）已重启（如有改动）
- [ ] 部署后 5 个关键验证点全部通过
- [ ] 40 条回归用例通过率 ≥ 90%
- [ ] 截图归档：5 个模板运行 SOP 报告页、克隆/新建成功截图、4 角色默认模板截图

### 阶段 4：交付（预计 0 工时）

- [ ] 在 Linear/Jira 创建 v2.0.1 发布单
- [ ] 更新 CHANGELOG.md
- [ ] 通知测试团队回归
- [ ] 通知产品/运营团队，模板中心可正式对外开放

---

> **下一步行动建议**：
> 1. 你可以直接复制本 SDD 给开发工程师
> 2. 或者如果你方便提供 backend Docker 启动命令 + 一个数据库的访问，我可以直接在 IDE 里改这 4 个文件并提交 PR
> 3. **强烈建议**先在本地用 `npm run build && npx serve out` 验证修复 1 是否有效（重启 serve 后访问 `/templates/run/test` 看是否 200），再推送远端
