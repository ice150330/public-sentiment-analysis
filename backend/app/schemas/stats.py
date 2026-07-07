"""
统计分析 Pydantic schemas

模块名称: stats.py
模块职责: 统计相关的响应数据模型
"""

from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel, Field


class SentimentDistributionItem(BaseModel):
    """情感分布单项"""
    label: str = Field(..., description="positive | negative | neutral")
    count: int
    percentage: float


class SentimentDistributionResponse(BaseModel):
    """情感分布统计响应"""
    total: int
    distribution: List[SentimentDistributionItem]
    by_platform: Optional[Dict[str, Dict[str, int]]] = Field(None, description="各平台分布")


class HeatTrendItem(BaseModel):
    """热度趋势单项"""
    date: str = Field(..., description="日期")
    avg_heat: float
    max_heat: int
    topic_count: int


class HeatTrendPlatform(BaseModel):
    """平台热度趋势"""
    platform: str
    data: List[HeatTrendItem]


class HeatTrendResponse(BaseModel):
    """热度趋势响应"""
    period: str = Field(..., description="时间范围")
    aggregation: str = Field(..., description="聚合粒度")
    series: List[HeatTrendPlatform]


class CrawlSuccessRateItem(BaseModel):
    """采集成功率单项"""
    status: str
    count: int
    percentage: float


class CrawlSuccessRateResponse(BaseModel):
    """采集成功率响应"""
    period: str
    total: int
    rates: List[CrawlSuccessRateItem]


class CrawlerStatus(BaseModel):
    """爬虫状态"""
    is_running: bool
    current_task: Optional[dict] = None
    queue_length: int = 0


class CrawlerScheduleConfig(BaseModel):
    """爬虫定时配置"""
    interval_minutes: int = Field(60, ge=5, le=1440, description="采集间隔（分钟）")
    is_enabled: bool = True


class OverviewResponse(BaseModel):
    """数据概览响应"""
    today: dict = Field(..., description="今日数据")
    crawler: dict = Field(..., description="爬虫状态")
    sentiment: dict = Field(..., description="情感统计")
