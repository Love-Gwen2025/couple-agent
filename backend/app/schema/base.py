from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class ApiResult(GenericModel, Generic[T]):
    """
    1. 统一的返回包装，保持与 Java 版 Result 结构一致，方便前端无感替换。
    """

    success: bool = Field(default=True, description="是否成功")
    code: str = Field(default="0", description="业务码，0 表示成功")
    message: str = Field(default="OK", description="提示信息")
    data: T | None = Field(default=None, description="返回数据")

    @classmethod
    def ok(cls, data: T | None = None, message: str = "OK") -> "ApiResult[T]":
        """
        1. 构造成功结果。
        """
        return cls(success=True, code="0", message=message, data=data)

    @classmethod
    def fail(cls, message: str, code: str = "FAIL") -> "ApiResult[T]":
        """
        构造失败结果（简化版）。
        """
        return cls(success=False, code=code, message=message, data=None)

    @classmethod
    def error(cls, code: str, message: str, data: T | None = None) -> "ApiResult[T]":
        """
        1. 构造失败结果。
        """
        return cls(success=False, code=code, message=message, data=data)


# ========== 分页相关 ==========


class PageParams(BaseModel):
    """
    分页查询参数。

    用于 GET 请求的分页参数，支持页码和每页大小。
    """

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    size: int = Field(default=10, ge=1, le=100, description="每页大小，最大 100")

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size


class PageResponse(BaseModel, Generic[T]):
    """
    分页响应。

    包含分页数据和分页元信息。
    """

    records: list = Field(default=[], description="当前页记录列表")
    total: int = Field(default=0, description="总记录数")
    size: int = Field(default=10, description="每页大小")
    current: int = Field(default=1, description="当前页码")
    pages: int = Field(default=0, description="总页数")

    @classmethod
    def of(
        cls,
        records: list,
        total: int,
        page: int,
        size: int,
    ) -> "PageResponse":
        """
        构造分页响应。

        Args:
            records: 当前页记录
            total: 总记录数
            page: 当前页码
            size: 每页大小

        Returns:
            分页响应对象
        """
        pages = (total + size - 1) // size if size > 0 else 0
        return cls(
            records=records,
            total=total,
            size=size,
            current=page,
            pages=pages,
        )
