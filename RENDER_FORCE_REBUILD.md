# 🚨 Render 强制 Rebuild 操作指南

> 状态：service 进程能跑，但 main.py 跑的是 `542f525`（2026-09-11 旧版），
> **缺所有 P2 功能**：数据管理 / 语义层 / 角色权限 / 审计 / BadCase / 通知中心
>
> 必须**清缓存、强制 rebuild**，否则 Render 会用旧 Docker layer。

---

## 🎯 一句话

```
Service → 右上 Manual Deploy → Clear build cache & deploy
```

---

## Step 1：打开后端 service

https://dashboard.render.com/web-services → 找到 `gac-chatbi-api`（如果列表里看到红色 "Deploy failed"，**先确认服务还能进**）

⚠️ **如果服务被 Suspended 状态**：先在右上角点 **"Resume Service"** → 等 1 分钟 → 再做下面操作

## Step 2：触发强制 rebuild

1. 进 service 后，**右上角**找到蓝色按钮 **"Manual Deploy"**
2. 下拉菜单，**选第 3 个**：
   ```
   Manual Deploy
   ├─ Deploy latest commit
   ├─ Deploy a specific commit (by SHA)
   └─ 🔥 Clear build cache & deploy  ← 选这个
   ```
3. 会弹一个确认框："This will invalidate the build cache and rebuild from scratch"
4. 点 **Confirm** 或 **Deploy**

> ⏳ **耗时 8-15 分钟**（因为从 0 开始 build + 安装 gcc + 装 duckdb）

## Step 3：等 build 完成（实时看 logs）

到 service 详情页 **左侧菜单 → Logs** 拉到底部看实时日志。

**正常 build 进度**：
```
==> Building Docker image...
==> Installing system packages: gcc g++ libstdc++6
==> Installing Python dependencies
==> Collecting duckdb             ← 关键，要 30-60 秒
==> Building wheel for duckdb    ← 编译，要 1-3 分钟
==> Successfully installed duckdb-1.x.x
==> ...
==> Build succeeded 🎉
==> Deploying...
==> Your service is live 🎉
```

**如果 build 卡死**：
- 看最后一行日志判断阶段
- "Waiting for free builder instance" → 免费版排队，等 5-30 分钟
- "Could not resolve to a Git repository" → github 授权问题，重连

## Step 4：build 完成后立刻验证

跑这个命令看路由是不是 26 个：
```bash
curl -sS https://gac-chatbi-api.onrender.com/openapi.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
paths = sorted(d['paths'].keys())
print(f'总计 {len(paths)} 个路由')
for p in paths:
    if 'data' in p or 'audit' in p or 'bad' in p or 'roles' in p:
        print(f'  ✅ {p}')
"
```

**期望输出**：能看到 `/api/data/uploads` `/api/audit/list` 等 8-12 个新路由
**现在的输出**：完全没有这些（生产还停在 12 路由）

## Step 5：同样的方法重新部署前端

1. 回到 Dashboard
2. 点 `gac-chat-bi`（前端 Static Site）
3. 右上角 **Manual Deploy** → **Clear build cache & deploy**（Static Site 没有 build cache，这个步骤可选但推荐）
4. 等 3-5 分钟

## Step 6：浏览器手动验证

打开 https://gac-chat-bi.onrender.com/，强刷（Cmd+Shift+R），应该看到：
- ✅ 🔔 铃铛在右上角
- ✅ "数据管理"在左侧菜单
- ✅ 点击数据管理 → 显示用户表列表
- ✅ 角色切换器在右上角
- ✅ 聊天问数能正常返回结果

---

## 🛟 如果 Clear Cache 还不行

### 备选方案 A：Suspend → Resume

1. Settings → **Suspend Service** → 确认
2. 等 30 秒
3. Settings → **Resume Service**
4. 这会强制 Render 重启并从零加载 image

### 备选方案 B：删除再重建（最后手段）

⚠️ 会丢失环境变量，要重新加 LLM_API_KEY：

1. Settings → 滚到底 → **Danger Zone** → Delete Service
2. 顶部 **+ New +** → Blueprint → 选仓库 → Apply
3. Environment → 加 `LLM_API_KEY=sk-xxx`
4. 等 10 分钟

### 备选方案 C：换平台（如果 Render 一直出问题）

考虑 Vercel / Railway / Fly.io，Dockerfile 可以不变。

---

## 📊 完成后请告诉我

跑这一句给我看结果：
```bash
curl -sS https://gac-chatbi-api.onrender.com/openapi.json | python3 -c "import json,sys; print(f'{len(json.load(sys.stdin)[\"paths\"])} 个路由')"
```

- 如果输出 **"26 个路由"** → 完美，build 成功 ✅
- 如果输出 **"12 个路由"** → 还是旧版本，build 没生效 ❌
