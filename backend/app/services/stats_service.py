"""
统计服务层

模块名称: stats_service.py
模块职责: 统计计算、数据聚合
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from app.models import CrawlLog, HotTopic, Platform, SentimentResult

logger = logging.getLogger(__name__)


class StatsService:
    """统计服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_sentiment_distribution(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        platform: Optional[str] = None,
    ) -> Dict:
        """获取情感分布统计"""
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=7)
        
        query = self.db.query(SentimentResult).join(HotTopic).join(Platform)
        query = query.filter(and_(
            SentimentResult.analyzed_at >= start_time,
            SentimentResult.analyzed_at <= end_time,
        ))
        
        if platform:
            query = query.filter(Platform.name == platform)
        
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
        
        return {
            "total": total,
            "distribution": distribution,
        }
    
    def get_heat_trend(
        self,
        days: int = 7,
        platform: Optional[str] = None,
    ) -> List[Dict]:
        """获取热度趋势"""
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        query = self.db.query(HotTopic).join(Platform)
        query = query.filter(HotTopic.crawl_time >= start_time)
        
        if platform:
            query = query.filter(Platform.name == platform)
        
        results = query.with_entities(
            func.date(HotTopic.crawl_time).label("date"),
            func.avg(HotTopic.heat_score).label("avg_heat"),
            func.max(HotTopic.heat_score).label("max_heat"),
            func.count(HotTopic.id).label("topic_count"),
        ).group_by("date").order_by("date").all()
        
        return [
            {
                "date": str(r.date),
                "avg_heat": round(r.avg_heat, 2) if r.avg_heat else 0,
                "max_heat": r.max_heat,
                "topic_count": r.topic_count,
            }
            for r in results
        ]
    
    def get_crawl_success_rate(self, days: int = 7) -> Dict:
        """获取采集成功率"""
        start_time = datetime.now() - timedelta(days=days)
        
        results = self.db.query(
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
            "period": f"最近 {days} 天",
            "total": total,
            "rates": rates,
        }
