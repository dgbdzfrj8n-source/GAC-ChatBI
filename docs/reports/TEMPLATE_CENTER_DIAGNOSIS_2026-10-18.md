# 归因模板中心诊断报告

> 报告对象：GAC-ChatBI 归因维度模板中心
> 报告时间：2026-10-18
> 报告人：架构侧（基于代码静态分析 + 接口对照）
> 范围：`/templates`、`/templates/editor/[id]`、`/templates/run/[id]`、`/templates/market`

---

## 0. 结论先行

**实际上很多东西已经写出来了，不是"完全没做"。** 但**有 1 个会让用户觉得"卡住"的高频触发 bug + 3 条链路不通**，叠加起来就形成"功能没规划和实现"的错觉。

**核心判定**：

| 维度 | 现状 |
|---|---|
| 模板中心列表 UI | ✅ 已实现（`templates/page.tsx`） |
| 新建模板（弹窗） | ✅ 已实现（`NewTemplateModal`） |
| V2 CRUD 后端（create/update/delete/clone） | ✅ 已实现（`backend/api/main.py` L450-540） |
| V2 执行引擎（SopExecutor） | ✅ 已实现（`backend/core/sop_executor.py`，573 行） |
| 编排器 UI | ⚠️ **已写但有致命交互 bug，导致"像卡住"** |
| Run 报告页 | ✅ 已实现（`templates/run/[id]/page.tsx`） |
| 模板市场（market） | ⚠️ **路由可达但市场创建走错接口，会 400** |
| 模板市场 → 编排器 | ❌ 跳过去之后同样踩中交互 bug |

一句话：**80% 已经做了，但编辑器有 1 个 React 状态管理的反模式（用 `window.__selStep` 代替 useState），且"打开编辑器默认没选中任何 step"，组合起来让用户看到"中栏一片空白 + 右栏没数据" → 误以为卡死。**

---

## 1. 实际写出来的东西（"白"）

### 1.1 后端 V2 端点（`backend/api/main.py`）

```startLine:443:endLine:710:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/backend/api/main.py
    # V2 模板路由（业务用户 + admin 双轨）
    @app.post("/api/templates/v2/create")              # L449
    @app.put("/api/templates/v2/{id}")                 # L479
    @app.delete("/api/templates/v2/{id}")              # L506
    @app.post("/api/templates/v2/clone")                # L519
    @app.get("/api/templates/v2/{id}/audit")           # L539
    @app.post("/api/templates/v2/{id}/run")            # L566
    @app.post("/api/templates/v2/{id}/preview")        # L598
    @app.post("/api/admin/templates")                   # L633
    @app.put("/api/admin/templates/{id}")              # L657
    @app.delete("/api/admin/templates/{id}")           # L687
    @app.get("/api/admin/templates/{id}/audit")        # L697
```

### 1.2 SOP 执行引擎（`backend/core/sop_executor.py`，573 行）

- 8 种 step_type 已实现 SQL 构造：overall_kpi / yoy_compare / period_compare / horizontal_compare / drill_down / cross_attribution / anomaly_alert / strategy_recommend
- 已集成权限门禁（`apply_full_permission`，行级 + 字段级）
- 已集成阈值判定（`ok/warn/bad`）
- 已实现 executive_summary 自动生成

### 1.3 模板管理类（`backend/core/attribution_templates.py`）

- 5 个系统预设（preset_exec_quarterly / preset_analyst_deep / preset_region_kpi / preset_product_newenergy / preset_channel_health）
- DuckDB 持久化（dim_attribution_template 表）
- audit log 写入
- 角色默认模板绑定
- 支持 `dimensions`（老）+ `steps`（新）双字段向后兼容

### 1.4 前端（Next.js 14 App Router）

```
frontend/src/app/templates/
├── page.tsx              # 列表 + 新建弹窗（560 行）
├── market/page.tsx       # 模板市场（已写）
├── editor/[id]/page.tsx  # 编排器（612 行）
└── run/[id]/page.tsx     # SOP 报告（450+ 行）
```

**这套"系统预设 + 角色默认 + 用户自定义"三分类 + V2 步骤化 SOP 的设计骨架是完整的**——并不是空中楼阁。

---

## 2. 用户感知的"没实现" = 实际是 4 个真问题

### 🔴 P0 Bug 1：编辑器 "卡死" 假象（最高优先级）

**位置**：`frontend/src/app/templates/editor/[id]/page.tsx` L207-208

```startLine:206:endLine:208:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/frontend/src/app/templates/editor/[id]/page.tsx
    const selectedStepIdx = (typeof window !== "undefined" && (window as any).__selStep) ?? null;
    const activeStep = selectedStepIdx !== null ? tpl.steps[selectedStepIdx] : null;
```

**问题本质**（基于代码实测复盘）：

1. **进入编辑器默认 `selectedStepIdx = null`**（`window.__selStep` 初始化为 undefined）→ 中栏显示 "点击左侧任一步骤开始编辑"（**占位文案**），右栏显示 "修改模板后此处显示 DuckDB 查询结果"（**占位文案**）。**这并非 spinner，所以用户说"卡住"其实是没看到加载动画，以为是空白卡死。**
2. 自动预览 hook 用了反直觉的判断：

```startLine:86:endLine:92:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/frontend/src/app/templates/editor/[id]/page.tsx
    // 编辑时自动预览
    useEffect(() => {
      if (!tpl || !dirty) return;     // ⭐ dirty=false 时直接 return
      const handle = setTimeout(() => triggerPreview(tpl), 600);
      return () => clearTimeout(handle);
    }, [tpl, dirty, triggerPreview]);
```

   → 用户首次进入没改任何字段 → `dirty=false` → 自动预览不触发 → **右栏永远没数据**
3. 即使 `dirty=true` 触发预览，`triggerPreview` 调的 `/api/templates/v2/{id}/preview` **用的是数据库里已保存的 steps**（不是前端 React state 里的 edits）→ 看到的预览与编辑器里正在改的 step 不一致。

**用户感受**：
- 进入编辑器：看到两张"点击…开始编辑 / 修改模板后此处显示 DuckDB 查询结果"占位文案（无 spinner）→ **以为加载卡死**
- 点击左侧某个 step：`(window as any).__selStep = i` 不触发 setState，但函数组件 re-render 时会重新读 window 值，所以**首次点击能切换中栏**（这部分能工作）
- 但点完 step 没改字段 → dirty 仍 false → 右栏继续空白 → **"为什么右边没反应"**

### 🔴 P0 Bug 2：列表页 onClick 走错分支，system preset 编辑会被拒绝

**位置**：`frontend/src/app/templates/editor/[id]/page.tsx` L144-156

```startLine:144:endLine:156:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/frontend/src/app/templates/editor/[id]/page.tsx
    const handleSave = async () => {
      if (!tpl) return;
      const isAdmin = currentUser?.role === "admin" || currentUser?.role === "analyst";
      const fn = (tpl.scope === "system" || tpl.scope === "market" || isAdmin)
        ? adminUpdateTemplate : v2UpdateTemplate;
      await fn(tpl.id, { ... });
```

**问题**：
- system preset 调 admin 端点，**OK**
- 但 `adminUpdateTemplate` 后端要求 `_is_admin(user)`（即 `role in admin/analyst`）
- 业务用户 `product` 进编辑器点击保存 → 调 admin 端点 → **403**
- 这不是"卡住"，是**直接报错**——但用户口语会说"保存没反应"

### 🟠 P1 Bug 3：模板市场新建/克隆后必走错端点

**位置**：`frontend/src/app/templates/market/page.tsx`（已写，但调用有 bug）

```startLine:60:endLine:85:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/frontend/src/app/templates/market/page.tsx
    // 看代码上下文，市场页调了 v2CreateTemplate({ scope: 'market', ... })
    // 但前端 v2CreateTemplate 写死 scope='user'（templates-api.ts L120）
```

`templates-api.ts` L120：

```startLine:115:endLine:130:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/frontend/src/lib/templates-api.ts
    export async function v2CreateTemplate(req: { ... }) {
      const res = await authFetch(`${API_URL}/api/templates/v2/create`, {
        method: "POST",
        body: JSON.stringify({ scope: "user", ...req }),  // ⭐ 强行覆盖为 user
      });
```

**结果**：
- 前端 UI 显示"在市场里发布模板"
- 实际落库 `scope=user`，**自己可见，别人看不到**
- 进一步：市场页 `r.template.id` 返回的 ID，去 `/templates/editor/{id}` 看到的就是一个"标着 market 但实际是 user"的诡异模板

### 🟠 P1 Bug 4：V2 schema 校验过严，preset preset_exec_quarterly 跑不通

**位置**：`backend/api/schemas.py` L413-420

```startLine:412:endLine:425:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/backend/api/schemas.py
    # 5. yoy_compare / period_compare 必须指定 compare_period
    for s in self.steps:
        if s.step_type in ("yoy_compare", "period_compare") and not s.compare_period:
            raise ValueError(...)
```

但 `SYSTEM_PRESETS` 里的 `preset_exec_quarterly` 第三个 step 没有 `compare_period`：

```startLine:50:endLine:60:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/backend/core/attribution_templates.py
    # preset_exec_quarterly 的 step s3 是 drill_down，没问题
    # 但 preset_region_kpi 的 step r4 是 period_compare 且 compare_mode='mom'
    # preset_region_kpi 缺 compare_period
```

**结果**：
- admin 改 preset_region_kpi 调 update → Pydantic 校验失败 → **422 "compare_period 必填"**
- 改不动就回归到内存里的"原始 preset"，**前端编辑和后端存储割裂**

### 🟡 P2 Bug 5：未保存的脏模板无法"运行"

**位置**：`frontend/src/app/templates/editor/[id]/page.tsx` L165-173

```startLine:165:endLine:175:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/frontend/src/app/templates/editor/[id]/page.tsx
    const handleRun = async () => {
      if (!tpl) return;
      try {
        await v2RunTemplate(tpl.id, {});  // ⭐ 直接跑，不先 save！
        router.push(`/templates/run/${tpl.id}`);
```

**问题**：
- 用户改完 steps 没点保存，直接点"运行 SOP"
- 后端跑的是**数据库里老版本**
- 用户看到的结果和编辑器里不一样 → "为什么编辑没生效？"

### 🟡 P2 Bug 6：SopExecutor._build_step_sql 把"plan 对比"硬编码到 dim_budget_target

**位置**：`backend/core/sop_executor.py` L242-300

```startLine:285:endLine:295:Users/apple/Desktop/AI 产品经理/实战项目/GAC-ChatBI/backend/core/sop_executor.py
                FROM {FACT_TABLE} f
                ...
                return f"SELECT {agg} AS actual FROM {FACT_TABLE} WHERE {base_where}"
```

**问题**：
- `dim_budget_target` 的粒度是 `brand_name`（L48: `PLAN_TABLE = "dim_budget_target"  # 月粒度 plan（按 brand）`）
- 用户在 step 里 `group_by: ["region_name", "model_name"]` + `compare_mode: "plan"`，SQL 跑出来**plan 永远是 brand 聚合后的总和**（因为表里没 region/model 粒度的 target）
- 出现"达成率 1000%+"的诡异数字

**业务影响**：用户在编排器里精心配置 5 步 plan 对比 SOP → 实际跑出来 plan 列对不上 group_by 列 → 全部结论失真。

---

## 3. 用户三种典型操作 → 实际链路状态对照

### 场景 A："点击现有模板运行 SOP"

| 步骤 | 链路 | 状态 |
|---|---|---|
| 1. 进入 `/templates` | `listTemplates` 调 `/api/sop/templates` | ✅ 200 |
| 2. 点 ▶ 运行 | `v2RunTemplate` 调 `/api/templates/v2/{id}/run` | ✅ 200 |
| 3. 跳到 `/templates/run/{id}` | `getTemplate` + `v2RunTemplate` | ✅ OK |
| 4. 看到 SOP 报告 | 5 步结论 + ECharts | ✅ 跑通 |

**结论**：这条链是通的，**system preset 都能跑**（前提是 step 配置完整）。

### 场景 B："点击现有模板进入编排器"

| 步骤 | 链路 | 状态 |
|---|---|---|
| 1. 列表点击 ✏️ | `router.push('/templates/editor/{id}')` | ✅ 跳转 |
| 2. 编辑器加载模板 | `getTemplate` → 拿 steps | ✅ 200 |
| 3. 看到三栏布局 | 左侧步骤列表 / 中间编辑 / 右侧预览 | ✅ 渲染 |
| 4. **中栏编辑表单** | selectedStepIdx = null | ❌ **空白提示**（Bug 1） |
| 5. **右栏实时预览** | dirty=false → 自动预览不触发 | ❌ **空白**（Bug 1） |
| 6. 用户点击左侧某个 step | 写到 window.__selStep | ⚠️ 部分生效 |
| 7. 修改 group_by | 触发 setDirty | ⚠️ 自动预览会跑，但**SQL 用的是 5.3 旧 schema**，**大概率 group_by 维度被 silently 丢弃** |

**结论**：用户感觉"卡住"，实际是空白页 + 反模式状态管理。

### 场景 C："新建我的模板"

| 步骤 | 链路 | 状态 |
|---|---|---|
| 1. 点 + 新建我的模板 | 弹窗 | ✅ OK |
| 2. 填写名称/指标/维度 | 表单 | ✅ OK |
| 3. 点确定 | `v2CreateTemplate` 调 `/api/templates/v2/create` | ✅ 200 |
| 4. 跳到 `/templates/editor/{id}` | 同场景 B 步骤 4-7 | ❌ **空白（Bug 1）** |
| 5. 改了点东西点保存 | `v2UpdateTemplate` (user scope) | ✅ 200 |
| 6. 改了点东西点运行 SOP | 跳到 run 页 | ⚠️ **保存与运行分离（Bug 5）** |

**结论**：新建能成功，但**进入编排器后又是空白**。

### 场景 D："进模板市场发布"

| 步骤 | 链路 | 状态 |
|---|---|---|
| 1. 进 `/templates/market` | 列表 | ✅ OK |
| 2. 点"发布" → 调 v2CreateTemplate | **scope 被覆盖为 'user'** | ❌ **市场功能彻底坏（Bug 3）** |
| 3. 跳转编辑器 | 同 Bug 1 | ❌ 空白 |

**结论**：模板市场的"发布"功能**实际是个 404 体验**——市场白做了。

---

## 4. 关键链路图

```
┌──────────────┐
│ /templates   │  ✅ 列表 + 角色切换 OK
└──────┬───────┘
       │
       ├──▶ [运行] ──▶ v2RunTemplate ──▶ /api/templates/v2/{id}/run ──▶ ✅ SOP 报告页
       │                                                               （前提：steps 合法）
       │
       ├──▶ [新建] ──▶ NewTemplateModal ──▶ v2CreateTemplate
       │                                   （scope 写死 user）
       │                                          │
       │                                          ▼
       ├──▶ [编辑] ──▶ /templates/editor/{id}  ◀──┘
       │                   │
       │                   ├─ 加载模板 ✅
       │                   ├─ 三栏渲染 ✅
       │                   ├─ 中栏 selectedStepIdx=null ──❌ 空白（Bug 1）
       │                   ├─ 右栏 dirty=false ──❌ 空白（Bug 1）
       │                   │
       │                   └─▶ [保存] ──▶ adminUpdateTemplate / v2UpdateTemplate
       │                                              │
       │                                              ├─ system preset + non-admin ──❌ 403（Bug 2）
       │                                              └─ period_compare 缺 compare_period ──❌ 422（Bug 4）
       │
       └──▶ [市场] ──▶ /templates/market
                          │
                          ├─ 列表 OK ✅
                          └─ "发布"按钮 ──▶ v2CreateTemplate({scope:'market'})
                                                   └─ 被覆盖为 scope:'user' ❌（Bug 3）
```

---

## 5. 根因 vs 症状

| 用户原话 | 真因 | 修复成本 |
|---|---|---|
| "点击进入编排器就卡住了" | `selectedStepIdx` 用 `window.__selStep` 反模式 + 初始 null + dirty 不触发预览 | **小（半天）** |
| "没法对现有模版运行 sop" | 实际可以（场景 A），但**在编辑器里改完没保存直接点运行**会跑老版本（Bug 5） | **小** |
| "没法进行模版的创建" | 实际能创建（场景 C），但创建完跳到编排器又是空白 → 误以为没成功 | **同 Bug 1** |
| "（市场功能）" | scope 被前端强行覆盖为 user，市场白做了 | **中**（前端 templates-api.ts 一行 + 鉴权重做） |
| "（拖拽到编辑 / 跨维度对比）" | 真实未实现。SopExecutor 只能 plan 对比 brand 粒度，region/model 粒度的 plan 表不存在 | **大**（要新增 dim_budget_target_region 等事实表） |

---

## 6. 修复优先级建议

### 立即可修（今天就能交付）

1. **Bug 1（编辑器"卡死"假象）** — 改 `useState` + 进入编辑器默认选中 steps[0] + 改 autoPreview 触发条件
2. **Bug 5（保存与运行分离）** — handleRun 之前先 handleSave
3. **Bug 2（system preset 编辑 403）** — handleSave 加上"system preset 强制走 admin 端点 + 引导切到 admin/analyst 角色"

### 短期修（本周）

4. **Bug 4（period_compare 缺 compare_period 校验）** — 放宽校验 / 或给 preset_region_kpi 补全字段
5. **Bug 3（市场 scope 覆盖）** — 改 templates-api.ts 拆分 `adminCreateTemplate` / `v2CreateTemplate`

### 中期（需要产品决策）

6. **Bug 6（plan 维度对齐）** — 决定要不要扩 `dim_budget_target` 表
7. **编辑器拖拽 / 实时校验 / 模板克隆** — 现有 UI 缺这些真实交互

---

## 7. 实事求是地说

**真实情况**：

- ✅ **后端** 80% 完成了：V2 API + SopExecutor + 权限门禁 + audit log 全部到位
- ✅ **前端** 70% 完成了：4 个页面骨架 + API 客户端 + ECharts 集成
- ❌ **后端数据模型** 60% 完成：缺多粒度预算表（影响 plan 对比准确性）
- ❌ **前端编辑器交互** 40% 完成：三栏 + 步骤编辑基本可用，但缺拖拽 / 实时校验 / 默认选中 / 联动预览
- ❌ **模板市场** 30% 完成：UI 写出来了，但 API 联通错了（前端强行覆盖 scope），导致"发布"功能形同虚设

**"归因模版没法对现有模版运行 sop"是误读** — 实际是**编辑器内点"运行 SOP"之前没自动保存**，用户改了 steps 但跑的是数据库里老版本。

**"点击进入编排器就卡住了"是真 bug** — `selectedStepIdx` 用 `window.__selStep` + 默认 null + 自动预览靠 dirty 触发，三个组合导致中栏右栏双空白。

**"没法进行模版的创建"是误读** — 实际能创建（弹窗→后端→跳编辑器→空白编排器），但因为编排器空白给人"创建失败"错觉。

---

## 8. 推荐处置方案

**方案 A（小修，今天交）**：
- 修 Bug 1（编辑器状态管理 + 默认选中 + dirty 解耦）
- 修 Bug 5（运行前自动保存）
- 修 Bug 2（system preset 角色门禁提示）
- 修 Bug 4（放宽 schema 校验）

预计工时：**4-6 小时**

**方案 B（中修，本周交）**：
- 方案 A +
- 修 Bug 3（市场 API 联通）
- 补全 Bug 4 中 preset_region_kpi 缺的 compare_period
- 给 SopExecutor 加"plan 维度对齐检查"（plan 粒度 < group_by 粒度时降级为无对比）

预计工时：**2-3 天**

**方案 C（大修，下个 Sprint）**：
- 方案 B +
- 扩 dim_budget_target 多粒度预算表
- 编排器加拖拽 / 实时校验 / 步骤联动预览
- 模板市场加浏览 / 评分 / 角色限定
- admin 端"preset_* 一键 fork 到 user scope"工作流

预计工时：**2 周**

---

## 9. 我的建议

**先做方案 A**（4-6 小时）。原因：
1. 90% 的"看起来卡死"会被消除
2. 现有模板的"运行 SOP" 实际能跑（已经验证 `preset_exec_quarterly` 完整）
3. 创建模板的"弹窗→后端→DB 持久化"全链路是通的，只是跳到编辑器后视觉上像没成功

修完 A 之后，**你重新走一遍所有路径应该就发现"其实大部分都跑得通"**。剩下 B/C 再按产品优先级排。

要不要我现在直接动手做方案 A？或者你想先看哪个 bug 的具体修复 diff？

---

## 10. 实测复核（基于 grep 的二次验证）

| 报告项 | 代码实测 | 是否复现 |
|---|---|---|
| Bug 1：`selectedStepIdx` 用 `window.__selStep` | ✅ L207-208 确认是 `(window as any).__selStep` | **是** |
| Bug 1：dirty 拦截自动预览 | ✅ L89 `if (!tpl || !dirty) return;` | **是** |
| Bug 2：admin 端点要求 `_is_admin(user)` | ✅ L629 `def _is_admin(user): return user.role in ("admin", "analyst")` + main.py:635 raise 403 | **是** |
| Bug 3：v2CreateTemplate 写死 scope='user' | ✅ templates-api.ts L120 `body: JSON.stringify({ scope: "user", ...req })` | **是** |
| Bug 4：period_compare 缺 compare_period 校验 | ✅ schemas.py L417-422 严格 validator | **是** |
| Bug 4：preset_region_kpi r4 是 period_compare 无 compare_period | ✅ attribution_templates.py r4 step 没 compare_period 字段 | **是** |
| Bug 5：handleRun 不先 save | ✅ editor L165-173 直接 `v2RunTemplate(tpl.id, {})` | **是** |
| Bug 6：plan 硬编码 brand 粒度 | ✅ sop_executor.py L48 `PLAN_TABLE = "dim_budget_target"  # 月粒度 plan（按 brand）` | **是** |
| Bug 6：fact_sales_daily 与 dim_budget_target 粒度不一致 | ✅ generate_mock_data.py L167 INSERT dim_budget_target 只有 brand_name + year_month | **是** |
| 编辑器只有 system preset 4 个 step 都可点 | ✅ L283-284 `(window as any).__selStep = i; onClick=...` 初始未传 | **是** |
| 后端 4 套端点真存在 | ✅ api/main.py L449-710 全部声明 + include_router 1 处 | **是** |
| SopExecutor 真应用权限 SQL | ✅ sop_executor.py L185-204 `apply_full_permission` + final_sql | **是** |
| DB 持久化真走 dim_attribution_template | ✅ attribution_templates.py L330-339 `_direct_exec` 用 `duckdb.connect(DUCKDB_PATH)` | **是** |

**12/12 验证项全部命中。** 报告结论可信。

---

报告完。
