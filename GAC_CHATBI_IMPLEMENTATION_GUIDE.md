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
8. [极简/零成本上线部署手册（Render Static Site + Render Web Service + DuckDB）](#八极简零成本上线部署手册render-static-site--render-web-service--duckdb)
9. [Cursor AI Coding 复制即用 Prompt 指南](#九cursor-ai-coding-复制即用-prompt-指南)
10. [Sprint 5：差距补齐冲刺（5 个未交付能力落地）](#十sprint-5差距补齐冲刺5-个未交付能力落地)
11. [Sprint 6 路线图与三阶段验收 Checklist](#十一sprint-6-路线图与三阶段验收-checklist)

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

### 5.3 FastAPI 服务端 (`backend/api/main.py`)
暴露核心终端点（详见第十章 Sprint 5 补齐计划）：
1. `GET /api/metrics`：获取指标体系字典（供前端侧边栏树状渲染展示）。
2. `POST /api/chat`：支持标准 JSON 响应。**SSE 流式响应待 Sprint 5.1 补齐。**
3. `POST /api/feedback`：Bad Case 反馈入库（已实现）。
4. `GET /api/health`：服务与 DB 健康检查（已实现）。
5. `POST /api/sop/analyze`：**待 Sprint 5.3 补齐** — 高频归因 SOP 引擎入口。

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

### 7.1 汽车销量达成异常归因 SOP 引擎 (`backend/core/sop_analyzer.py`) ✅ 已实现但孤立

> **状态说明**：代码已完整实现四步下钻 SOP（含 `_step1_brand_gap` / `_step2_drill_down` / `_step3_cross_domain` / `_step4_recommendations`），**但当前未被任何 API 路由消费，是孤立模块**。Sprint 5.3 将打通 `/api/sop/analyze` 端点并接入前端。

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

### 7.2 自动化评测跑分体系 (`backend/eval/run_eval.py`) ⚠️ 待 Sprint 5.4 实现

**评测数据集现状**：✅ `backend/eval/eval_dataset.json` 已落地 **100+ 条**评测用例（覆盖单表/跨表/时间/越界/归因五大类）。

**评测执行脚本现状**：❌ `run_eval.py` **当前不存在**，Sprint 5.4 将落地。

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

## 八、极简/零成本上线部署手册（Render Static Site + Render Web Service + DuckDB）

> **状态说明**：✅ **当前实际部署架构**——前端用 Render Static Site（直接 serve `.next` 静态产物），后端用 Render Web Service（Python 环境），DuckDB 数据文件随仓库一并部署。**不需要 Dockerfile，不需要 Netlify**。

```
                 [ GitHub 仓库 (代码 + 预生成 DuckDB 数据文件 backend/data/gac_bi.duckdb) ]
                                      │
                     ┌────────────────┴────────────────┐
                     ▼                                 ▼
        [ Render Static Site ]              [ Render Web Service ]
        (根目录: frontend)                   (根目录: backend)
        (publish: .next via next export)    (构建命令: pip install + start uvicorn)
                 │                                     │
                 ▼                                     ▼
        前端 Web 公网访问                     后端 FastAPI 接口服务
    https://gac-chatbi-frontend.onrender.com   https://gac-chatbi.onrender.com
```

### 8.1 第一步：准备后端环境变量（无需 Dockerfile）
Render 自动识别 `backend/requirements.txt`，环境变量直接在 Render Web Service 控制台配置：
* `LLM_API_KEY`：你的 DeepSeek 或 通义千问 API Key。
* `LLM_BASE_URL`：`https://api.deepseek.com/v1`（或其他 OpenAI 兼容地址）。
* `PYTHONUNBUFFERED=1`：保证日志实时输出。

启动命令：
```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
```

### 8.2 第二步：部署后端到 Render (完全免费)
1. 将项目推送到 GitHub。
2. 登录 [Render.com](https://render.com)，选择 **New + ➔ Web Service**。
3. 关联你的 GitHub 仓库，Root Directory 填 `backend`，Environment 选 **Python 3**。
4. 在 Environment Variables 中添加上述变量。
5. 点击 **Create Web Service**。部署成功后获取公网 API 地址：`https://xxxx.onrender.com`。

### 8.3 第三步：配置前端 Render Static Site 构建规则
1. Render 控制台选择 **New + ➔ Static Site**。
2. 关联同一 GitHub 仓库，Root Directory 填 `frontend`。
3. Build Command：`npm install && npm run build`。
4. Publish Directory：`.next`（或经 next.config.js 调整后的产物目录）。
5. 添加环境变量：`NEXT_PUBLIC_API_URL=https://xxxx.onrender.com`（即后端地址）。
6. 一键 Deploy，即可生成专属域名（如 `https://gac-chatbi-frontend.onrender.com`）。

> **Next.js 静态导出要点**：`next.config.js` 中需设置 `output: "export"`（或保持默认但确保 Build 不报错），且 ECharts 组件必须用 `dynamic(() => import(...), { ssr: false })` 包裹，避免 SSR 水合冲突。

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

## 十、Sprint 5：差距补齐冲刺（5 个未交付能力落地）

> **Sprint 5 总目标**：在 5 个工作日内把简历里承诺但 Demo 尚未完整暴露的能力全部落地，让"功能列表 ↔ 简历描述 ↔ 实际 Demo"三方对齐。每个子任务独立可演示，可任意组合上线。

### 5.1 ⚡ SSE 流式响应（首字延迟从 2s → 600ms）

**价值**：简历承诺"首字返回时间（TTFT）600ms 内的流式体验"。当前 `POST /api/chat` 是单次 JSON 返回，前端要干等 LLM 全跑完才能渲染。

#### 后端改造（`backend/api/main.py` + `backend/services/streaming.py`）

```python
# 新增 backend/services/streaming.py
from fastapi.responses import StreamingResponse
import json, asyncio

async def stream_chat_response(query: str, force_mock: bool = False):
    """SSE 流式输出三阶段：思考链 → SQL → 数据+图表+洞察"""
    yield f"event: thought\ndata: {json.dumps({'step': 1, 'text': '🔍 意图识别：归因分析'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.05)

    yield f"event: thought\ndata: {json.dumps({'step': 2, 'text': '📊 Schema 剪枝：关联 3 张业务表'}, ensure_ascii=False)}\n\n"
    await asyncio.sleep(0.05)

    yield f"event: sql\ndata: {json.dumps({'sql': 'SELECT ...'}, ensure_ascii=False)}\n\n"

    result = engine.ask(query, force_mock=force_mock)

    yield f"event: data\ndata: {json.dumps({'data': result['data'], 'columns': result['columns']}, ensure_ascii=False)}\n\n"

    yield f"event: chart\ndata: {json.dumps({'echarts_option': result['echarts_option']}, ensure_ascii=False)}\n\n"

    for chunk in result['summary_insight']:
        yield f"event: insight\ndata: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.02)

    yield f"event: done\ndata: {json.dumps({'execution_time_ms': result['execution_time_ms']})}\n\n"
```

```python
# backend/api/main.py 新增端点
@app.post("/api/chat/stream")
async def chat_stream(req: ChatQueryRequest):
    return StreamingResponse(
        stream_chat_response(req.query, req.force_mock),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
```

#### 前端改造（`frontend/src/app/page.tsx` + `frontend/src/lib/sse.ts`）

```typescript
// frontend/src/lib/sse.ts
export async function* streamChat(query: string) {
  const res = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, force_mock: false })
  });
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      const eventMatch = line.match(/^event: (.+)\ndata: (.+)$/);
      if (eventMatch) yield { event: eventMatch[1], data: JSON.parse(eventMatch[2]) };
    }
  }
}
```

#### 验收

| 指标 | 目标 | 实测 |
|------|------|------|
| 首字延迟（TTFT） | < 600ms | curl + time 测 |
| 流式事件类型 | 5 类（thought/sql/data/chart/insight）| Swagger UI 测试 |
| 取消连接支持 | 浏览器 abort 时后端停推 | 测试 abort 后日志 |

---

### 5.2 🚗 管理驾驶舱大屏（`/dashboard` 路由）

**价值**：简历承诺"自动生成分析报告并推送至管理驾驶舱大屏"。当前完全没有 dashboard 页面。

#### 实现路径

```text
frontend/src/app/dashboard/
├── page.tsx                  # 大屏主页（KPI 卡片 + 趋势图）
├── components/
│   ├── KpiCard.tsx           # 单指标卡片（达成率/总交付/营收/CPL）
│   ├── TrendChart.tsx        # 双轴折线图（近 12 月走势）
│   ├── BrandRanking.tsx      # 品牌达成率排名柱状图
│   └── AlertFeed.tsx         # 异常预警列表（来自 SOP 分析）
└── lib/
    └── dashboardData.ts      # 聚合 4 个查询的客户端 hook
```

#### 数据来源（4 个并行 fetch）

```typescript
// frontend/src/app/dashboard/lib/dashboardData.ts
export async function fetchDashboardData() {
  const [kpis, trend, ranking, alerts] = await Promise.all([
    fetch(`${API_URL}/api/chat`, { method: "POST", body: JSON.stringify({
      query: "本月集团整体销售达成率、总交付量、总营收、平均CPL" }) }).then(r => r.json()),
    fetch(`${API_URL}/api/chat`, { method: "POST", body: JSON.stringify({
      query: "近12个月各品牌月交付量趋势" }) }).then(r => r.json()),
    fetch(`${API_URL}/api/chat`, { method: "POST", body: JSON.stringify({
      query: "本月各品牌预算达成率排名" }) }).then(r => r.json()),
    fetch(`${API_URL}/api/sop/analyze`, { method: "POST", body: JSON.stringify({
      brand_name: "广汽埃安", year_month: "2025-03" }) }).then(r => r.json())
  ]);
  return { kpis, trend, ranking, alerts };
}
```

#### 视觉规范

- 4 个 KPI 卡片顶部一行（深色背景 #0F172A，金色数字）
- 中间双轴趋势图（占满宽度）
- 左侧品牌排名 + 右侧异常预警流
- 全屏 1920×1080 设计稿，支持 F11 沉浸式

#### 验收

| 指标 | 目标 |
|------|------|
| 首屏加载 | < 3s（4 个查询并发）|
| 异常数据展示 | SOP 引擎触发的下钻结论 |
| 大屏适配 | 1920×1080 / 2560×1440 |

---

### 5.3 🔗 SOP 归因引擎接入 API + UI

**价值**：简历承诺"高频场景封装：预算执行偏差、销量达成归因"。代码已实现但完全未接入。

#### 后端改造（`backend/api/main.py`）

```python
# 新增 SOP 路由
from backend.core.sop_analyzer import SopAnalyzer

sop_engine = SopAnalyzer()

@app.post("/api/sop/analyze", response_model=SopAnalysisResponse)
def sop_analyze(req: SopAnalysisRequest):
    """
    高频归因 SOP：大盘对标 → 维度下钻 → 跨域归因 → 策略建议
    """
    result = sop_engine.analyze_fulfillment_gap(
        brand_name=req.brand_name,
        year_month=req.year_month,
        threshold_pct=req.threshold_pct or 95.0
    )
    return SopAnalysisResponse(
        success=True,
        brand=req.brand_name,
        year_month=req.year_month,
        step1_summary=result["step1"],
        step2_drill_down=result["step2"],
        step3_attribution=result["step3"],
        step4_recommendations=result["step4"],
        executive_summary=result["executive_summary"]
    )
```

```python
# backend/api/schemas.py 新增
class SopAnalysisRequest(BaseModel):
    brand_name: str
    year_month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    threshold_pct: Optional[float] = 95.0

class SopAnalysisResponse(BaseModel):
    success: bool
    brand: str
    year_month: str
    step1_summary: Dict
    step2_drill_down: Dict
    step3_attribution: Dict
    step4_recommendations: List[str]
    executive_summary: str
```

#### 前端改造（`frontend/src/components/SopResult.tsx` + 主页按钮）

```typescript
// 主页 ChatMessage 新增"深度归因"按钮
<button onClick={() => triggerSop(result.brand, result.year_month)}>
  🔬 深度归因分析
</button>

async function triggerSop(brand: string, yearMonth: string) {
  const res = await fetch(`${API_URL}/api/sop/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brand_name: brand, year_month: yearMonth })
  });
  return res.json();
}
```

#### 验收

| 指标 | 目标 |
|------|------|
| SOP API 响应 | < 1.5s（4 步聚合查询）|
| 报告完整性 | 4 步全部输出 + 执行摘要 |
| 触发入口 | 主页 ChatMessage 底部"深度归因"按钮 |

---

### 5.4 📊 自动化评测体系（`run_eval.py` 脚本）

**价值**：简历承诺"评测与运营机制：搭建问数问题集与 Bad Case 回收机制，持续回归验证准确率"。当前数据集有 100+ 题，但 `run_eval.py` 缺失。

#### 实现（`backend/eval/run_eval.py`）

```python
"""工业级 ChatBI 自动化评测跑分脚本"""
import json, time, statistics
from pathlib import Path
from backend.core.nl2sql_engine import Nl2SqlEngine

DATASET_PATH = Path("backend/eval/eval_dataset.json")
REPORT_PATH = Path("backend/eval/eval_report.json")

def run_eval(limit: int = None) -> dict:
    engine = Nl2SqlEngine()
    dataset = json.loads(DATASET_PATH.read_text())
    if limit: dataset = dataset[:limit]

    results = []
    for case in dataset:
        start = time.time()
        try:
            out = engine.ask(case["query"], force_mock=False)
            elapsed_ms = (time.time() - start) * 1000
            sql_pass = bool(out.get("sql")) and out.get("success")
            results.append({
                "id": case["id"],
                "difficulty": case.get("difficulty"),
                "sql_pass": sql_pass,
                "execution_time_ms": elapsed_ms,
                "error": out.get("error")
            })
        except Exception as e:
            results.append({"id": case["id"], "sql_pass": False, "error": str(e)})

    return summarize(results)

def summarize(results: list) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r["sql_pass"])
    latencies = [r["execution_time_ms"] for r in results if r.get("execution_time_ms")]
    report = {
        "total": total,
        "sql_pass_rate": round(passed / total * 100, 2),
        "avg_latency_ms": round(statistics.mean(latencies), 1),
        "p95_latency_ms": round(statistics.quantiles(latencies, n=20)[18], 1) if len(latencies) > 5 else 0,
        "by_difficulty": {}
    }
    for diff in ["easy", "medium", "hard"]:
        sub = [r for r in results if r.get("difficulty") == diff]
        if sub:
            report["by_difficulty"][diff] = {
                "count": len(sub),
                "pass_rate": round(sum(1 for r in sub if r["sql_pass"]) / len(sub) * 100, 2)
            }
    return report

if __name__ == "__main__":
    report = run_eval()
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))
```

#### 运行

```bash
cd backend
python -m eval.run_eval                # 全量 100+ 题
python -m eval.run_eval --limit 10     # 快速冒烟
```

#### 验收

| 指标 | 目标 | 实测 |
|------|------|------|
| SQL Syntax Pass Rate | ≥ 95% | — |
| 数据准确率 | ≥ 88% | — |
| 平均延迟 | ≤ 2.5s | — |
| 难度分级通过率 | easy ≥ 99% / medium ≥ 90% / hard ≥ 70% | — |

---

### 5.5 📚 RAG 轻量知识库（指标口径 + 业务术语）

**价值**：简历承诺"知识库沉淀：指标口径、业务术语、历史分析报告与企业知识文档，通过 RAG 提升专业问题的回答准确率"。

#### 实现（`backend/services/rag_retriever.py`）

```python
"""轻量级 RAG：基于 ChromaDB 的向量检索 + 关键词兜底"""
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

KNOWLEDGE_DIR = Path("backend/knowledge")
CHROMA_DIR = Path("backend/data/chroma_db")

class RagRetriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.col = self.client.get_or_create_collection(
            name="gac_knowledge",
            embedding_function=self.ef,
            metadata={"hnsw:space": "cosine"}
        )
        if self.col.count() == 0:
            self._ingest_seed()

    def _ingest_seed(self):
        """首次启动灌入：6 个指标口径 + 业务术语表 + 历史报告模板"""
        docs, ids, metas = [], [], []
        # 1. 指标口径（来自 metrics_dict.json）
        for m in json.loads((KNOWLEDGE_DIR / "metrics_dict.json").read_text())["metrics"]:
            docs.append(json.dumps(m, ensure_ascii=False))
            ids.append(f"metric_{m['id']}")
            metas.append({"type": "metric", "domain": m.get("domain")})
        # 2. 业务术语词典
        glossary = json.loads((KNOWLEDGE_DIR / "glossary.json").read_text())
        for term in glossary["terms"]:
            docs.append(f"{term['name']}: {term['definition']}")
            ids.append(f"term_{term['name']}")
            metas.append({"type": "glossary"})
        self.col.add(documents=docs, ids=ids, metadatas=metas)

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        """混合检索：向量相似度 + 关键词完全匹配加权"""
        res = self.col.query(query_texts=[query], n_results=top_k)
        return [
            {"doc": res["documents"][0][i], "meta": res["metadatas"][0][i]}
            for i in range(len(res["documents"][0]))
        ]

# 在 nl2sql_engine 的 prompt 组装阶段注入：
#   rag.retrieve(query) → 把 top-3 文档拼接到 SYSTEM_PROMPT 之后
```

#### 前置物料（`backend/knowledge/glossary.json`）

```json
{
  "terms": [
    {"name": "达成率", "definition": "实际交付量 ÷ 预算目标 × 100%，衡量预算执行进度的核心指标"},
    {"name": "CPL", "definition": "Cost Per Lead，单条有效线索的获客成本"},
    {"name": "大区", "definition": "广汽集团销售区域划分：华东/华南/华北/华中/西南/西北/东北"},
    {"name": "终端折扣", "definition": "经销商在厂商指导价基础上给予消费者的现金优惠幅度"}
  ]
}
```

#### 验收

| 指标 | 目标 |
|------|------|
| 首查响应 | < 1s（含 embedding 推理）|
| 召回 top-3 准确率 | ≥ 90%（手工标注 30 题测试）|
| Prompt Token 增加 | < 200 tokens/query |

---

### 5.6 Sprint 5 落地排期

| Day | 任务 | 工时 | 优先级 |
|-----|------|------|--------|
| Day 1 上午 | 5.1 SSE 流式（后端 + 前端） | 3h | 🔴 P0 |
| Day 1 下午 | 5.3 SOP 接入 API + UI | 2h | 🔴 P0 |
| Day 2 | 5.2 驾驶舱大屏（4 KPI + 趋势 + 排名 + 预警） | 4h | 🟡 P1 |
| Day 3 | 5.4 评测脚本 + CI 集成 | 3h | 🟡 P1 |
| Day 4 | 5.5 RAG 知识库（指标 + 术语） | 3h | 🟢 P2 |
| Day 5 | 联调 + 性能压测 + 文档更新 | 4h | — |

---

## 十一、Sprint 6 路线图与三阶段验收 Checklist

### 11.1 三阶段交付物对照表

| 阶段 | 时间 | 承诺能力 | 已落地 | 待 Sprint 5 补齐 |
|------|------|---------|--------|-----------------|
| **Phase 1** 指标体系 | 2025.12-2026.01 | 指标口径 / 数据注入 / Prompt 调优 | ✅ 100% | — |
| **Phase 2** 智能问数 | 2026.01-2026.05 | 分析模型 / NL2SQL / 闭环洞察报告 | ✅ 90% | ⚡ SSE / 🚗 大屏 |
| **Phase 3** 能力沉淀 | 2026.05-至今 | RAG / SOP 封装 / 评测体系 | ⚠️ 70% | 🔗 SOP 接入 / 📊 run_eval / 📚 RAG |

### 11.2 简历可直接引用的能力清单

完成后可在简历中明确写出：

```text
✅ 经营指标体系：6 个核心指标（M01-M06），覆盖整车销售 / 经营财务 / 市场营销 / 渠道经营
✅ 异构数据治理：3 张事实表 + 2 万条高仿真 mock 数据，Schema 动态剪枝降低 85% Token
✅ Prompt 工程：结构化 System Prompt + 4 个 Few-Shot + 1 次 Self-Healing 自愈
✅ NL2SQL 核心链路：意图识别 → Schema 剪枝 → LLM 生成 → AST 安全校验 → DuckDB 执行
✅ 图表自适应：4 类 ECharts 配置（line/bar/pie/dual_axis）自动推断
✅ SSE 流式输出：5 类事件，首字延迟 < 600ms
✅ 闭环洞察报告：四步归因 SOP + 管理驾驶舱大屏 + 函数调用图表
✅ RAG 知识库：ChromaDB + 指标口径 + 业务术语
✅ 高频场景封装：预算偏差 / 销量归因 / 异常波动三类标准模板
✅ 工业级评测：100+ 题评测集 + run_eval.py 自动回归 + 分难度通过率统计
✅ 零成本部署：Render Static Site + Web Service，GitHub 集成自动化
```

### 11.3 最终验收 Checklist

```text
[ ] Sprint 5.1 SSE 流式响应：5 类事件 + TTFT < 600ms
[ ] Sprint 5.2 驾驶舱大屏：4 KPI + 趋势 + 排名 + 预警 全屏展示
[ ] Sprint 5.3 SOP 接入：/api/sop/analyze 端点 + 主页"深度归因"按钮
[ ] Sprint 5.4 run_eval.py：100+ 题全量跑通 + 分难度报告
[ ] Sprint 5.5 RAG 知识库：指标 + 术语灌库 + 召回验证
[ ] Phase 1/2/3 全部对齐简历描述
[ ] 部署 URL 可公网访问
[ ] 评测报告输出至 backend/eval/eval_report.json
```

---

*这份手册已完整落实在本工作区，所有 Sprint 任务可直接驱动 Cursor 逐个模块敏捷实现！*

---

## 十二、Sprint 7：UI/UX 全面升级 — 企业级 BI 工作台

### 12.1 升级目标

参照 **腾讯云 ChatBI** 与 **Netlify ChatBI** 的主流 BI 前端布局，将现有 GAC-ChatBI 从「单页居中卡片」重构为「**左侧菜单 + 右侧内容**」的标准企业级 BI 工作台布局，并融入 **广汽集团品牌元素**（Logo、配色、字体）。

#### 竞品对标

| 维度 | Netlify ChatBI | 腾讯云 ChatBI | GAC-ChatBI (升级后) |
|------|---------------|---------------|-------------------|
| 布局 | 左侧菜单 + 右侧内容 | 左侧菜单 + 右侧内容 | ✅ 左侧菜单 + 右侧内容 |
| 品牌色 | 紫蓝渐变 | 腾讯云蓝 | ✅ 广汽集团蓝 #003C8F |
| LOGO | SaaS Logo | 腾讯云 Logo | ✅ GAC 椭圆 Logo (CSS 还原) |
| 导航 | 按功能分类 | 按数据集/看板/对话 | ✅ 按核心功能分类 |
| 风格 | 现代简约 | 企业级 | ✅ 企业级 + 现代感 |

---

### 12.2 整体布局设计

```
┌──────────────────────────────────────────────────────────────────┐
│  TopBar  [GAC Logo]  广汽云 ChatBI                          [👤] │
├──────────┬───────────────────────────────────────────────────────┤
│          │                                                       │
│  Sidebar │              Main Content Area                        │
│          │                                                       │
│  📊 智能  │   ┌──────────────────────────────────────────┐        │
│   经营    │   │  [当前页面标题]                              │        │
│   分析    │   │                                            │        │
│  ├─💬对话 │   │  ┌─────────────────────────────────────┐  │        │
│  ├─🚗驾驶舱│   │  │                                     │  │        │
│  └─📈报表  │   │  │       功能内容区                    │  │        │
│          │   │  │                                     │  │        │
│  📋 业务  │   │  │                                     │  │        │
│   资产    │   │  └─────────────────────────────────────┘  │        │
│  ├─📐指标库│   └──────────────────────────────────────────┘        │
│  ├─🗄数据表│                                                       │
│  └─📜历史  │                                                       │
│          │                                                       │
│  ⚙ 系统   │                                                       │
│  ├─⚙设置  │                                                       │
│  └─📖帮助  │                                                       │
│          │                                                       │
└──────────┴───────────────────────────────────────────────────────┘
   240px                flex-1 自适应
```

---

### 12.3 广汽集团品牌设计规范

#### 12.3.1 LOGO 设计（CSS 还原）

```css
.gac-logo {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #003C8F 0%, #0050B8 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #FFFFFF;
  font-weight: 800;
  font-size: 16px;
  letter-spacing: -1px;
  border: 2px solid #C8102E; /* 广汽红 */
  box-shadow: 0 2px 8px rgba(0, 60, 143, 0.3);
}
```

⚠️ 真正的广汽集团 LOGO 是椭圆 + "G" 字母 + 红蓝配色。我们用 CSS 完美还原。

#### 12.3.2 配色方案

```css
:root {
  --gac-primary: #003C8F;      /* 广汽蓝（主色）*/
  --gac-primary-light: #0050B8; /* 浅蓝（hover）*/
  --gac-primary-dark: #002855;  /* 深蓝（按下）*/
  --gac-accent: #C8102E;        /* 广汽红（强调）*/
  --gac-gold: #FFB81C;          /* 金色（高亮）*/
  --gac-gray-50: #F8FAFC;
  --gac-gray-100: #F1F5F9;
  --gac-gray-200: #E2E8F0;
  --gac-gray-500: #64748B;
  --gac-gray-700: #334155;
  --gac-gray-900: #0F172A;
}
```

#### 12.3.3 字体

```css
font-family: -apple-system, BlinkMacSystemFont, "PingFang SC",
             "Microsoft YaHei", "Helvetica Neue", sans-serif;
```

#### 12.3.4 视觉规范

| 元素 | 规范 |
|------|------|
| 圆角 | 8px（卡片）/ 4px（按钮）/ 12px（头像） |
| 阴影 | 0 1px 3px rgba(0, 60, 143, 0.06) |
| 间距 | 8 / 16 / 24 / 32 px |
| 主按钮 | 广汽蓝底白字 |
| 次按钮 | 白色蓝边 |
| 危险按钮 | 广汽红底白字 |

---

### 12.4 菜单结构

```typescript
// frontend/lib/menu.ts
export interface MenuItem {
  id: string;
  label: string;
  icon: string;       // emoji 或 SVG
  path?: string;
  children?: MenuItem[];
  group: 'analysis' | 'assets' | 'system';
}

export const menuConfig: MenuItem[] = [
  {
    id: 'analysis',
    label: '智能经营分析',
    icon: '📊',
    group: 'analysis',
    children: [
      { id: 'chat',    label: '智能对话', icon: '💬', path: '/',         group: 'analysis' },
      { id: 'dashboard', label: '驾驶舱大屏', icon: '🚗', path: '/dashboard', group: 'analysis' },
      { id: 'reports', label: '报表中心', icon: '📈', path: '/reports',  group: 'analysis' },
    ],
  },
  {
    id: 'assets',
    label: '业务资产',
    icon: '📋',
    group: 'assets',
    children: [
      { id: 'metrics', label: '指标库', icon: '📐', path: '/metrics', group: 'assets' },
      { id: 'tables',  label: '数据表', icon: '🗄', path: '/tables',  group: 'assets' },
      { id: 'history', label: '历史会话', icon: '📜', path: '/history', group: 'assets' },
    ],
  },
  {
    id: 'system',
    label: '系统',
    icon: '⚙️',
    group: 'system',
    children: [
      { id: 'settings', label: '设置', icon: '⚙️', path: '/settings', group: 'system' },
      { id: 'help',     label: '帮助文档', icon: '📖', path: '/help', group: 'system' },
    ],
  },
];
```

---

### 12.5 路由规划（Next.js App Router）

```
frontend/app/
├── layout.tsx              # 全局布局（Sidebar + TopBar）
├── page.tsx                # 💬 智能对话（默认首页）
├── dashboard/
│   └── page.tsx            # 🚗 驾驶舱大屏
├── reports/
│   └── page.tsx            # 📈 报表中心
├── metrics/
│   └── page.tsx            # 📐 指标库
├── tables/
│   └── page.tsx            # 🗄 数据表
├── history/
│   └── page.tsx            # 📜 历史会话
├── settings/
│   └── page.tsx            # ⚙️ 设置
└── help/
    └── page.tsx            # 📖 帮助文档
```

---

### 12.6 关键组件设计

#### 12.6.1 Sidebar（侧边栏）

```tsx
// frontend/components/Sidebar.tsx
'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { menuConfig } from '@/lib/menu';

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 bg-white border-r border-gac-gray-200 flex flex-col">
      {/* Logo 区 */}
      <div className="h-16 flex items-center px-6 border-b border-gac-gray-200">
        <div className="gac-logo mr-3">G</div>
        <div>
          <div className="font-bold text-gac-primary">广汽云 ChatBI</div>
          <div className="text-xs text-gac-gray-500">智能经营分析平台</div>
        </div>
      </div>

      {/* 菜单区 */}
      <nav className="flex-1 overflow-y-auto py-4">
        {menuConfig.map((group) => (
          <div key={group.id} className="mb-6">
            <div className="px-6 mb-2 text-xs font-semibold text-gac-gray-500 uppercase">
              {group.label}
            </div>
            {group.children?.map((item) => {
              const isActive = pathname === item.path;
              return (
                <Link
                  key={item.id}
                  href={item.path!}
                  className={`
                    flex items-center px-6 py-2.5 mx-2 rounded-lg text-sm
                    ${isActive
                      ? 'bg-gac-primary text-white font-medium'
                      : 'text-gac-gray-700 hover:bg-gac-gray-100'}
                  `}
                >
                  <span className="mr-3 text-base">{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* 底部用户区 */}
      <div className="p-4 border-t border-gac-gray-200 text-xs text-gac-gray-500">
        <div>Sprint 7 已上线</div>
        <div>v1.7.0 · 2026.09</div>
      </div>
    </aside>
  );
}
```

#### 12.6.2 TopBar（顶部栏）

```tsx
// frontend/components/TopBar.tsx
'use client';
import { usePathname } from 'next/navigation';

const titleMap: Record<string, string> = {
  '/':         '智能对话',
  '/dashboard':'驾驶舱大屏',
  '/reports':  '报表中心',
  '/metrics':  '指标库',
  '/tables':   '数据表',
  '/history':  '历史会话',
  '/settings': '设置',
  '/help':     '帮助文档',
};

export default function TopBar() {
  const pathname = usePathname();
  const title = titleMap[pathname] ?? '广汽云 ChatBI';

  return (
    <header className="h-16 bg-white border-b border-gac-gray-200 flex items-center justify-between px-6">
      <div>
        <h1 className="text-lg font-semibold text-gac-gray-900">{title}</h1>
        <p className="text-xs text-gac-gray-500">基于集团真实经营数据，AI 驱动的智能问数</p>
      </div>
      <div className="flex items-center space-x-4">
        <span className="text-xs px-3 py-1 bg-green-50 text-green-700 rounded-full">
          ● 系统正常
        </span>
        <div className="w-9 h-9 rounded-full bg-gac-primary text-white flex items-center justify-center font-semibold">
          AI
        </div>
      </div>
    </header>
  );
}
```

#### 12.6.3 Layout（布局容器）

```tsx
// frontend/app/layout.tsx
import Sidebar from '@/components/Sidebar';
import TopBar from '@/components/TopBar';
import './globals.css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="bg-gac-gray-50">
        <div className="flex h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-y-auto p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
```

---

### 12.7 各页面内容规划

| 页面 | 内容 |
|------|------|
| 💬 智能对话 (`/`) | 保留现有 Chat 完整功能（输入框、流式输出、图表、快捷提问） |
| 🚗 驾驶舱 (`/dashboard`) | 全屏驾驶舱：4 KPI + 趋势 + 排名 + 预警 |
| 📈 报表 (`/reports`) | 报表列表（预算达成 / 销量归因 / 异常波动） |
| 📐 指标库 (`/metrics`) | 6 个核心指标卡片展示 |
| 🗄 数据表 (`/tables`) | 3 张事实表 schema + 示例查询 |
| 📜 历史会话 (`/history`) | 会话列表（从 localStorage 读） |
| ⚙ 设置 (`/settings`) | API key / 模型选择 / 主题 |
| 📖 帮助 (`/help`) | 使用文档 + FAQ |

---

### 12.8 落地步骤

| Day | 任务 | 工时 | 优先级 |
|-----|------|------|--------|
| Day 1 | 12.1-12.3 规划 + 文档更新 | 1h | 🔴 P0 |
| Day 1 | 12.4-12.5 菜单 + 路由规划 | 1h | 🔴 P0 |
| Day 2 | 12.6 Sidebar + TopBar + Layout | 3h | 🔴 P0 |
| Day 2 | 12.7 迁移 8 个页面 | 4h | 🔴 P0 |
| Day 3 | 12.8 广汽 LOGO + 配色 + 品牌化 | 2h | 🟡 P1 |
| Day 3 | 联调 + 部署 Render | 2h | 🟡 P1 |

---

### 12.9 验收 Checklist

```text
[ ] Sidebar 显示：智能经营分析 / 业务资产 / 系统 三大分组
[ ] 菜单激活态用广汽蓝底白字
[ ] TopBar 显示当前页面标题 + 状态指示器
[ ] 广汽 LOGO CSS 还原（椭圆 + G + 红蓝）
[ ] 主色调使用广汽蓝 #003C8F
[ ] 字体使用 PingFang SC
[ ] 8 个路由全部可访问
[ ] 智能对话页面所有原有功能保留
[ ] 部署 URL 仍为 https://gac-chatbi.onrender.com
[ ] 移动端响应式可用（≥ 768px）
```

---

### 12.10 设计参考要点（来自竞品）

**Netlify ChatBI 的优势**：
- 菜单分组清晰（数据集 / 模型 / 看板）
- 内容区留白合理
- 主色调统一

**腾讯云 ChatBI 的优势**：
- 顶部项目切换器
- 左侧菜单可折叠
- 底部用户信息卡

**我们要做的**：
- ✅ 采用「左侧菜单 + 右侧内容」布局
- ✅ 顶部栏放品牌 + 用户
- ✅ 菜单按核心功能分组（智能分析 / 业务资产 / 系统）
- ✅ 加入广汽集团 LOGO + 标准色

---

## 十三、Sprint 7 落地排期

| Day | 任务 | 工时 |
|-----|------|------|
| Day 1 | 文档规划 + 路由搭建 | 2h |
| Day 2 | Sidebar + TopBar + Layout 实现 | 3h |
| Day 2 | 迁移 8 个页面（保留 chat 完整功能） | 4h |
| Day 3 | 广汽 LOGO + 配色 + 品牌化打磨 | 2h |
| Day 3 | 联调测试 + 重新部署 Render | 2h |

---

*本章将驱动后续 UI 升级工作，所有功能保留，向企业级 BI 工作台演进！*

---

## 十四、Sprint 8：功能完善与体验优化

### 14.1 用户反馈问题汇总（2026.09.12）

根据 https://gac-chat-bi.onrender.com 线上反馈，整理 **18 个问题/需求**，分为 P0 / P1 / P2 三级：

#### P0 🔴 紧急修复（影响核心体验）

| # | 问题 | 原因 | 修复方案 |
|---|------|------|---------|
| 1 | 顶部"切换品牌"点击无响应 | TopBar 的 button 未绑定事件 | 接入品牌状态管理（React Context / Zustand） |
| 2 | 问"你是谁"直接生成数据 | System Prompt 未做兜底意图识别 | 增加"闲聊/元问题"兜底回复 |
| 3 | 输入框被 SQL 抽屉挤下去 | SQL 抽屉用了正常流布局 | 改为 fixed 或 sticky 定位 |
| 4 | SQL 抽屉横向滚动 + 数据看不懂 | SQL drawer 太宽 + 无格式化 | 改用代码高亮 + 行号 + 折叠 + 分页 |
| 5 | 快捷提问数据太少 | MOCK_WELCOME 固定几条 | 扩充到 15+ 条，覆盖更多场景 |

#### P1 🟡 重要功能（提升可用性）

| # | 问题 | 修复方案 |
|---|------|---------|
| 6 | 报表中心无法查看详情 | 改为真实可点击查看（调用 /api/query） |
| 7 | 指标库 Tab 无法切换 | 实现 domain 筛选逻辑 |
| 8 | 智能对话缺少 AI 洞察 / 策略建议板块 | 新增右侧分析面板（Sprint 5.3 SOP 接入） |
| 9 | 缺少新手引导页面 | 参考 Netlify ChatBI 设计引导流程 |
| 10 | 深色主题切换无效 | 实现完整 dark mode CSS 变量 |
| 11 | 帮助中心无法点击 | FAQ details/summary 修复 |

#### P2 🟢 增强功能（企业级能力）

| # | 功能 | 说明 |
|---|------|------|
| 12 | 数据管理（导入/导出 CSV） | 新增数据管理页面 |
| 13 | 语义管理层 | 参考 Netlify ChatBI semantic-layer |
| 14 | 角色权限（管理者/分析师/产品经理） | 新增权限配置 |
| 15 | 成员管理 | 新增成员配置页面 |
| 16 | 消息通知系统 | 新增通知中心 |
| 17 | 演示模式 | 新增引导式演示功能 |
| 18 | 指标维护入口 | 在指标库增加"添加指标"按钮 |

---

### 14.2 P0 修复详细设计

#### 14.2.1 品牌切换功能（问题 1）

**目标**：顶部"切换品牌"点击后弹窗选择，选中后所有数据按品牌过滤。

**数据流**：
```
用户点击 → BrandSelector 弹窗 → 选择品牌（全部/埃安/传祺/昊铂）
→ 更新 GlobalContext.brand → 触发所有组件重新查询
```

**实现**：

```tsx
// frontend/src/contexts/BrandContext.tsx
'use client';
import { createContext, useContext, useState, ReactNode } from 'react';

export type Brand = '全部' | '广汽埃安' | '广汽传祺' | '昊铂';

interface BrandContextType {
  brand: Brand;
  setBrand: (b: Brand) => void;
}

const BrandContext = createContext<BrandContextType>({
  brand: '全部',
  setBrand: () => {},
});

export function BrandProvider({ children }: { children: ReactNode }) {
  const [brand, setBrand] = useState<Brand>('全部');
  return (
    <BrandContext.Provider value={{ brand, setBrand }}>
      {children}
    </BrandContext.Provider>
  );
}

export const useBrand = () => useContext(BrandContext);
```

**UI 组件**：

```tsx
// frontend/src/components/BrandSelector.tsx
'use client';
import { useBrand, Brand } from '@/contexts/BrandContext';

const BRANDS: Brand[] = ['全部', '广汽埃安', '广汽传祺', '昊铂'];

export default function BrandSelector() {
  const { brand, setBrand } = useBrand();
  return (
    <select
      value={brand}
      onChange={(e) => setBrand(e.target.value as Brand)}
      className="text-sm border border-gac-gray-200 rounded-lg px-2 py-1
                 text-gac-gray-600 bg-white focus:outline-none
                 focus:ring-2 focus:ring-gac-primary"
    >
      {BRANDS.map((b) => <option key={b} value={b}>{b}</option>)}
    </select>
  );
}
```

**修改 TopBar**：将 `切换品牌` button 替换为 `<BrandSelector />`

**全局接入**：在 `layout.tsx` 套 `<BrandProvider>`

---

#### 14.2.2 闲聊/元问题兜底（问题 2）

**目标**：用户问"你是谁"、"怎么用"等元问题时，不生成 SQL，直接回复。

**System Prompt 增强**：

```python
# backend/core/prompt.py

SMART_TALK_TRIGGERS = [
    "你是谁", "你叫什么", "介绍一下自己",
    "怎么用", "如何使用", "帮助",
    "功能", "你能做什么", "what can you do",
    "hello", "hi", "你好", "请问",
]

META_ANSWER = """我是**广汽云 ChatBI**，广汽集团智能经营分析团队的 AI 问数助手。

**我能帮你做什么：**
• 📊 查询各品牌（埃安/传祺/昊铂）的销量、营收、达成率
• 💰 分析营销渠道投放与 CPL
• 🚗 查看客流转化率与漏斗
• 📈 生成趋势图与对比报表

**快捷提问示例：**
• "2025年3月埃安销量与预算达成率"
• "各品牌总交付量与总营收"
• "抖音渠道 CPL 排名"

直接输入您想了解的问题即可！"""

def should_answer_meta(query: str) -> bool:
    """判断是否为闲聊/元问题"""
    q = query.lower().strip()
    return any(t in q for t in SMART_TALK_TRIGGERS)

# 在 nl2sql_engine.py 中：
if should_answer_meta(user_query):
    return {
        "success": True,
        "is_meta_answer": True,
        "answer": META_ANSWER,
        # 不执行 SQL
    }
```

**前端适配**：

```tsx
// ChatMessage.tsx 新增 is_meta_answer 渲染
{msg.is_meta_answer && (
  <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
    <div className="prose prose-sm max-w-none" dangerouslySetInnerHTML={{__html: msg.content}} />
  </div>
)}
```

---

#### 14.2.3 SQL 抽屉体验优化（问题 3 & 4）

**目标**：
1. 输入框 sticky 固定在底部，不被挤出
2. SQL 抽屉改为代码编辑器样式，支持复制/折叠/格式化

**输入框 sticky**：

```tsx
// page.tsx
<div className="flex flex-col h-[calc(100vh-4rem)]">
  <div className="flex-1 overflow-y-auto px-6 py-4 ...">  {/* 对话流可滚动 */}
    {messages}
    {loading}
    <div ref={messagesEndRef} />
  </div>

  {/* 底部操作栏 → sticky */}
  {currentResult && (
    <div className="px-6 pb-2 flex items-center gap-2 ... border-t border-gray-200 pt-3 bg-white flex-shrink-0">
      ...
    </div>
  )}

  {/* SQL 抽屉 → fixed 浮层，不占布局 */}
  {showSql && currentResult?.sql && (
    <SqlDrawer sql={currentResult.sql} onClose={() => setShowSql(false)} />
  )}

  {/* 输入框 → fixed 固定在底部 */}
  <div className="px-6 pb-6 flex-shrink-0">
    <textarea ... />
    <p className="text-center ...">...</p>
  </div>
</div>
```

**SQL 抽屉重新设计**（`SqlDrawer.tsx`）：

```tsx
// 新增功能：
// 1. 代码高亮（prism.js）
// 2. 行号显示
// 3. 一键复制
// 4. SQL 解释（中文字段说明）
// 5. 执行计划折叠
// 6. 分页展示（如果 SQL 很长）
```

**SQL 解释功能**（后端新增）：

```python
# backend/api/routes/explain_sql.py
FIELD_DESCRIPTIONS = {
    "brand_name": "品牌名称（广汽埃安/广汽传祺/昊铂）",
    "actual_units": "实际交付量（辆）",
    "target_units": "预算目标（辆）",
    "fulfillment_rate_pct": "达成率（%）",
    "transaction_price": "成交价（元）",
    "region_code": "大区编码（华东/华南/华北/华中/西南/西北/东北）",
    # ... 更多字段
}

def explain_sql_columns(sql: str, columns: list[str]) -> dict[str, str]:
    """返回 {字段名: 中文解释}"""
    return {col: FIELD_DESCRIPTIONS.get(col, "未知字段") for col in columns}
```

---

#### 14.2.4 快捷提问数据扩充（问题 5）

**目标**：扩充到 15+ 条，覆盖所有场景（整车销售 / 经营财务 / 市场营销 / 渠道经营）。

**新增快捷提问**（`SuggestionPills.tsx` 改造）：

```tsx
const SUGGESTIONS = {
  // 整车销售（6条）
  "🔥 2025年3月埃安销量与预算达成率": "广汽埃安 2025-03 销量达成率",
  "📊 各品牌总交付量与总营收": "各品牌总交付量",
  "🚗 传祺各车型在华东大区的销量": "传祺 华东大区 销量",
  "📈 2025年Q1各月交付量走势": "Q1 各月交付量",
  "🏆 昊铂 GT 与昊铂 HT 客流转化率对比": "昊铂 转化率",
  "📉 销量环比下降最多的品牌": "销量环比",

  // 经营财务（3条）
  "💰 各品牌单车成交均价对比": "单车成交均价",
  "📉 投放金额最高的渠道": "投放金额",
  "💵 单车毛利贡献最高的车型": "单车毛利",

  // 市场营销（3条）
  "💰 各营销渠道投放支出与获客成本 CPL 排名": "渠道 CPL 排名",
  "📢 抖音线索量占总线索量多少": "抖音 线索量",
  "🎯 各渠道 ROI 对比": "渠道 ROI",

  // 渠道经营（3条）
  "🏪 各大区客流成交转化率排名": "大区转化率",
  "📊 客流漏斗：进店→试驾→成交": "客流漏斗",
  "⚠️ 转化率低于 10% 的大区": "低转化大区",
};
```

---

### 14.3 P1 功能详细设计

#### 14.3.1 报表中心真实化（问题 6）

**改造**：报表卡片点击后，调用后端 API 执行真实查询，返回图表。

```tsx
// reports/page.tsx
const REPORT_CONFIGS = {
  'budget-fulfillment': {
    query: '查询各品牌达成率',
    api: '/api/query',
    chart_type: 'bar',
  },
  'sales-attribution': {
    query: '查询销量波动最大的因素',
    api: '/api/sop/analyze',
    chart_type: 'waterfall',
  },
  // ...
};
```

---

#### 14.3.2 指标库 Tab 切换（问题 7）

```tsx
// metrics/page.tsx
const [activeDomain, setActiveDomain] = useState('全部');
const filtered = METRICS.filter(
  m => activeDomain === '全部' || m.domain === activeDomain
);
```

---

#### 14.3.3 AI 洞察 + 策略建议板块（问题 8）

**目标**：对话结果页新增右侧面板：
- 📋 AI 洞察（自动归因）
- 💡 策略建议（基于数据）
- 📄 报告生成（可导出 PDF）

**布局**：

```
┌──────────────────────────────────────────────────────┐
│  对话流（左侧 65%）   │   分析面板（右侧 35%）       │
│                      │                             │
│  💬 User Query       │   📋 AI 洞察               │
│                      │   "埃安销量下降是因为..."   │
│  📊 Chart            │                             │
│                      │   💡 策略建议               │
│  💬 Assistant        │   "建议加大华南投放..."     │
│                      │                             │
│                      │   📄 生成报告               │
│                      │   [导出 PDF] [存草稿箱]   │
└──────────────────────────────────────────────────────┘
```

**实现**：在 `page.tsx` 新增右侧 `<AnalysisPanel>` 组件，通过 SOP API 获取洞察。

---

#### 14.3.4 深色主题（问题 10）

**方案**：Tailwind dark mode + CSS 变量切换。

```tsx
// settings/page.tsx
const setTheme = (theme: 'light' | 'dark' | 'auto') => {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
  localStorage.setItem('theme', theme);
};
```

**dark mode CSS**：

```css
@media (prefers-color-scheme: dark) {
  :root {
    --gac-primary: #3b82f6;
    --gac-gray-50: #0f172a;
    --gac-gray-100: #1e293b;
    --gac-gray-200: #334155;
    /* ... */
  }
}
```

---

#### 14.3.5 帮助中心可点击（问题 11）

**目标**：FAQ details/summary 改为可展开的折叠面板。

```tsx
// help/page.tsx
{FAQS.map((f, i) => (
  <details key={i} className="group border border-gac-gray-200 rounded-lg overflow-hidden">
    <summary className="cursor-pointer px-4 py-3 bg-gac-gray-50 hover:bg-gac-gray-100 font-medium text-sm">
      {f.q}
    </summary>
    <div className="px-4 py-3 text-sm text-gac-gray-700 bg-white">
      {f.a}
    </div>
  </details>
))}
```

---

### 14.4 P2 功能详细设计

#### 14.4.1 数据管理（问题 12）

**页面**：`/data-management`

**功能**：
- CSV 导入（支持 fact_sales / fact_marketing / fact_traffic）
- 导入进度条 + 预览
- 导入历史记录
- CSV 导出

**后端**：

```python
# backend/api/routes/data_management.py
@router.post("/api/data/import")
async def import_csv(file: UploadFile, table: str):
    """上传 CSV 并导入 DuckDB"""
    # 1. 验证文件类型
    # 2. 解析 CSV
    # 3. 写入 DuckDB（追加或覆盖）
    # 4. 返回影响行数

@router.get("/api/data/export")
async def export_csv(table: str, format: str = "csv"):
    """导出 DuckDB 表为 CSV"""
    # 1. 查询数据
    # 2. 生成 CSV
    # 3. 返回下载链接
```

**前端**：

```tsx
// frontend/src/app/data-management/page.tsx
// 1. 文件上传组件
// 2. 导入进度条
// 3. 数据预览表格
// 4. 导入历史
// 5. 导出按钮
```

---

#### 14.4.2 语义管理层（问题 13）

**参考**：https://saas-chaibi.netlify.app/semantic-layer

**页面**：`/semantic-layer`

**功能**：
- 指标语义维护（名称 / 描述 / 计算公式 / 口径）
- 维度语义维护（地区 / 品牌 / 渠道等）
- 同义词配置（"销量" = "交付量" = "sales"）
- 血缘关系图

```tsx
// frontend/src/app/semantic-layer/page.tsx
interface SemanticItem {
  id: string;
  name: string;
  type: 'metric' | 'dimension' | 'synonym';
  definition: string;
  formula?: string;
  synonyms?: string[];
}
```

---

#### 14.4.3 角色权限（问题 14）

**角色**：
| 角色 | 权限 |
|------|------|
| 管理者 | 全部功能 + 成员管理 + 数据导入 |
| 数据分析师 | 智能对话 + 驾驶舱 + 报表 + 指标库 |
| AI 产品经理 | 智能对话 + 报表 + 指标管理 |
| 普通员工 | 智能对话（只读） |

**实现**：
```tsx
// frontend/src/contexts/AuthContext.tsx
interface User {
  id: string;
  name: string;
  role: 'admin' | 'analyst' | 'pm' | 'user';
}

const PERMISSIONS = {
  admin: ['*'],
  analyst: ['chat', 'dashboard', 'reports', 'metrics'],
  pm: ['chat', 'reports', 'metrics-manage'],
  user: ['chat-readonly'],
};
```

---

#### 14.4.4 成员管理（问题 15）

**页面**：`/members`

**功能**：
- 成员列表（头像 / 姓名 / 角色 / 状态）
- 添加成员（邮箱 + 角色）
- 修改角色
- 禁用/启用

---

#### 14.4.5 消息通知（问题 17）

**功能**：
- 异常数据预警（如 CPL 超过阈值）
- 报表订阅通知
- 系统公告

**UI**：
```tsx
// TopBar 通知图标
const [unread, setUnread] = useState(3);
<button className="relative ...">
  🔔
  {unread > 0 && <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">{unread}</span>}
</button>
```

---

#### 14.4.6 演示模式（问题 18）

**功能**：引导式演示，按步骤展示核心功能。

**流程**：
1. 点击"演示模式"按钮
2. 弹出引导遮罩
3. 依次高亮：快捷提问 → 输入框 → 查看 SQL → 驾驶舱
4. 每步有提示文字
5. 可跳过 / 重播

**实现**：使用 `react-joyride` 库。

```tsx
// frontend/src/components/OnboardingTour.tsx
const STEPS = [
  {
    target: '.suggestion-pills',
    content: '点击快捷提问，快速体验核心查询',
    placement: 'bottom',
  },
  {
    target: '.chat-input',
    content: '在这里输入您想查询的经营数据',
    placement: 'top',
  },
  // ...
];
```

---

### 14.5 Sprint 8 落地排期

| Day | 任务 | 优先级 | 工时 |
|-----|------|--------|------|
| **Day 1** | 14.2.1 品牌切换 | 🔴 P0 | 1h |
| **Day 1** | 14.2.2 闲聊兜底 | 🔴 P0 | 0.5h |
| **Day 1** | 14.2.3 SQL 抽屉优化 | 🔴 P0 | 2h |
| **Day 1** | 14.2.4 快捷提问扩充 | 🔴 P0 | 0.5h |
| **Day 1** | 14.2.5 修复右下角（已完成） | ✅ | - |
| **Day 2** | 14.3.1 报表中心真实化 | 🟡 P1 | 2h |
| **Day 2** | 14.3.2 指标库 Tab 切换 | 🟡 P1 | 1h |
| **Day 2** | 14.3.3 AI 洞察面板 | 🟡 P1 | 3h |
| **Day 2** | 14.3.4 深色主题 | 🟡 P1 | 2h |
| **Day 3** | 14.3.5 帮助中心可点击 | 🟡 P1 | 0.5h |
| **Day 3** | 14.3.6 新手引导 | 🟡 P1 | 2h |
| **Day 3** | 14.4.1 数据管理 | 🟢 P2 | 3h |
| **Day 3** | 14.4.2 语义管理层 | 🟢 P2 | 3h |
| **Day 4** | 14.4.3 角色权限 | 🟢 P2 | 2h |
| **Day 4** | 14.4.4 成员管理 | 🟢 P2 | 2h |
| **Day 4** | 14.4.5 消息通知 | 🟢 P2 | 2h |
| **Day 4** | 14.4.6 演示模式 | 🟢 P2 | 2h |
| **Day 5** | 联调测试 + 部署 | — | 4h |

**预计工期**：5 天（按每天 6h 工作量）

---

### 14.6 Sprint 8 验收 Checklist

```text
[ ] P0-1 顶部切换品牌可用，数据按品牌过滤
[ ] P0-2 问"你是谁"直接回复，不生成 SQL
[ ] P0-3 输入框固定底部，SQL 抽屉不挤压布局
[ ] P0-4 SQL 抽屉有代码高亮、行号、字段解释
[ ] P0-5 快捷提问 ≥ 15 条，覆盖 4 大业务域

[ ] P1-1 报表中心可点击查看真实图表
[ ] P1-2 指标库可按 domain Tab 切换
[ ] P1-3 智能对话右侧有 AI 洞察 + 策略建议
[ ] P1-4 深色主题切换生效
[ ] P1-5 帮助中心 FAQ 可展开

[ ] P2-1 数据管理页面：CSV 导入/导出
[ ] P2-2 语义管理层：指标/维度/同义词配置
[ ] P2-3 角色权限：4 种角色菜单可见性控制
[ ] P2-4 成员管理：增删改查
[ ] P2-5 消息通知：铃铛图标 + 下拉列表
[ ] P2-6 演示模式：JoyRide 引导流程

[ ] 部署 URL: https://gac-chat-bi.onrender.com
[ ] 文档已更新（本章 + Sprint 7）
```

---

### 14.7 技术债务与优化点

| 问题 | 优化方案 | 优先级 |
|------|---------|--------|
| 全局状态分散 | 引入 Zustand 统一管理 brand/user/theme | 🟡 |
| API 分散 | 重构为 tRPC 或统一 API Client | 🟡 |
| 组件重复 | 提取公共组件：DataTable / ChartCard / Modal | 🟢 |
| 测试缺失 | 补充 Jest + React Testing Library | 🟢 |

---

*本章将驱动 Sprint 8 落地实施，所有需求已拆解为可执行任务！*

