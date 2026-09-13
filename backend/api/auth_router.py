"""
[Sprint 10] 鉴权 API 路由

端点：
  POST /api/auth/login       登录（Mock：username + 任意非空 password）
  GET  /api/auth/me          获取当前用户信息
  POST /api/auth/logout      登出（Mock：前端清 token 即可）
  GET  /api/auth/demo-accounts  演示账号列表（前端登录页展示）
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status

from ..core.auth import (
    create_access_token,
    get_current_user,
    CurrentUser,
)
from ..core.mock_iam import (
    authenticate,
    get_user,
    to_public_dict,
    DEMO_ACCOUNTS_HINT,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================
# Request / Response 模型
# ============================================================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=100, description="密码（演示版任意非空）")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 8 * 3600
    user: dict


class MeResponse(BaseModel):
    user: dict
    role_description: str


# ============================================================
# 端点实现
# ============================================================
@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Mock 登录

    真实 IAM 接入后，本接口会被替换为 OIDC 回调：
      GET /api/auth/oidc/callback?code=xxx&state=xxx
      → 用 code 换 access_token + ID Token
      → 用 ID Token claims 构造 CurrentUser
      → 同样签发本系统 JWT（用于 API 鉴权）

    切换时，前端调用 login 的代码逻辑不变（仍然是 POST /api/auth/login 拿 token）
    """
    user = authenticate(req.username, req.password)
    if not user:
        # 真实环境应该返回模糊错误，避免暴露用户存在性
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token = create_access_token(user)
    logger.info(f"[Auth] 用户登录: {user.username} ({user.role})")

    return LoginResponse(
        access_token=token,
        user=to_public_dict(user),
    )


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser = Depends(get_current_user)):
    """获取当前登录用户信息（前端右上角胶囊用）"""
    from ..core.permission import get_permission

    perm = get_permission(user.role)
    mock_user = get_user(user.username)
    if not mock_user:
        # Token 有效但用户已被 IAM 注销
        raise HTTPException(status_code=401, detail="用户已失效")

    return MeResponse(
        user=to_public_dict(mock_user),
        role_description=perm.description,
    )


@router.post("/logout")
async def logout(user: CurrentUser = Depends(get_current_user)):
    """
    登出（Mock 版：仅前端清 token，后端无状态）
    真实 IAM 接入：增加 /api/auth/oidc/logout 跳转到 IAM 注销端点
    """
    logger.info(f"[Auth] 用户登出: {user.username}")
    return {"message": "已登出", "username": user.username}


@router.get("/demo-accounts")
async def demo_accounts():
    """
    返回演示账号列表（前端登录页直接展示）

    生产环境（真实 IAM 接入后）应该删除本接口
    """
    return {"accounts": DEMO_ACCOUNTS_HINT}
