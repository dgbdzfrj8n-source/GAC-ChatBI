# SDD-前端：归因模板模块前端详细设计

> **模块**：归因模板（Attribution Templates）
> **关联PRD**：归因模板模块PRD_v2.0
> **技术栈**：Next.js 14 App Router + TypeScript + TailwindCSS + ECharts

---

## 一、页面与路由

| 路由 | 文件路径 | 页面职责 |
|---|---|---|
| `/templates` | `app/templates/page.tsx` | 模板列表页（预设+我的模板） |
| `/templates/market` | `app/templates/market/page.tsx` | 模板市场页（预设详情+克隆） |
| `/templates/editor/[templateId]` | `app/templates/editor/[templateId]/page.tsx` | 模板编辑器页 |
| `/templates/run/[templateId]` | `app/templates/run/[templateId]/page.tsx` | SOP运行页 |

---

## 二、目录结构

```
app/templates/
├── page.tsx                    # 列表页
├── market/page.tsx             # 市场页
├── editor/[templateId]/page.tsx # 编辑器页
└── run/[templateId]/page.tsx   # 运行页

components/templates/
├── TemplateCard.tsx            # 模板卡片（列表页用）
├── TemplateMarketCard.tsx      # 模板详情卡片（市场页用）
├── StepList.tsx                # 编辑器左侧步骤列表
├── StepEditor.tsx              # 编辑器右侧步骤编辑表单
├── RunProgressBar.tsx          # 运行页顶部进度条
├── RunStepNav.tsx              # 运行页左侧步骤导航
├── RunStepResult.tsx           # 运行页右侧结果展示
├── RunSummary.tsx              # 运行页总结阶段
├── CreateTemplateModal.tsx     # 新建模板弹窗
└── DeleteConfirmModal.tsx      # 删除确认弹窗

lib/templates/
├── api.ts                      # 归因模板API封装
├── types.ts                    # TypeScript类型定义
└── utils.ts                    # 工具函数
```

---

## 三、TypeScript 类型定义

```typescript
// lib/templates/types.ts
export interface Template {
  id: string;
  name: string;
  description: string;
  template_type: 'system' | 'role_default' | 'user';
  role: string;
  metric_key: string;
  step_count: number;
  dimensions: string[];
  created_at: string;
}

export interface TemplateDetail extends Template {
  steps: TemplateStep[];
  dimensions: TemplateDimension[];
}

export interface TemplateStep {
  step_order: number;
  step_name: string;
  step_icon: string;
  step_type: 'overview' | 'horizontal' | 'drilldown' | 'breakdown' | 'trend' | 'strategy';
  query_template: string;
  dimension_hints: string[];
  expected_output: 'kpi' | 'bar' | 'line' | 'pie' | 'table' | 'text';
  is_auto_execute: number;
}

export interface TemplateDimension {
  dimension_key: string;
  dimension_name: string;
  is_required: number;
}

export interface StepResult {
  step_name: string;
  step_type: string;
  status: 'success' | 'failed' | 'skipped';
  replaced_question?: string;
  thinking_steps?: any[];
  sql?: string | null;
  result?: { columns: string[]; rows: any[] } | null;
  chart_type?: string | null;
  chart_config?: any | null;
  conclusion?: string;
  key_numbers?: { label: string; value: string }[];
  error?: string;
  duration_ms: number;
}

export interface RunParams {
  brand: string;
  time_range: string;
  region: string;
}

export interface RunRecord {
  run_id: string;
  template_id: string;
  status: 'running' | 'completed' | 'failed';
  current_step: number;
  params: RunParams;
  step_results: StepResult[];
  total_duration_ms: number;
  started_at: string;
  completed_at: string | null;
}
```

---

## 四、API 封装

```typescript
// lib/templates/api.ts
const BASE = '/api';

export const templateApi = {
  // 模板列表
  list: (type = 'all', role?: string) =>
    fetch(`${BASE}/templates?type=${type}${role ? `&role=${role}` : ''}`).then(r => r.json()),

  // 模板详情
  get: (templateId: string) =>
    fetch(`${BASE}/templates/${templateId}`).then(r => r.json()),

  // 创建模板
  create: (data: { name: string; description?: string; metric_key?: string; dimensions?: string[] }) =>
    fetch(`${BASE}/templates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => r.json()),

  // 更新模板
  update: (templateId: string, data: any) =>
    fetch(`${BASE}/templates/${templateId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }).then(r => r.json()),

  // 删除模板
  remove: (templateId: string) =>
    fetch(`${BASE}/templates/${templateId}`, { method: 'DELETE' }).then(r => r.json()),

  // 克隆模板
  clone: (templateId: string) =>
    fetch(`${BASE}/templates/${templateId}/clone`, { method: 'POST' }).then(r => r.json()),

  // 开始运行
  startRun: (templateId: string, params: RunParams) =>
    fetch(`${BASE}/templates/${templateId}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }).then(r => r.json()),

  // 执行单步
  executeStep: (runId: string, stepIndex: number, params: RunParams) =>
    fetch(`${BASE}/template-runs/${runId}/steps/${stepIndex}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    }).then(r => r.json()),

  // 获取运行状态
  getRun: (runId: string) =>
    fetch(`${BASE}/template-runs/${runId}`).then(r => r.json()),

  // 运行历史
  listRuns: (templateId?: string, limit = 20) =>
    fetch(`${BASE}/template-runs?limit=${limit}${templateId ? `&template_id=${templateId}` : ''}`).then(r => r.json()),
};
```

---

## 五、页面详细设计

### 5.1 模板列表页（/templates）

#### 页面状态

```typescript
const [templates, setTemplates] = useState<Template[]>([]);
const [userTemplates, setUserTemplates] = useState<Template[]>([]);
const [currentRole, setCurrentRole] = useState('executive');
const [showCreateModal, setShowCreateModal] = useState(false);
const [deleteTarget, setDeleteTarget] = useState<Template | null>(null);
const [loading, setLoading] = useState(true);
```

#### 页面加载

```typescript
useEffect(() => {
  Promise.all([
    templateApi.list('system'),  // 系统预设+角色默认
    templateApi.list('user'),    // 我的模板
  ]).then(([sysRes, userRes]) => {
    setTemplates(sysRes.templates);
    setUserTemplates(userRes.templates);
    setLoading(false);
  });
}, []);
```

#### 角色默认模板映射

```typescript
const ROLE_DEFAULT_MAP: Record<string, string> = {
  executive: 'preset_exec_quarterly',
  analyst: 'preset_analyst_deepdive',
  product_manager: 'preset_region_kpi',
  guest: 'preset_exec_quarterly',
};
```

#### 模板卡片组件（TemplateCard）

Props：`template: Template`、`isDefault: boolean`、`onRun: () => void`、`onEdit?: () => void`、`onDelete?: () => void`

渲染内容：
- 卡片头部：模板名称 + 角色默认标签（isDefault时）
- 描述（1行，line-clamp-1）
- SOP步数标签：`📋 {step_count} 步 SOP`
- 维度标签：前3个维度，超出显示"+N"
- 底部操作区：
  - 预设模板：绿色「运行 SOP」按钮 + 灰色「🔒 系统预设」文字
  - 自定义模板：「运行 SOP」+ 编辑图标 + 删除图标

#### 运行按钮点击

```typescript
const handleRun = (templateId: string) => {
  router.push(`/templates/run/${templateId}`);
};
```

**关键**：每个模板用自己的 id，不硬编码 preset_exec_quarterly。

#### 新建模板弹窗（CreateTemplateModal）

表单字段：
- 模板名称（文本输入，必填，maxLength=50）
- 描述（文本域，可选）
- 归因指标（下拉，选项来自语义层，默认"总交付量"）
- 初始维度（多选checkbox：品牌/区域/车型/能源类型/价格段/时间，最多4个，默认勾选品牌+区域）

提交逻辑：
```typescript
const handleSubmit = async () => {
  if (!name.trim()) return;
  setSubmitting(true);
  const res = await templateApi.create({ name, description, metric_key: metricKey, dimensions });
  setSubmitting(false);
  if (res.template_id) {
    toast.success('创建成功');
    setShowCreateModal(false);
    router.push(`/templates/editor/${res.template_id}`);  // 先创建成功再跳编辑器
  }
};
```

**关键**：先调API创建成功，拿到 template_id 后才跳转编辑器。不允许直接跳编辑器而不创建。

#### 删除确认弹窗

- 显示"确定删除模板「XX」吗？删除后不可恢复。"
- 确认 → 调 DELETE API → 成功 → 刷新列表 → toast
- 取消 → 关闭弹窗

---

### 5.2 模板市场页（/templates/market）

#### 页面结构

- 顶部：「← 返回模板中心」按钮 + 标题「模板市场」+ 副标题
- 主体：2列网格，5个模板详情卡片

#### 模板详情卡片（TemplateMarketCard）

Props：`template: TemplateDetail`

渲染内容：
- 模板名称 + 描述
- 步骤化SOP详情：竖向列表，每步显示序号 + 图标 + 步骤名称
- 聚合维度标签
- 底部「克隆为我的模板」蓝色按钮

#### 克隆逻辑

```typescript
const handleClone = async (templateId: string) => {
  setCloningId(templateId);
  const res = await templateApi.clone(templateId);
  setCloningId(null);
  if (res.template_id) {
    toast.success(`已克隆「${res.name}」到我的模板`);
    setTimeout(() => router.push('/templates'), 1500);  // 成功后跳回列表页
  }
};
```

**关键**：克隆成功后跳回列表页，**不跳编辑器**。

---

### 5.3 模板编辑器页（/templates/editor/[templateId]）

#### 页面状态

```typescript
const [template, setTemplate] = useState<TemplateDetail | null>(null);
const [currentStepIndex, setCurrentStepIndex] = useState(0);
const [dirty, setDirty] = useState(false);  // 是否有未保存修改
const [saving, setSaving] = useState(false);
const [loading, setLoading] = useState(true);
```

#### 页面加载

```typescript
const { templateId } = useParams();
useEffect(() => {
  templateApi.get(templateId as string).then(data => {
    setTemplate(data);
    setLoading(false);
  }).catch(() => {
    // 模板不存在，显示404
    setNotFound(true);
    setLoading(false);
  });
}, [templateId]);
```

#### 三栏布局

```
┌──────────────────────────────────────────────────────────┐
│ ← 返回  [模板名称输入框]  [归因指标下拉]        [保存]    │
├──────────┬───────────────────────────────────────────────┤
│ 步骤列表  │  步骤详情编辑区                                │
│          │                                               │
│ ① 总览   │  步骤名称：[____________]                      │
│ ② 横向   │  步骤图标：[🎯] (emoji选择)                    │
│ ③ 下钻   │  步骤类型：[总览 ▾]                            │
│ ④ 车型   │  查询模板：                                    │
│ ⑤ 策略   │  [{{time}} {{brand}}的{{metric}}...        ]  │
│          │  聚焦维度：[品牌][区域][车型] (多选)            │
│ [+添加]  │  期望输出：[KPI数字 ▾]                         │
│          │  自动执行：[开关]                              │
│          │                                               │
│          │  [删除此步骤]                                  │
└──────────┴───────────────────────────────────────────────┘
```

#### 左侧步骤列表（StepList）

- 每步显示：序号 + 步骤名称
- 当前步高亮（蓝色背景）
- 点击切换 currentStepIndex
- 支持上移/下移按钮（或拖拽排序，Phase 5实现）
- 底部「+ 添加步骤」按钮，在末尾新增一步（默认overview类型）
- 至少保留1步，最后1步的删除按钮禁用

#### 右侧步骤编辑（StepEditor）

字段与 TemplateStep 对应：
- step_name：文本输入
- step_icon：6个emoji按钮选择（🎯↔️🔍🧩📈💡）
- step_type：下拉6选1
- query_template：多行文本域，placeholder提示可用变量 {{brand}}/{{time}}/{{region}}/{{prev_result}}/{{metric}}
- dimension_hints：多选checkbox
- expected_output：下拉
- is_auto_execute：开关

**任何字段修改都设置 dirty=true**

#### 保存逻辑

```typescript
const handleSave = async () => {
  if (!template || !dirty) return;
  setSaving(true);
  await templateApi.update(template.id, {
    name: template.name,
    description: template.description,
    metric_key: template.metric_key,
    steps: template.steps,
    dimensions: template.dimensions,
  });
  setSaving(false);
  setDirty(false);
  toast.success('保存成功');
};
```

#### 返回逻辑（未保存提示）

```typescript
const handleBack = () => {
  if (dirty) {
    if (confirm('有未保存的修改，确定离开吗？')) {
      router.push('/templates');
    }
  } else {
    router.push('/templates');
  }
};
```

---

### 5.4 SOP运行页（/templates/run/[templateId]）

#### 页面三阶段状态机

```typescript
type RunPhase = 'prepare' | 'executing' | 'summary';
const [phase, setPhase] = useState<RunPhase>('prepare');
```

#### 阶段A：准备阶段

页面内容：
- 「← 返回列表」
- 模板名称 + 描述
- SOP步骤列表（只读展示，每步序号+图标+名称）
- 参数配置区：
  - 品牌下拉（全部/广汽埃安/广汽传祺/昊铂），默认全部
  - 时间范围下拉（本月/上月/本季度/上季度/今年/去年），默认上季度
  - 区域下拉（全部/华东/华南/华北/西南/华中），默认全部
- 底部「开始执行」主按钮 + 预计耗时提示

开始执行逻辑：
```typescript
const handleStart = async () => {
  setStarting(true);
  const res = await templateApi.startRun(templateId, params);
  setRunId(res.run_id);
  setCurrentStepIndex(0);
  setStepResults([]);
  setPhase('executing');
  setStarting(false);
  // 自动执行第一步
  executeStep(0);
};
```

#### 阶段B：执行阶段

页面布局：
```
┌─────────────────────────────────────────────────┐
│ 进度条：第 2 步 / 共 5 步  ████░░░░  40%        │
├──────────┬──────────────────────────────────────┤
│ 步骤导航  │  当前步骤：② 横向对比品牌            │
│          │                                      │
│ ✓① 总览  │  ┌────────────────────────────┐     │
│ ●② 横向  │  │ 思考链（折叠，可展开）      │     │
│ ○③ 下钻  │  │ SQL（折叠，可展开+复制）   │     │
│ ○④ 车型  │  │                              │     │
│ ○⑤ 策略  │  │  [图表区域]                 │     │
│          │  │                              │     │
│          │  │ 结论文字 + 关键数字高亮      │     │
│          │  └────────────────────────────┘     │
│          │                                      │
│          │  [重新执行本步]      [下一步 →]      │
└──────────┴──────────────────────────────────────┘
```

**单步执行逻辑**：
```typescript
const executeStep = async (index: number) => {
  setStepLoading(true);
  const result = await templateApi.executeStep(runId, index, params);
  setStepLoading(false);
  setStepResults(prev => {
    const next = [...prev];
    next[index] = result;
    return next;
  });
};

const handleNext = () => {
  const nextIndex = currentStepIndex + 1;
  if (nextIndex >= template.steps.length) {
    setPhase('summary');  // 全部完成，进入总结
  } else {
    setCurrentStepIndex(nextIndex);
    executeStep(nextIndex);  // 自动执行下一步
  }
};
```

**步骤导航点击**：
- 点击已完成的步骤（✓）→ 切换到该步，展示已保存的结果（不重新执行）
- 点击当前步（●）→ 无变化
- 点击未执行步（○）→ 不允许跳转，提示"请按顺序执行"

**结果展示组件（RunStepResult）**：
- 思考链：默认折叠，展开显示8步，每步名称+耗时（复用智能对话页的 ThinkingChain 组件）
- SQL：默认折叠，展开显示SQL代码 + 复制按钮（复用智能对话页的 SqlViewer 组件）
- 图表：根据 chart_type 渲染（复用智能对话页的 ChartRenderer 组件）
  - single_kpi → 大数字卡片
  - bar → ECharts 柱状图
  - line → ECharts 折线图
  - pie → ECharts 饼图
  - table → 数据表格
  - text → 纯文字（策略步骤）
- 结论：大模型生成的1-2句解读，关键数字高亮标签
- 失败状态：红色错误卡片 + 错误原因 + 「重试」+ 「跳过此步」按钮

**跳过逻辑**：
```typescript
const handleSkip = () => {
  setStepResults(prev => {
    const next = [...prev];
    next[currentStepIndex] = { status: 'skipped', step_name: template.steps[currentStepIndex].step_name, duration_ms: 0 };
    return next;
  });
  handleNext();
};
```

#### 阶段C：总结阶段

页面内容：
- ✅ SOP执行完成 + 总耗时
- 成功/失败/跳过步数统计
- 关键发现汇总：每步结论的第一句话，编号列表
- 关键数字看板：前6个 key_numbers，卡片式展示
- 操作按钮：「重新运行」（回到准备阶段）、「修改参数重跑」（回到准备阶段，保留参数）、「返回模板列表」

---

## 六、复用现有组件

| 现有组件 | 复用位置 | 说明 |
|---|---|---|
| ChartRenderer | RunStepResult | 图表渲染，支持kpi/bar/line/pie/table |
| ThinkingChain | RunStepResult | 思考链折叠展示 |
| SqlViewer | RunStepResult | SQL查看+复制 |
| KeyNumberTag | RunStepResult/RunSummary | 关键数字高亮标签 |
| Toast | 全局 | 操作成功/失败提示 |
| ConfirmModal | 列表页 | 删除确认 |
| LoadingSpinner | 各页面 | 加载中状态 |

---

## 七、错误处理

| 场景 | 处理方式 |
|---|---|
| 模板列表加载失败 | 显示错误提示 + 重试按钮 |
| 编辑器加载模板404 | 显示404状态页 + 返回列表按钮 |
| 保存失败 | toast错误，保留用户输入，可重试 |
| 删除失败 | toast错误 |
| 克隆失败 | toast错误，按钮恢复可点击 |
| 开始运行失败 | toast错误，停留在准备阶段 |
| 单步执行失败 | 结果区显示错误卡片 + 重试/跳过 |
| 网络中断 | 全局错误提示，已执行的步骤结果保留 |

---

## 八、与后端接口契约

| 前端调用 | 后端接口 | 关键参数 |
|---|---|---|
| 列表加载 | GET /api/templates | type=system/user |
| 编辑器加载 | GET /api/templates/{id} | — |
| 新建提交 | POST /api/templates | name/description/metric_key/dimensions |
| 保存编辑 | PUT /api/templates/{id} | 完整模板+步骤+维度 |
| 删除 | DELETE /api/templates/{id} | — |
| 克隆 | POST /api/templates/{id}/clone | — |
| 开始运行 | POST /api/templates/{id}/run | brand/time_range/region |
| 执行单步 | POST /api/template-runs/{runId}/steps/{index}/execute | params |
| 运行状态 | GET /api/template-runs/{runId} | — |

---

> **前端SDD结束**。算法细节见 SDD-算法，后端实现见 SDD-后端。
