"""
Langfuse 可观测性服务

提供 LLM 调用追踪、成本分析和质量评估功能。
"""

from langfuse.langchain import CallbackHandler
from loguru import logger

from app.core.settings import Settings


class LangfuseService:
    """
    Langfuse 服务封装

    职责：
    1. 管理 Langfuse CallbackHandler
    2. 创建 Trace 和 Span
    3. 上报评估分数
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.enabled = settings.langfuse_enabled
        self._handler: CallbackHandler | None = None

        if self.enabled:
            if not settings.langfuse_public_key or not settings.langfuse_secret_key:
                logger.warning("⚠️ Langfuse enabled but missing keys, disabling...")
                self.enabled = False
            else:
                logger.info(f"✅ Langfuse enabled, host: {settings.langfuse_host}")

    def get_callback_handler(
        self,
        user_id: str | None = None,
        session_id: str | None = None,
        trace_name: str = "chat",
        metadata: dict | None = None,
    ) -> CallbackHandler | None:
        """
        获取 Langfuse CallbackHandler，用于 LangChain/LangGraph 集成

        Args:
            user_id: 用户 ID（用于用户级别追踪）
            session_id: 会话 ID（用于会话级别追踪）
            trace_name: Trace 名称
            metadata: 额外的元数据

        Returns:
            CallbackHandler 实例，如果未启用则返回 None
        """
        if not self.enabled:
            return None

        try:
            import os

            # Langfuse 3.x 通过环境变量配置
            os.environ["LANGFUSE_PUBLIC_KEY"] = self.settings.langfuse_public_key or ""
            os.environ["LANGFUSE_SECRET_KEY"] = self.settings.langfuse_secret_key or ""
            os.environ["LANGFUSE_HOST"] = self.settings.langfuse_host

            # Langfuse 3.x CallbackHandler 不接受显式参数，使用环境变量
            handler = CallbackHandler()
            return handler
        except Exception as e:
            logger.error(f"Failed to create Langfuse handler: {e}")
            return None

    def score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> bool:
        """
        上报评估分数

        Args:
            trace_id: Trace ID
            name: 评估维度名称（如 accuracy, relevance）
            value: 分数值（0-1）
            comment: 评论

        Returns:
            是否成功
        """
        if not self.enabled:
            return False

        try:
            from langfuse import Langfuse

            langfuse = Langfuse(
                public_key=self.settings.langfuse_public_key,
                secret_key=self.settings.langfuse_secret_key,
                host=self.settings.langfuse_host,
            )
            langfuse.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
            )
            logger.info(f"📊 Score uploaded: {name}={value} for trace {trace_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload score: {e}")
            return False


# 单例工厂
_langfuse_service: LangfuseService | None = None


def get_langfuse_service(settings: Settings | None = None) -> LangfuseService:
    """获取 Langfuse 服务单例"""
    global _langfuse_service
    if _langfuse_service is None:
        if settings is None:
            from app.core.settings import get_settings

            settings = get_settings()
        _langfuse_service = LangfuseService(settings)
    return _langfuse_service
