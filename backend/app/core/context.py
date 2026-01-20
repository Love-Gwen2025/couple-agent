"""
请求上下文中间件

为每个请求自动注入追踪信息（request_id、user_id 等），
使日志具备完整的上下文，便于问题排查和链路追踪。
"""

import uuid
from contextvars import ContextVar
from typing import Any

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# 使用 ContextVar 存储请求上下文，确保异步安全
# 注意：默认值不使用可变对象，通过 get() 时判断处理
request_context: ContextVar[dict[str, Any] | None] = ContextVar("request_context", default=None)


def get_request_id() -> str | None:
    """获取当前请求的 request_id"""
    ctx = request_context.get()
    return ctx.get("request_id") if ctx else None


def get_user_id() -> int | None:
    """获取当前请求的 user_id"""
    ctx = request_context.get()
    return ctx.get("user_id") if ctx else None


def set_user_id(user_id: int) -> None:
    """设置当前请求的 user_id（在认证成功后调用）"""
    ctx = request_context.get()
    if ctx is not None:
        ctx["user_id"] = user_id


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    请求上下文中间件

    功能：
    1. 为每个请求生成唯一的 request_id
    2. 将上下文绑定到 loguru，自动注入到所有日志
    3. 在响应头中返回 request_id，方便前端排查问题
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. 生成 request_id（优先使用客户端传入的，否则自动生成）
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]

        # 2. 设置上下文
        ctx = {
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        }
        request_context.set(ctx)

        # 3. 绑定到 loguru，后续所有日志自动带上这些字段
        with logger.contextualize(request_id=request_id, path=request.url.path):
            # 4. 记录请求开始
            logger.info(f"Request started: {request.method} {request.url.path}")

            # 5. 执行请求
            response = await call_next(request)

            # 6. 在响应头中返回 request_id
            response.headers["X-Request-ID"] = request_id

            # 7. 记录请求完成
            logger.info(f"Request completed: status={response.status_code}")

        return response
