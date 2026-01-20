"""
Loguru 日志配置模块。
开发环境使用彩色控制台输出，生产环境支持 JSON 格式。
"""

import sys
from typing import Literal

from loguru import logger


def setup_logging(
    level: str = "INFO",
    format_type: Literal["console", "json"] = "console",
) -> None:
    """
    配置应用日志。

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: 输出格式 (console: 彩色控制台, json: JSON 格式)
    """
    # 移除默认 handler
    logger.remove()

    if format_type == "json":
        # 生产环境 JSON 格式
        logger.add(
            sys.stdout,
            level=level.upper(),
            format="{message}",
            serialize=True,  # 自动输出 JSON 格式
        )
    else:
        # 开发环境彩色输出（包含请求上下文）
        logger.add(
            sys.stdout,
            level=level.upper(),
            format=(
                "<dim>{time:YYYY-MM-DD HH:mm:ss}</dim> | "
                "<level>{level: <8}</level> | "
                "<magenta>[{extra[request_id]:<8}]</magenta> "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            colorize=True,
            # 为没有 request_id 的日志提供默认值
            filter=lambda record: record["extra"].setdefault("request_id", "--------") or True,
        )

    # 过滤第三方库的日志（通过添加 filter）
    # Loguru 会自动继承 Python 标准库的日志配置
    import logging

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str = __name__):
    """
    获取指定名称的 logger 实例。

    Args:
        name: logger 名称，通常使用 __name__

    Returns:
        绑定了模块名称的 logger 实例
    """
    return logger.bind(name=name)
