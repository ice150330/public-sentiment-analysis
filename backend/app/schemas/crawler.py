"""
爬虫控制 Pydantic schemas

模块名称: crawler.py
模块职责: 爬虫控制相关的请求/响应数据模型
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CrawlerTriggerRequest(BaseModel):
    """手动触发爬虫请求"""
    platforms: Optional[List[str]] = Field(None, description="指定平台，不传则全部")
    is_async: bool = Field(True, description="是否异步执行")


class CrawlerTriggerResponse(BaseModel):
    """手动触发爬虫响应"""
    task_id: str
    status: str = Field(..., description="running | queued")
    platforms: List[str]
    started_at: datetime


class CrawlLogResponse(BaseModel):
    """采集日志响应"""
    id: int
    platform_id: int
    platform_name: Optional[str] = None
    status: str
    records_count: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
