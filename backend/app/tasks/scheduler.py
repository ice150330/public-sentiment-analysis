"""
定时任务调度模块

模块名称: scheduler.py
模块职责: APScheduler 配置、定时采集任务、情感分析任务

使用方式:
    from app.tasks.scheduler import TaskScheduler
    
    scheduler = TaskScheduler()
    scheduler.start()
    scheduler.add_crawl_job(interval_minutes=60)
"""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.crawler_service import CrawlerService
from app.services.sentiment_service import SentimentService

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self._running = False
    
    def start(self):
        """启动调度器"""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Task scheduler started")
    
    def shutdown(self):
        """关闭调度器"""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Task scheduler shutdown")
    
    def add_crawl_job(self, interval_minutes: int = 60):
        """
        添加定时采集任务
        
        Args:
            interval_minutes: 采集间隔（分钟），默认 60
        """
        # 移除已有的采集任务
        self._remove_job("crawl_task")
        
        # 添加新任务
        self.scheduler.add_job(
            self._run_crawl_task,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="crawl_task",
            name="定时采集任务",
            replace_existing=True,
        )
        
        logger.info(f"Crawl job added with interval {interval_minutes} minutes")
    
    def add_sentiment_job(self, interval_minutes: int = 30):
        """
        添加定时情感分析任务
        
        Args:
            interval_minutes: 分析间隔（分钟），默认 30
        """
        self._remove_job("sentiment_task")
        
        self.scheduler.add_job(
            self._run_sentiment_task,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="sentiment_task",
            name="定时情感分析任务",
            replace_existing=True,
        )
        
        logger.info(f"Sentiment job added with interval {interval_minutes} minutes")
    
    def add_cleanup_job(self, interval_hours: int = 24):
        """
        添加定时数据清理任务
        
        Args:
            interval_hours: 清理间隔（小时），默认 24
        """
        self._remove_job("cleanup_task")
        
        self.scheduler.add_job(
            self._run_cleanup_task,
            trigger=IntervalTrigger(hours=interval_hours),
            id="cleanup_task",
            name="定时数据清理任务",
            replace_existing=True,
        )
        
        logger.info(f"Cleanup job added with interval {interval_hours} hours")
    
    def _run_crawl_task(self):
        """执行采集任务"""
        logger.info("Running scheduled crawl task")
        
        db = SessionLocal()
        try:
            service = CrawlerService(db)
            
            # 查询启用的平台
            from app.models import Platform
            platforms = db.query(Platform).filter(Platform.is_active == True).all()
            platform_names = [p.name for p in platforms]
            
            if platform_names:
                result = service.run_crawl(platform_names)
                logger.info(f"Crawl completed: {result}")
            else:
                logger.warning("No active platforms to crawl")
                
        except Exception as e:
            logger.error(f"Crawl task failed: {e}")
        finally:
            db.close()
    
    def _run_sentiment_task(self):
        """执行情感分析任务"""
        logger.info("Running scheduled sentiment task")
        
        db = SessionLocal()
        try:
            service = SentimentService(db)
            count = service.analyze_unprocessed_topics(limit=100)
            logger.info(f"Sentiment analysis completed: {count} topics analyzed")
            
        except Exception as e:
            logger.error(f"Sentiment task failed: {e}")
        finally:
            db.close()
    
    def _run_cleanup_task(self):
        """执行数据清理任务"""
        logger.info("Running scheduled cleanup task")
        
        db = SessionLocal()
        try:
            # 清理过期数据（默认保留30天）
            from app.models import HotTopic, CrawlLog
            
            cutoff_date = datetime.now() - timedelta(days=30)
            
            # 删除旧的热榜数据
            deleted_topics = db.query(HotTopic).filter(
                HotTopic.crawl_time < cutoff_date
            ).delete()
            
            # 删除旧的采集日志
            deleted_logs = db.query(CrawlLog).filter(
                CrawlLog.started_at < cutoff_date
            ).delete()
            
            db.commit()
            logger.info(f"Cleanup completed: {deleted_topics} topics, {deleted_logs} logs deleted")
            
        except Exception as e:
            logger.error(f"Cleanup task failed: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _remove_job(self, job_id: str):
        """移除已有任务"""
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass  # 任务不存在则忽略
    
    def get_jobs(self) -> list:
        """获取所有任务列表"""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in self.scheduler.get_jobs()
        ]


# 全局调度器实例
_scheduler_instance: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """获取全局调度器实例（单例）"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
