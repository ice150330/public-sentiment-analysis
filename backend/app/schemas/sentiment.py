"""
情感分析 Pydantic schemas

模块名称: sentiment.py
模块职责: 情感分析相关的请求/响应数据模型
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class SentimentAnalyzeRequest(BaseModel):
    """情感分析请求"""
    text: str = Field(..., min_length=1, max_length=4096, description="待分析文本")


class SentimentAnalyzeBatchRequest(BaseModel):
    """批量情感分析请求"""
    texts: List[str] = Field(..., min_length=1, max_length=100, description="文本列表")


class SentimentScores(BaseModel):
    """情感分数"""
    positive: float = Field(..., ge=0, le=1, description="正面分数")
    negative: float = Field(..., ge=0, le=1, description="负面分数")
    neutral: float = Field(..., ge=0, le=1, description="中性分数")


class SentimentResultResponse(BaseModel):
    """情感分析结果响应"""
    id: int
    topic_id: int = Field(..., description="关联热榜ID")
    sentiment_label: str = Field(..., description="positive | negative | neutral")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    positive_score: float = Field(..., ge=0, le=1)
    negative_score: float = Field(..., ge=0, le=1)
    neutral_score: float = Field(..., ge=0, le=1)
    model_version: Optional[str] = Field(None, description="模型版本")
    analyzed_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


class SentimentAnalyzeResponse(BaseModel):
    """单条分析响应"""
    text: str = Field(..., description="原始文本")
    sentiment_label: str = Field(..., description="positive | negative | neutral")
    confidence: float = Field(..., ge=0, le=1)
    scores: SentimentScores
    model_version: Optional[str] = None
    analyzed_at: datetime


class SentimentQueryParams(BaseModel):
    """情感结果查询参数"""
    label: Optional[str] = Field(None, description="筛选: positive/negative/neutral")
    platform: Optional[str] = Field(None, description="平台名称")
    min_confidence: float = Field(0.0, ge=0, le=1, description="最小置信度")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
