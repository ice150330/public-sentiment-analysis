"""
通用响应模型 Pydantic schemas

模块名称: common.py
模块职责: 分页、统一响应等通用模型
"""

from typing import TypeVar, Generic, List, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")


class Pagination(BaseModel):
    """分页信息"""
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应包装"""
    items: List[T]
    pagination: Pagination


class UnifiedResponse(BaseModel, Generic[T]):
    """统一响应包装"""
    code: int = 200
    data: Optional[T] = None
    message: str = "success"
    request_id: Optional[str] = None


class ErrorResponse(BaseModel):
    """错误响应模型"""
    code: int
    data: Optional[Any] = None
    message: str
    error_type: Optional[str] = None
