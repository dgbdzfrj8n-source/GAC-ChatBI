# 广汽云 ChatBI 智能问数 Agent —— 全流程具体实施手册与 AI Coding 行动指南

> **项目版本**：v1.0.0  
> **适用角色**：AI 产品经理（兼全栈 AI Coding 负责人）  
> **核心目标**：借助 Cursor 快速构建一套可在本地秒级运行、支持公网零成本部署、具备严谨车企指标口径与归因 SOP 的企业级 ChatBI 产品。  
> **参考体验标杆**：`https://saas-chaibi.netlify.app/` 交互范式（引导词、折叠思考链、SQL抽屉、图表/表格双模切换、驾驶舱大屏、Bad Case 收集）。

---

## 目录索引
1. [项目总览与代价架构（Cost Architecture）设计](#一项目总览与代价架构cost-architecture设计)
2. [工程目录规范与 `.cursorrules` 初始化](#二工程目录规范与-cursorrules-初始化)
3. [Sprint 0：业务建模与 DuckDB 经营数据底座](#三sprint-0业务建模与-duckdb-经营数据底座)
4. [Sprint 1：语义层（Semantic Layer）与核心 NL2SQL 引擎](#四sprint-1语义层semantic-layer与核心-nl2sql-引擎)
5. [Sprint 2：图表自适应推荐与 FastAPI 流式服务](#五sprint-2图表自适应推荐与-fastapi-流式服务)
6. [Sprint 3：前端交互系统构建（对标 saas-chaibi）](#六sprint-3前端交互系统构建对标-saas-chaibi)
7. [Sprint 4：高频归因 SOP 引擎与工业级评测体系](#七sprint-4高频归因-sop-引擎与工业级评测体系)
8. [极简/零成本上线部署手册（Netlify + Render + DuckDB）](#八极简零成本上线部署手册netlify--render--duckdb)
9. [Cursor AI Coding 复制即用 Prompt 指南](#九cursor-ai-coding-复制即用-prompt-指南)

---

## 一、项目总览与代价架构（Cost Architecture）设计

在大模型与数据智能交叉的产品中，单纯跑通 Demo 毫无壁垒。AI PM 必须在第一天定义**代价模型（Token 预算、计算延迟、运维费用与容错代价）**。

```
                               【全链路代价控制与数据拓扑图】

  [ Web 浏览器端 (Netlify) ] 
          │ 
          │ (0 部署费 / 静态托管 / 极速 CDN)
          ▼
  [ FastAPI 网关 (Render / 本地) ] 
          │
          ├─── 1. 精准路由过滤 ──────────────> [ 规则拦截器 (0 Token / 0ms) ] -> 命中预设口径/闲聊
          │
          ├─── 2. 动态 Schema 剪枝 ──────────> [ 只召回 Top-1 表与核心 5 字段 (降低 85% Token) ]
          │
          ├─── 3. 低成本模型调度 ────────────> [ DeepSeek-V3 / Qwen-2.5 (单次成本 < 0.003 元) ]
          │
          ├─── 4. 安全与自愈引擎 ────────────> [ AST 只读检查 + 1次语法自愈 (失败率 < 2%) ]
          │
          └─── 5. 分析型引擎执行 ────────────> [ 嵌入式 DuckDB 内存列存 (10~50ms 聚合 / 0 RDS费) ]
```

### 1.1 代价架构详析表（核心工程指标）

| 维度 | 传统方案代价值 | 本项目代价架构方案 | 降本效能与工程机制 |
| :--- | :--- | :--- | :--- |
| **数据库运行代价** | 采用云 RDS (MySQL / ClickHouse)，每月约 150~600 元，需维护连接池。 | **采用 DuckDB 嵌入式单文件数据库**（`backend/data/gac_bi.duckdb`）。 | **数据库成本归零（0 元）**，支持百万行数据列式向量化加速，无连接池溢出风险。 |
| **Token 预算代价** | 每次提问把全部 3 张表（35+ 字段）、指标说明全量输入 Prompt，单次超 6,000 Tokens。 | **Schema Linking 剪枝机制**：通过 BM25 + 指标关键字预筛选，单次 Prompt 限制在 600~900 Tokens 以内。 | **单次调用 Token 降低 85%**，API 单次查询成本从 0.05 元降至 **0.002~0.004 元**。 |
| **模型分级代价** | 全量调用 GPT-4o 或 Claude 3.5 Sonnet，问答成本极高且国内易被封禁。 | **双轨分级路由**：常规 SQL 走 **DeepSeek-V3**；深度归因推演走 **DeepSeek-R1**；同时置备 Local Mock 录像模式。 | 成本下降 **90%**，具备无网络/无 API 时的面试现场演示兜底（100% 稳定）。 |
| **端到端响应时延** | 串行黑盒运行，端到端 10~15 秒，用户界面长时间呈现加载白屏。 | **SSE 流式传输 + 阶段思维链输出**：首字返回时间（TTFT）控制在 **600ms** 内，图表渲染在 2.5s 内完成。 | **感知等待时延降低 70%**，极大缓解业务人员等待焦虑。 |
| **SQL 报错与重试代价**| 模型偶尔出现 DuckDB 函数语法偏差，直接抛给用户 Internal Error。 | **自动反哺自愈重试（Self-Healing Loop）**：限制最多 1 次重试，将错误原因直接注入模型进行修正。 | 问数执行成功率提升至 **96%** 以上。 |

---

## 二、工程目录规范与 `.cursorrules` 初始化

项目采用前后端清晰解耦的单体 Monorepo 目录结构，便于本地一键拉起与云端分发构建。

### 2.1 推荐目录结构
```text
GAC-ChatBI/
├── .cursorrules                       # Cursor AI Coding 专属规范配置文件
├── README.md                          # 项目说明与快速启动
├── GAC_CHATBI_IMPLEMENTATION_GUIDE.md # 本实施方案手册
├── backend/                           # 后端 Python 智能服务
│   ├── requirements.txt               # 后端依赖清单
│   ├── Dockerfile                     # 容器化镜像构建文件
│   ├── data/                          # 数据管理目录
│   │   ├── schema.sql                 # DuckDB 表结构 DDL
│   │   ├── generate_mock_data.py      # 广汽经营模拟数据生成脚本
│   │   └── gac_bi.duckdb              # 生成的 DuckDB 单文件数据库
│   ├── core/                          # 核心 Agent 模块
│   │   ├── metrics_dict.json          # 集团指标语义定义字典
│   │   ├── schema_linker.py           # 动态字段剪枝器
│   │   ├── prompt_templates.py        # System Prompt 与 Few-Shot 样本
│   │   ├── sql_executor.py            # AST 只读安全检查与 DuckDB 执行器
│   │   ├── nl2sql_engine.py           # 核心问数 Agent 流
│   │   ├── chart_recommender.py       # ECharts 自动化可视化推断器
│   │   └── sop_analyzer.py            # 汽车经营未达成归因 SOP 引擎
│   ├── eval/                          # 评测与工业化运营
│   │   ├── eval_dataset.json          # 50 道标准问数基准测试集
│   │   ├── bad_cases.json             # 生产/测试点踩收集池
│   │   └── run_eval.py                # 评测跑分脚本
│   └── api/                           # API 路由暴露
│       ├── schemas.py                 # Pydantic 数据契约定义
│       └── main.py                    # FastAPI 入口与 SSE 流处理
└── frontend/                          # 前端 Next.js 交互工作台
    ├── package.json                   # 前端依赖配置
    ├── netlify.toml                   # Netlify 部署重定向配置文件
    ├── .env.example                   # 环境变量配置模板
    ├── tailwind.config.js             # Tailwind CSS 样式配置
    └── src/
        ├── app/
        │   ├── page.tsx               # 问数对话主界面
        │   ├── dashboard/page.tsx     # 经营驾驶舱大屏页面
        │   └── layout.tsx             # 全局骨架与侧边栏
        └── components/
            ├── Sidebar.tsx            # 左侧导航与指标库抽屉
            ├── SuggestionPills.tsx    # 顶部引导词组件
            ├── ChatMessage.tsx        # 对话气泡与折叠思考链
            ├── DataVisualizer.tsx     # 图表(ECharts)/表格(Table)双模切换
            ├── SqlDrawer.tsx          # 隐藏式 SQL 代码抽屉
            └── BadCaseModal.tsx       # 点踩反馈收集弹窗
```

### 2.2 初始化 `.cursorrules` 文件

请在根目录创建 `.cursorrules` 文件，内容如下：

```markdown
# GAC-ChatBI 专有开发规范

你是广汽集团智能经营分析团队的资深全栈架构师。你正在协助 AI 产品经理构建企业级“广汽云 ChatBI 智能问数 Agent”。

## 架构与工程规范
1. 数据底座：严格使用 DuckDB，SQL 语法遵循 DuckDB 规范（如使用 `STRFTIME(sale_date, '%Y-%m')` 处理年月聚合，使用 `NULLIF(val, 0)` 规避除零异常）。
2. 安全与性能原则：
   - 严禁产生增删改（INSERT/UPDATE/DELETE/DROP）操作，SQL 执行前必须执行只读安全校验。
   - 控制 Token 消耗：NL2SQL 时只输入必要的表结构与关联字段。
3. 代码风格与规范：
   - 后端：Python 3.10+，使用 FastAPI，所有数据结构严格采用 Pydantic v2 定义。
   - 前端：Next.js 14 (App Router)，TypeScript，Tailwind CSS，图表严格基于 ECharts 并做好 SSR 水合保护（客户端动态导入）。
4. 业务真实性：指标口径必须与 `backend/core/metrics_dict.json` 保持 100% 一致。
```

---

## 三、Sprint 0：业务建模与 DuckDB 经营数据底座

### 3.1 业务宽表设计（车企经营三域）

在 `backend/data/schema.sql` 中定义三张核心事实与目标表：

```sql
-- 1. 交付与销售事实表
CREATE TABLE IF NOT EXISTS fact_sales_daily (
    sale_date DATE,                   -- 销售交付日期
    brand_name VARCHAR,               -- 品牌（广汽埃安、广汽传祺、昊铂）
    model_name VARCHAR,               -- 车型（AION Y、AION S、传祺GS8、传祺M8、昊铂GT等）
    region_name VARCHAR,              -- 大区（华南区、华东区、华北区、华中区、西南区）
    delivered_units INTEGER,          -- 当日交付量（辆）
    gross_revenue DOUBLE,             -- 营业总收入（元）
    discount_rate DOUBLE,             -- 终端平均折扣率（如 0.08 表示 8%）
    customer_leads INTEGER            -- 进店意向客流量（组）
);

-- 2. 经营预算与销量目标表（月度颗粒度）
CREATE TABLE IF NOT EXISTS dim_budget_target (
    year_month VARCHAR,               -- 年月，格式 'YYYY-MM'
    brand_name VARCHAR,               -- 品牌
    target_units INTEGER,             -- 预算交付目标（辆）
    target_revenue DOUBLE,            -- 预算营收目标（元）
    expense_limit DOUBLE              -- 营销费用预算限额（元）
);

-- 3. 市场营销与获客支出事实表
CREATE TABLE IF NOT EXISTS fact_marketing_expenses (
    expense_date DATE,                -- 投放日期
    brand_name VARCHAR,               -- 品牌
    channel_name VARCHAR,             -- 投放渠道（懂车帝、抖音信息流、商圈外拓巡展、区域电台广告）
    expense_amount DOUBLE,            -- 投放支出金额（元）
    leads_generated INTEGER           -- 带来的销售线索数量（条）
);
```

### 3.2 统一经营指标字典：`backend/core/metrics_dict.json`

```json
{
  "metrics": [
    {
      "metric_name": "销售达成率",
      "domain": "整车销售",
      "definition": "实际交付量 / 预算目标交付量 * 100%",
      "calculation_sql": "ROUND(SUM(s.delivered_units) * 100.0 / NULLIF(SUM(b.target_units), 0), 2)",
      "required_tables": ["fact_sales_daily", "dim_budget_target"],
      "join_condition": "s.brand_name = b.brand_name AND STRFTIME(s.sale_date, '%Y-%m') = b.year_month"
    },
    {
      "metric_name": "单车营销费用",
      "domain": "经营财务",
      "definition": "营销投放总额 / 交付总量（衡量获客成本效率）",
      "calculation_sql": "ROUND(SUM(m.expense_amount) * 1.0 / NULLIF(SUM(s.delivered_units), 0), 2)",
      "required_tables": ["fact_marketing_expenses", "fact_sales_daily"],
      "join_condition": "m.brand_name = s.brand_name AND m.expense_date = s.sale_date"
    },
    {
      "metric_name": "单渠道获客成本(CPL)",
      "domain": "营销分析",
      "definition": "渠道投放总金额 / 渠道线索产生量",
      "calculation_sql": "ROUND(SUM(expense_amount) * 1.0 / NULLIF(SUM(leads_generated), 0), 2)",
      "required_tables": ["fact_marketing_expenses"]
    }
  ]
}
```

### 3.3 数据自动生成脚本：`backend/data/generate_mock_data.py`
* **目标**：生成 2024.01 - 2025.04 广汽三大品牌、3 万条以上高仿真波动数据。
* **特点**：植入真实车企波动规律（例如：2 月春节假期销量环比下滑 35%、四季度年末冲刺销量翘尾、华东区促销折扣放大）。
* **执行命令**：
  ```bash
  cd backend
  python data/generate_mock_data.py
  ```
* **验收**：生成 `gac_bi.duckdb`（大小约为 3~8MB），验证查询：
  ```bash
  python -c "import duckdb; con=duckdb.connect('data/gac_bi.duckdb'); print(con.execute('SELECT brand_name, sum(delivered_units) FROM fact_sales_daily GROUP BY 1').fetchall())"
  ```

---

## 四、Sprint 1：语义层（Semantic Layer）与核心 NL2SQL 引擎

### 4.1 动态 Schema 剪枝器 (`backend/core/schema_linker.py`)
* **逻辑**：避免全量 Table Schema 注入。扫描用户 Query：
  * 若提到了“销量”、“交付”、“达成率”，召回 `fact_sales_daily` 与 `dim_budget_target` 相关字段；
  * 若提到了“广告”、“ROI”、“投放”，召回 `fact_marketing_expenses`；
  * 输出格式精简为 Markdown 表结构摘要，注入 Prompt。

### 4.2 AST 安全校验与 DuckDB 执行器 (`backend/core/sql_executor.py`)
```python
import duckdb
import re
from typing import Dict, Any, List

class SqlExecutor:
    def __init__(self, db_path: str = "backend/data/gac_bi.duckdb"):
        self.db_path = db_path

    def validate_safe_sql(self, sql: str) -> bool:
        """AST级/正则级只读检查，拦截 DDL/DML 注入"""
        forbidden_patterns = [r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b", r"\bALTER\b", r"\bTRUNCATE\b"]
        for pattern in forbidden_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                return False
        # 必须以 SELECT 或 WITH 开头
        clean_sql = sql.strip().upper()
        return clean_sql.startswith("SELECT") or clean_sql.startswith("WITH")

    def execute_query(self, sql: str) -> Dict[str, Any]:
        if not self.validate_safe_sql(sql):
            return {"success": False, "error": "安全拦截：仅允许执行只读分析查询（SELECT/WITH）"}
        
        try:
            con = duckdb.connect(self.db_path, read_only=True)
            df = con.execute(sql).fetchdf()
            con.close()
            return {
                "success": True,
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "row_count": len(df)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### 4.3 具备单次自愈能力的 NL2SQL 主管道 (`backend/core/nl2sql_engine.py`)
```
用户提问 ➔ SchemaLinker 动态剪枝 ➔ 拼装 Few-Shot ➔ 调用 LLM ➔ 提取 SQL 
          │
          ▼
     执行 DuckDB 查询 
          ├── 成功 ➔ 输出数据与执行报告
          └── 失败 ➔ 捕获 Exception 拼接 Prompt ➔ 触发 1 次 Self-Healing 修正重试
```

---

## 五、Sprint 2：图表自适应推荐与 FastAPI 流式服务

### 5.1 图表自适应推荐器 (`backend/core/chart_recommender.py`)
根据 SQL 查询结果的列名特征与行数，自动推断最佳 ECharts 类型，输出前端可直接消费的 ECharts Option：
* **时间趋势列（sale_date / month / quarter）** ➔ **折线图 (line)**
* **类别对比列（brand_name / model_name / region_name）且行数 <= 10** ➔ **柱状图 (bar)**
* **占比分析（渠道占比 / 品牌贡献度）** ➔ **环形饼图 (pie/ring)**
* **双指标分析（如交付量 vs 营销支出）** ➔ **双轴复合图 (line + bar)**

### 5.2 API 契约设计 (`backend/api/schemas.py`)
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ChatRequest(BaseModel):
    query: str = Field(..., description="业务自然语言问数提问")
    session_id: Optional[str] = "default_session"
    mode: Optional[str] = "live" # "live" 或 "mock" 演示模式

class ChatResponse(BaseModel):
    query: str
    thought_steps: List[str] = Field(..., description="Agent 分析步骤：意图-口径-剪枝-执行")
    generated_sql: str
    data: List[Dict[str, Any]]
    columns: List[str]
    chart_type: str # 'line' | 'bar' | 'pie' | 'table'
    echarts_option: Optional[Dict[str, Any]] = None
    summary_insight: str = Field(..., description="基于数据的经营分析师核心洞察与预警")
```

### 5.3 FastAPI 流式服务端 (`backend/api/main.py`)
暴露两大核心终端点：
1. `GET /api/metrics`：获取指标体系字典（供前端侧边栏树状渲染展示）。
2. `POST /api/chat`：支持标准 JSON 响应与 SSE（Server-Sent Events）流式响应。

---

## 六、Sprint 3：前端交互系统构建（对标 saas-chaibi）

前端采用 Next.js 14 + Tailwind CSS + Lucide Icons + ECharts。核心设计直接借鉴并优化 `saas-chaibi.netlify.app` 的优秀特性：

### 6.1 前端核心组件拆解

```text
┌────────────────────────────────────────────────────────────────────────────┐
│ Top: 广汽云 ChatBI 导航条  [品牌切换: 埃安/传祺]  [模式: Live/演示] [API状态: OK] │
├──────────────┬─────────────────────────────────────────────────────────────┤
│ 左侧业务侧边栏 │ 主对话工作台                                                 │
│              │ ┌─────────────────────────────────────────────────────────┐ │
│ 1. 经营指标库 │ │ 顶部高频引导词 (SuggestionPills)                          │ │
│   • 销售达成率│ │ [🔥 埃安3月达成率] [传祺M8各区销量] [高获客成本渠道排查] │ │
│   • 单车营销成本│ └─────────────────────────────────────────────────────────┘ │
│   • 折扣敏感度│                                                             │
│              │ [用户]: 2025年Q1广汽埃安各车型交付量走势与达成率？             │
│ 2. 数据表视图 │                                                             │
│   • 交付事实表│ [Agent 经营分析师]:                                         │
│   • 预算目标表│ ┌─ 思考链明细 (点击折叠) ─────────────────────────────────┐ │
│   • 营销支出表│ │ ✔ 识别时间维度：2025-01-01 至 2025-03-31               │ │
│              │ │ ✔ 召回字段：model_name, delivered_units, target_units   │ │
│ 3. 历史会话  │ │ ✔ 自动关联 fact_sales_daily 与 dim_budget_target        │ │
│   • 昨天会话 │ └─────────────────────────────────────────────────────────┘ │
│   • 上周分析 │ 埃安 2025 年 Q1 交付总量达 78,520 辆，整体达成率 88.3%。    │
│              │ ┌─────────────────────────────────────────────────────────┐ │
│              │ │ 切换视图：[ 📊 可视化图表 ]   [ 📋 数据明细表 ]          │ │
│              │ │                                                         │ │
│              │ │   [ ECharts 动态双轴图：柱状(交付量) + 折线(达成率%) ]   │ │
│              │ │                                                         │ │
│              │ └─────────────────────────────────────────────────────────┘ │
│              │ 底部操作：[ 💻 查看 SQL 抽屉 ] [ 📌 钉入驾驶舱 ] [ 👍 点赞 ] [ 👎 点踩 ] │
└──────────────┴─────────────────────────────────────────────────────────────┘
```

### 6.2 关键组件实现关键点

1. **`SqlDrawer.tsx`（透明度抽屉）**：
   - 支持高亮展示生成的 DuckDB SQL，右侧支持一键复制 SQL；
   - 支持点击“在当前数据表解释执行”，消除黑盒担忧。
2. **`DataVisualizer.tsx`（图表与明细双模切换）**：
   - 默认展示 ECharts 交互图表（带 Tooltip、Legend 筛选、下载为图片）；
   - 点击 Tab 切换为清晰的 Tailwind 表格，带列名排序与“导出 CSV”功能。
3. **`SuggestionPills.tsx`（车企经营高频 Prompt Pills）**：
   - 包含：“2025年3月埃安销量与预算达成率”、“近半年各营销渠道获客ROI对比”、“传祺GS8华东大区终端折扣与客流相关性”。
4. **`BadCaseModal.tsx`（Bad Case 收集弹窗）**：
   - 用户点击点踩按钮后，弹出弹窗：“请指出该问题所在：[ 口径计算错误 | 图表类型不匹配 | SQL语法错误 | 数据缺失 ]”，提交后持久化保存至 `backend/eval/bad_cases.json`。

---

## 七、Sprint 4：高频归因 SOP 引擎与工业级评测体系

### 7.1 汽车销量达成异常归因 SOP 引擎 (`backend/core/sop_analyzer.py`)

传统 ChatBI 只能查出“AION Y 3月未达标”，本项目的高级能力是自动执行四步下钻 SOP：

```
【第 1 步：大盘对标】 计算埃安整体销量缺口：目标 35,000 辆，实际 28,100 辆，达成率 80.3%（缺口 6,900 辆）。
          │
          ▼
【第 2 步：维度下钻】 自动下钻车型与大区：发现 AION Y 缺口占比高达 72%；华东与华北两区下滑最明显。
          │
          ▼
【第 3 步：跨域归因】 关联外部营销与终端：华东区 3 月进店意向客流同比下降 28%，竞品降价导致终端折扣收窄失效。
          │
          ▼
【第 4 步：策略建议】 建议针对华东区 AION Y 专项下沉商圈巡展，短期置换补贴追加 3,000 元/台。
```

### 7.2 自动化评测跑分体系 (`backend/eval/run_eval.py`)

准备 50 道覆盖各种复杂场景的问题测试集 (`eval_dataset.json`)：
* **单表基础聚合**（15 题）
* **跨表关联与口径计算**（15 题）
* **时间/范围模糊问答**（10 题）
* **越界攻击/非只读提问拦截**（5 题）
* **归因综合推演**（5 题）

#### 评测执行与打分标准：
```bash
python backend/eval/run_eval.py
```
* **输出指标**：
  * **SQL Syntax Pass Rate** (目标 >= 95%)
  * **Data Result Exact Match** (目标 >= 88%)
  * **Average Latency** (目标 <= 2.5s)
  * **Token Cost per Query** (目标 <= 1000 tokens)

---

## 八、极简/零成本上线部署手册（Netlify + Render + DuckDB）

这是全行业最具性价比、最不容易翻车的个人实战项目部署拓扑：

```
                 [ GitHub 仓库 (代码 + 预生成 DuckDB 数据) ]
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
             [ Netlify 平台 ]                  [ Render / Railway ]
         (构建目录: frontend)                 (构建环境: Dockerfile)
                 │                                     │
                 ▼                                     ▼
        前端 Web 公网访问                     后端 FastAPI 接口服务
    https://gac-chatbi.netlify.app         https://gac-api.onrender.com
```

### 8.1 第一步：准备后端 Dockerfile (`backend/Dockerfile`)

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装必要依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码与数据文件
COPY . /app/backend

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.2 第二步：部署后端到 Render (完全免费)
1. 将项目推送到 GitHub。
2. 登录 [Render.com](https://render.com)，选择 **New + ➔ Web Service**。
3. 关联你的 GitHub 仓库，选择 **Docker** 环境，Root Directory 填 `backend`。
4. 在 Environment Variables 中添加：
   * `LLM_API_KEY`：你的 DeepSeek 或 通义千问 API Key。
   * `LLM_BASE_URL`：`https://api.deepseek.com/v1`（或其他 OpenAI 兼容地址）。
5. 点击 **Create Web Service**。部署成功后获取公网 API 地址：`https://xxxx.onrender.com`。

### 8.3 第三步：配置前端 Netlify 构建规则 (`frontend/netlify.toml`)

```toml
[build]
  base = "frontend"
  publish = ".next"
  command = "npm run build"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

* 在 Netlify 后台添加环境变量：
  `NEXT_PUBLIC_API_URL=https://xxxx.onrender.com`
* 一键绑定 GitHub 仓库，即可生成专属域名（如 `https://gac-chatbi.netlify.app`）。

### 8.4 第四步：离线演示防翻车设计（Mock Fallback）
在 `frontend/src/app/page.tsx` 中置入开关：
* 若后端请求超时（> 8秒）或网络不可达，前端自动平滑降级到预置的 Mock 录像数据（包含预置的 5 个经典车企问数案例），确保你在任何面试、晋升现场**绝不出现白屏或报错崩盘**。

---

## 九、Cursor AI Coding 复制即用 Prompt 指南

在 Cursor 中，请按照以下顺序直接复制提示词发给 Cursor Composer / Agent：

### 指令 1：生成经营宽表与模拟数据
> “参考 `GAC_CHATBI_IMPLEMENTATION_GUIDE.md` 第 3 节。请在 `backend/data/` 目录下生成 `generate_mock_data.py`。使用 DuckDB 建立 `fact_sales_daily`、`dim_budget_target` 和 `fact_marketing_expenses` 三张表，生成广汽埃安、传祺、昊铂 2024~2025 年 4 万条高仿真经营数据，包含春节淡季、四季度冲刺等业务特征，保存为 `backend/data/gac_bi.duckdb` 并验证数据行数。”

### 指令 2：实现安全 SQL 执行器与 Schema Linker
> “参考实施指南第 4 节。请实现 `backend/core/schema_linker.py` 和 `backend/core/sql_executor.py`。要求：
> 1. `sql_executor.py` 必须使用 AST 或关键词严格校验只读权限，杜绝 DDL/DML；
> 2. 具备执行异常捕获，返回包含列名、数据字典、行数的标准化 Dict；
> 3. 编写单元测试验证对合法与非法 SQL 的处理表现。”

### 指令 3：实现 NL2SQL 引擎与图表推荐
> “参考实施指南第 4 与第 5 节。请编写 `backend/core/nl2sql_engine.py` 和 `chart_recommender.py`。
> 1. 使用 LiteLLM 或 OpenAI SDK 调用 DeepSeek 模型；
> 2. 注入 `metrics_dict.json` 的业务口径；
> 3. 若 SQL 执行失败，自动触发 1 次错误重试修正；
> 4. 根据查询结果自适应生成 ECharts Line/Bar/Pie 完整配置项。”

### 指令 4：搭建 FastAPI 服务
> “参考第 5 节。请在 `backend/api/` 下实现 `schemas.py` 与 `main.py`。暴露 `/api/chat` 和 `/api/metrics` 接口，支持 CORS 跨域，提供清晰的 Swagger 文档，支持以 Mock 模式返回预置数据。”

### 指令 5：搭建 Next.js 前端（对标 saas-chaibi）
> “参考第 6 节。请在 `frontend/` 下初始化 Next.js 14 App Router 项目，使用 Tailwind CSS 和 ECharts。构建包含左侧指标字典抽屉、顶部车企引导词、思考链折叠卡片、图表与明细表格双模切换、SQL 查看抽屉、点赞点踩反馈弹窗的现代 ChatBI 界面。”

---

*这份手册已完整落实在本工作区，你随时可以调阅，并以此驱动 Cursor 逐个模块敏捷实现！*
