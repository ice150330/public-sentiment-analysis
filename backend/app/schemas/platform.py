"""
平台模型 Pydantic schemas

模块名称: platform.py
模块职责: 平台相关的请求/响应数据模型
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class PlatformBase(BaseModel):
    """平台基础模型"""
    name: str = Field(..., min_length=1, max_length=32, description="英文标识")
    display_name: str = Field(..., min_length=1, max_length=64, description="中文显示名")
    base_url: Optional[str] = Field(None, max_length=255, description="平台首页URL")
    crawl_config: Optional[dict] = Field(None, description="爬虫配置(JSON)")
    is_active: bool = Field(True, description="是否启用采集")
    sort_order: int = Field(0, description="排序权重")


class PlatformCreate(PlatformBase):
    """创建平台请求模型"""
    pass


class PlatformUpdate(BaseModel):
    """更新平台请求模型（全部可选）"""
    display_name: Optional[str] = Field(None, max_length=64)
    base_url: Optional[str] = Field(None, max_length=255)
    crawl_config: Optional[dict] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class PlatformResponse(PlatformBase):
    """平台响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PlatformListResponse(BaseModel):
    """平台列表响应模型"""
    items: List[PlatformResponse]
    total: int
