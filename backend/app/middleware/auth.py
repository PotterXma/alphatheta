"""
JWT 认证中间件 (Permissive 模式)

行为:
- 从 Authorization: Bearer <token> 头提取 JWT
- 有效令牌 → 注入 request.state.user_id (UUID)
- 无令牌   → request.state.user_id = None (放行, 路由自行决定是否需要认证)
- 无效/过期令牌 → 401 Unauthorized (防止伪造)

认证执行点:
  中间件只负责 "解析 + 注入", 不负责 "强制"
  强制认证在路由层通过 Depends(get_current_user) 完成
  这样未接入 auth 的旧路由不会被阻断
"""

import logging
import uuid

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.services.auth import decode_token

logger = logging.getLogger("alphatheta.auth")


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 认证中间件 — 解析令牌, 注入 user_id, 不强制"""

    async def dispatch(self, request: Request, call_next):
        # 默认: 未认证
        request.state.user_id = None
        request.state.account_type = "paper"

        # 提取 Bearer token
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                if payload.get("type") == "access":
                    request.state.user_id = uuid.UUID(payload["sub"])
                    request.state.account_type = payload.get("acct", "paper")
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token expired"},
                )
            except jwt.InvalidTokenError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token"},
                )

        return await call_next(request)
