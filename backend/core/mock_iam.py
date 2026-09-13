"""
[Sprint 10] Mock IAM 模块 - 演示版广汽 IAM 接入

设计原则：
  1. 演示用，预置 4 个测试账号覆盖 4 种角色
  2. 接口与未来真实 OIDC IAM 保持一致（/api/auth/login 返回同结构 user）
  3. 切换到真实 IAM 时，只需替换本文件的 USERS 为 OIDC 回调逻辑，其他代码零改动

未来真实接入步骤：
  1. 在广汽 IAM 管理后台申请 OIDC Client
  2. 拿到 client_id / client_secret / redirect_uri
  3. 安装 authlib: pip install authlib httpx
  4. 把本文件 USERS 替换为 OIDC 回调处理（authlib.integrations.starlette_client.OAuth）
  5. 其他模块（auth.py / permission.py）零改动
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class MockUser:
    """用户信息 - 与未来 OIDC ID Token claims 对齐"""
    username: str
    name: str         # 显示名
    role: str         # 角色 ID（对应 roles.py 中的 ROLE_HIERARCHY key）
    department: str   # 所属部门（广汽典型：埃安/传祺/昊铂/集团）
    region: str       # 所属区域（用于行级数据隔离）
    email: str
    phone: str        # 【敏感字段】演示脱敏用


# ============================================================
# Mock IAM 用户库（演示用）
# ============================================================
MOCK_USERS: Dict[str, MockUser] = {
    # 业务用户 - 一线销售/营销（行级隔离最严）
    "zhangsan": MockUser(
        username="zhangsan",
        name="张三",
        role="business_user",
        department="埃安",
        region="广州",
        email="zhangsan@gac.com.cn",
        phone="13812345678",
    ),
    "lisi": MockUser(
        username="lisi",
        name="李四",
        role="business_user",
        department="传祺",
        region="深圳",
        email="lisi@gac.com.cn",
        phone="13987654321",
    ),

    # 数据分析师 - 全局只读，能看 SQL
    "wangwu": MockUser(
        username="wangwu",
        name="王五",
        role="analyst",
        department="集团",
        region="ALL",  # 区域不限
        email="wangwu@gac.com.cn",
        phone="13511112222",
    ),

    # 管理员 - 全部权限
    "admin": MockUser(
        username="admin",
        name="谢志锋",
        role="admin",
        department="集团",
        region="ALL",
        email="admin@gac.com.cn",
        phone="18888888888",
    ),

    # 审计员 - 只读 + 审计日志
    "auditor": MockUser(
        username="auditor",
        name="审计员-赵六",
        role="auditor",
        department="集团",
        region="ALL",
        email="auditor@gac.com.cn",
        phone="13700001111",
    ),
}


# ============================================================
# 演示账号提示文案（前端登录页展示）
# ============================================================
DEMO_ACCOUNTS_HINT = [
    {"username": "admin",    "name": "谢志锋", "role_label": "管理员", "scope": "全部权限（推荐演示首选）"},
    {"username": "zhangsan", "name": "张三", "role_label": "业务用户", "scope": "仅看埃安 + 广州区域"},
    {"username": "lisi",     "name": "李四", "role_label": "业务用户", "scope": "仅看传祺 + 深圳区域"},
    {"username": "wangwu",   "name": "王五", "role_label": "数据分析师", "scope": "全集团只读"},
    {"username": "auditor",  "name": "赵六", "role_label": "审计员", "scope": "只读 + 审计日志"},
]


def authenticate(username: str, password: str) -> Optional[MockUser]:
    """
    Mock 鉴权：演示用，任意非空密码都通过（生产环境替换为 IAM OIDC 回调）
    未来真实接入：删除本函数，改用 OIDC Authorization Code Flow
    """
    if not username or not password:
        return None
    return MOCK_USERS.get(username)


def get_user(username: str) -> Optional[MockUser]:
    return MOCK_USERS.get(username)


def to_public_dict(user: MockUser) -> Dict[str, Any]:
    """返回给前端的用户信息（自动脱敏手机号/邮箱）"""
    d = asdict(user)
    # 字段级脱敏：手机号 138****5678
    if d.get("phone") and len(d["phone"]) == 11:
        d["phone_masked"] = d["phone"][:3] + "****" + d["phone"][-4:]
    else:
        d["phone_masked"] = ""
    # 邮箱脱敏：z****@gac.com.cn
    if d.get("email") and "@" in d["email"]:
        local, domain = d["email"].split("@", 1)
        d["email_masked"] = (local[0] + "****@" + domain) if len(local) > 1 else "****@" + domain
    else:
        d["email_masked"] = ""
    return d
