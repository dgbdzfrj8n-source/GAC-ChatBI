# Render 控制台操作 Checklist

> 目的：删除两个 Deploy failed 的 service，重新用 Blueprint 部署，并补上 LLM_API_KEY
> 总耗时：**~15 分钟**（含部署等待）

---

## 🚨 步骤 1：登录并进入服务列表（30 秒）

1. 浏览器打开 https://dashboard.render.com/
2. 用你的 GitHub 账号登录（首次会要求授权 GitHub）
3. 进入后你应该看到主面板，左侧导航栏有 **Dashboard / Services / Blueprints / etc.**

**你看到的应该是这样**：

```
+ New +
─────────────────────────────────────
📦 gac-chatbi-api       [Deploy failed]  ← 红框
📦 gac-chat-bi          [Deploy failed]  ← 红框
```

---

## 🗑️ 步骤 2：删除失败的后端服务（30 秒）

1. **点击 `gac-chatbi-api`**（后端那个，有红色 Deploy failed 标志）
2. 进入服务详情页后，**左侧菜单**找 **Settings**（在最下面）
3. 滚到页面**最底部**，找到一个红色框框：**Danger Zone**
4. 框里有一个按钮 **Delete Service**（或 Delete Web Service）
5. 点它 → 弹出确认对话框 → 输入服务名 `gac-chatbi-api` → 点 **Delete**

---

## 🗑️ 步骤 3：删除失败的前端服务（30 秒）

1. 回到 Dashboard 主页面
2. **点击 `gac-chat-bi`**（前端那个，红框）
3. 同样：**Settings → 滚到底部 → Danger Zone → Delete Service**
4. 输入 `gac-chat-bi` 确认删除

> ⚠️ **两个都删完后，Dashboard 应该显示空**（或者只剩你想保留的其他服务）

---

## 🆕 步骤 4：用 Blueprint 重新创建（1 分钟）

1. 顶部右上角找到一个 **"+ New +"** 按钮（蓝色）
2. 下拉菜单选 **"Blueprint"**
3. 进入页面后：
   - **"Connect a repository"**：选 `dgbdzfrj8n-source/GAC-ChatBI`（如果没有授权，先点 "Configure account" 授权 GitHub）
   - **Name**：保持默认（Render 会从 render.yaml 推断）
4. 点底部蓝色按钮 **"Next"** 或 **"Apply"**
5. Render 会读取仓库根目录的 `render.yaml`，列出 2 个即将创建的 service：

   ```
   ✅ gac-chatbi-api  (Web Service, Docker)
   ✅ gac-chat-bi     (Static Site)
   ```

6. 点 **"Apply"** 或 **"Create Services"**

> ⏳ 这一步之后 Render 会自动开始构建两个服务，**不需要任何操作**，等待就行。

---

## 🔑 步骤 5：添加 LLM_API_KEY（必须，否则聊天调不通）（30 秒）

> 这一步要在第一个 service 创建后立刻做，否则就算 build 成功，聊天问数也会 500 报错。

1. 在 Dashboard 上 **点击 `gac-chatbi-api`**（正在或已经构建的那个）
2. 左侧菜单 → **Environment**（不是 Settings）
3. 页面下方有一个表单：**"Add Environment Variable"**
4. 填：
   - **Key**：`LLM_API_KEY`
   - **Value**：`sk-你的真实DeepSeek密钥`（粘贴你自己的 DeepSeek key）
5. 右边下拉框选 **"Sync"**（意思是跟部署同步）
6. 点 **"Save Changes"**

> 自动会触发一次重启（~1 分钟），重启完后 `/api/health` 才会出现 `engine: DuckDB`

---

## ⏳ 步骤 6：等待构建完成（被动等待 5-10 分钟）

在 Dashboard 上你能看到每个服务右上角的状态：

| 状态 | 含义 | 你要做的 |
|---|---|---|
| `Building` | 正在 Docker build | 等 |
| `Deploying` | 镜像构建完，开始部署 | 等 |
| `Live`（绿） | 部署成功，service 在线 | 恭喜，**进入验证** |
| `Failed`（红） | 又失败了 | 看下面的排错 |

> 如果 10 分钟过去了还在 Building → 看下面"卡住怎么办"

---

## ✅ 步骤 7：验证服务真的上线了（30 秒）

打开你的 Terminal（macOS 自带的 Terminal.app），粘这几行：

```bash
echo "后端健康检查："
curl -sS --max-time 15 https://gac-chatbi-api.onrender.com/api/health
echo ""
echo ""
echo "前端首页："
curl -sS -o /dev/null -w "HTTP %{http_code} | %{size_download} bytes\n" https://gac-chat-bi.onrender.com/
```

**预期结果**：

```
后端健康检查：
{"status":"healthy","service":"GAC-ChatBI API","engine":"DuckDB","database_file":"/app/data/gac_bi.duckdb","timestamp":"..."}

前端首页：
HTTP 200 | 24800 bytes
```

如果返回 `engine: SQLite3` 而不是 `DuckDB` → 说明 backend/data/gac_bi.duckdb 没被拷贝进去，需要再修 Dockerfile。

---

## 🎉 步骤 8：浏览器手动验证（2 分钟）

打开浏览器，访问 https://gac-chat-bi.onrender.com/ ：

| 验证项 | 应该看到 |
|---|---|
| 页面加载 | 顶部有 Logo / 角色切换 / **🔔 铃铛图标** |
| 点击"数据管理"左侧菜单 | 显示用户表列表（即使为空也应有"暂无数据"提示） |
| 点 🔔 铃铛 | 下拉显示 7-12 条通知（按角色过滤） |
| 在聊天框问"广汽传祺 3 月销量" | 返回 SQL + 图表 + 经营洞察 |

---

## 🛟 卡住了怎么办？（自助排错）

### 情况 A：构建一直停在 "Building"，超过 15 分钟

**原因**：免费版 Docker build machine 偶发排队。
**解决**：
1. 打开 service → 左侧 **Events** → 看最后一行日志
2. 如果显示 "Waiting for available build machine..." → **等**（最多 30 分钟）
3. 如果显示具体的 build 错误 → 复制错误末尾 10 行发给我

### 情况 B：Build 报错 `pip install failed` / `Module not found`

**原因**：依赖装不上。
**解决**：
1. 打开 service → 左侧 **Logs**（不是 Events，是实时日志）
2. 滚到报错处，看完整的堆栈
3. 截图发给我，我会改 backend/requirements.txt

### 情况 C：Build 成功但 Deploy 失败

**原因**：容器启动失败（依赖缺失、端口冲突等）。
**解决**：
1. 打开 service → 左侧 **Logs**
2. 找最后 50 行，特别看包含 `Traceback`、`Error`、`exec format error` 的字样
3. 截图发给我

### 情况 D：服务是 Live 状态但 curl 超时

**原因**：可能是 Render 给你分配的临时域名（如果你之前删了 service，URL 可能变成新随机串）。
**解决**：
1. Dashboard 上点开 service，看右上角 **URL** 字段
2. 把它和我在指南里写的 URL 比对，如果不一样 → 用新的 URL 验证
3. 也告诉我新 URL，我重新记一下

### 情况 E：build 通过但 `/api/health` 返回 engine: SQLite3

**原因**：`backend/data/gac_bi.duckdb` 没被打包进镜像。
**排查**：
1. 打开 service → Logs → 找 `database_file:` 后面那个路径
2. 如果是 `/app/data/gac_bi.db` 而不是 `/app/data/gac_bi.duckdb` → 真的没打包进去
3. 截图发给我，我改 Dockerfile 加 `.dockerignore` 排除规则 + 强制 COPY data/

---

## 📝 一句话速查卡

```
Dashboard → 删除两个失败服务
New + → Blueprint → 选仓库 → Apply
Environment → 加 LLM_API_KEY = sk-xxx
等 5-10 分钟
curl 验证 → 浏览器手动验证 → 完成
```

---

## 🚀 完成后请告诉我

1. **两个 service 都 Live（绿）了吗？** ✅ / ❌
2. **curl /api/health 返回的 engine 是什么？** (DuckDB / SQLite3)
3. **浏览器打开前端，能看到 🔔 铃铛吗？**
4. **聊天问数能正常返回结果吗？**

如果哪步卡住，**截图发我**，我直接帮你看。
