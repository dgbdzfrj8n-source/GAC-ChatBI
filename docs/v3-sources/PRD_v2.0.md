# 广汽云 ChatBI — 归因模板模块 PRD（v2.0 重做版）

> **文档版本**：v2.0
> **模块**：归因模板（Attribution Templates）
> **作者**：AI 产品经理
> **日期**：2026-10-18
> **状态**：待开发
> **关联系统**：广汽云 ChatBI 智能经营问数平台 v2.0.0 · Sprint 10

---

## 0. 背景与目标

### 0.1 为什么重做

现有归因模板模块存在 3 个 P0 阻断 Bug，导致核心功能完全不可用：

| Bug | 现象 | 根因 |
|---|---|---|
| 运行 SOP 404 | 5个模板的「运行SOP」按钮全部跳转到 `/templates/run/preset_exec_quarterly` 返回404 | 动态路由未实现 + 所有按钮硬编码同一个 templateId |
| 克隆模板 404 | 点击「克隆为我的模板」跳转到 `/templates/editor/user_xxx` 返回404 | 编辑器路由未实现 + 克隆后直接跳编辑器 |
| 新建模板 404 | 填写名称点击「创建并进入编排器」跳转到编辑器页404，且模板未保存 | 编辑器路由未实现 + 数据未持久化 |

**本次重做的核心目标**：创建、编辑、克隆、运行、删除全链路打通，数据持久化，SOP 可真正执行。

### 0.2 产品定位

归因模板是将**经营分析方法论固化为可复用的 SOP 步骤**，让非技术用户（高管、区域总监、车型经理）一键发起标准化的归因分析，而不需要每次从零开始提问。

**用户价值**：
- 高管：季度复盘不用等分析师，5步自动跑完整体→品牌→区域→车型下钻
- 分析师：把常用的分析路径存为模板，下次一键复用
- 产品经理：不同角色有不同的默认模板，开箱即用

### 0.3 设计原则

1. **先保存再跳转**：任何创建/克隆操作必须先调用 API 持久化，成功后才跳转
2. **动态路由必有页**：`/templates/editor/[id]` 和 `/templates/run/[id]` 必须有对应 page.tsx
3. **复用不重造**：SOP 执行复用现有 Text2SQL Workflow，不重新实现 NL2SQL
4. **预设不可删**：系统预设模板有保护机制，用户只能克隆后修改自己的副本
5. **分步可验证**：按 Phase 实施，每阶段完成后可独立测试

---

## 一、数据模型设计（SQLite）

### 1.1 ER 关系

```
templates (1) ──── (N) template_steps
templates (1) ──── (N) template_dimensions
templates (1) ──── (N) template_runs
template_runs (1) ── step_results (JSON字段内存储每步结果)
```

### 1.2 建表 SQL

```sql
-- 模板主表
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,                    -- 预设用 preset_xxx，用户用 user_ + UUID
    name TEXT NOT NULL,                     -- 模板名称
    description TEXT DEFAULT '',            -- 模板描述
    template_type TEXT NOT NULL,            -- system / role_default / user
    role TEXT DEFAULT 'all',                -- 适用角色：executive/analyst/product_manager/guest/all
    metric_key TEXT DEFAULT 'delivered_units', -- 归因指标（对应语义层指标key）
    creator TEXT DEFAULT 'system',          -- 创建者用户名
    is_active INTEGER DEFAULT 1,            -- 是否启用
    sort_order INTEGER DEFAULT 0,           -- 排序权重
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 模板步骤表
CREATE TABLE IF NOT EXISTS template_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,            -- 步骤序号，从0开始
    step_name TEXT NOT NULL,                -- 步骤名称，如"整体达成率对标"
    step_icon TEXT DEFAULT '🎯',            -- 步骤图标 emoji
    step_type TEXT NOT NULL,                -- overview/horizontal/drilldown/breakdown/trend/strategy
    query_template TEXT NOT NULL,           -- 查询模板，支持 {{brand}} {{time}} {{region}} {{prev_result}}
    dimension_hints TEXT DEFAULT '[]',      -- JSON数组，该步骤聚焦的维度key列表
    expected_output TEXT DEFAULT 'kpi',     -- kpi/bar/line/table/pie
    is_auto_execute INTEGER DEFAULT 1,      -- 是否自动执行（1=自动，0=需用户确认）
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);

-- 模板维度配置表
CREATE TABLE IF NOT EXISTS template_dimensions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id TEXT NOT NULL,
    dimension_key TEXT NOT NULL,            -- 维度key：brand/region/model/energy_type/price_segment/time
    dimension_name TEXT NOT NULL,           -- 维度显示名
    is_required INTEGER DEFAULT 0,          -- 是否必选维度
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);

-- SOP运行记录表
CREATE TABLE IF NOT EXISTS template_runs (
    id TEXT PRIMARY KEY,                    -- run_ + UUID
    template_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    params TEXT DEFAULT '{}',               -- JSON：运行时参数 {brand, time_range, region}
    status TEXT DEFAULT 'running',          -- running/completed/failed
    current_step INTEGER DEFAULT 0,         -- 当前执行到第几步
    step_results TEXT DEFAULT '[]',         -- JSON数组，每步的完整结果
    total_duration_ms INTEGER DEFAULT 0,
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_templates_type ON templates(template_type);
CREATE INDEX IF NOT EXISTS idx_templates_role ON templates(role);
CREATE INDEX IF NOT EXISTS idx_steps_template ON template_steps(template_id);
CREATE INDEX IF NOT EXISTS idx_runs_template ON template_runs(template_id);
CREATE INDEX IF NOT EXISTS idx_runs_user ON template_runs(user_id);
```

### 1.3 5个系统预设模板初始数据（Seed）

应用启动时检查 `templates` 表是否为空，为空则执行以下 INSERT：

```sql
-- 预设1：高管季度复盘（高管角色默认）
INSERT INTO templates (id, name, description, template_type, role, metric_key, sort_order) VALUES
('preset_exec_quarterly', '高管季度复盘', '高管视角5步SOP：整体达成率→横向看品牌→下钻问题品牌-区域→下钻问题区域-车型→策略建议', 'role_default', 'executive', 'delivered_units', 1);

-- 预设2：分析师深度下钻
INSERT INTO templates (id, name, description, template_type, role, metric_key, sort_order) VALUES
('preset_analyst_deepdive', '分析师深度下钻', '5维度细粒度（品牌+区域+车型+能源+价格段），适合专题分析', 'system', 'analyst', 'delivered_units', 2);

-- 预设3：区域总监KPI
INSERT INTO templates (id, name, description, template_type, role, metric_key, sort_order) VALUES
('preset_region_kpi', '区域总监KPI', '聚焦区域×车型，评估区域总经理经营质量', 'system', 'product_manager', 'delivered_units', 3);

-- 预设4：车型经理产品复盘
INSERT INTO templates (id, name, description, template_type, role, metric_key, sort_order) VALUES
('preset_model_review', '车型经理产品复盘', '聚焦车型×价格段×能源类型，定位产品定位偏差', 'system', 'product_manager', 'delivered_units', 4);

-- 预设5：新能源专项
INSERT INTO templates (id, name, description, template_type, role, metric_key, sort_order) VALUES
('preset_ev_special', '新能源专项', '新能源转型追踪：能源类型×价格段×车型', 'system', 'all', 'delivered_units', 5);
```

每个预设模板的步骤数据见第五章。

---

## 二、路由设计（Next.js App Router）

| 路由 | 文件路径 | 页面职责 | 之前状态 |
|---|---|---|---|
| `/templates` | `app/templates/page.tsx` | 模板列表页（预设+我的模板） | 已有，保留 |
| `/templates/market` | `app/templates/market/page.tsx` | 模板市场页（预设模板详情+克隆） | 已有，保留 |
| `/templates/editor/[templateId]` | `app/templates/editor/[templateId]/page.tsx` | 模板编辑器页 | **之前404，必须新建** |
| `/templates/run/[templateId]` | `app/templates/run/[templateId]/page.tsx` | SOP运行页 | **之前404，必须新建** |

**路由跳转规则**：
- 列表页「运行SOP」按钮 → `router.push(/templates/run/${template.id})`，每个模板用自己的 id
- 列表页「编辑」按钮（仅自定义模板）→ `router.push(/templates/editor/${template.id})`
- 市场页「克隆为我的模板」→ 调用 API 成功后 `router.push(/templates)`，**不跳编辑器**
- 新建弹窗「创建并进入编辑器」→ 调用 API 成功后 `router.push(/templates/editor/${newId})`

---

## 三、核心页面详细设计

### 3.1 模板列表页（/templates）

**页面结构**（从上到下）：

```
┌─────────────────────────────────────────────────┐
│  归因维度模板中心                                │
│  SOP步骤化编排 · 系统预设/角色默认/我的模板      │
│                          [模板市场] [新建我的模板]│
├─────────────────────────────────────────────────┤
│  当前角色：[高管][分析师][产品经理][访客]        │
│  ⭐ 高管角色默认模板：高管季度复盘               │
├─────────────────────────────────────────────────┤
│  🔒 系统预设模板（5）                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │模板卡片1  │ │模板卡片2  │ │模板卡片3  │        │
│  │5步SOP    │ │5步SOP    │ │4步SOP    │        │
│  │维度标签   │ │维度标签   │ │维度标签   │        │
│  │[运行SOP] │ │[运行SOP] │ │[运行SOP] │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────┐ ┌──────────┐                     │
│  │模板卡片4  │ │模板卡片5  │                     │
│  └──────────┘ └──────────┘                     │
├─────────────────────────────────────────────────┤
│  👤 我的模板（N）                               │
│  ┌──────────┐                                   │
│  │自定义模板  │ [编辑][删除][运行SOP]            │
│  └──────────┘                                   │
│  （空状态：还没有自定义模板，去模板市场逛逛→）   │
└─────────────────────────────────────────────────┘
```

**模板卡片内容**：
- 模板名称 + 「角色默认」标签（仅第一个预设）
- 描述（1行，超出省略）
- SOP步数标签（如「5 步 SOP」）
- 聚合维度标签（如 总交付量、品牌、区域、车型）
- 操作按钮：
  - 预设模板：仅「运行 SOP」+ 「🔒 系统预设」标识
  - 自定义模板：「运行 SOP」+ 编辑图标 + 删除图标

**角色切换逻辑**：
- 4个角色按钮：高管/分析师/产品经理/访客
- 切换后更新「角色默认模板」提示文字
- 系统预设5个模板在所有角色下都可见（不随角色过滤）
- 产品理由：预设模板是公共资产，所有角色都能看到和使用，变化的只是"默认推荐哪一个"

### 3.2 模板市场页（/templates/market）

**页面结构**：
- 顶部：「← 返回模板中心」+ 标题「模板市场」+ 副标题
- 主体：5个预设模板的详细卡片，2列布局

**每个详细卡片包含**：
- 模板名称 + 描述
- 步骤化 SOP 详情：每步有序号、图标、步骤名称（竖向列表）
- 聚合维度标签
- 「克隆为我的模板」按钮（蓝色主按钮）

**克隆交互**：
1. 点击「克隆为我的模板」
2. 按钮变为 loading
3. 调用 `POST /api/templates/{id}/clone`
4. 成功：显示 toast「克隆成功，已添加到我的模板」，1.5秒后自动跳回 `/templates`
5. 失败：显示错误提示，按钮恢复可点击

**产品理由**：克隆后跳回列表页而非编辑器，因为克隆的目的是快速得到一个可用模板，用户不一定需要马上编辑。

### 3.3 模板编辑器页（/templates/editor/[templateId]）

**这是之前完全缺失的页面，本次必须实现。**

**页面布局**（三栏式）：

```
┌──────────────────────────────────────────────────────────┐
│ ← 返回  |  模板名称输入框  |  归因指标下拉  |  [保存]     │
├──────────┬───────────────────────────────────────────────┤
│ 步骤列表  │  步骤详情编辑区                                │
│          │                                               │
│ ① 总览   │  步骤名称：[整体达成率对标]                    │
│ ② 横向   │  步骤图标：[🎯] (emoji选择)                   │
│ ③ 下钻   │  步骤类型：[总览▾] (6选1)                     │
│ ④ 车型   │  查询模板：                                    │
│ ⑤ 策略   │  [{{time}} {{brand}}的总交付量与预算达成率？]  │
│          │  聚焦维度：[品牌][区域][车型] (多选)           │
│ [+添加]  │  期望输出：[KPI数字▾]                         │
│          │  自动执行：[开关]                              │
│          │                                               │
│          │  [删除此步骤]                                  │
└──────────┴───────────────────────────────────────────────┘
```

**左侧步骤列表**：
- 每步显示序号 + 步骤名称
- 当前编辑步高亮
- 支持拖拽排序（或上移/下移按钮）
- 底部「+ 添加步骤」按钮
- 至少保留1步，最后1步不可删除

**右侧编辑区字段**：
| 字段 | 类型 | 说明 |
|---|---|---|
| 步骤名称 | 文本输入 | 如"整体达成率对标" |
| 步骤图标 | emoji选择 | 🎯↔️🔍🧩📈💡 6个预设 |
| 步骤类型 | 下拉6选1 | 总览/横向对比/下钻/拆解/趋势/策略建议 |
| 查询模板 | 多行文本 | 自然语言查询模板，支持变量占位符 |
| 聚焦维度 | 多选 | 该步骤重点分析的维度 |
| 期望输出 | 下拉 | KPI数字/柱状图/折线图/饼图/表格 |
| 自动执行 | 开关 | 开启=进入该步自动查询，关闭=需用户点确认 |

**顶部信息栏**：
- 模板名称（文本输入，必填）
- 描述（文本输入，可选）
- 归因指标（下拉，来自语义层30个指标，默认总交付量）
- 「保存」按钮（主按钮）
- 「← 返回」按钮

**保存逻辑**：
- 点击保存 → 调用 `PUT /api/templates/{id}` → 成功显示 toast「保存成功」
- 有未保存修改时点击返回 → 弹出确认框「有未保存的修改，确定离开吗？」
- 自动保存（可选）：编辑停止3秒后自动调用PUT，显示「已自动保存」

**加载逻辑**：
- 进入页面时从 URL 获取 templateId
- 调用 `GET /api/templates/{id}` 加载数据
- 加载中显示 skeleton
- 加载失败（ID不存在）→ 显示404状态页 + 返回按钮

### 3.4 SOP运行页（/templates/run/[templateId]）

**这是之前完全缺失的页面，本次必须实现。**

**页面三阶段状态机**：

#### 阶段A：准备阶段（SOP概览 + 参数配置）

```
┌─────────────────────────────────────────────────┐
│ ← 返回列表                                      │
│                                                 │
│  📋 高管季度复盘                                │
│  高管视角5步SOP：整体→品牌→区域→车型→策略       │
│                                                 │
│  步骤列表：                                      │
│  ① 🎯 整体达成率对标                            │
│  ② ↔️ 横向对比品牌                              │
│  ③ 🔍 下钻问题品牌-区域                         │
│  ④ 🔍 下钻问题区域-车型                         │
│  ⑤ 💡 策略建议                                  │
│                                                 │
│  ⚙️ 运行参数配置                                 │
│  品牌：[全部▾]   时间范围：[上季度▾]            │
│  区域：[全部▾]                                  │
│                                                 │
│  [开始执行]   预计耗时：约30秒                   │
└─────────────────────────────────────────────────┘
```

#### 阶段B：执行阶段（单步执行循环）

```
┌─────────────────────────────────────────────────┐
│ 进度条：第 2 步 / 共 5 步  ████░░░░░░░░  40%    │
├──────────┬──────────────────────────────────────┤
│ 步骤导航  │  当前步骤：② 横向对比品牌            │
│          │                                      │
│ ✓① 总览  │  ┌──────────────────────────────┐   │
│ ●② 横向  │  │ 思考链（可展开）8步          │   │
│ ○③ 下钻  │  │ SQL（可展开+复制）           │   │
│ ○④ 车型  │  │                              │   │
│ ○⑤ 策略  │  │  [图表区域：柱状图]          │   │
│          │  │                              │   │
│          │  │ 2025年Q2各品牌交付量对比...  │   │
│          │  │ 关键数字：埃安12,345 传祺... │   │
│          │  └──────────────────────────────┘   │
│          │                                      │
│          │  [重新执行本步]      [下一步 →]      │
└──────────┴──────────────────────────────────────┘
```

#### 阶段C：总结阶段

```
┌─────────────────────────────────────────────────┐
│ ✅ SOP 执行完成   总耗时：28秒                   │
│                                                 │
│  📊 关键发现汇总                                 │
│  ① 整体达成率87%，未达90%目标                    │
│  ② 传祺表现最差，达成率仅72%                     │
│  ③ 传祺在华南区域下滑最明显                      │
│  ④ 主要拖累车型是影豹，同比下降15%               │
│  ⑤ 建议：加大华南区域营销投入，优化影豹定价      │
│                                                 │
│  关键数字看板：                                  │
│  [整体达成率87%] [最低品牌传祺72%] [总交付45,678]│
│                                                 │
│  [重新运行]  [修改参数重跑]  [返回模板列表]      │
└─────────────────────────────────────────────────┘
```

**执行阶段核心交互**：
- 左侧步骤导航：已完成✓（绿色）、当前●（蓝色高亮）、未执行○（灰色）
- 点击已完成的步骤可回看结果（只读）
- 右侧结果区：思考链（默认折叠）→ SQL（可展开）→ 图表 → 结论
- 底部：「重新执行本步」+ 「下一步」
- 某步失败时：显示错误卡片 + 「重试」+ 「跳过此步」

---

## 四、SOP 执行引擎设计

### 4.1 核心原则

**复用现有 Text2SQL Workflow，不重新实现 NL2SQL。** SOP 执行引擎只做"步骤编排 + 变量替换 + 结果聚合"，实际的自然语言转SQL能力完全复用智能对话页的8步链路。

### 4.2 单步执行流程

```
输入：step_index, run_id, params
  ↓
1. 从 template_steps 表读取该步配置
   → step_name, query_template, step_type, expected_output
  ↓
2. 变量替换
   {{brand}} → params.brand（如"广汽埃安"）
   {{time}} → params.time_range（如"2025年Q2"）
   {{region}} → params.region（如"华南"）
   {{prev_result}} → 从 step_results[step_index-1] 提取的关键实体
  ↓
3. 得到替换后的自然语言问题
   示例："2025年Q2 广汽埃安的总交付量与预算目标达成率是多少？"
  ↓
4. 调用 Text2SQL Workflow（复用现有8步链路）
   意图识别→指标匹配→维度解析→表定位→SQL生成→执行校验→可视化决策→业务解读
  ↓
5. 得到完整结果
   { thinking_steps, sql, result{columns,rows}, chart_type, chart_config, conclusion, key_numbers }
  ↓
6. 存入 template_runs.step_results[step_index]（JSON）
  ↓
7. 返回完整结果给前端渲染
```

### 4.3 变量替换规则

| 变量 | 替换来源 | 示例 |
|---|---|---|
| `{{brand}}` | 运行参数 params.brand | "广汽埃安" / "全部品牌" |
| `{{time}}` | 运行参数 params.time_range | "2025年第二季度" / "上个月" |
| `{{region}}` | 运行参数 params.region | "华南区域" / "全部区域" |
| `{{prev_result}}` | 上一步结果中提取的关键实体 | "传祺"（从上一步"达成率最低的品牌"提取） |
| `{{metric}}` | 模板的 metric_key 对应的中文名 | "总交付量" |

**prev_result 提取规则**：
- 从上一步的 conclusion 中用正则匹配品牌名（埃安/传祺/昊铂）
- 匹配不到时用默认值"全部品牌"，并在思考链中注明"未提取到上一步结果，使用全部品牌"
- 产品理由：步骤间依赖是归因分析的核心（先找问题品牌再下钻），但提取失败不能阻断整个SOP，用默认值兜底

### 4.4 步骤类型与查询模板对应关系

| 步骤类型 | 图标 | 典型查询模板 | 期望输出 |
|---|---|---|---|
| overview 总览 | 🎯 | "{{time}} {{brand}}的{{metric}}与预算目标达成率是多少？" | KPI数字 |
| horizontal 横向对比 | ↔️ | "{{time}}各品牌的{{metric}}对比" | 柱状图 |
| drilldown 下钻 | 🔍 | "{{prev_result}}在各区域的{{metric}}表现如何？" | 柱状图/表格 |
| breakdown 拆解 | 🧩 | "{{prev_result}}按能源类型拆解{{metric}}" | 饼图/柱状图 |
| trend 趋势 | 📈 | "近6个月{{prev_result}}的{{metric}}趋势" | 折线图 |
| strategy 策略建议 | 💡 | （不执行SQL，由大模型基于前几步结果生成建议） | 文本 |

**strategy 类型特殊处理**：
- 不调用 Text2SQL，而是将前几步的 conclusion 拼接后调用大模型生成策略建议
- Prompt："基于以下经营分析发现，给出3条具体的策略建议：{前几步结论汇总}"

### 4.5 错误处理

| 错误场景 | 处理方式 |
|---|---|
| Text2SQL 返回错误 | 该步标记为 failed，显示错误原因 + 重试/跳过按钮 |
| SQL 执行超时（>30s） | 前端超时提示，后端设置 Text2SQL 调用超时30s |
| 结果为空 | 显示「当前条件下无数据」+ 建议调整参数，不算失败，可继续下一步 |
| 图表渲染失败 | 降级为表格展示原始数据 |
| 用户中途关闭页面 | 运行记录保持 running，下次进入可继续或重新开始 |

---

## 五、5个系统预设模板完整定义

### 5.1 高管季度复盘（preset_exec_quarterly，5步）

| 步 | 名称 | 类型 | 查询模板 | 聚焦维度 | 输出 |
|---|---|---|---|---|---|
| 0 | 整体达成率对标 | overview | "{{time}}全集团的{{metric}}与预算目标达成率是多少？" | 品牌、时间 | KPI |
| 1 | 横向对比品牌 | horizontal | "{{time}}各品牌的{{metric}}和营收对比，按达成率排序" | 品牌 | 柱状图 |
| 2 | 下钻问题品牌-区域 | drilldown | "达成率最低的品牌是{{prev_result}}，该品牌在各区域的{{metric}}表现如何？" | 品牌、区域 | 柱状图 |
| 3 | 下钻问题区域-车型 | drilldown | "{{prev_result}}区域表现最差，该区域各车型的{{metric}}如何？" | 区域、车型 | 表格 |
| 4 | 策略建议 | strategy | （基于前4步结果生成3条策略建议） | — | 文本 |

维度配置：品牌（必选）、区域、车型、时间（必选）

### 5.2 分析师深度下钻（preset_analyst_deepdive，5步）

| 步 | 名称 | 类型 | 查询模板 | 聚焦维度 | 输出 |
|---|---|---|---|---|---|
| 0 | 整体大盘 | overview | "{{time}}全集团{{metric}}整体表现" | 时间 | KPI |
| 1 | 按品牌横向 | horizontal | "{{time}}各品牌{{metric}}对比" | 品牌 | 柱状图 |
| 2 | 品牌×区域下钻 | drilldown | "{{prev_result}}品牌各区域{{metric}}分布" | 品牌、区域 | 热力图/表格 |
| 3 | 能源类型拆解 | breakdown | "{{prev_result}}区域按能源类型拆解{{metric}}" | 能源类型 | 饼图 |
| 4 | 价格段归因 | breakdown | 各价格段的{{metric}}贡献占比" | 价格段 | 柱状图 |

维度配置：品牌、区域、车型、能源类型、价格段、时间

### 5.3 区域总监KPI（preset_region_kpi，4步）

| 步 | 名称 | 类型 | 查询模板 | 聚焦维度 | 输出 |
|---|---|---|---|---|---|
| 0 | 区域整体达成 | overview | "{{time}}各区域{{metric}}达成率排名" | 区域、时间 | 排名表 |
| 1 | 区域横向对比 | horizontal | "{{time}}各区域{{metric}}和目标对比" | 区域 | 柱状图 |
| 2 | 区域-车型下钻 | drilldown | "{{prev_result}}区域各车型{{metric}}表现" | 区域、车型 | 柱状图 |
| 3 | 月度趋势 | trend | "近6个月{{prev_result}}区域{{metric}}趋势" | 时间、区域 | 折线图 |

维度配置：区域（必选）、车型、时间（必选）

### 5.4 车型经理产品复盘（preset_model_review，4步）

| 步 | 名称 | 类型 | 查询模板 | 聚焦维度 | 输出 |
|---|---|---|---|---|---|
| 0 | 车型大盘 | horizontal | "{{time}}各车型{{metric}}排名" | 车型 | 排名表 |
| 1 | 车型-价格段 | drilldown | "{{prev_result}}车型在各价格段的{{metric}}" | 车型、价格段 | 柱状图 |
| 2 | 能源类型对比 | breakdown | "{{prev_result}}车型按能源类型的{{metric}}对比" | 能源类型 | 饼图 |
| 3 | 策略建议 | strategy | （基于前3步生成产品定位建议） | — | 文本 |

维度配置：车型、价格段、能源类型

### 5.5 新能源专项（preset_ev_special，5步）

| 步 | 名称 | 类型 | 查询模板 | 聚焦维度 | 输出 |
|---|---|---|---|---|---|
| 0 | 新能源整体占比 | overview | "{{time}}新能源车型{{metric}}占总销量比例" | 能源类型 | KPI |
| 1 | 能源类型对比 | horizontal | "{{time}}纯电/插混/燃油的{{metric}}对比" | 能源类型 | 柱状图 |
| 2 | 价格段分布 | breakdown | 新能源车型各价格段{{metric}}分布" | 价格段 | 饼图 |
| 3 | 车型排名 | horizontal | "{{time}}新能源车型{{metric}}TOP5" | 车型 | 排名表 |
| 4 | 趋势追踪 | trend | "近6个月新能源{{metric}}渗透率趋势" | 时间 | 折线图 |

维度配置：能源类型、价格段、车型、时间

---

## 六、后端 API 设计（FastAPI）

### 6.1 模板 CRUD

#### GET /api/templates
获取模板列表
- Query：`type`（all/system/user，默认all）、`role`（可选筛选）
- 响应：
```json
{
  "templates": [
    {
      "id": "preset_exec_quarterly",
      "name": "高管季度复盘",
      "description": "...",
      "template_type": "role_default",
      "role": "executive",
      "metric_key": "delivered_units",
      "step_count": 5,
      "dimensions": ["brand","region","model","time"],
      "created_at": "2026-10-01"
    }
  ]
}
```

#### GET /api/templates/{template_id}
获取单个模板详情（含步骤和维度）
- 响应：模板基本信息 + steps数组 + dimensions数组

#### POST /api/templates
创建模板
- 请求体：
```json
{
  "name": "我的季度复盘",
  "description": "可选",
  "metric_key": "delivered_units",
  "dimensions": ["brand","region"]
}
```
- 行为：创建模板 + 自动插入3个默认步骤（总览/横向对比/策略建议）+ 插入维度
- 响应：`{ "template_id": "user_abc123", ... }`

#### PUT /api/templates/{template_id}
更新模板（全量更新步骤和维度）
- 请求体：完整的模板信息 + steps数组 + dimensions数组
- 权限校验：template_type=system 时拒绝更新（403）
- 行为：先删后插 steps 和 dimensions，更新 templates 主表

#### DELETE /api/templates/{template_id}
删除模板
- 权限校验：仅 template_type=user 且 creator=当前用户 可删除
- 行为：级联删除 steps、dimensions、runs

### 6.2 克隆

#### POST /api/templates/{template_id}/clone
克隆模板
- 行为：复制原模板的所有 steps 和 dimensions，生成新 template_id（user_前缀），名称加"副本"后缀，type=user，creator=当前用户
- 响应：`{ "template_id": "user_xyz789", "name": "高管季度复盘 副本" }`

### 6.3 SOP 运行

#### POST /api/templates/{template_id}/run
开始一次 SOP 运行
- 请求体：`{ "brand": "全部", "time_range": "上季度", "region": "全部" }`
- 行为：向 template_runs 插入记录，status=running
- 响应：`{ "run_id": "run_abc123" }`

#### POST /api/template-runs/{run_id}/steps/{step_index}/execute
执行单步
- 行为：变量替换 → 调用 Text2SQL Workflow → 存 step_results → 返回完整结果
- 响应：
```json
{
  "step_index": 0,
  "step_name": "整体达成率对标",
  "thinking_steps": [...],
  "sql": "WITH ...",
  "result": { "columns": [...], "rows": [...] },
  "chart_type": "single_kpi",
  "chart_config": {...},
  "conclusion": "2025年Q2整体达成率87%",
  "key_numbers": [{"label":"达成率","value":"87%"}]
}
```

#### GET /api/template-runs/{run_id}
获取运行状态和结果
- 响应：run基本信息 + status + current_step + step_results数组

#### GET /api/template-runs
获取运行历史列表
- Query：`template_id`（可选）、`limit`（默认20）
- 响应：运行记录列表（不含完整step_results，只含摘要）

---

## 七、与现有系统的集成点

| 集成点 | 调用方式 | 说明 |
|---|---|---|
| Text2SQL Workflow | 后端内部函数调用 | SOP单步执行时直接调用 `workflow.run(question)`，不通过HTTP自调用 |
| 语义层指标 | `GET /api/semantic/metrics` | 编辑器页的归因指标下拉选项来自语义层30个指标 |
| 图表渲染组件 | 前端组件复用 | 运行页的图表展示直接复用智能对话页的 `ChartRenderer` 组件 |
| 思考链组件 | 前端组件复用 | 运行页的思考链展示复用智能对话页的 `ThinkingChain` 组件 |
| 用户体系 | 请求头 token | 模板的 creator、runs 的 user_id 都来自当前登录用户 |
| 审计日志 | 后端中间件 | 模板的创建/修改/删除/运行操作写入审计日志 |

**产品理由**：最大化复用现有能力，归因模板的增量只在"步骤编排"和"参数管理"，NL2SQL 和图表渲染都是成熟能力。

---

## 八、持久化方案

1. **模板数据**：SQLite `app.db`，建表SQL见第一章
2. **运行历史**：SQLite `template_runs` 表，step_results 用 JSON 字段存储完整结果
3. **系统预设 seed**：应用启动时检查 templates 表为空则自动插入5个预设模板 + 对应步骤
4. **数据迁移**：本次重做直接清空旧的模板相关表（如果有），重建表结构 + seed，不做兼容迁移
5. **运行记录清理**：保留最近30天，超过的定时任务清理（或手动删除API）

---

## 九、创建模板完整流程编排（端到端）

### 9.1 流程状态机

```
[列表页] → 点击"新建我的模板"
  → [创建弹窗] 填写名称/指标/维度
  → 点击"创建并进入编辑器"
  → POST /api/templates（先保存基础信息+3个默认步骤）
  → 成功 → router.push(/templates/editor/{newId})
  → [编辑器页] GET /api/templates/{id} 加载数据
  → 用户编辑步骤（增删改排序）
  → 点击"保存" → PUT /api/templates/{id}
  → 成功 toast
  → 点击"返回" → router.push(/templates)
  → [列表页] 我的模板区域显示新模板
```

### 9.2 为什么"先创建再编辑"

创建弹窗只收集最基础的信息（名称+指标+维度），SOP步骤的编辑需要更大的操作空间（拖拽排序、多字段编辑），弹窗装不下。先创建一个带默认步骤的模板空壳，再进入完整编辑器逐步完善，避免用户在小弹窗里编辑复杂内容。

同时先保存再跳转确保了：即使用户进入编辑器后什么都不改就关闭，模板也已经存在于列表中，不会丢失。

### 9.3 克隆流程（与新建共用编辑器）

```
[市场页] → 点击"克隆为我的模板"
  → POST /api/templates/{id}/clone（后端复制所有步骤和维度）
  → 成功 → toast"克隆成功" → router.push(/templates)
  → [列表页] 我的模板显示"XX模板 副本"
  → 用户可点编辑进入编辑器修改
```

克隆后**跳回列表页不跳编辑器**，因为克隆的目的是快速得到可用模板，不是马上编辑。

### 9.4 异常处理

| 异常 | 处理 |
|---|---|
| 创建API失败 | 弹窗不关闭，显示错误，可重试 |
| 创建成功但跳转失败 | 停在列表页，toast提示创建成功 |
| 编辑器加载失败（ID不存在） | 404状态页 + 返回按钮 |
| 保存失败 | 显示错误，保留用户输入，可重试 |
| 未保存就离开 | beforeunload 提示 + 确认弹窗 |
| 重复点击创建 | 按钮loading期间禁用 |

---

## 十、运行 SOP 完整闭环流程（端到端）

### 10.1 流程状态机

```
[列表页] → 点击"运行SOP" → router.push(/templates/run/{templateId})
  → [准备阶段] GET /api/templates/{id} 加载SOP概览
  → 用户配置参数（品牌/时间/区域）
  → 点击"开始执行" → POST /api/templates/{id}/run → 返回run_id
  → [执行阶段] 循环每一步：
      POST /api/template-runs/{run_id}/steps/{index}/execute
        → 变量替换 query_template
        → 调用 Text2SQL Workflow
        → 存 step_results[index]
        → 返回结果 → 前端渲染（思考链+SQL+图表+结论）
      → 用户点击"下一步" → index+1
      → 某步失败 → 重试或跳过
  → 全部完成 → [总结阶段] 聚合各步关键发现
  → 更新 run.status=completed
  → 用户可重新运行 / 修改参数重跑 / 返回列表
  → 运行历史可查（GET /api/template-runs）
```

### 10.2 为什么需要参数配置

SOP步骤的查询模板里有 `{{brand}}`、`{{time}}` 等变量，执行前必须让用户指定上下文。否则"销量怎么样"这种问题没有时间和品牌范围，Text2SQL 无法生成准确SQL。

### 10.3 单步执行的数据流

```
前端 POST /execute
  → 后端读 step配置
  → 变量替换（brand/time/region/prev_result）
  → 调用 Text2SQL Workflow（8步链路）
  → 得到 {thinking_steps, sql, result, chart, conclusion}
  → 存入 template_runs.step_results[index]
  → 返回前端
  → 前端渲染：思考链(折叠) → SQL(可展开) → 图表 → 结论
```

**同步返回而非SSE**：SOP是分步执行的，每步之间有用户确认，不需要流式输出。同步返回更简单，结果可直接存数据库。耗时较长时（>5s）前端显示 loading。

### 10.4 步骤间依赖

第3步"下钻问题品牌-区域"需要知道第2步找出的"问题品牌是谁"。处理方式：
- 执行第N步时，从 step_results[N-1].conclusion 中正则提取品牌名
- 注入到 `{{prev_result}}` 变量
- 提取失败时用"全部品牌"兜底，在思考链注明

### 10.5 运行历史回看

点击历史记录 → 进入运行页 → 从 step_results 加载各步结果（只读模式）→ 不重新执行 → 支持逐步回看结果。

---

## 十一、实施顺序（5个 Phase）

| Phase | 内容 | 交付标准 | 预估 |
|---|---|---|---|
| **Phase 1 基础** | 建表 + seed数据 + 模板列表API + 列表页读真实数据 | 我的模板区域从数据库读取（即使为0），5个预设正确显示 | 1人天 |
| **Phase 2 创建链路** | 新建/克隆API + 编辑器页面 + 保存功能 | 从新建弹窗→创建→编辑器→保存→返回列表，全链路通，模板持久化 | 2人天 |
| **Phase 3 编辑删除** | 编辑API + 删除API + 列表页编辑/删除按钮 + 确认弹窗 | 自定义模板可编辑可删除，预设模板受保护 | 1人天 |
| **Phase 4 执行引擎** | 运行页面 + 步骤执行API + 调用Text2SQL + 结果展示 + 总结页 | 点击运行SOP→参数配置→逐步执行→看到图表结论→总结页 | 2人天 |
| **Phase 5 完善** | 运行历史 + 步骤间依赖 + 自动保存 + 错误处理优化 | 运行历史可查可回看，prev_result变量正常工作 | 1人天 |

**总计约7人天**。每阶段完成后用《归因模板测试用例集》回归验证。

---

## 十二、验收标准

| 编号 | 验收项 | 验证方法 |
|---|---|---|
| AC-01 | 5个预设模板在列表页正确显示 | 进入/templates，核对名称/步数/维度 |
| AC-02 | 新建模板持久化 | 新建→保存→刷新页面，模板仍在 |
| AC-03 | 克隆模板持久化 | 市场页克隆→返回列表，模板出现 |
| AC-04 | 编辑器页面可访问 | 点击编辑，进入编辑器页不404 |
| AC-05 | 运行页面可访问 | 点击运行SOP，进入运行页不404 |
| AC-06 | SOP可执行 | 运行SOP→配置参数→逐步执行→看到图表和结论 |
| AC-07 | 预设模板不可删 | 预设模板无删除按钮，调用DELETE API返回403 |
| AC-08 | 运行历史可查 | 完成一次运行后，在历史列表中能看到 |
| AC-09 | 每个模板用自己的ID跳转 | 5个模板的运行按钮跳转到不同URL |
| AC-10 | 数据刷新不丢失 | 任意操作后刷新页面，数据状态保持 |

---

> **PRD 结束**。开发按 Phase 1→5 顺序实施，每阶段完成后回归测试。
