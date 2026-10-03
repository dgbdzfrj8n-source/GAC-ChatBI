# 报表中心改造方案 — Sprint 8 路线图

> **状态**：方案文档（不动代码）
> **目标读者**：AI 产品经理、后端 / 前端工程师
> **背景**：上一轮诊断确认 6 个详情页全部复用同一份 `SnapshotBoard`、同一份 `/api/dashboard/snapshot` 数据，导致每张报表点进去看到的内容完全相同。本方案彻底解决这个问题。

---

## 0. 一句话总结

> **6 张报表 = 6 个独立的"报表契约（report contract）"，每个契约定义自己的 SQL / 数据形态 / 可视化形态，前端按契约渲染。后端不复用驾驶舱接口，而是开 6 条独立端点。**

---

## 1. 问题回顾（不再长篇解释）

| # | 现象 | 根因 |
|---|---|---|
| 1 | 6 张报表数据完全一样 | 全部走 `/api/dashboard/snapshot` |
| 2 | UI 从浅色跳到暗色，视觉突兀 | `SnapshotBoard` 强制暗色，与列表页浅色风格断裂 |
| 3 | 6 个详情页除了标题文字没有任何差别 | 6 个 page.tsx 只是 SnapshotBoard 的不同 prop |

---

## 2. 设计原则

1. **报表 ≠ 仪表盘**：报表必须有自己的"业务问题"和"输出形态"，不允许任何 2 张报表调同一个端点。
2. **口径统一**：所有报表的指标计算全部走 `metrics_dict.json` 已定义的 M01–M06，不得私自改 SQL。
3. **DuckDB 规范 + 只读**：`STRFTIME`、`NULLIF`、`TRY_CAST` 等防御性写法统一沿用；任何报表端点都不得执行 DDL/DML。
4. **视觉一致性**：所有报表详情页统一一种风格（推荐沿用 dashboard 的暗色驾驶舱），但列表页 → 详情页之间必须有视觉过渡（推荐浅色 → 暗色的渐变 banner）。
5. **可降级**：每张报表自带 Mock 数据，后端接口不通时前端自动降级到 Mock 演示模式，但 Mock 必须"长得像真报表"。

---

## 3. 整体架构

```
┌────────────────────────────────────────────────────────────────────────┐
│  前端                                                                   │
│                                                                        │
│  /reports                       浅色报表中心（保留现状）                  │
│  /reports/[id]                  ReportDetailPage 路由组件                │
│      └─ <ReportRenderer reportId={id} />    单一渲染入口，按 contract 切换 │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ HTTP (JSON)
┌────────────────────────────────────────────────────────────────────────┐
│  后端 (FastAPI)                                                         │
│                                                                        │
│  GET /api/reports/registry                       6 张报表的元信息清单     │
│  GET /api/reports/{report_id}?month=YYYY-MM      单张报表完整 payload    │
│                                                                        │
│  ReportExecutor (新模块)                                                │
│      ├─ 按 report_id 路由到 6 个独立 builder                              │
│      └─ 每个 builder 调 SQLExecutor 执行 DuckDB 只读查询                  │
└────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                              DuckDB
                          (backend/data/*.parquet)
```

**关键变化**：

- 旧的 `/api/dashboard/snapshot` 保留不动（dashboard 主页继续用）
- 新增 `/api/reports/registry` + `/api/reports/{id}` 两套端点
- 新增后端模块 `backend/core/report_executor.py`，**不复用 SOP 归因引擎、不复用 dashboard snapshot builder**

---

## 4. 6 张报表契约（Report Contracts）

每张报表契约至少包含 5 个字段：`title / subtitle / summary_cards[] / charts[] / mock_payload`。下面是 6 张报表的设计草案。

### 4.1 预算达成分析 `budget-fulfillment`

| 字段 | 设计 |
|---|---|
| **业务问题** | 本月各品牌预算完成进度如何？哪些品牌 / 大区低于 90%？ |
| **数据形态** | 按 `brand_name × region × vehicle_model` 三维聚合，输出 `target / actual / fulfillment_rate` |
| **SQL 主轴** | 复用 `metrics_dict.json` 的 `M01_fulfillment_rate_pct` 口径 |
| **前端组件** | 1 张左对齐 KPI 卡（综合达成率）+ 1 张品牌达成率横向条形图 + 1 张大区达成率树状图 |
| **交互** | KPI 卡可点 → 跳到详情维度的明细表 |
| **Mock 数据** | 3 品牌 × 7 大区 × 5 车型 = 105 行 |

### 4.2 销量归因分析 `sales-attribution`

| 字段 | 设计 |
|---|---|
| **业务问题** | 销量同比 / 环比波动，根因来自渠道 / 大区 / 价格 / 产品哪个维度？ |
| **数据形态** | 4 个归因维度并行展示：渠道贡献 / 大区贡献 / 价格带贡献 / 车型贡献 |
| **SQL 主轴** | `M03`（销量）+ `M04`（均价） |
| **前端组件** | 4 列瀑布图（waterfall）并排，每列代表一个归因维度的"贡献度 = 实际 − 预期" |
| **交互** | 点击瀑布图某一柱 → 跳到对应维度的明细（如"渠道贡献 −120 辆" → 跳到渠道明细） |
| **Mock 数据** | 4 个维度各 8 行 |

### 4.3 渠道投放 ROI `channel-roi`

| 字段 | 设计 |
|---|---|
| **业务问题** | 哪个营销渠道的 CPL 最低、转化率最高？ |
| **数据形态** | 按 `channel_name` 聚合，输出 `spend_wan / leads / conversions / cpl / conversion_rate / roi` |
| **SQL 主轴** | 新增 metric `M07_channel_roi`，需要在 `metrics_dict.json` 中追加定义 |
| **前端组件** | 渠道横向对比表（带排序、Top/Bottom 高亮）+ CPL 散点图（气泡 = 渠道，气泡大小 = 投放金额） |
| **交互** | 表格支持列排序、筛选；点击渠道名 → 跳到该渠道的"投放 → 线索 → 成交"链路图 |
| **Mock 数据** | 6 个渠道 |

### 4.4 库存预警 `inventory-warning`

| 字段 | 设计 |
|---|---|
| **业务问题** | 哪些经销商的库存周转天数 > 60？哪些车型库存系数 > 1.5？ |
| **数据形态** | 经销商 × 车型双层聚合，输出 `inventory_count / turnover_days / coefficient / status`（`status = normal / warning / alert`） |
| **SQL 主轴** | 新增 `M08_inventory_turnover_days` + `M09_inventory_coefficient` |
| **前端组件** | 热力图（行 = 车型，列 = 大区，颜色 = 库存系数）+ 预警清单表（按周转天数倒序） |
| **交互** | 点击热力图格子 → 筛选出该车型 × 大区的经销商明细 |
| **Mock 数据** | 7 大区 × 8 车型 + 30 条预警清单 |

### 4.5 客流转化漏斗 `conversion-funnel`

| 字段 | 设计 |
|---|---|
| **业务问题** | 从客流 → 留资 → 试驾 → 成交，每一步的转化率与流失率？ |
| **数据形态** | 4 级漏斗：客流 → 留资 → 试驾 → 成交，含 step-over-step 转化率 |
| **SQL 主轴** | 新增 `M10_funnel_step_conversion`，从 `store_visit` + `lead` + `test_drive` + `order` 4 张表聚合 |
| **前端组件** | 横向漏斗图（横向步骤，每段标注绝对值与转化率）+ 流失环节 Top3 排名 |
| **交互** | 点击流失环节 → 跳到该环节的"流失原因分布"（来自 NL2SQL 自然语言查询） |
| **Mock 数据** | 4 级漏斗，每级含 30 大区明细 |

### 4.6 大区销售排行 `regional-ranking`

| 字段 | 设计 |
|---|---|
| **业务问题** | 7 大区销售业绩排名 + 同比 / 环比 / 达成率多维对比 |
| **数据形态** | 按 `region` 聚合，输出 `units / revenue / yoy_pct / mom_pct / fulfillment_rate` |
| **SQL 主轴** | `M01` + `M03` + `M06`（同比环比） |
| **前端组件** | 7 行卡片网格（每大区一张），支持按 KPI 切换排序 + 同比 / 环比趋势小图 |
| **交互** | 点击大区卡 → 跳到该大区的"销售明细"页（路由预留） |
| **Mock 数据** | 7 大区，每大区 12 个月趋势 |

---

## 5. 后端 API 设计

### 5.1 端点清单

| Method | Path | 说明 |
|---|---|---|
| GET | `/api/reports/registry` | 返回 6 张报表的元信息（id / name / category / description / icon / status: ready/mocked） |
| GET | `/api/reports/{report_id}?month=YYYY-MM` | 返回某张报表的完整 payload（统一 schema） |

### 5.2 统一 Response Schema

```python
# backend/api/schemas.py 新增

class ReportKpi(BaseModel):
    label: str              # "综合达成率"
    value: float | int | str # 99.25 / 8498 / "¥129"
    unit: str = ""          # "%" / "辆" / "万"
    trend: Literal["up", "down", "flat"] | None = None
    hint: str | None = None # "高于阈值"

class ReportChart(BaseModel):
    chart_type: Literal[
        "bar", "line", "pie", "scatter", "heatmap",
        "funnel", "waterfall", "table", "ranking"
    ]
    title: str              # "品牌达成率横向对比"
    data: list[dict]        # ECharts 友好的 list of dict
    columns: list[str]
    x_axis: str | None = None
    y_axis: str | None = None
    series: list[str] | None = None

class ReportAlert(BaseModel):
    level: Literal["info", "warning", "alert"]
    title: str
    body: str
    link: str | None = None

class ReportPayload(BaseModel):
    report_id: str
    title: str
    subtitle: str
    month: str
    generated_at: datetime
    is_mocked: bool         # True 表示当前是 Mock 数据
    kpis: list[ReportKpi]
    charts: list[ReportChart]
    alerts: list[ReportAlert] = []

class ReportRegistryItem(BaseModel):
    report_id: str
    name: str
    category: str
    description: str
    icon: str
    status: Literal["ready", "mocked", "wip"]
    estimated_sprint: str   # "Sprint 8.1" / "Sprint 8.2"

class ReportRegistryResponse(BaseModel):
    items: list[ReportRegistryItem]
```

### 5.3 模块结构

```
backend/core/
    report_executor.py        # 路由入口
    report_builders/
        __init__.py
        budget_fulfillment.py
        sales_attribution.py
        channel_roi.py
        inventory_warning.py
        conversion_funnel.py
        regional_ranking.py
    report_mocks/
        __init__.py
        budget_fulfillment.json
        sales_attribution.json
        channel_roi.json
        inventory_warning.json
        conversion_funnel.json
        regional_ranking.json
```

### 5.4 ReportExecutor 核心逻辑（伪代码）

```python
# backend/core/report_executor.py

REPORT_BUILDERS: dict[str, Callable[[str], ReportPayload]] = {
    "budget-fulfillment": build_budget_fulfillment,
    "sales-attribution":  build_sales_attribution,
    "channel-roi":        build_channel_roi,
    "inventory-warning":  build_inventory_warning,
    "conversion-funnel":  build_conversion_funnel,
    "regional-ranking":   build_regional_ranking,
}

class ReportExecutionError(Exception): pass

def execute_report(report_id: str, month: str) -> ReportPayload:
    if report_id not in REPORT_BUILDERS:
        raise HTTPException(404, f"未知报表 ID: {report_id}")
    try:
        return REPORT_BUILDERS[report_id](month)
    except DuckDBError as e:
        # SQL 失败 → 返回 Mock 数据，is_mocked=True
        return load_mock(report_id, month)
```

每个 builder 必须遵守：
1. 只允许 `SQLExecutor.execute_readonly(sql, params)` 这一个 DB 出口
2. 不允许 `INSERT / UPDATE / DELETE / DROP`
3. SQL 必须能放进 `metrics_dict.json` 已定义的指标口径（不允许私自造口径）
4. 计算失败时 fallback 到该报表对应的 `report_mocks/{id}.json`

### 5.5 SQL 模板示例（仅 1 张，给后端工程师参考）

```sql
-- budget_fulfillment.py
SELECT
    b.brand_name,
    r.region_name,
    SUM(s.target_units) AS target,
    SUM(s.actual_units) AS actual,
    CASE
        WHEN SUM(s.target_units) = 0 THEN NULL
        ELSE ROUND(SUM(s.actual_units) * 100.0 / SUM(s.target_units), 2)
    END AS fulfillment_rate_pct
FROM sales_monthly s
JOIN dim_brand b ON s.brand_id = b.brand_id
JOIN dim_region r ON s.region_id = r.region_id
WHERE STRFTIME(s.sale_date, '%Y-%m') = ?
GROUP BY b.brand_name, r.region_name
ORDER BY fulfillment_rate_pct ASC;  -- 弱项排前面
```

---

## 6. 前端改造方案

### 6.1 路由结构（不变）

```
/reports                  → 浅色报表中心（保持现状）
/reports/[id]             → 浅色 → 暗色渐变过渡 → ReportRenderer
```

### 6.2 视觉过渡设计（解决"突兀"问题）

把"详情页"分成 3 段，每段有明确视觉权责：

```
┌──────────────────────────────────────────────────┐
│  Section 1: 浅色 Banner（Hero）                   │
│  - 报表标题（大字）                                │
│  - 报表副标题（业务问题）                          │
│  - 业务说明（3 行）                                │
│  - 月份选择器 + 返回按钮                           │
│  - 背景：白 / 极浅灰（与 /reports 列表同色系）    │
└──────────────────────────────────────────────────┘
            ▼ 渐变（from-slate-100 to-slate-900）
┌──────────────────────────────────────────────────┐
│  Section 2: 暗色 KPI 行（与 dashboard 同款色）    │
│  - 4 张 KPI 卡片                                  │
│  - 背景：slate-900                                │
└──────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────┐
│  Section 3: 暗色图表区                            │
│  - 2~3 个 ReportChart 渲染                        │
│  - 背景：slate-900                                │
└──────────────────────────────────────────────────┘
            ▼ 渐变（from-slate-900 to-slate-100）
┌──────────────────────────────────────────────────┐
│  Section 4: 浅色预警清单 + 行动建议                │
│  - 报表专属的预警列表                              │
│  - 下一步行动按钮（导出 / 订阅占位）              │
└──────────────────────────────────────────────────┘
```

**这套 4 段式的好处**：

1. 浅色 → 暗色 → 浅色形成"沙漏"形视觉节奏，不像现在直接"啪"的一下跳到暗色
2. 每张报表都可以共享同一套过渡壳，只换内部 Section 2/3 的具体内容
3. 跟 `/reports` 列表的浅色 + dashboard 的暗色都能自然衔接

### 6.3 ReportRenderer 组件

```tsx
// frontend/src/components/reports/ReportRenderer.tsx
'use client';

interface Props {
  reportId: string;          // "budget-fulfillment" / "channel-roi" / ...
  reportMeta: ReportMeta;    // 由 /api/reports/registry 拿到
}

export default function ReportRenderer({ reportId, reportMeta }: Props) {
  const [payload, setPayload] = useState<ReportPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [month, setMonth] = useState('2025-03');

  useEffect(() => {
    fetch(`${API_URL}/api/reports/${reportId}?month=${month}`, { cache: 'no-store' })
      .then(r => r.json())
      .then(data => { setPayload(data); setLoading(false); })
      .catch(() => { /* 失败 → ReportRenderer 内部自带 Mock */ });
  }, [reportId, month]);

  if (loading || !payload) return <LoadingHero />;

  return (
    <>
      <LightBanner reportMeta={reportMeta} month={month} onMonthChange={setMonth} />
      <KpiRow kpis={payload.kpis} />
      <ChartGrid charts={payload.charts} />
      <AlertList alerts={payload.alerts} />
    </>
  );
}
```

### 6.4 6 个详情页变成"薄壳"

```tsx
// frontend/src/app/reports/budget-fulfillment/page.tsx  (改造后)
import ReportRenderer from '@/components/reports/ReportRenderer';
import { REPORT_REGISTRY } from '@/lib/reportRegistry';

export default function Page() {
  const meta = REPORT_REGISTRY['budget-fulfillment'];
  return <ReportRenderer reportId="budget-fulfillment" reportMeta={meta} />;
}
```

**6 个 page.tsx 全部改成 5~8 行的薄壳**。

### 6.5 客户端组件边界

- `ReportRenderer` 必须 `'use client'`
- ECharts 图表继续走 `dynamic(() => import('@/components/charts/...'), { ssr: false })`
- `/reports` 列表保持 SSR（已是 `'use client'`，验证一下不要换）

---

## 7. 指标口径扩展

`metrics_dict.json` 目前只有 M01–M06，本方案需要新增 3 个：

| ID | 名称 | 公式（伪 SQL） |
|---|---|---|
| M07 | 渠道 ROI | `(conversions × avg_order_value - spend) / spend` |
| M08 | 库存周转天数 | `inventory_count / avg_daily_sales` |
| M09 | 库存系数 | `inventory_count / monthly_sales` |
| M10 | 漏斗步骤转化率 | `step_next_count / step_prev_count` |

**写入 metrics_dict.json 的纪律**：
1. 必须由后端工程师 + AI 产品经理双签字
2. SQL 模板必须在 `query_templates.py` 中实现并加单测
3. 不允许在报表 builder 里"临时算"一个新指标，所有指标都必须先入 metrics_dict

---

## 8. Mock 数据纪律（重要）

为了避免 Sprint 8 上线后又被吐槽"数据看着像假的"，每个报表的 Mock 必须满足：

| 规则 | 说明 |
|---|---|
| 数字合理 | 不能用 1/2/3 这种线性占位 |
| 维度真实 | 必须包含真实业务维度（如大区、品牌、车型、渠道） |
| 异常数据 | 至少 2 条达成率 < 95% 的预警，让用户看到"这张报表真的有用" |
| 时间序列 | 12 个月连续数据，避免断点 |
| 中文标签 | 渠道名 / 大区名必须用真实业务名（如"华南大区"、"抖音渠道"） |

Mock 文件结构示例：

```json
{
  "report_id": "channel-roi",
  "kpis": [
    {"label": "总投放", "value": 1247, "unit": "万"},
    {"label": "总线索", "value": 9621, "unit": "条"},
    {"label": "平均 CPL", "value": 129.78, "unit": "元"},
    {"label": "平均 ROI", "value": 3.42, "unit": ""}
  ],
  "charts": [
    {
      "chart_type": "table",
      "title": "渠道投放对比",
      "columns": ["渠道", "投放(万)", "线索数", "转化数", "CPL(元)", "ROI"],
      "data": [
        {"渠道": "抖音", "投放(万)": 320, "线索数": 2410, "转化数": 412, "CPL(元)": 132, "ROI": 3.8},
        {"渠道": "微信", "投放(万)": 280, "线索数": 1980, "转化数": 358, "CPL(元)": 141, "ROI": 3.5},
        ...
      ]
    }
  ],
  "alerts": [
    {"level": "warning", "title": "抖音 CPL 偏高", "body": "近 30 天 CPL 132 元，环比 +18%"}
  ]
}
```

---

## 9. 分期实施

### Sprint 8.1（前 2 周）

| 任务 | 工时 | 优先级 |
|---|---|---|
| 6 张报表的指标口径在 metrics_dict.json 补齐（M07–M10） | 1 天 | P0 |
| 6 个 `report_mocks/*.json` 写满 | 3 天 | P0 |
| 后端 `ReportExecutor` + 6 个 builder（含 SQL） | 5 天 | P0 |
| `/api/reports/registry` + `/api/reports/{id}` 端点 | 1 天 | P0 |
| 后端 6 张报表的 SQL 单测（pytest） | 2 天 | P0 |
| 前端 `ReportRenderer` 抽象 + 视觉过渡 4 段 | 3 天 | P0 |
| 6 个详情页薄壳化 | 1 天 | P0 |
| 暗色 KPI/图表组件从 dashboard 抽出来 | 2 天 | P1 |
| 报表中心 `/reports` 列表加上 `status: ready/mocked/wip` 角标 | 0.5 天 | P1 |
| 集成测试（端到端 6 个路径） | 2 天 | P0 |
| 上线文档 + 演示数据快照 | 1 天 | P1 |
| **小计** | **~22 人天** | |

### Sprint 8.2（再 2 周，可选）

| 任务 | 工时 | 优先级 |
|---|---|---|
| 报表内交互（点击柱状图跳转明细） | 4 天 | P1 |
| 导出 PDF / Excel | 3 天 | P2 |
| 订阅推送（飞书 / 邮件） | 3 天 | P2 |
| 报表自定义参数（用户可改月份、改车型筛选） | 4 天 | P2 |

---

## 10. 风险与对策

| 风险 | 影响 | 对策 |
|---|---|---|
| DuckDB 性能：6 个端点同时被前端轮询 | 高 | `/api/reports/{id}` 加 Redis 缓存（key = report_id:month，TTL 5min） |
| Mock 数据被当真数据 | 中 | 前端在 Mock 模式下显示"📦 离线演示"红色徽章，且 KPI 卡片上加斜纹水印 |
| 报表 SQL 与 metrics_dict 口径不一致 | 高 | 报表 builder 强制从 metrics_dict 读取 SQL 模板，禁止硬编码 |
| 视觉过渡再次"突兀" | 中 | 设计先出 1 张报表的高保真原型，UI 评审通过后再批量复刻 5 张 |
| ECharts 水合警告复发 | 低 | 继续保留 `dynamic(..., { ssr: false })`，不引入 SSR 图表 |

---

## 11. 验收标准（DoD）

- [ ] 6 张报表点开看到的内容**互不相同**（视觉 + 数据都不同）
- [ ] 每张报表至少有 1 条预警，且预警跟该报表的业务主题相关
- [ ] 后端关闭时，前端自动降级到 Mock，UI 上有明确标识
- [ ] DuckDB 只读校验通过（任何 builder 都不能执行 DML）
- [ ] 所有指标计算口径在 metrics_dict.json 中可追溯
- [ ] `/reports` 列表 + 6 个详情页 Lighthouse Performance ≥ 85
- [ ] 6 张报表的 SQL 在 DuckDB 中执行 < 1.5s
- [ ] 端到端测试覆盖 6 张报表的 happy path + mock fallback path

---

## 12. 不在本方案范围内（明确排除）

为防止 scope creep，下面**明确不做**：

- ❌ 报表的可视化拖拽配置（Tableau 式编辑）
- ❌ 报表的自定义 SQL 编辑器
- ❌ 报表的协同编辑 / 评论
- ❌ 报表的移动端原生 App
- ❌ 报表的离线导出 PDF（仅在线导出 Excel）
- ❌ 报表的 AI 自动解读（NL2SQL 输出仍走 Chat 页）

---

## 13. 下一步

1. **本周**：AI 产品经理评审本方案，确认 6 张报表契约的口径和可视化形态
2. **下周一**：后端工程师开 Sprint 8.1 启动会，拆分 M07–M10 指标口径
3. **下周三**：出第 1 张报表（建议 `budget-fulfillment`，因为 SQL 最简单）的高保真原型
4. **2 周后**：6 张报表全量上线，覆盖率达 100%

---

## 附录 A：6 张报表 mock 数据总览（建议最低数据量）

| 报表 | KPI | 图表 1 | 图表 2 | 图表 3 | 预警 |
|---|---|---|---|---|---|
| 预算达成分析 | 4 | 品牌达成率横向条形 | 大区达成率树状 | 弱项明细表 | 3 条 |
| 销量归因分析 | 4 | 渠道瀑布图 | 大区瀑布图 | 价格带瀑布图 | 2 条 |
| 渠道投放 ROI | 4 | 渠道对比表 | CPL 散点图 | 转化漏斗 | 3 条 |
| 库存预警 | 4 | 库存热力图 | 经销商明细表 | 周转天数 Top10 | 5 条 |
| 客流转化漏斗 | 4 | 4 级漏斗图 | 大区漏斗对比 | 流失原因分布 | 2 条 |
| 大区销售排行 | 4 | 7 大区卡片网格 | 同比趋势小图 | 环比趋势小图 | 1 条 |

## 附录 B：与现有资产的复用清单

| 现有资产 | 复用方式 |
|---|---|
| `/api/dashboard/snapshot` | dashboard 主页继续用，不动 |
| `/api/metrics` | 前端报表中心列表用，展示每张报表用了哪些 metric |
| `/api/sop/analyze` | 不复用（这是归因，不是报表）；销量归因报表里只调其中 1 个子查询 |
| `metrics_dict.json` | 6 张报表的 SQL 必须从这里派生 |
| `query_templates.py` | 报表 SQL 作为新模块加进去 |
| `SQLExecutor`（只读） | 报表 builder 唯一 DB 出口 |
| `SnapshotBoard.tsx` | **废弃**，被 `ReportRenderer` 替代；但 KPI / TrendChart / BrandRanking 组件可以继续复用 |
| ECharts 包装组件 | 继续用，引入更多 chart_type |
| 浅色 `/reports` 列表 | **完全保留**，改一个 `status` 角标即可 |
