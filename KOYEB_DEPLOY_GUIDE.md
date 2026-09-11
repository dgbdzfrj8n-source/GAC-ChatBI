# 广汽云 ChatBI · 零成本部署指南（Vercel + Koyeb）

> 本指南用**纯免费 + 不绑信用卡**的方式，把 ChatBI 部署到生产环境。
> 适合个人作品集、企业内演示、简历项目展示。

---

## 📊 平台分工

| 角色 | 平台 | 免费额度 | 部署方式 |
|------|------|---------|---------|
| 前端 (Next.js) | **Vercel** | 100GB 带宽/月 + 无限部署 | Git 集成 |
| 后端 (FastAPI + DuckDB) | **Koyeb** | nano 实例 (512MB / 0.1 vCPU) | Docker |
| **总计** | | **0 元/月** ✅ | |

> 🟢 Koyeb 永久免费层无需绑卡，比 Render 更友好；不冷启动，访问即时响应。

---

## 🗺️ 整体架构

```
用户浏览器
    ↓
Vercel CDN (前端 · 全球加速)
    ↓  HTTPS /api/*
Koyeb Container (后端 · 法兰克福节点)
    ↓
DuckDB (内存 OLAP) + DeepSeek API (LLM)
```

---

## 🚀 部署步骤（预计 15 分钟）

### 第一步：准备 GitHub 仓库

确保你的代码已推送到 GitHub：
```bash
cd GAC-ChatBI
git add -A
git commit -m "chore: 配置 Vercel + Koyeb 部署物料"
git push origin main
```

---

### 第二步：部署后端到 Koyeb

#### 2.1 注册 Koyeb
1. 打开 https://www.koyeb.com
2. 点击 **Sign Up** → **Continue with GitHub**
3. 授权 Koyeb 访问你的 GitHub 仓库

#### 2.2 创建服务
1. 控制台首页 → **Create Web Service**
2. 选择 **GitHub** 作为部署源
3. 选仓库：`GAC-ChatBI`
4. 分支：`main`
5. 关键配置：
   - **Builder**：Docker
   - **Dockerfile path**：`backend/Dockerfile`
   - **Work directory**：留空（Dockerfile 已写 `WORKDIR /app`）
   - **Service name**：`gac-chatbi-api`
   - **Instance type**：**Nano**（免费）
   - **Region**：Frankfurt (fra)

#### 2.3 配置环境变量
在 Koyeb Service 页面 → **Environment variables**：

| Key | Value | 备注 |
|-----|-------|------|
| `LLM_API_KEY` | `sk-xxxxx` | **你的 DeepSeek Key** ⚠️ |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | |
| `FRONTEND_URL` | `https://gac-chatbi.vercel.app` | 部署前端后回填 |
| `PYTHONUNBUFFERED` | `1` | |
| `PYTHONPATH` | `/app` | |

#### 2.4 设置健康检查
- **Path**：`/api/health`
- **Port**：`8000`

#### 2.5 点 Deploy
- 等 3-5 分钟，状态变绿 = 部署成功
- 访问 `https://gac-chatbi-api-<你的账户>.koyeb.app/api/health`
- 应该返回：`{"status":"ok"}`

📝 **记录下你的 Koyeb URL**，下一步要用！

---

### 第三步：部署前端到 Vercel

#### 3.1 注册 Vercel
1. 打开 https://vercel.com
2. 点击 **Sign Up** → **Continue with GitHub**

#### 3.2 导入项目
1. 控制台 → **Add New** → **Project**
2. 选 `GAC-ChatBI` 仓库 → **Import**
3. 配置：
   - **Framework Preset**：Next.js（自动识别）
   - **Root Directory**：`frontend` ⚠️
   - **Build Command**：`npm run build`（默认即可）
   - **Output Directory**：`out`（Next.js 静态导出）

#### 3.3 配置环境变量
在 Vercel 项目 → **Settings** → **Environment Variables**：

| Key | Value | Environment |
|-----|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://gac-chatbi-api-xxx.koyeb.app` | **Production** |

> ⚠️ 粘贴第二步记录的 Koyeb URL，不要带尾部斜杠！

#### 3.4 点 Deploy
- 等 2-3 分钟，状态变绿 = 部署成功
- 访问 `https://gac-chatbi.vercel.app`（或 Vercel 自动分配的域名）

📝 **记录下你的 Vercel URL**，下一步要回填给后端！

---

### 第四步：回填前端 URL 给后端

回到 Koyeb → `gac-chatbi-api` → **Environment variables**：
- 把 `FRONTEND_URL` 改成实际的 Vercel URL，例如：
  ```
  FRONTEND_URL=https://gac-chatbi.vercel.app
  ```
- 保存 → Koyeb 自动重新部署（约 1 分钟）

---

## ✅ 验收测试清单

打开 Vercel 给你的 URL，依次测试：

| 测试项 | 预期结果 | ✅ |
|--------|---------|---|
| 主聊天界面 | 能看到欢迎卡片和输入框 | ☐ |
| 提问："本月销量如何" | 表格 + 趋势图渲染成功 | ☐ |
| 开启 SOP 归因分析 | 显示"📊 归因链路" | ☐ |
| 驾驶舱大屏 `/dashboard` | 4 个 KPI 卡片 + 3 个图表 | ☐ |
| 反馈点赞/点踩 | 提示"反馈已收到" | ☐ |
| 口碑雷达按钮 | 弹出 RAG 检索结果 | ☐ |

---

## 🔧 常见问题

### Q1：部署后前端报 404 / CORS 错误？
**A**：检查 Vercel 的 `NEXT_PUBLIC_API_URL` 是否正确，且 Koyeb 的 `FRONTEND_URL` 是否回填完成。两边都改完需要 2-3 分钟重新部署。

### Q2：提问没返回数据？
**A**：
1. 检查 Koyeb 的 `LLM_API_KEY` 是否正确
2. Koyeb Logs 找 `LLM call failed` 关键字
3. 访问 `/docs` 看 Swagger 是否能打开（能打开 = 服务起来了）

### Q3：Koyeb 免费实例会不会挂？
**A**：Koyeb 的 Nano 实例没有冷启动机制，但单实例挂了会自动重启。如果担心稳定性，可以升级到 Starter（$7/月）。

### Q4：数据会被清空吗？
**A**：Koyeb 容器重启会清空 DuckDB 的内存数据，但你的 `data/` 目录在 Docker 镜像里，**重启不会丢失**。如果担心，可以挂载 Koyeb Volume（高级用法）。

### Q5：怎么回滚到上一个版本？
**A**：
- **Koyeb**：Service → Deployments → 点旧版本 → Redeploy
- **Vercel**：Deployments → 点旧版本 → Promote to Production

---

## 🔄 后续更新代码

只需要 `git push origin main`：
- Koyeb 检测到 push → 自动构建镜像 → 自动部署（3-5 分钟）
- Vercel 检测到 push → 自动构建 → 自动部署（1-2 分钟）

---

## 💰 成本估算

| 服务 | 免费额度 | 超出后单价 |
|------|---------|----------|
| Vercel | 100GB 带宽/月 | $0.15/GB |
| Koyeb nano | 无限时间 | 无（Nano 永久免费） |
| DeepSeek | ¥1 元 ≈ 100 万 tokens | 按用量 |
| **个人作品集月成本** | | **≈ ¥0-3 元** |

> 对比：同样配置的 Render 要 $7/月（≈ ¥50），**省了 95%**。

---

## 🎁 加分项

部署成功后建议做这些：

1. **绑定自定义域名**（Vercel 免费送 1 个 `vercel.app` 子域名）
2. **加 Google Analytics** 统计访问量（作品集展示加分项）
3. **写 Release Notes** 在 GitHub Releases（展示工程规范）
4. **录 30 秒 demo 视频** 放在 README（招聘方最爱看）

---

## 📞 部署遇阻？

把以下截图发给我：
1. Koyeb Logs（部署失败的错误）
2. Vercel Build Logs
3. 浏览器 Console 报错

我直接帮你定位修复 🚀
