"""
模型相关数据结构
"""

from pydantic import BaseModel, Field

from app.schema.base import SnowflakeId


class ModelVo(BaseModel):
    """
    1. 对应前端 AiModel 类型，描述可用模型信息。
    """

    id: SnowflakeId = Field(..., description="模型 ID（自动序列化为字符串）")
    modelCode: str = Field(..., description="模型编码")
    modelName: str = Field(..., description="模型名称")
    provider: str = Field(..., description="模型提供商")
    isDefault: bool = Field(default=False, description="是否默认模型")
    status: int = Field(default=1, description="模型状态 0=不可用 1=可用")
