"""
用户模型相关数据结构
"""

from pydantic import BaseModel, Field


class UserModelPayload(BaseModel):
    """
    添加用户模型请求体
    """

    modelName: str = Field(..., max_length=100, description="模型显示名称")
    provider: str = Field(..., description="提供商: openai/deepseek/gemini/custom")
    modelCode: str = Field(..., max_length=100, description="模型编码")
    apiKey: str = Field(..., min_length=1, description="API Key")
    baseUrl: str | None = Field(default=None, description="Base URL（custom 必填）")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    timeout: int = Field(default=30, ge=1, le=300, description="超时(秒)")
    # 高级参数
    topP: float | None = Field(default=None, ge=0, le=1, description="Top P 核采样参数")
    maxTokens: int | None = Field(default=None, ge=1, le=128000, description="最大输出 token 数")
    topK: int | None = Field(default=None, ge=1, le=100, description="Top K 参数 (Gemini)")


class UserModelUpdatePayload(BaseModel):
    """
    更新用户模型请求体（apiKey 可选）
    """

    modelName: str | None = Field(default=None, max_length=100, description="模型显示名称")
    provider: str | None = Field(default=None, description="提供商")
    modelCode: str | None = Field(default=None, max_length=100, description="模型编码")
    apiKey: str | None = Field(default=None, min_length=1, description="API Key（不传则不更新）")
    baseUrl: str | None = Field(default=None, description="Base URL")
    temperature: float | None = Field(default=None, ge=0, le=2, description="温度参数")
    timeout: int | None = Field(default=None, ge=1, le=300, description="超时(秒)")
    # 高级参数
    topP: float | None = Field(default=None, ge=0, le=1, description="Top P 核采样参数")
    maxTokens: int | None = Field(default=None, ge=1, le=128000, description="最大输出 token 数")
    topK: int | None = Field(default=None, ge=1, le=100, description="Top K 参数 (Gemini)")


class UserModelVo(BaseModel):
    """
    用户模型返回视图

    注意：不返回 apiKey 字段保护敏感信息
    """

    id: str = Field(..., description="模型 ID")
    modelName: str = Field(..., description="模型显示名称")
    provider: str = Field(..., description="提供商")
    modelCode: str = Field(..., description="模型编码")
    baseUrl: str | None = Field(default=None, description="Base URL")
    temperature: float = Field(default=0.7, description="温度参数")
    timeout: int = Field(default=30, description="超时(秒)")
    topP: float | None = Field(default=None, description="Top P 核采样参数")
    maxTokens: int | None = Field(default=None, description="最大输出 token 数")
    topK: int | None = Field(default=None, description="Top K 参数")
    isDefault: bool = Field(default=False, description="是否为默认模型")
    status: int = Field(default=1, description="状态")


class UserModelTestPayload(BaseModel):
    """
    测试模型连接请求体
    """

    provider: str = Field(..., description="提供商: openai/deepseek/gemini/custom")
    modelCode: str = Field(..., description="模型编码")
    apiKey: str = Field(..., min_length=1, description="API Key")
    baseUrl: str | None = Field(default=None, description="Base URL")
