"""
用户自定义模型配置实体
"""

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserModel(Base):
    """
    用户自定义 AI 模型配置实体

    对应 t_user_model 表，存储用户添加的自定义模型配置。
    API Key 使用 Fernet 加密存储。
    """

    __tablename__ = "t_user_model"

    # 所属用户 ID
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # 模型显示名称（如 "我的 GPT-4"）
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # 提供商: openai / deepseek / gemini / custom
    provider: Mapped[str] = mapped_column(String(50), nullable=False)

    # 模型编码（如 gpt-4, deepseek-chat）
    model_code: Mapped[str] = mapped_column(String(100), nullable=False)

    # API Key（加密存储）
    api_key: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Base URL（可选，custom 提供商必填）
    base_url: Mapped[str | None] = mapped_column(String(500))

    # 温度参数 0-2
    temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.70"))

    # 超时时间（秒）
    timeout: Mapped[int] = mapped_column(Integer, default=30)

    # Top P 核采样参数 (0-1)，与 temperature 二选一调整
    top_p: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), default=None)

    # 最大输出 token 数 (OpenAI/DeepSeek 支持)
    max_tokens: Mapped[int | None] = mapped_column(Integer, default=None)

    # Top K 参数 (Gemini 专用)
    top_k: Mapped[int | None] = mapped_column(Integer, default=None)

    # 是否为该用户的默认模型
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # 状态: 0=禁用 1=启用
    status: Mapped[int] = mapped_column(Integer, default=1)

    def to_vo(self) -> dict:
        """
        转为接口返回视图

        注意：不返回 api_key 字段
        """
        return {
            "id": str(self.id),
            "modelName": self.model_name,
            "provider": self.provider,
            "modelCode": self.model_code,
            "baseUrl": self.base_url,
            "temperature": float(self.temperature),
            "timeout": self.timeout,
            "topP": float(self.top_p) if self.top_p is not None else None,
            "maxTokens": self.max_tokens,
            "topK": self.top_k,
            "isDefault": self.is_default,
            "status": self.status,
        }

    @property
    def id_str(self) -> str:
        """返回字符串形式的主键"""
        return str(self.id)
