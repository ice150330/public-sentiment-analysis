"""
后台任务调度器

模块名称: scheduler.py
模块职责: 定时执行预警评估、数据质量检查等后台任务
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Dict, Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.alert_engine import AlertEngine
from app.services.data_quality_service import DataQualityService

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """后台任务调度器"""
    
    def __init__(self):
        self.tasks = {}
        self.running = False
    
    async def start(self):
        """启动调度器"""
        if self.running:
            return
        
        self.running = True
        logger.info("Background scheduler started")
        
        # 注册定时任务
        self.tasks["alert_evaluation"] = asyncio.create_task(
            self._run_periodic("alert_evaluation", self._evaluate_alerts, interval_minutes=5)
        )
        self.tasks["data_quality_check"] = asyncio.create_task(
            self._run_periodic("data_quality_check", self._check_data_quality, interval_minutes=60)
        )
    
    async def stop(self):
        """停止调度器"""
        self.running = False
        for task in self.tasks.values():
            task.cancel()
        self.tasks.clear()
        logger.info("Background scheduler stopped")
    
    async def _run_periodic(self, task_name: str, task_func: Callable, interval_minutes: int):
        """
        周期性执行任务
        
        Args:
            task_name: 任务名称
            task_func: 任务函数
            interval_minutes: 执行间隔（分钟）
        """
        while self.running:
            try:
                logger.info(f"Running scheduled task: {task_name}")
                await task_func()
                logger.info(f"Scheduled task completed: {task_name}")
            except Exception as e:
                logger.error(f"Scheduled task failed: {task_name}, error: {e}")
            
            # 等待下一次执行
            await asyncio.sleep(interval_minutes * 60)
    
    async def _evaluate_alerts(self):
        """执行预警规则评估"""
        db = SessionLocal()
        try:
            engine = AlertEngine(db)
            result = engine.evaluate_all_rules()
            logger.info(f"Alert evaluation: {result['triggered']} triggered, {result['skipped']} skipped")
        finally:
            db.close()
    
    async def _check_data_quality(self):
        """执行数据质量检查"""
        db = SessionLocal()
        try:
            service = DataQualityService(db)
            result = service.run_quality_check(run_type="daily")
            logger.info(f"Data quality check: {result.get('issues_found', 0)} issues found")
        finally:
            db.close()


# 全局调度器实例
_scheduler = None


def get_scheduler() -> BackgroundScheduler:
    """获取调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler
