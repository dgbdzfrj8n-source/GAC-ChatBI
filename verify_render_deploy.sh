#!/bin/bash
# ============================================
# Render 部署验证脚本
# 用法：bash verify_render_deploy.sh
# 期望：看到所有模块都 ✅
# ============================================

set -e

API_BASE="https://gac-chatbi-api.onrender.com"
FRONT_BASE="https://gac-chat-bi.onrender.com"

echo "════════════════════════════════════════════"
echo "🔍 GAC-ChatBI Render 部署验证"
echo "════════════════════════════════════════════"
echo ""

# 1. 后端健康
echo "[1/5] 后端健康检查..."
HEALTH=$(curl -sS --max-time 20 "$API_BASE/api/health")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo "  ✅ 后端健康"
else
    echo "  ❌ 后端异常: $HEALTH"
    exit 1
fi
echo ""

# 2. 路由数量
echo "[2/5] 路由数量统计..."
ROUTE_COUNT=$(curl -sS --max-time 20 "$API_BASE/openapi.json" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['paths']))")
echo "  当前路由数：$ROUTE_COUNT"
if [ "$ROUTE_COUNT" -ge 30 ]; then
    echo "  ✅ 路由数量充足（≥30 包含 IAM 新模块）"
else
    echo "  ⚠️  路由数量偏少（<30，可能 IAM 模块未部署）"
fi
echo ""

# 3. IAM 模块
echo "[3/5] Sprint 10 IAM 模块检查..."
AUTH_STATUS=$(curl -sS --max-time 15 -o /tmp/auth.json -w "%{http_code}" "$API_BASE/api/auth/demo-accounts")
if [ "$AUTH_STATUS" = "200" ]; then
    ACCOUNTS=$(python3 -c "import json; d=json.load(open('/tmp/auth.json')); print(len(d['accounts']))")
    echo "  ✅ IAM 已部署，演示账号数：$ACCOUNTS"
else
    echo "  ❌ IAM 未部署（/api/auth/demo-accounts 返回 $AUTH_STATUS）"
    echo "     → 请去 Render 控制台：Manual Deploy → Clear build cache & deploy"
fi
echo ""

# 4. 鉴权保护
echo "[4/5] /api/chat 鉴权保护检查..."
CHAT_STATUS=$(curl -sS --max-time 15 -o /tmp/chat.json -w "%{http_code}" -X POST "$API_BASE/api/chat" \
    -H "Content-Type: application/json" -d '{"query":"test"}')
if [ "$CHAT_STATUS" = "401" ]; then
    echo "  ✅ /api/chat 已加鉴权保护（401 Unauthorized，符合预期）"
elif [ "$CHAT_STATUS" = "200" ]; then
    echo "  ⚠️  /api/chat 仍返回 200（说明鉴权未生效，还是旧代码）"
    echo "     → 后端需要重新部署"
else
    echo "  ❓ /api/chat 返回异常状态码：$CHAT_STATUS"
fi
echo ""

# 5. 前端
echo "[5/5] 前端可达性..."
FRONT_STATUS=$(curl -sS --max-time 20 -o /dev/null -w "%{http_code}" "$FRONT_BASE/login")
if [ "$FRONT_STATUS" = "200" ]; then
    echo "  ✅ 前端可达（/login 返回 200）"
else
    echo "  ❌ 前端异常：$FRONT_STATUS"
fi
echo ""

echo "════════════════════════════════════════════"
echo "📋 验证总结"
echo "════════════════════════════════════════════"
echo "后端：$API_BASE"
echo "前端：$FRONT_BASE"
echo "登录页：$FRONT_BASE/login"
echo ""
echo "🎯 演示账号："
echo "  zhangsan  → 张三（埃安业务，广州）"
echo "  lisi      → 李四（传祺业务，深圳）"
echo "  wangwu    → 王五（数据分析师）"
echo "  admin     → 谢志锋（管理员）"
echo "  auditor   → 赵六（审计员）"
