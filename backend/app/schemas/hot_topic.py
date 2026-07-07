"""
热榜数据 Pydantic schemas

模块名称: hot_topic.py
模块职责: 热榜相关的请求/响应数据模型
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.sentiment import SentimentResultResponse


class HotTopicBase(BaseModel):
    """热榜基础模型"""
    platform_id: int = Field(..., description="平台ID")
    topic_id: str = Field(..., max_length=128, description="平台原始话题ID")
    title: str = Field(..., max_length=512, description="话题标题")
    url: Optional[str] = Field(None, max_length=1024, description="详情链接")
    heat_score: Optional[int] = Field(None, description="热度值")
    category: Optional[str] = Field(None, max_length=64, description="分类标签")
    content_summary: Optional[str] = Field(None, description="正文摘要")
    raw_data: Optional[dict] = Field(None, description="原始数据(JSON)")
    crawl_time: datetime = Field(..., description="采集时间")


class HotTopicCreate(HotTopicBase):
    """创建热榜请求模型"""
    pass


class HotTopicResponse(HotTopicBase):
    """热榜响应模型"""
    id: int
    created_at: datetime
    platform_name: Optional[str] = Field(None, description="平台中文名")
    sentiment: Optional[SentimentResultResponse] = Field(None, description="情感分析结果")
    
    class Config:
        from_attributes = True


class HotTopicListResponse(BaseModel):
    """热榜列表响应模型"""
    items: List[HotTopicResponse]
    pagination: dict


class HotTopicQueryParams(BaseModel):
    """热榜查询参数"""
    platform: Optional[str] = Field(None, description="平台名称")
    keyword: Optional[str] = Field(None, description="标题关键词")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    category: Optional[str] = Field(None, description="分类标签")
    sort_by: str = Field("heat_score", description="排序字段")
    sort_order: str = Field("desc", description="排序: asc/desc")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
