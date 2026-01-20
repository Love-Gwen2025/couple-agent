"""
应用配置 - 按功能域分组

使用嵌套 Pydantic 模型组织配置，提高可读性和类型安全。
"""

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file() -> str:
    """
    根据 APP_ENV 环境变量动态决定加载哪个 .env 文件。
    """
    root_dir = Path(__file__).resolve().parents[3]
    app_env = os.getenv("APP_ENV", "dev").lower()

    if app_env == "dev":
        env_file = root_dir / ".env"
    else:
        env_file = root_dir / f".env.{app_env}"
        if not env_file.exists():
            sys.stderr.write(f"⚠️ 配置文件 {env_file} 不存在，回退使用 .env\n")
            env_file = root_dir / ".env"

    sys.stderr.write(f"📋 加载配置文件: {env_file}\n")
    return str(env_file)


# ==================== 配置分组 ====================


class Settings(BaseSettings):
    """
    应用配置 - 扁平结构，按功能域分组注释

    由于 pydantic-settings 从环境变量加载配置，使用嵌套会导致
    环境变量名需要加前缀（如 DB__HOST），不符合常规习惯。
    因此保持扁平结构，用注释分组提高可读性。
    """

    # ==================== 应用基础 ====================
    app_env: str = Field(default="dev", description="环境标识")
    app_name: str = Field(default="my-agent-py", description="应用名称")
    app_host: str = Field(default="0.0.0.0", description="监听地址")
    app_port: int = Field(default=8080, description="监听端口")
    app_log_level: str = Field(default="info", description="日志级别")

    # ==================== PostgreSQL 数据库 ====================
    db_host: str = Field(default="localhost", description="主机地址")
    db_port: int = Field(default=5432, description="端口")
    db_name: str = Field(default="my_agent", description="数据库名")
    db_user: str = Field(default="postgres", description="用户名")
    db_password: str = Field(default="123456", description="密码")
    db_pool_size: int = Field(default=5, description="连接池大小")
    db_max_overflow: int = Field(default=5, description="超出池后最大连接数")

    # ==================== Redis 缓存 ====================
    redis_host: str = Field(default="localhost", description="主机地址")
    redis_port: int = Field(default=6379, description="端口")
    redis_password: str | None = Field(default="123456", description="密码")
    redis_db: int = Field(default=3, description="库序号")

    # ==================== JWT 认证 ====================
    jwt_secret: str = Field(default="my-agent", description="密钥")
    jwt_expire_minutes: int = Field(default=60, description="过期分钟数")
    jwt_issuer: str = Field(default="my-agent", description="颁发者")

    # ==================== DeepSeek 配置（系统默认模型） ====================
    # 其他提供商通过用户自定义模型功能配置
    ai_deepseek_api_key: str | None = Field(default=None, description="API Key")
    ai_deepseek_base_url: str = Field(default="https://api.deepseek.com", description="基础地址")
    ai_deepseek_model_name: str = Field(default="deepseek-chat", description="模型名称")
    ai_deepseek_temperature: float = Field(default=0.7, description="温度")
    ai_deepseek_timeout: int = Field(default=30, description="超时(秒)")

    # ==================== Embedding 向量化 ====================
    ai_embedding_provider: str = Field(default="local", description="提供商: local/openai/deepseek")
    ai_embedding_model: str = Field(default="BAAI/bge-small-zh-v1.5", description="模型名称")
    ai_embedding_dimension: int = Field(default=512, description="向量维度")
    ai_embedding_api_key: str | None = Field(default=None, description="API Key(远程)")
    ai_embedding_base_url: str | None = Field(default=None, description="Base URL")

    # ==================== 对话上下文 ====================
    conversation_cache_ttl: int = Field(default=3600, description="缓存 TTL(秒)")
    conversation_cache_max_messages: int = Field(default=20, description="缓存最大消息数")
    max_history_messages: int = Field(default=20, description="发送 LLM 的最大历史数")
    max_history_tokens: int = Field(default=4000, description="历史最大 Token 估算")

    # ==================== RAG 检索 ====================
    rag_top_k: int = Field(default=5, description="检索返回数量")
    rag_similarity_threshold: float = Field(default=0.6, description="相似度阈值")

    # ==================== Tavily 搜索 ====================
    tavily_api_key: str | None = Field(default=None, description="API Key")

    # ==================== DeepSearch 深度搜索 ====================
    deep_search_max_rounds: int = Field(default=5, description="最大规划轮次")
    deep_search_model: str | None = Field(
        default=None, description="推理模型名称（留空则使用当前 provider 的模型）"
    )

    # ==================== OSS 对象存储 ====================
    oss_access_key_id: str | None = Field(default=None, description="AccessKey ID")
    oss_access_key_secret: str | None = Field(default=None, description="AccessKey Secret")
    oss_bucket: str | None = Field(default=None, description="存储桶名称")
    oss_region: str = Field(default="us-west-1", description="地域")
    oss_endpoint: str | None = Field(default=None, description="访问域名")
    oss_custom_domain: str | None = Field(default=None, description="自定义域名")
    oss_object_prefix: str | None = Field(default=None, description="对象前缀")

    # ==================== Langfuse 可观测性 ====================
    langfuse_enabled: bool = Field(default=True, description="启用 Langfuse 追踪")
    langfuse_public_key: str | None = Field(default=None, description="Langfuse Public Key")
    langfuse_secret_key: str | None = Field(default=None, description="Langfuse Secret Key")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse 服务地址"
    )

    # ==================== Celery 消息队列 ====================
    celery_broker_db: int = Field(default=1, description="Celery Broker Redis DB")
    celery_result_db: int = Field(default=2, description="Celery Result Redis DB")

    model_config = SettingsConfigDict(
        env_file=get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==================== 便捷属性 ====================

    @property
    def database_url(self) -> str:
        """生成 PostgreSQL 连接 URL"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        """生成 Redis 连接 URL"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker_url(self) -> str:
        """Celery Broker URL (使用单独的 Redis DB)"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.celery_broker_db}"

    @property
    def celery_result_url(self) -> str:
        """Celery Result Backend URL (使用单独的 Redis DB)"""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.celery_result_db}"


@lru_cache
def get_settings() -> Settings:
    """单例模式获取配置实例"""
    return Settings()
