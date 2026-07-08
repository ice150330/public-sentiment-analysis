"""
统计分析 API 路由

模块名称: stats.py
模块职责: 情感分布、热度趋势、数据概览、平台分布、日环比等统计接口
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.core.database import get_db
from app.models import HotTopic, SentimentResult, Platform, CrawlLog, SystemConfig
from app.schemas import (
    SentimentDistributionResponse,
    HeatTrendResponse,
    CrawlSuccessRateResponse,
    OverviewResponse,
    UnifiedResponse,
)

router = APIRouter()


@router.get("/overview", response_model=UnifiedResponse[OverviewResponse])
async def get_overview(
    db: Session = Depends(get_db),
):
    """
    获取数据概览（Dashboard 用）
    
    扩展：补充负面占比、昨日对比、下次采集时间
    """
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # 今日热榜数
    today_topics = db.query(HotTopic).filter(
        func.date(HotTopic.crawl_time) == today
    ).count()
    
    # 昨日热榜数（用于对比）
    yesterday_topics = db.query(HotTopic).filter(
        func.date(HotTopic.crawl_time) == yesterday
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
    total_analyzed_today = sum(sentiment_dict.values())
    negative_count = sentiment_dict.get("negative", 0)
    negative_ratio = round(negative_count * 100 / total_analyzed_today, 2) if total_analyzed_today > 0 else 0
    
    # 昨日情感分布（用于对比）
    yesterday_sentiment = db.query(
        SentimentResult.sentiment_label,
        func.count(SentimentResult.id).label("count"),
    ).join(HotTopic).filter(
        func.date(HotTopic.crawl_time) == yesterday
    ).group_by(SentimentResult.sentiment_label).all()
    
    yesterday_sentiment_dict = {r.sentiment_label: r.count for r in yesterday_sentiment}
    yesterday_negative = yesterday_sentiment_dict.get("negative", 0)
    yesterday_total = sum(yesterday_sentiment_dict.values())
    yesterday_negative_ratio = round(yesterday_negative * 100 / yesterday_total, 2) if yesterday_total > 0 else 0
    
    # 最新采集日志
    last_log = db.query(CrawlLog).order_by(desc(CrawlLog.started_at)).first()
    
    # 采集成功率（今日）
    today_logs = db.query(CrawlLog).filter(
        func.date(CrawlLog.started_at) == today
    ).all()
    
    success_count = sum(1 for log in today_logs if log.status == "success")
    success_rate = round(success_count * 100 / len(today_logs), 2) if today_logs else 0
    
    # 下次采集时间
    next_crawl = None
    schedule = db.query(SystemConfig).filter(SystemConfig.config_key == "crawler_interval_minutes").first()
    if schedule and last_log and last_log.completed_at:
        interval = int(schedule.config_value)
        next_crawl_time = last_log.completed_at + timedelta(minutes=interval)
        next_crawl = next_crawl_time.isoformat()
    
    # 平台分布（今日）
    platform_dist = db.query(
        Platform.name,
        Platform.display_name,
        func.count(HotTopic.id).label("count"),
    ).join(HotTopic).filter(
        func.date(HotTopic.crawl_time) == today
    ).group_by(Platform.id).all()
    
    platform_distribution = [
        {"name": p.name, "display_name": p.display_name, "count": p.count}
        for p in platform_dist
    ]
    
    return {
        "code": 200,
        "data": {
            "today": {
                "total_topics": today_topics,
                "active_platforms": active_platforms,
                "sentiment_distribution": sentiment_dict,
                "negative_ratio": negative_ratio,
            },
            "yesterday": {
                "total_topics": yesterday_topics,
                "negative_ratio": yesterday_negative_ratio,
            },
            "crawler": {
                "last_run": last_log.started_at.isoformat() if last_log else None,
                "today_success_rate": success_rate,
                "next_crawl": next_crawl,
            },
            "sentiment": {
                "total_analyzed": db.query(SentimentResult).count(),
                "total_analyzed_today": total_analyzed_today,
            },
            "platform_distribution": platform_distribution,
        },
        "message": "success",
    }


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
    group_by: str = Query("status", description="分组维度: status/platform"),
    db: Session = Depends(get_db),
):
    """
    获取采集成功率统计
    
    扩展：支持按平台分组
    """
    start_time = datetime.now() - timedelta(days=days)
    
    if group_by == "platform":
        results = db.query(
            Platform.name.label("group_key"),
            CrawlLog.status,
            func.count(CrawlLog.id).label("count"),
        ).join(Platform).filter(CrawlLog.started_at >= start_time).group_by(
            Platform.name, CrawlLog.status
        ).all()
        
        # 按平台重组数据
        platform_data = {}
        for r in results:
            if r.group_key not in platform_data:
                platform_data[r.group_key] = {"total": 0, "rates": []}
            platform_data[r.group_key]["rates"].append({
                "status": r.status,
                "count": r.count,
            })
            platform_data[r.group_key]["total"] += r.count
        
        # 计算百分比
        for platform_name, data in platform_data.items():
            for rate in data["rates"]:
                rate["percentage"] = round(rate["count"] * 100 / data["total"], 2) if data["total"] > 0 else 0
        
        return {
            "code": 200,
            "data": {
                "period": f"最近 {days} 天",
                "group_by": "platform",
                "platforms": [
                    {"platform": k, "total": v["total"], "rates": v["rates"]}
                    for k, v in platform_data.items()
                ],
            },
            "message": "success",
        }
    else:
        # 按状态分组（默认）
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
                "group_by": "status",
                "total": total,
                "rates": rates,
            },
            "message": "success",
        }


@router.get("/platform-distribution", response_model=UnifiedResponse[dict])
async def get_platform_distribution(
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """
    获取各平台分布统计
    
    返回各平台的话题数、平均热度、负面占比
    """
    start_time = datetime.now() - timedelta(days=days)
    
    # 各平台话题数 + 平均热度
    platform_stats = db.query(
        Platform.name,
        Platform.display_name,
        func.count(HotTopic.id).label("topic_count"),
        func.avg(HotTopic.heat_score).label("avg_heat"),
        func.max(HotTopic.heat_score).label("max_heat"),
    ).join(HotTopic).filter(
        HotTopic.crawl_time >= start_time
    ).group_by(Platform.id).all()
    
    # 各平台负面占比
    negative_stats = db.query(
        Platform.name,
        func.count(SentimentResult.id).label("negative_count"),
    ).join(HotTopic).join(SentimentResult).filter(
        and_(
            HotTopic.crawl_time >= start_time,
            SentimentResult.sentiment_label == "negative",
        )
    ).group_by(Platform.id).all()
    
    negative_dict = {p.name: p.negative_count for p in negative_stats}
    
    platforms = []
    for p in platform_stats:
        topic_count = p.topic_count
        negative_count = negative_dict.get(p.name, 0)
        negative_ratio = round(negative_count * 100 / topic_count, 2) if topic_count > 0 else 0
        
        platforms.append({
            "name": p.name,
            "display_name": p.display_name,
            "topic_count": topic_count,
            "avg_heat": round(p.avg_heat, 2) if p.avg_heat else 0,
            "max_heat": p.max_heat,
            "negative_count": negative_count,
            "negative_ratio": negative_ratio,
        })
    
    return {
        "code": 200,
        "data": {
            "period": f"最近 {days} 天",
            "platforms": platforms,
        },
        "message": "success",
    }


@router.get("/kpi-deltas", response_model=UnifiedResponse[dict])
async def get_kpi_deltas(
    date: str = None,
    db: Session = Depends(get_db),
):
    """
    获取 KPI 日环比数据
    
    Args:
        date: 指定日期（YYYY-MM-DD），默认今天
    """
    if date:
        today = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        today = datetime.now().date()
    
    yesterday = today - timedelta(days=1)
    
    # 今日 vs 昨日话题数
    today_topics = db.query(HotTopic).filter(
        func.date(HotTopic.crawl_time) == today
    ).count()
    yesterday_topics = db.query(HotTopic).filter(
        func.date(HotTopic.crawl_time) == yesterday
    ).count()
    
    topic_delta = today_topics - yesterday_topics
    topic_delta_pct = round(topic_delta * 100 / yesterday_topics, 2) if yesterday_topics > 0 else 0
    
    # 今日 vs 昨日情感分析数
    today_sentiment = db.query(SentimentResult).join(HotTopic).filter(
        func.date(HotTopic.crawl_time) == today
    ).count()
    yesterday_sentiment = db.query(SentimentResult).join(HotTopic).filter(
        func.date(HotTopic.crawl_time) == yesterday
    ).count()
    
    sentiment_delta = today_sentiment - yesterday_sentiment
    sentiment_delta_pct = round(sentiment_delta * 100 / yesterday_sentiment, 2) if yesterday_sentiment > 0 else 0
    
    # 今日 vs 昨日负面占比
    today_negative = db.query(SentimentResult).join(HotTopic).filter(
        and_(
            func.date(HotTopic.crawl_time) == today,
            SentimentResult.sentiment_label == "negative",
        )
    ).count()
    yesterday_negative = db.query(SentimentResult).join(HotTopic).filter(
        and_(
            func.date(HotTopic.crawl_time) == yesterday,
            SentimentResult.sentiment_label == "negative",
        )
    ).count()
    
    today_negative_ratio = round(today_negative * 100 / today_sentiment, 2) if today_sentiment > 0 else 0
    yesterday_negative_ratio = round(yesterday_negative * 100 / yesterday_sentiment, 2) if yesterday_sentiment > 0 else 0
    
    negative_ratio_delta = round(today_negative_ratio - yesterday_negative_ratio, 2)
    
    # 采集成功率环比
    today_logs = db.query(CrawlLog).filter(
        func.date(CrawlLog.started_at) == today
    ).all()
    yesterday_logs = db.query(CrawlLog).filter(
        func.date(CrawlLog.started_at) == yesterday
    ).all()
    
    today_success_rate = round(
        sum(1 for log in today_logs if log.status == "success") * 100 / len(today_logs), 2
    ) if today_logs else 0
    yesterday_success_rate = round(
        sum(1 for log in yesterday_logs if log.status == "success") * 100 / len(yesterday_logs), 2
    ) if yesterday_logs else 0
    
    return {
        "code": 200,
        "data": {
            "date": str(today),
            "comparison_date": str(yesterday),
            "metrics": {
                "total_topics": {
                    "today": today_topics,
                    "yesterday": yesterday_topics,
                    "delta": topic_delta,
                    "delta_percentage": topic_delta_pct,
                },
                "sentiment_analyzed": {
                    "today": today_sentiment,
                    "yesterday": yesterday_sentiment,
                    "delta": sentiment_delta,
                    "delta_percentage": sentiment_delta_pct,
                },
                "negative_ratio": {
                    "today": today_negative_ratio,
                    "yesterday": yesterday_negative_ratio,
                    "delta": negative_ratio_delta,
                },
                "crawl_success_rate": {
                    "today": today_success_rate,
                    "yesterday": yesterday_success_rate,
                    "delta": round(today_success_rate - yesterday_success_rate, 2),
                },
            },
        },
        "message": "success",
    }
