"""P2-3 权限矩阵单元测试
验证后端 /api/roles 返回的权限矩阵与前端 lib/roles.ts 完全一致。
"""
import json
import re
import sys
from pathlib import Path

# 1. 读取后端 main.py 中的权限矩阵
MAIN_PY = Path(__file__).parent.parent / "api" / "main.py"
text = MAIN_PY.read_text(encoding="utf-8")

# 提取 permissions 块（用 ast.literal_eval 安全解析）
import ast

m = re.search(r'"permissions"\s*:\s*\{', text)
assert m, "未找到 permissions 块"
start = m.end()
# 大括号配对扫描
depth = 1
i = start
while i < len(text) and depth > 0:
    if text[i] == '{':
        depth += 1
    elif text[i] == '}':
        depth -= 1
    i += 1
permissions_str = "{" + text[start:i-1] + "}"
backend_perms = {}
for line in permissions_str.split("\n"):
    line = line.strip().rstrip(",").strip()
    if not line or not line.startswith('"'):
        continue
    mm = re.match(r'"(/[^"]*)"\s*:\s*\[([^\]]*)\]', line)
    if mm:
        path = mm.group(1)
        if not path:
            continue
        roles_str = mm.group(2)
        roles = re.findall(r'"(\w+)"', roles_str)
        backend_perms[path] = roles

print(f"=== 后端权限矩阵 ===")
for p, rs in backend_perms.items():
    print(f"  {p}: {rs}")

# 2. 读取前端 roles.ts 的权限矩阵
ROLES_TS = Path(__file__).parent.parent.parent / "frontend" / "src" / "lib" / "roles.ts"
roles_text = ROLES_TS.read_text(encoding="utf-8")
# 解析
frontend_perms = {}
m = re.search(r'export const ROLE_PERMISSIONS[^=]+=\s*\{(.+?)\};', roles_text, re.DOTALL)
assert m, "未找到 ROLE_PERMISSIONS"
for line in m.group(1).split("\n"):
    mm = re.match(r"\s*'([^']+)'\s*:\s*\[([^\]]*)\]", line)
    if mm:
        path = "/" if mm.group(1) == "/" else "/" + mm.group(1).lstrip("/")
        # 修首字符
        path_norm = "/" + mm.group(1).lstrip("/")
        roles = re.findall(r"'(\w+)'", mm.group(2))
        frontend_perms[path_norm] = roles

print(f"\n=== 前端权限矩阵 ===")
for p, rs in frontend_perms.items():
    print(f"  {p}: {rs}")

# 3. 一致性校验
print("\n=== 一致性校验 ===")
mismatch = []
for path in sorted(set(backend_perms) | set(frontend_perms)):
    b = set(backend_perms.get(path, []))
    f = set(frontend_perms.get(path, []))
    if b != f:
        mismatch.append((path, b, f))
        print(f"  ❌ {path}: 后端={b}, 前端={f}")
    else:
        print(f"  ✅ {path}: {sorted(b)}")

if mismatch:
    print(f"\n❌ {len(mismatch)} 处不一致")
    sys.exit(1)

# 4. 关键角色必含页面
print("\n=== 关键访问校验 ===")
must = [
    # (角色, 路径, 期望允许?, 描述)
    ("guest",     "/",             True,  "访客可访问首页"),
    ("guest",     "/dashboard",    True,  "访客可看驾驶舱"),
    ("guest",     "/help",         True,  "访客可看帮助"),
    ("guest",     "/semantic",     False, "访客不能看语义层"),
    ("product",   "/semantic",     True,  "产品经理可看语义层"),
    ("analyst",   "/data-manager", True,  "分析师可管理数据"),
    ("executive", "/data-manager", False, "高管不能管数据"),
    ("executive", "/dashboard",    True,  "高管可看驾驶舱"),
    ("guest",     "/reports",      False, "访客不能看报表"),
]
fail = 0
for role, path, expect_allow, desc in must:
    allowed = backend_perms.get(path, [])
    is_allowed = role in allowed
    ok = (is_allowed == expect_allow)
    status = "✅" if ok else "❌"
    print(f"  {status} {desc} (期望 {'允许' if expect_allow else '拒绝'}, 实际 {'允许' if is_allowed else '拒绝'})")
    if not ok:
        fail += 1

if fail:
    print(f"\n❌ {fail} 项关键校验失败")
    sys.exit(1)

print("\n🎉 权限矩阵全量一致 + 关键场景全过\n")
