# 🚀 GAC-ChatBI 部署指南（Render 平台）

> 当前生产部署基于 Render 平台：前端 Static Site + 后端 Web Service
> 完整免费额度（无需绑卡）· 自动 HTTPS · Git 推送即部署

---

## 📊 平台分工

| 角色 | 平台 | 类型 | URL |
|------|------|------|-----|
| 前端 (Next.js 14) | **Render** | Static Site | https://gac-chat-bi.onrender.com |
| 后端 (FastAPI + DuckDB) | **Render** | Web Service (Docker) | https://gac-chatbi-api.onrender.com |
| CI | **GitHub Actions** | Workflow | PR + main 推送自动跑 |

**自动部署触发**：`git push origin main` → Render webhook → 重建 + 部署（约 3-5 分钟）

---

## 🗺️ 整体架构

```
用户浏览器
    ↓
Render CDN (前端 · 全球加速)
    ↓  HTTPS /api/* (CORS: NEXT_PUBLIC_API_URL)
Render Container (后端 · 美国节点)
    ↓
DuckDB (嵌入式列存 OLAP) + DeepSeek API (LLM)
    ↓
审计日志 (append-only) · Bad Case 表 (P2-4 + P2-7)
```

---

## 🚀 部署步骤（约 15 分钟首次 / 推送即部署后续）

### 第一步：准备 GitHub 仓库

```bash
cd GAC-ChatBI
git init  # 如果尚未初始化
git add .
git commit -m "feat: 初始版本"
git remote add origin https://github.com/<your-org>/GAC-ChatBI.git
git push -u origin main
```

### 第二步：Render 后端部署

1. 打开 https://dashboard.render.com
2. 点击 **New +** → **Web Service**
3. 选择 GitHub 仓库 `GAC-ChatBI`
4. 配置：
   - **Name**：`gac-chatbi-api`
   - **Region**：Oregon (US West) 或 Singapore
   - **Branch**：`main`
   - **Root Directory**：`backend`
   - **Runtime**：Docker
   - **Dockerfile Path**：`backend/Dockerfile`（如不存在则用 Python 环境）
   - **Plan**：Free

5. 添加环境变量（Environment）：

```bash
# 必填
ENV=production
PYTHONUNBUFFERED=1
LLM_PROVIDER=mock              # 或 deepseek
DUCKDB_PATH=/app/data/gac_bi.duckdb

# 可选（接入 DeepSeek）
DEEPSEEK_API_KEY=sk-xxx         # 如使用 mock 则无需填写
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# P2-4/P2-7 自动建表（启动时调用）
AUTO_INIT_AUDIT=true
```

6. **Advanced**：
   - **Health Check Path**：`/api/health`

7. 点击 **Create Web Service** → 等待 5-10 分钟构建

### 第三步：Render 前端部署

1. 点击 **New +** → **Static Site**
2. 选择同一仓库 `GAC-ChatBI`
3. 配置：
   - **Name**：`gac-chat-bi`
   - **Branch**：`main`
   - **Root Directory**：`frontend`
   - **Build Command**：`npm install && npm run build`
   - **Publish Directory**：`out`

4. 添加环境变量：

```bash
NEXT_PUBLIC_API_URL=https://gac-chatbi-api.onrender.com
NEXT_PUBLIC_APP_NAME=广汽云 ChatBI
```

5. **Redirects/Rewrites**：
   - Source：`/*`
   - Destination：`/index.html`
   - Status：`200`（SPA fallback）

6. 点击 **Create Static Site** → 等待 3-5 分钟构建

### 第四步：验证部署

```bash
# 后端健康检查
curl https://gac-chatbi-api.onrender.com/api/health

# 前端首页
curl -I https://gac-chat-bi.onrender.com/

# API 端点
curl https://gac-chatbi-api.onrender.com/api/metrics | head
```

打开浏览器：
- 前端：https://gac-chat-bi.onrender.com
- API 文档：https://gac-chatbi-api.onrender.com/docs

---

## ⚙️ 环境变量清单

### 后端（Web Service）

| 变量名 | 必填 | 默认 | 说明 |
|--------|------|------|------|
| `ENV` | ✅ | production | 运行环境 |
| `PYTHONUNBUFFERED` | ✅ | 1 | Python 日志立即输出 |
| `LLM_PROVIDER` | ✅ | mock | `mock` 或 `deepseek` |
| `DUCKDB_PATH` | ✅ | /app/data/gac_bi.duckdb | DuckDB 数据文件路径 |
| `DEEPSEEK_API_KEY` | ⚠️ | — | DeepSeek API key（仅 deepseek 模式） |
| `DEEPSEEK_BASE_URL` | ❌ | https://api.deepseek.com/v1 | LLM API base URL |
| `DEEPSEEK_MODEL` | ❌ | deepseek-chat | LLM 模型名 |
| `AUTO_INIT_AUDIT` | ❌ | true | 启动时初始化审计表 |
| `LOG_LEVEL` | ❌ | INFO | 日志级别 |

### 前端（Static Site）

| 变量名 | 必填 | 默认 | 说明 |
|--------|------|------|------|
| `NEXT_PUBLIC_API_URL` | ✅ | http://localhost:8000 | 后端 API 地址（生产替换） |
| `NEXT_PUBLIC_APP_NAME` | ❌ | 广汽云 ChatBI | 应用名 |

---

## 🔄 持续部署

### 自动触发（推荐）

```bash
git add .
git commit -m "feat: 新功能"
git push origin main
# → Render 自动拉取 → 重新构建 → 重新部署
# → 约 3-5 分钟后线上生效
```

### 手动触发

在 Render Dashboard 选择对应 Service → **Manual Deploy** → **Deploy latest commit**

---

## 🐛 故障排查

### 后端启动失败：`ModuleNotFoundError`

- 检查 `backend/requirements.txt` 是否完整
- 确认 Render Dockerfile / Python 路径正确

### 前端构建失败：`Module not found`

- 检查 `frontend/package.json` 依赖完整
- 确认环境变量 `NEXT_PUBLIC_API_URL` 在 build 时已设置

### CORS 错误

- 检查后端 `CORSMiddleware` 配置允许 `https://gac-chat-bi.onrender.com`
- 在 `backend/api/main.py` 中允许 origins

### 数据丢失

- Render 免费层文件系统是**临时**的，重启会丢失 DuckDB 文件
- **生产建议**：用 Render Persistent Disk（$1/月/GB）或迁移到云数据库

### 冷启动慢

- Render 免费层会空闲休眠（15 分钟无访问）
- 首次访问会触发冷启动，约 30-60 秒
- **付费方案** ($7/月) 可保持常驻

---

## 💰 成本估算

| 方案 | 月成本 | 性能 |
|------|--------|------|
| **全免费层** | ¥0 | 冷启动 30-60s，文件临时 |
| **后端 Standard** | $7/月 | 常驻 + 持久磁盘 |
| **后端 Pro + 数据库** | $25/月 | 全性能 + 1GB 持久 + 监控 |

---

## 📊 监控

### Render 内置

- **Metrics**：CPU / 内存 / 带宽
- **Logs**：实时日志流
- **Events**：部署历史

### 健康检查

后端 `GET /api/health` 返回：

```json
{
  "status": "healthy",
  "service": "GAC-ChatBI API",
  "version": "1.8.0",
  "duckdb": "ok",
  "audit_tables": "ready",
  "ts": "2026-09-13T10:00:00Z"
}
```

可对接：
- UptimeRobot（免费监控）
- Better Stack
- Datadog

---

## 🔐 安全建议

1. **API Key 隔离**：DeepSeek key 用 Render Secret（加密存储）
2. **CORS 白名单**：后端只允许生产前端域名
3. **Rate Limit**：生产可加 `slowapi` 限流
4. **审计日志**：P2-4 已自动记录所有写操作
5. **HTTPS**：Render 自动配置 Let's Encrypt

---

## 📦 数据持久化方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **Render 临时 FS** | 免费 | 重启丢失 ❌ |
| **Render Persistent Disk** ($1/GB/月) | 简单 | 单实例 |
| **AWS S3 + DuckDB 备份** | 便宜 + 可靠 | 需手动恢复 |
| **云数据库（PostgreSQL/ClickHouse）** | 企业级 | 复杂 |

**当前选择**：演示用临时 FS（每次重启重新生成数据），生产用 Persistent Disk。

---

## 🔄 从 Koyeb 迁移到 Render（已完成）

历史部署基于 Koyeb，2026-09 切换到 Render：
- Koyeb 优势：永久免费层不绑卡
- Render 优势：更稳定的 Build Cache + 更好的 GitHub 集成
- 旧 Koyeb 部署指南保留在 `KOYEB_DEPLOY_GUIDE.md`

---

## 🎓 下一步优化

- [ ] 接入企业 SSO（飞书 / 钉钉 / 企微）
- [ ] 接入真实数据源（SAP / 用友 / 销售易）
- [ ] 切换到付费层（避免冷启动）
- [ ] 配置 CDN（Cloudflare）加速静态资源
- [ ] 接入 APM（Application Performance Monitoring）
- [ ] 增加 WAF（Web Application Firewall）
