from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.checkpointer import close_checkpointer_pool, init_checkpointer_pool
from app.core.context import RequestContextMiddleware
from app.core.database_init import init_database
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.settings import get_settings
from app.schema.base import ApiResult
from app.services.embedding_service import EmbeddingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()

    # 🆕 自动执行数据库迁移（使用 IF NOT EXISTS，可重复执行）
    await init_database(settings)

    # 启动时初始化 checkpointer 连接池
    await init_checkpointer_pool(settings)
    logger.info("Checkpointer pool initialized")

    # 预加载 embedding 模型
    if settings.ai_embedding_provider == "local":
        embedding_service = EmbeddingService(settings)
        embedding_service.warmup()
        logger.info("Embedding model warmed up")

    yield

    # 关闭时清理连接池
    await close_checkpointer_pool()
    logger.info("Checkpointer pool closed")


def create_app() -> FastAPI:
    """
    1. 构建 FastAPI 应用，挂载路由与基础中间件。
    2. 保持与 Java 版相同的接口前缀，以便前端无缝切换。
    """
    settings = get_settings()

    # 初始化日志
    log_format = "json" if settings.app_env == "prod" else "console"
    setup_logging(level=settings.app_log_level, format_type=log_format)

    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 请求上下文中间件（自动注入 request_id 到日志）
    app.add_middleware(RequestContextMiddleware)

    # 注册全局异常处理器
    register_exception_handlers(app)

    # 挂载路由
    app.include_router(api_router)

    # 根级别健康检查端点（供 Docker/K8s/监控服务使用）
    @app.get("/health")
    async def health_check():
        """根级别健康检查端点"""
        return {"status": "ok"}

    logger.info(f"Application {settings.app_name} started in {settings.app_env} mode")

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册全局异常处理器，统一返回 ApiResult 格式。
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理自定义业务异常"""
        logger.warning(f"AppException: {exc.code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResult.error(exc.code, exc.message, exc.data).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """处理 HTTP 异常"""
        # 日志包含请求路径，方便排查 404 等问题
        logger.warning(
            f"HTTPException: {exc.status_code} - {exc.detail} | Path: {request.url.path}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiResult.error(str(exc.status_code), str(exc.detail)).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """处理请求参数校验异常"""
        errors = exc.errors()
        message = "; ".join([f"{e['loc']}: {e['msg']}" for e in errors])
        logger.warning(f"ValidationError: {message}")
        return JSONResponse(
            status_code=422,
            content=ApiResult.error("VALIDATION_ERROR", message).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content=ApiResult.error("INTERNAL_ERROR", "服务器内部错误").model_dump(),
        )


app = create_app()
