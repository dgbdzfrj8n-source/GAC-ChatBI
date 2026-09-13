# 广汽云 ChatBI 智能问数 Agent

> 🚗 面向大型车企集团的全链路经营决策问数 Agent · AI 产品经理全栈实战项目
>
> 从自然语言提问到智能归因 · 从指标治理到合规审计 · 4 角色权限矩阵 · 一键演示模式

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.0-black.svg)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)](https://www.typescriptlang.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg)](https://fastapi.tiangolo.com/)
[![DuckDB](https://img.shields.io/badge/DuckDB-OLAP-yellow.svg)](https://duckdb.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![CI](https://github.com/dgbdzfrj8n-source/GAC-ChatBI/actions/workflows/ci.yml/badge.svg)

**🌐 在线体验**：
- 前端：https://gac-chat-bi.onrender.com
- 后端 API：https://gac-chatbi-api.onrender.com/docs

---

## 📖 项目简介

**GAC-ChatBI** 是面向大型车企集团（以广汽集团为蓝本）的智能经营分析平台。业务人员用自然语言提问，系统自动完成"理解 → NL2SQL → 安全校验 → 自适应图表 → 智能归因"全链路，并配套 4 角色权限矩阵、语义层治理、Bad Case 闭环、操作审计等企业级能力。

### 解决的核心痛点

| 痛点 | 解决方案 |
|------|---------|
| 业务人员不会 SQL | 🤖 自然语言问数 · AI 自动生成 DuckDB SQL |
| 同一指标口径不一 | 📚 语义层管理 · 6 个集团标准指标 100% 一致 |
| 误操作风险 | 🛡️ AST 只读校验 · 100% 拦截 DDL/DML |
| 数字异常找不到原因 | 🔍 4 步归因 SOP 引擎 · 一键深度归因 |
| 反馈无人跟进 | 🐛 Bad Case 闭环 · 一键关联语义层 |
| 角色权限混乱 | 👥 4 角色矩阵 · 路由级 + 按钮级双重隔离 |
| 缺少合规审计 | 🔍 append-only 审计日志 · 谁/何时/改了什么 |

---

## ✨ 核心特性

### P0 - 数据底座 & 安全保障
- 🛡️ **AST 只读安全**：基于 `sqlglot` 解析 SQL，100% 拦截 DDL/DML 注入
- 📚 **Schema 动态剪枝**：根据 NL 关键词智能过滤表/字段，Token 消耗降低 85%
- ⚡ **DuckDB 列存引擎**：单次查询 < 50ms，支撑 19,440 行日销售数据
- 🎯 **6 项集团标准指标**（M01-M06）：严格一致的口径字典

### P1 - 智能分析与可视化
- 🤖 **NL2SQL 主管道**：DeepSeek-V3 + Few-Shot Prompt + Self-Healing 自愈
- 📊 **ECharts 自适应推荐**：折线/柱状/饼图/双轴复合图自动选型
- 🔍 **4 步归因 SOP**：销量异动一键深度归因（外部/内部/同比/环比）
- 📈 **驾驶舱大屏**：4 KPI + 趋势 + 排名 + 预警一屏掌控
- 🎬 **流式输出**：Agent 思考链逐字输出，体验接近 ChatGPT

### P2 - 企业级治理（✅ 全部交付）
| 子任务 | 功能 | 入口 |
|--------|------|------|
| P2-1 | 📤 数据管理（CSV 导入/导出/预览/删除，独立 DuckDB 库） | `/data-manager` |
| P2-2 | 🧠 语义层管理（指标/维度/同义词三层 + 编辑 + 召回预览） | `/semantic` |
| P2-3 | 👥 4 角色权限（高管/分析师/AI PM/访客 + 路由级守卫） | TopBar 切换器 |
| P2-4 | 🔍 操作审计日志（append-only · 7 类动作 · 3 类分布） | `/audit` |
| P2-5 | 🔔 消息通知中心（7 类通知 · 铃铛下拉 · 角色过滤） | TopBar 铃铛 |
| P2-6 | 🎓 演示模式（5 步新手引导 · 自研无依赖） | TopBar 🎓 图标 |
| P2-7 | 🐛 Bad Case 闭环（采纳/不采纳/修正 + AI PM 一键闭环） | `/bad-case` |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                       前端 (Next.js 14 + TypeScript)              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Sidebar  │ │ TopBar   │ │ ChatPage │ │ Dashboard / Audit │   │
│  │ 菜单路由 │ │ 角色切换 │ │ 流式问数 │ │ /semantic /bad-case│  │
│  └──────────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘   │
│                    │  4 角色   │                  │              │
│  ┌─────────────────┴────────────┴──────────────────┴────────┐   │
│  │ BrandContext / RoleContext / NotificationContext          │  │
│  └─────────────────────────────────────────────────────────┬─┘   │
└────────────────────────────────────────────────────────────┼─────┘
                            │ HTTPS (CORS / JWT-less)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       后端 (FastAPI · 30+ 端点)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ SchemaLinker │→ │  NL2SQL LLM  │→ │ AST ReadOnly Guard    │  │
│  │   85% 剪枝   │  │ DeepSeek-V3  │  │     (sqlglot)         │  │
│  └──────────────┘  └──────────────┘  └──────────┬───────────┘  │
│                                                  ▼              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ ChartRecom.  │← │ SOP Analyzer │← │   DuckDB / SQLite    │  │
│  │  ECharts 推荐 │  │ 4 步归因引擎 │  │    gac_bi.duckdb     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                  │
│  P2 治理层：语义层服务 · 数据管理 · 审计日志 · Bad Case 闭环    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       数据底座 (DuckDB / SQLite)                  │
│  fact_sales_daily (19,440 行) · dim_budget_target · marketing   │
│  + user_datasets (CSV 导入) · audit_log · bad_case (P2)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 项目结构

```
GAC-ChatBI/
├── README.md                          # 本文件
├── GAC_CHATBI_IMPLEMENTATION_GUIDE.md  # 完整实施手册（1957 行）
├── DEMO_GUIDE.md                      # 5 分钟演示脚本
├── DEPLOY_GUIDE.md                    # Render 部署详细说明
├── render.yaml                        # Render 声明式 IaC
│
├── backend/                           # Python FastAPI 后端
│   ├── api/
│   │   ├── main.py                    # FastAPI 主入口（30+ 端点）
│   │   └── schemas.py                 # Pydantic v2 模型
│   ├── core/
│   │   ├── schema_linker.py           # Schema 动态剪枝（Token -85%）
│   │   ├── sql_executor.py            # AST 只读安全检查 + DuckDB 执行
│   │   ├── nl2sql_engine.py           # NL2SQL 主管道 + Self-Healing
│   │   ├── chart_recommender.py       # ECharts 自适应推荐
│   │   ├── sop_analyzer.py            # 4 步归因 SOP 引擎
│   │   ├── metrics_dict.json          # 集团指标语义字典
│   │   └── prompt_templates.py        # Few-Shot Prompt 库
│   ├── services/
│   │   ├── semantic_layer.py          # P2-2 语义层管理
│   │   ├── data_manager.py            # P2-1 数据管理
│   │   ├── audit_log.py               # P2-4 审计日志
│   │   └── rag_retriever.py           # RAG 检索
│   ├── data/                          # DuckDB 数据底座
│   ├── tests/                         # 测试套件
│   │   ├── test_sprint1.py
│   │   ├── test_sprint2.py
│   │   ├── test_role_permissions.py
│   │   └── test_audit_badcase_api.py
│   ├── eval/                          # 评测体系（20 道基准题）
│   └── requirements.txt
│
└── frontend/                          # Next.js 14 前端
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx             # 全局布局 + 4 嵌套 Provider
    │   │   ├── page.tsx               # 智能对话主页面
    │   │   ├── dashboard/             # P1 驾驶舱
    │   │   ├── reports/               # 报表中心
    │   │   ├── metrics/               # 指标库
    │   │   ├── tables/                # 数据表
    │   │   ├── data-manager/          # P2-1 数据管理
    │   │   ├── semantic/              # P2-2 语义层
    │   │   ├── bad-case/              # P2-7 Bad Case 收件箱
    │   │   ├── audit/                 # P2-4 审计日志
    │   │   ├── history/               # 历史会话
    │   │   ├── settings/              # 设置
    │   │   └── help/                  # 帮助
    │   ├── components/
    │   │   ├── Sidebar.tsx            # 侧边栏（按角色过滤）
    │   │   ├── TopBar.tsx             # 顶部栏（角色切换 + 通知 + 演示）
    │   │   ├── NotificationBell.tsx   # P2-5 通知中心
    │   │   ├── FeedbackButtons.tsx    # P2-7 反馈按钮
    │   │   ├── ChatMessage.tsx        # AI 消息 + 折叠思考链
    │   │   ├── DataVisualizer.tsx     # ECharts 图表
    │   │   ├── SqlDrawer.tsx          # SQL 抽屉
    │   │   ├── DemoTour.tsx           # P2-6 演示模式
    │   │   └── ... 30+ 组件
    │   ├── contexts/
    │   │   ├── BrandContext.tsx
    │   │   ├── RoleContext.tsx        # P2-3 角色
    │   │   └── NotificationContext.tsx # P2-5 通知
    │   └── lib/
    │       ├── menu.ts                # 菜单配置
    │       ├── roles.ts               # 角色权限矩阵
    │       ├── notifications.ts       # P2-5 通知类型
    │       └── ...
    ├── netlify.toml
    ├── package.json
    ├── tailwind.config.ts             # 广汽品牌色板
    └── tsconfig.json
```

---

## 🚀 快速启动

### 前置要求

- Python 3.10+
- Node.js 18+
- 2GB 内存

### 1. 克隆仓库

```bash
git clone https://github.com/dgbdzfrj8n-source/GAC-ChatBI.git
cd GAC-ChatBI
```

### 2. 后端启动

```bash
cd backend
pip install -r requirements.txt
python3 data/generate_mock_data.py   # 首次生成 ~1MB DuckDB
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
# API 文档：http://localhost:8000/docs
```

### 3. 前端启动

```bash
cd frontend
npm install
cp .env.example .env.local   # 配置 NEXT_PUBLIC_API_URL
npm run dev
# 浏览器打开 http://localhost:3000
```

### 4. 一键演示

打开前端 → 点击 TopBar 右侧 🎓 图标 → 跟随 5 步新手引导 → 完整体验

或跟随 [`DEMO_GUIDE.md`](./DEMO_GUIDE.md) 的 5 分钟演示脚本。

---

## 🧪 测试与质量

| 测试维度 | 命令 | 通过率 |
|----------|------|--------|
| **TypeScript 类型** | `cd frontend && npx tsc --noEmit` | ✅ 0 报错 |
| **Sprint 1 单元** | `python3 backend/tests/test_sprint1.py` | ✅ Schema 剪枝 + AST 安全 + NL2SQL |
| **Sprint 2 单元** | `python3 backend/tests/test_sprint2.py` | ✅ 图表推荐 + HTTP 服务端到端 |
| **权限矩阵** | `python3 backend/tests/test_role_permissions.py` | ✅ 9 关键场景 + 10 路径 |
| **审计 + Bad Case** | `python3 backend/tests/test_audit_badcase_api.py` | ✅ 9 断言全过 |
| **CI 自动** | GitHub Actions · PR + main 推送 | ✅ 自动跑全部 |

---

## 📊 数据底座

| 表名 | 记录数 | 时间范围 | 业务粒度 |
|------|--------|---------|---------|
| `fact_sales_daily` | 19,440 行 | 2024-01-01 ~ 2025-04-30 | 日/品牌/车型/大区 |
| `dim_budget_target` | 48 行 | 16 个月 × 3 品牌 | 月/品牌 |
| `fact_marketing_expenses` | 5,832 行 | 2024-01-01 ~ 2025-04-30 | 日/品牌/渠道 |
| `user_datasets` | 用户导入 | — | CSV 自定义 |
| `audit_log` (P2-4) | append-only | — | 操作审计 |
| `bad_case` (P2-7) | 用户反馈 | — | Bad Case 闭环 |

**已植入的业务真实性特征**：
- 2 月春节淡季：销量环比 -35%
- 3 月节后反弹：销量环比 +25%
- 9-10 月金九银十：销量翘尾
- 12 月年末冲刺：超额完成目标
- 华东区折扣率放大、华南区销量权重 1.35x

---

## 🎯 核心指标体系

| ID | 指标 | 域 | 单位 | 公式 |
|----|------|----|------|------|
| M01 | 销售达成率 | 整车销售 | % | actual / target × 100 |
| M02 | 总交付量 | 整车销售 | 辆 | SUM(销量) |
| M03 | 单车成交均价 | 整车销售 | 元/辆 | 销售额 / 销量 |
| M04 | 单车营销费用 | 经营财务 | 元/辆 | 营销费用 / 销量 |
| M05 | 单渠道获客成本(CPL) | 市场营销 | 元/条 | 渠道费用 / 线索数 |
| M06 | 客流成交转化率 | 渠道经营 | % | 成交 / 到店 |

口径详情见 `backend/core/metrics_dict.json`。

---

## 🎭 4 角色权限矩阵

| 角色 | 标识 | 可见菜单 | 关键权限 |
|------|------|---------|---------|
| 🚗 **高管** (executive) | 高管视角 | 首页/驾驶舱/报表/指标/审计/设置/帮助 | 全局决策视角 |
| 📊 **分析师** (analyst) | 业务操作 | 高管全部 + 数据表/数据管理/历史/Bad Case | 数据操作 + 反馈闭环 |
| 🧠 **AI 产品经理** (product) | 治理视角 | 分析师全部 + **语义层管理** | 指标口径治理 |
| 👁️ **访客** (guest) | 只读访客 | 仅首页/驾驶舱/帮助 | 只读 |

权限矩阵前后端一致性测试通过（9 关键场景 + 10 路径）。

---

## 🎨 技术栈

### 后端
- **Python 3.10+** + **FastAPI** + **Uvicorn**
- **DuckDB 1.x**（列存 OLAP）+ **SQLite 3**（回退）
- **sqlglot**（AST 安全校验 + SQL 解析）
- **Pydantic v2**（请求/响应模型）
- **httpx**（调用 LLM）
- **DeepSeek-V3** / Mock LLM（可切换）

### 前端
- **Next.js 14**（App Router）+ **TypeScript 5**
- **Tailwind CSS 3**（广汽品牌色板：003C8F / C8102E）
- **ECharts 5**（SSR 安全 + 客户端动态导入）
- **Lucide Icons** + **Heroicons**
- 自研轻量组件（零额外 UI 库依赖）

### DevOps
- **Render**（前端 Static Site + 后端 Docker Web Service）
- **GitHub Actions**（CI：lint / type-check / build）
- **声明式 IaC**：`render.yaml`

---

## 🔄 自动部署

| 平台 | 触发 | 状态 |
|------|------|------|
| 前端（`gac-chat-bi`） | Render Static Site · 监听 `main` | https://gac-chat-bi.onrender.com |
| 后端（`gac-chatbi-api`） | Render Web Service · 监听 `main` | https://gac-chatbi-api.onrender.com |
| CI | GitHub Actions · PR + main 推送 | 自动跑 lint / type-check / build |

**只要你执行 `git push origin main`，Render 会自动重新部署前端 + 后端**，无需任何手动操作。

完整部署说明见 [`DEPLOY_GUIDE.md`](./DEPLOY_GUIDE.md)。

---

## 📝 License

MIT
