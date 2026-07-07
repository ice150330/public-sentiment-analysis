"""
统计分析 API 路由

模块名称: stats.py
模块职责: 情感分布、热度趋势、数据概览等统计接口
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.core.database import get_db
from app.models import HotTopic, SentimentResult, Platform, CrawlLog
from app.schemas import (
    SentimentDistributionResponse,
    HeatTrendResponse,
    CrawlSuccessRateResponse,
    OverviewResponse,
    UnifiedResponse,
)

router = APIRouter()


@router.get("/sentiment-distribution", response_model=UnifiedResponse[SentimentDistributionResponse])
async def get_sentiment_distribution(
    platform: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    db: Session = Depends(get_db),
):
    """
    获取情感分布统计
    
    返回正面/负面/中性的数量及占比，可按平台筛选
    """
    # 默认查询最近7天
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(days=7)
    
    query = db.query(SentimentResult).join(HotTopic).join(Platform)
    query = query.filter(and_(
        SentimentResult.analyzed_at >= start_time,
        SentimentResult.analyzed_at <= end_time,
    ))
    
    if platform:
        query = query.filter(Platform.name == platform)
    
    # 按标签分组统计
    results = query.with_entities(
        SentimentResult.sentiment_label,
        func.count(SentimentResult.id).label("count"),
    ).group_by(SentimentResult.sentiment_label).all()
    
    total = sum(r.count for r in results)
    
    distribution = []
    for r in results:
        distribution.append({
            "label": r.sentiment_label,
            "count": r.count,
            "percentage": round(r.count * 100 / total, 2) if total > 0 else 0,
        })
    
    # 按平台统计
    by_platform = {}
    if not platform:
        platform_results = db.query(
            Platform.name,
            SentimentResult.sentiment_label,
            func.count(SentimentResult.id).label("count"),
        ).select_from(SentimentResult).join(HotTopic).join(Platform).filter(and_(
            SentimentResult.analyzed_at >= start_time,
            SentimentResult.analyzed_at <= end_time,
        )).group_by(Platform.name, SentimentResult.sentiment_label).all()
        
        for p in platform_results:
            if p.name not in by_platform:
                by_platform[p.name] = {}
            by_platform[p.name][p.sentiment_label] = p.count
    
    return {
        "code": 200,
        "data": {
            "total": total,
            "distribution": distribution,
            "by_platform": by_platform if by_platform else None,
        },
        "message": "success",
    }


@router.get("/heat-trend", response_model=UnifiedResponse[HeatTrendResponse])
async def get_heat_trend(
    days: int = Query(7, ge=1, le=365),
    platform: str = None,
    aggregation: str = Query("daily", description="聚合粒度: hourly/daily/weekly"),
    db: Session = Depends(get_db),
):
    """
    获取热度趋势数据
    
    Args:
        days: 查询天数
        platform: 指定平台，不传则全部
        aggregation: 聚合粒度
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    query = db.query(HotTopic).join(Platform)
    query = query.filter(HotTopic.crawl_time >= start_time)
    
    if platform:
        query = query.filter(Platform.name == platform)
    
    # 按日期聚合
    if aggregation == "daily":
        date_func = func.date(HotTopic.crawl_time)
    elif aggregation == "hourly":
        date_func = func.strftime("%Y-%m-%d %H", HotTopic.crawl_time)
    else:  # weekly
        date_func = func.strftime("%Y-%W", HotTopic.crawl_time)
    
    results = query.with_entities(
        Platform.name.label("platform"),
        date_func.label("date"),
        func.avg(HotTopic.heat_score).label("avg_heat"),
        func.max(HotTopic.heat_score).label("max_heat"),
        func.count(HotTopic.id).label("topic_count"),
    ).group_by("platform", "date").order_by("date").all()
    
    # 按平台分组
    series = {}
    for r in results:
        if r.platform not in series:
            series[r.platform] = []
        series[r.platform].append({
            "date": r.date,
            "avg_heat": round(r.avg_heat, 2) if r.avg_heat else 0,
            "max_heat": r.max_heat,
            "topic_count": r.topic_count,
        })
    
    series_list = [{"platform": k, "data": v} for k, v in series.items()]
    
    return {
        "code": 200,
        "data": {
            "period": f"{start_time.date()} ~ {end_time.date()}",
            "aggregation": aggregation,
            "series": series_list,
        },
        "message": "success",
    }


@router.get("/crawl-success-rate", response_model=UnifiedResponse[CrawlSuccessRateResponse])
async def get_crawl_success_rate(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """获取采集成功率统计"""
    start_time = datetime.now() - timedelta(days=days)
    
    results = db.query(
        CrawlLog.status,
        func.count(CrawlLog.id).label("count"),
    ).filter(CrawlLog.started_at >= start_time).group_by(CrawlLog.status).all()
    
    total = sum(r.count for r in results)
    
    rates = []
    for r in results:
        rates.append({
            "status": r.status,
            "count": r.count,
            "percentage": round(r.count * 100 / total, 2) if total > 0 else 0,
        })
    
    return {
        "code": 200,
        "data": {
            "period": f"最近 {days} 天",
            "total": total,
            "rates": rates,
        },
        "message": "success",
    }


@router.get("/overview", response_model=UnifiedResponse[OverviewResponse])
async def get_overview(
    db: Session = Depends(get_db),
):
    """获取数据概览（Dashboard 用）"""
    today = datetime.now().date()
    
    # 今日热榜数
    today_topics = db.query(HotTopic).filter(
        func.date(HotTopic.crawl_time) == today
    ).count()
    
    # 活跃平台数
    active_platforms = db.query(Platform).filter(Platform.is_active == True).count()
    
    # 今日情感分布
    sentiment_dist = db.query(
        SentimentResult.sentiment_label,
        func.count(SentimentResult.id).label("count"),
    ).join(HotTopic).filter(
        func.date(HotTopic.crawl_time) == today
    ).group_by(SentimentResult.sentiment_label).all()
    
    sentiment_dict = {r.sentiment_label: r.count for r in sentiment_dist}
    
    # 最新采集日志
    last_log = db.query(CrawlLog).order_by(desc(CrawlLog.started_at)).first()
    
    # 采集成功率（今日）
    today_logs = db.query(CrawlLog).filter(
        func.date(CrawlLog.started_at) == today
    ).all()
    
    success_count = sum(1 for log in today_logs if log.status == "success")
    success_rate = round(success_count * 100 / len(today_logs), 2) if today_logs else 0
    
    return {
        "code": 200,
        "data": {
            "today": {
                "total_topics": today_topics,
                "active_platforms": active_platforms,
                "sentiment_distribution": sentiment_dict,
            },
            "crawler": {
                "last_run": last_log.started_at.isoformat() if last_log else None,
                "today_success_rate": success_rate,
            },
            "sentiment": {
                "total_analyzed": db.query(SentimentResult).count(),
            },
        },
        "message": "success",
    }
