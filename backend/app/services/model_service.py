from collections.abc import AsyncIterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from app.core.settings import Settings
from app.utils.content import extract_text_content


class ModelService:
    """
    模型服务层 - 封装 LLM 调用逻辑

    职责：
    1. 管理 LLM 客户端 (系统默认 DeepSeek，其他通过用户自定义模型支持)
    2. 提供同步/流式对话接口
    3. 封装不同模型的输出格式差异
    4. 支持从用户自定义模型创建实例
    """

    def __init__(self, settings: Settings):
        """
        初始化模型服务

        系统默认使用 DeepSeek，其他提供商通过用户自定义模型支持
        """
        self.model = self._create_model(settings)
        logger.info("ModelService initialized with DeepSeek")

    def _create_model(self, settings: Settings) -> BaseChatModel:
        """
        创建 DeepSeek 模型实例

        系统默认使用 DeepSeek，其他提供商通过用户自定义模型支持

        Returns:
            BaseChatModel: LangChain 兼容的 ChatModel 实例
        """
        logger.info(f"Creating ChatOpenAI (DeepSeek): model={settings.ai_deepseek_model_name}")
        return ChatOpenAI(
            api_key=settings.ai_deepseek_api_key or "",
            base_url=settings.ai_deepseek_base_url,
            model=settings.ai_deepseek_model_name,
            temperature=settings.ai_deepseek_temperature,
            timeout=settings.ai_deepseek_timeout,
        )

    @classmethod
    def from_user_model(
        cls,
        user_model,
    ) -> "ModelService":
        """
        从用户自定义模型配置创建 ModelService 实例

        Args:
            user_model: UserModel 实体（api_key 应已解密）

        Returns:
            ModelService 实例
        """
        from langchain_google_genai import ChatGoogleGenerativeAI

        provider = user_model.provider.lower()
        instance = cls.__new__(cls)

        # 提取高级参数（转换为 float/int，None 值保持不变）
        top_p = float(user_model.top_p) if user_model.top_p is not None else None
        max_tokens = user_model.max_tokens
        top_k = user_model.top_k

        # 根据提供商创建模型
        if provider == "gemini":
            logger.info(f"Creating ChatGoogleGenerativeAI from user_model: {user_model.model_code}")
            # Gemini 支持 top_p 和 top_k，不支持 max_tokens
            kwargs = {
                "model": user_model.model_code,
                "google_api_key": user_model.api_key,
                "temperature": float(user_model.temperature),
            }
            if top_p is not None:
                kwargs["top_p"] = top_p
            if top_k is not None:
                kwargs["top_k"] = top_k
            instance.model = ChatGoogleGenerativeAI(**kwargs)

        elif provider == "openai":
            logger.info(f"Creating ChatOpenAI (OpenAI) from user_model: {user_model.model_code}")
            # OpenAI 支持 top_p 和 max_tokens
            kwargs = {
                "api_key": user_model.api_key,
                "base_url": user_model.base_url or "https://api.openai.com/v1",
                "model": user_model.model_code,
                "temperature": float(user_model.temperature),
                "timeout": user_model.timeout,
            }
            if top_p is not None:
                kwargs["top_p"] = top_p
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            instance.model = ChatOpenAI(**kwargs)

        elif provider == "deepseek":
            logger.info(f"Creating ChatOpenAI (DeepSeek) from user_model: {user_model.model_code}")
            # DeepSeek 支持 top_p 和 max_tokens
            kwargs = {
                "api_key": user_model.api_key,
                "base_url": user_model.base_url or "https://api.deepseek.com",
                "model": user_model.model_code,
                "temperature": float(user_model.temperature),
                "timeout": user_model.timeout,
            }
            if top_p is not None:
                kwargs["top_p"] = top_p
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            instance.model = ChatOpenAI(**kwargs)

        elif provider == "custom":
            if not user_model.base_url:
                raise ValueError("custom 提供商必须配置 base_url")
            logger.info(f"Creating ChatOpenAI (Custom) from user_model: {user_model.model_code}")
            # Custom 只支持基础参数
            instance.model = ChatOpenAI(
                api_key=user_model.api_key,
                base_url=user_model.base_url,
                model=user_model.model_code,
                temperature=float(user_model.temperature),
                timeout=user_model.timeout,
            )
        else:
            raise ValueError(f"不支持的提供商: {provider}")

        return instance

    @classmethod
    def create_default_deepseek(cls, api_key: str) -> "ModelService":
        """
        创建默认的 DeepSeek 模型服务

        系统默认模型，使用 DeepSeek-Chat (V3)，支持工具调用
        """
        instance = cls.__new__(cls)

        logger.info("Creating default DeepSeek Chat ModelService")
        instance.model = ChatOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            temperature=0.7,
            timeout=60,
        )

        return instance

    def get_model(self) -> BaseChatModel:
        """
        获取底层模型实例，供 LangGraph 或其他高级用途使用。

        Returns:
            BaseChatModel 实例
        """
        return self.model

    async def chat(self, content: str) -> str:
        """
        1. 同步式获取完整回复（无上下文）。

        注意: 不同模型返回的 content 格式可能不同:
        - OpenAI/DeepSeek: 字符串
        - Gemini: 列表 [{'type': 'text', 'text': '...', 'index': 0}]
        """
        response = await self.model.ainvoke([HumanMessage(content=content)])
        return self._extract_content(response.content)

    def _extract_content(self, content) -> str:
        """
        从模型响应中提取文本内容

        外部调用保留，内部委托给统一工具函数
        """
        return extract_text_content(content)

    async def chat_with_messages(self, messages: list[BaseMessage]) -> str:
        """
        2. 带上下文的对话，接收完整消息列表。
        """
        response = await self.model.ainvoke(messages)
        return self._extract_content(response.content)

    async def invoke_with_tools(self, messages: list[BaseMessage]) -> AIMessage:
        """
        3. 带工具调用的对话，返回完整 AIMessage（可能包含 tool_calls）。

        当 LLM 决定调用工具时，返回的 AIMessage 会包含 tool_calls 字段，
        调用方需要执行工具并将结果追加到消息历史中继续对话。

        Returns:
            AIMessage: 包含 content 和可能的 tool_calls
        """
        if self.model_with_tools:
            return await self.model_with_tools.ainvoke(messages)
        else:
            # 没有绑定工具时，使用普通模型
            return await self.model.ainvoke(messages)

    async def stream(self, content: str) -> AsyncIterator[str]:
        """
        4. 流式获取回复分片，逐步 yielding token 内容。
        """
        async for chunk in self.model.astream([HumanMessage(content=content)]):
            if chunk and chunk.content:
                yield str(chunk.content)

    async def stream_with_messages(self, messages: list[BaseMessage]) -> AsyncIterator[str]:
        """
        5. 带上下文的流式对话。
        """
        async for chunk in self.model.astream(messages):
            if chunk and chunk.content:
                yield str(chunk.content)

    async def stream_with_tools(self, messages: list[BaseMessage]) -> AsyncIterator[AIMessage]:
        """
        6. 带工具的流式对话。

        注意: 流式模式下 tool_calls 可能分散在多个 chunk 中，
        通常需要在所有 chunk 接收完毕后才能得到完整的 tool_calls。
        建议在需要 tool_calls 时使用 invoke_with_tools 同步调用。

        Yields:
            AIMessage chunks (每个 chunk 可能包含部分 content 或 tool_calls)
        """
        model = self.model_with_tools if self.model_with_tools else self.model
        async for chunk in model.astream(messages):
            yield chunk
