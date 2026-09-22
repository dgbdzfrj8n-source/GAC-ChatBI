# 广汽云 ChatBI 产品经理工作流程

> 适用角色：AI 产品经理（兼全栈 AI Coding 负责人）
> 项目：广汽云 ChatBI 智能问数 Agent
> 数据底座：DuckDB 嵌入式单文件（`backend/data/gac_bi.duckdb`）
> 核心业务域：整车销售 / 经营财务 / 市场营销 / 渠道经营

---

## 一、需求池（Intake）

承接业务侧模糊诉求，统一收敛到本产品迭代漏斗中。

| 来源 | 典型输入 | 输出物 |
| :--- | :--- | :--- |
| 高管季度复盘会 | "为什么 3 月广汽埃安华南区达成率掉了" | 归因问数需求单 |
| 区域总监周报 | "本月华北区各车型客流转化率明细" | 经营指标查询需求单 |
| 营销/市场部 | "哪个渠道 CPL 最划算，能不能动态切换预算" | 投放分析需求单 |
| 车型经理 | "昊铂 GT 在 30 万以上价格段新能源销量" | 产品复盘需求单 |
| 销售一线 | "这个月我还能不能达成目标" | 一线达成率问数需求单 |
| 内部 Bad Case | 评测集/点踩收集（`backend/eval/bad_cases.json`） | 口径修正 / 归因模板新增需求 |

**收口原则**：所有需求先映射到 `backend/core/metrics_dict.json` 中的 6 类核心指标（销售达成率、总交付量、单车成交均价、单车营销费用、单渠道获客成本 CPL、客流成交转化率），并标注归因维度（品牌 / 区域 / 车型 / 能源类型 / 价格段 / 月份）。

---

## 二、排期（Planning）

按"业务紧迫度 × 工程依赖"双维度排入对应 Sprint。

### 2.1 Sprint 划分（与实施手册对齐）

| Sprint | 主题 | 关键产物 |
| :--- | :--- | :--- |
| Sprint 0 | 业务建模与 DuckDB 经营数据底座 | `schema.sql` 三张事实/目标表（`fact_sales_daily` / `dim_budget_target` / `fact_marketing_expenses`） |
| Sprint 1 | 语义层与 NL2SQL 引擎 | `metrics_dict.json` + `schema_linker.py` + `prompt_templates.py` |
| Sprint 2 | 图表自适应与 FastAPI 流式服务 | `chart_recommender.py` + ECharts 推荐策略 + SSE 流 |
| Sprint 3 | 前端交互系统（对标 saas-chaibi） | 引导词、折叠思考链、SQL 抽屉、图表/表格双模、驾驶舱 |
| Sprint 4 | 归因 SOP 引擎与工业级评测体系 | `sop_analyzer.py` + `attribution_templates.py` + 50 题评测集 |
| Sprint 5 | 差距补齐冲刺 | 5 个未交付能力落地 |
| Sprint 6 | 路线图与三阶段验收 | 公网部署 + 验收 Checklist |

### 2.2 排期看板字段

每个需求单必填：
- 关联指标 ID（M01 ~ M06）
- 关联归因模板（高管季度复盘 / 分析师深度下钻 / 区域总监 KPI / 车型经理产品复盘 / 新能源专项）
- 业务角色（executive / analyst / product / visitor）
- Token 预算预估（基于 Schema Linking 剪枝后 ≤ 900 Tokens）
- 安全风险（是否触发 DuckDB AST 只读校验边界）

---

## 三、开发（Build）

Cursor AI Coding 主战场，严格遵循 `.cursorrules` 规范。

### 3.1 后端工程规范

- Python 3.10+ / FastAPI / Pydantic v2
- SQL 严格遵循 DuckDB 语法：`STRFTIME(sale_date, '%Y-%m')` 处理年月聚合、`NULLIF(val, 0)` 规避除零
- 严禁 INSERT/UPDATE/DELETE/DROP，SQL 执行前必经 AST 只读校验
- Schema Linking 剪枝：单次 Prompt 限制 600 ~ 900 Tokens

### 3.2 前端工程规范

- Next.js 14（App Router）+ TypeScript + Tailwind CSS
- 图表严格基于 ECharts，客户端动态导入做 SSR 水合保护
- 关键组件：`SuggestionPills` / `ChatMessage` / `DataVisualizer` / `SqlDrawer` / `BadCaseModal` / `Sidebar`

### 3.3 业务真实性红线

- 指标口径 100% 与 `backend/core/metrics_dict.json` 一致
- 归因维度字段白名单（来自 `core/sop_analyzer.py::DIMENSION_FIELD_MAP`）：`brand_name` / `region_name` / `model_name` / `energy_type` / `price_segment` / `monthly`
- 自定义归因模板上限：1 ~ 4 个维度

---

## 四、测试（Test）

含单测、评测、口径校验三层防线。

### 4.1 单元测试（功能正确性）

- `SchemaLinker`：BM25 + 指标关键字预筛选召回率
- `SqlExecutor`：AST 只读校验拒绝率（应 100% 拦截写操作）
- `ChartRecommender`：时序→折线、TOP N→条形、占比→饼图 的推荐准确率
- `AttributionTemplateManager`：维度白名单 / 4 维上限 / 角色默认绑定

### 4.2 工业级评测（NL2SQL 质量）

- 测试集：`backend/eval/eval_dataset.json`（50 题标准问数基准）
- 跑分脚本：`backend/eval/run_eval.py`
- 关键指标：执行成功率（目标 ≥ 96%）、单次 Token 成本（目标 ≤ 0.004 元）、首字返回时延 TTFT（目标 ≤ 600ms）

### 4.3 口径校验（业务真实性）

- M01 销售达成率：必须先 CTE 按月聚合再 JOIN，避免日×月 1:N 扇出
- M04 单车营销费用：营销表与销售表分别聚合后再 JOIN 比值
- M05 CPL：`NULLIF(SUM(leads_generated), 0)` 必须保留
- 任何指标口径变更必须同步更新 `metrics_dict.json` 并走 PR Review

---

## 五、上线（Release）

零成本公网部署链路（极简上线手册）。

### 5.1 部署拓扑

- 前端：Netlify Static Site（0 部署费 / 极速 CDN）
- 后端：Render Web Service（FastAPI 网关）
- 数据：嵌入式 DuckDB 单文件（0 RDS 费）

### 5.2 发布 Checklist

- [ ] `backend/data/gac_bi.duckdb` 已生成且三表行数符合预期
- [ ] `.cursorrules` 已提交至仓库根目录
- [ ] 50 题评测集通过率 ≥ 96%
- [ ] Bad Case 池无 P0 级未修复项
- [ ] SSE 流式首字返回 ≤ 600ms，图表渲染 ≤ 2.5s
- [ ] DuckDB AST 只读校验拦截日志无异常绕过

### 5.3 双轨模型路由

| 场景 | 模型 | 单次成本目标 |
| :--- | :--- | :--- |
| 常规 NL2SQL | DeepSeek-V3 | < 0.003 元 |
| 深度归因推演 | DeepSeek-R1 | 可放宽 |
| 离线/无网络演示 | Local Mock 录像模式 | 0 元 / 100% 稳定 |

---

## 六、复盘（Retro）

每 Sprint 末的双视角复盘。

### 6.1 业务价值复盘

- 高管视角：本期上线能力是否支撑季度复盘会 80% 临时问数
- 区域视角：区域总监 KPI 模板是否被实际使用（用户自定义模板创建量）
- 一线视角：访客（visitor）角色的达成率查询成功率

### 6.2 工程指标复盘

- 问数执行成功率（目标 ≥ 96%）
- 平均单次 Token 消耗（目标 600 ~ 900 Tokens）
- Bad Case 闭环率（点踩 → 修复 → 回归的平均周期）
- 归因模板复用率（系统预设 5 个 + 用户自定义）

### 6.3 下一周期输入

复盘结论直接回流到：
- `backend/eval/eval_dataset.json`（补充新问数）
- `backend/eval/bad_cases.json`（未修复项跟进）
- `backend/core/attribution_templates.py`（新增场景化预设）
- `backend/core/metrics_dict.json`（口径扩展，需走 PR Review）
