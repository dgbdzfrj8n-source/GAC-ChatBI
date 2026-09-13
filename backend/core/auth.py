"""
[Sprint 10] JWT 鉴权模块

功能：
  1. JWT 签发（HS256，对称密钥，生产环境建议 RS256 + 公私钥）
  2. JWT 校验（过期/签名/签发者）
  3. FastAPI Depends 装饰器：get_current_user / require_role

依赖：
  pip install python-jose[cryptography] passlib[bcrypt]
  （已有 pydantic v2, fastapi）
"""

import os
import time
import logging
from typing import Optional, List
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

try:
    from jose import jwt, JWTError
    HAS_JOSE = True
except ImportError:
    HAS_JOSE = False
    print("[WARN] python-jose 未安装，请运行: pip install python-jose[cryptography]")

from .mock_iam import MockUser, MOCK_USERS

logger = logging.getLogger(__name__)


# ============================================================
# JWT 配置（生产环境应该从环境变量注入密钥）
# ============================================================
JWT_SECRET = os.environ.get("JWT_SECRET", "gac-chatbi-sprint10-demo-secret-CHANGE-IN-PROD")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8  # 广汽典型工作时间 8 小时


# Bearer Token 提取器（前端用 Authorization: Bearer xxx）
security = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    """FastAPI Depends 注入的当前用户对象"""
    username: str
    name: str
    role: str
    department: str
    region: str
    email: str
    phone: str

    @classmethod
    def from_mock(cls, u: MockUser) -> "CurrentUser":
        return cls(
            username=u.username,
            name=u.name,
            role=u.role,
            department=u.department,
            region=u.region,
            email=u.email,
            phone=u.phone,
        )


# ============================================================
# JWT 签发与校验
# ============================================================
def create_access_token(user: MockUser) -> str:
    """签发 JWT Token"""
    if not HAS_JOSE:
        raise RuntimeError("python-jose 未安装")

    payload = {
        "sub": user.username,        # subject（用户 ID）
        "name": user.name,
        "role": user.role,
        "department": user.department,
        "region": user.region,
        "email": user.email,
        "phone": user.phone,
        "iat": int(time.time()),                          # issued at
        "exp": int(time.time()) + JWT_EXPIRE_HOURS * 3600,  # expire
        "iss": "gac-chatbi-mock-iam",                     # issuer
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[CurrentUser]:
    """校验 JWT 并返回 CurrentUser"""
    if not HAS_JOSE:
        return None

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # 校验 issuer
        if payload.get("iss") != "gac-chatbi-mock-iam":
            logger.warning(f"非本系统签发的 token: iss={payload.get('iss')}")
            return None

        return CurrentUser(
            username=payload["sub"],
            name=payload.get("name", ""),
            role=payload.get("role", "guest"),
            department=payload.get("department", ""),
            region=payload.get("region", "ALL"),
            email=payload.get("email", ""),
            phone=payload.get("phone", ""),
        )
    except JWTError as e:
        logger.warning(f"JWT 校验失败: {e}")
        return None


# ============================================================
# FastAPI Depends 装饰器
# ============================================================
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """
    FastAPI 依赖注入：从 Authorization Header 解析用户

    使用方式：
      @app.get("/api/xxx")
      async def xxx(user: CurrentUser = Depends(get_current_user)):
          ...
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Authorization 头",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = decode_access_token(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[CurrentUser]:
    """可选鉴权：未登录也能访问（用于公开页面）"""
    if not credentials or not credentials.credentials:
        return None
    return decode_access_token(credentials.credentials)


def require_role(*allowed_roles: str):
    """
    角色权限装饰器工厂

    使用方式：
      @app.get("/api/admin/xxx")
      async def xxx(user: CurrentUser = Depends(require_role("admin"))):
          ...

      @app.delete("/api/yyy")
      async def yyy(user: CurrentUser = Depends(require_role("admin", "analyst"))):
          ...
    """
    async def role_checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要角色 {allowed_roles}，当前角色 {user.role}",
            )
        return user

    return role_checker
