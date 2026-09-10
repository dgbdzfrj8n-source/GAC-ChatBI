# 广汽云 ChatBI 智能问数 Agent

> 🚗 面向大型车企集团的全链路经营决策问数 Agent · AI 产品经理全栈实战项目

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.0-black.svg)](https://nextjs.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP-yellow.svg)](https://duckdb.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## ✨ 核心特性

- 🤖 **自然语言问数**：业务人员用中文提问，AI 自动生成 SQL 并返回可视化数据
- 📊 **自适应图表**：根据查询结果自动推荐折线图、柱状图、饼图、双轴复合图
- 🛡️ **AST 只读安全**：100% 拦截 DDL/DML 注入，杜绝数据篡改风险
- 🎯 **指标口径统一**：6 项集团标准经营指标（M01-M06）严格一致
- ⚡ **秒级响应**：基于 DuckDB 嵌入式 OLAP，单次查询 < 50ms
- 💰 **零成本部署**：Netlify + Render + DuckDB，全免费云端分发

## 📂 项目结构

```
GAC-ChatBI/
├── .cursorrules              # Cursor AI Coding 规范
├── GAC_CHATBI_IMPLEMENTATION_GUIDE.md  # 完整实施手册（502 行）
├── backend/                  # Python FastAPI 后端
│   ├── api/                  # API 路由层（FastAPI + 零依赖 http.server 双引擎）
│   ├── core/                 # 核心 Agent 模块
│   │   ├── schema_linker.py        # Schema 动态剪枝（降低 85% Token）
│   │   ├── sql_executor.py         # AST 只读安全检查 + DuckDB 执行
│   │   ├── nl2sql_engine.py        # NL2SQL 主管道（含 Self-Healing 自愈）
│   │   ├── chart_recommender.py    # ECharts 自适应推荐
│   │   ├── sop_analyzer.py         # 四步归因 SOP 引擎
│   │   ├── metrics_dict.json       # 集团指标语义字典（6 项）
│   │   ├── metrics_dict.py         # 指标字典访问层
│   │   └── prompt_templates.py     # Few-Shot Prompt 库
│   ├── data/                 # 数据底座（DuckDB + SQLite 双引擎）
│   ├── eval/                 # 评测体系（20 道基准题）
│   ├── tests/                # 单元测试（Sprint 1/2）
│   └── requirements.txt
└── frontend/                 # Next.js 14 前端
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx        # 全局布局（含顶部导航）
    │   │   ├── page.tsx          # 问数对话主界面
    │   │   └── globals.css       # Tailwind 样式 + 品牌色板
    │   └── components/
    │       ├── Sidebar.tsx       # 左侧业务资产侧边栏
    │       ├── SuggestionPills.tsx   # 高频引导词
    │       ├── ChatMessage.tsx   # 消息气泡 + 折叠思考链
    │       ├── DataVisualizer.tsx   # 图表/表格双模切换
    │       ├── SqlDrawer.tsx     # SQL 抽屉（带语法高亮）
    │       └── BadCaseModal.tsx  # 点踩反馈收集
    ├── netlify.toml          # Netlify 部署配置
    ├── package.json
    ├── tailwind.config.ts
    └── tsconfig.json
```

## 🚀 快速启动

### 1. 后端服务（3 种启动方式）

```bash
# 方式 1：使用 Python 内置 http.server（零依赖，1 秒启动）
cd backend
python3 -m backend.api.server 8000

# 方式 2：FastAPI + Uvicorn（生产级）
pip install -r backend/requirements.txt
cd backend
python3 -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 数据生成（首次运行）

```bash
cd backend
python3 data/generate_mock_data.py
# 生成 gac_bi.duckdb (~1MB) 或 gac_bi.db (回退模式)
```

### 3. 前端启动

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
# 浏览器打开 http://localhost:3000
```

### 4. 运行测试验证

```bash
python3 backend/tests/test_sprint1.py   # Sprint 1（Schema 剪枝 + 安全拦截 + NL2SQL）
python3 backend/tests/test_sprint2.py   # Sprint 2（图表推荐 + HTTP 服务端到端）
```

## 📊 数据底座速览（Sprint 0 已交付）

| 表名 | 记录数 | 时间范围 | 业务粒度 |
|------|--------|---------|---------|
| `fact_sales_daily` | 19,440 行 | 2024-01-01 ~ 2025-04-30 | 日/品牌/车型/大区 |
| `dim_budget_target` | 48 行 | 16 个月 × 3 品牌 | 月/品牌 |
| `fact_marketing_expenses` | 5,832 行 | 2024-01-01 ~ 2025-04-30 | 日/品牌/渠道 |

**已植入的业务真实性特征**：
- 2 月春节淡季：销量环比 -35%
- 3 月节后反弹：销量环比 +25%
- 9-10 月金九银十：销量翘尾
- 12 月年末冲刺：超额完成目标
- 华东区折扣率放大、华南区销量权重 1.35x

## 🎯 核心指标体系（metrics_dict.json）

| ID | 指标 | 域 | 单位 |
|----|------|----|------|
| M01 | 销售达成率 | 整车销售 | % |
| M02 | 总交付量 | 整车销售 | 辆 |
| M03 | 单车成交均价 | 整车销售 | 元/辆 |
| M04 | 单车营销费用 | 经营财务 | 元/辆 |
| M05 | 单渠道获客成本(CPL) | 市场营销 | 元/条 |
| M06 | 客流成交转化率 | 渠道经营 | % |

## 🏗️ 架构亮点

```
[Web (Netlify)]  →  [FastAPI 网关]  →  [SchemaLinker 剪枝]
                                       →  [DeepSeek-V3 / Mock]
                                       →  [AST 只读检查]
                                       →  [DuckDB 列存执行]
                                       →  [ECharts 自适应推荐]
                                       →  [四步归因 SOP]
```

详细架构与全流程见 [`GAC_CHATBI_IMPLEMENTATION_GUIDE.md`](./GAC_CHATBI_IMPLEMENTATION_GUIDE.md)

## 📝 License

MIT