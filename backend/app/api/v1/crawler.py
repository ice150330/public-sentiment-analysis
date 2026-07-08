"""
爬虫控制 API 路由

模块名称: crawler.py
模块职责: 手动触发采集、查询状态、查看日志、配置定时任务
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import CrawlLog, Platform, SystemConfig
from app.schemas import (
    CrawlerTriggerRequest,
    CrawlerTriggerResponse,
    CrawlLogResponse,
    CrawlerScheduleConfig,
    UnifiedResponse,
)
from app.services.crawler_service import CrawlerService

router = APIRouter()


@router.post("/trigger", response_model=UnifiedResponse[CrawlerTriggerResponse], status_code=202)
async def trigger_crawler(
    request: CrawlerTriggerRequest,
    db: Session = Depends(get_db),
):
    """
    手动触发爬虫采集
    
    Args:
        request: 可指定平台，默认异步执行
    """
    service = CrawlerService(db)
    
    # 确定采集平台
    if request.platforms:
        platforms = request.platforms
    else:
        platforms = [p.name for p in db.query(Platform).filter(Platform.is_active == True).all()]
    
    # 启动采集（异步或同步）
    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    if request.is_async:
        # 异步执行：后台启动（实际实现需接入 APScheduler 或线程）
        # TODO: 接入后台任务队列
        return {
            "code": 202,
            "data": {
                "task_id": task_id,
                "status": "running",
                "platforms": platforms,
                "started_at": datetime.now(),
            },
            "message": "Crawler task started in background",
        }
    else:
        # 同步执行：等待完成
        results = service.run_crawl(platforms)
        return {
            "code": 200,
            "data": {
                "task_id": task_id,
                "status": "completed",
                "platforms": platforms,
                "started_at": datetime.now(),
                "results": results,
            },
            "message": "Crawler task completed",
        }


@router.get("/status", response_model=UnifiedResponse[dict])
async def get_crawler_status(
    db: Session = Depends(get_db),
):
    """查询当前爬虫运行状态"""
    # 查询最新采集日志
    last_log = db.query(CrawlLog).order_by(desc(CrawlLog.started_at)).first()
    
    is_running = False
    current_task = None
    
    if last_log and last_log.completed_at is None:
        # 有未完成的日志，认为正在运行
        is_running = True
        current_task = {
            "task_id": f"task_{last_log.started_at.strftime('%Y%m%d%H%M%S')}",
            "platforms": [last_log.platform.display_name] if last_log.platform else [],
            "started_at": last_log.started_at.isoformat() if last_log.started_at else None,
            "elapsed_seconds": (datetime.now() - last_log.started_at).seconds if last_log.started_at else 0,
        }
    
    return {
        "code": 200,
        "data": {
            "is_running": is_running,
            "current_task": current_task,
            "queue_length": 0,  # TODO: 接入任务队列
        },
        "message": "success",
    }


@router.get("/logs", response_model=UnifiedResponse[List[CrawlLogResponse]])
async def list_crawl_logs(
    platform: str = None,
    status: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询采集日志列表"""
    query = db.query(CrawlLog).join(Platform)
    
    if platform:
        query = query.filter(Platform.name == platform)
    if status:
        query = query.filter(CrawlLog.status == status)
    if start_time:
        query = query.filter(CrawlLog.started_at >= start_time)
    if end_time:
        query = query.filter(CrawlLog.started_at <= end_time)
    
    total = query.count()
    logs = query.order_by(desc(CrawlLog.started_at))
    logs = logs.offset((page - 1) * page_size).limit(page_size).all()
    
    # 组装响应数据
    items = []
    for log in logs:
        log_data = CrawlLogResponse.from_orm(log).dict()
        log_data["platform_name"] = log.platform.display_name if log.platform else None
        log_data["duration_seconds"] = (
            int((log.completed_at - log.started_at).total_seconds())
            if log.completed_at and log.started_at
            else None
        )
        items.append(log_data)
    
    return {
        "code": 200,
        "data": items,
        "message": "success",
    }


@router.get("/schedule", response_model=UnifiedResponse[CrawlerScheduleConfig])
async def get_schedule_config(
    db: Session = Depends(get_db),
):
    """查询定时采集配置"""
    interval = db.query(SystemConfig).filter(SystemConfig.config_key == "crawler_interval_minutes").first()
    enabled = db.query(SystemConfig).filter(SystemConfig.config_key == "crawler_enabled").first()
    
    return {
        "code": 200,
        "data": {
            "interval_minutes": int(interval.config_value) if interval else 60,
            "is_enabled": enabled.config_value == "true" if enabled else True,
        },
        "message": "success",
    }


@router.put("/schedule", response_model=UnifiedResponse[CrawlerScheduleConfig])
async def update_schedule_config(
    config: CrawlerScheduleConfig,
    db: Session = Depends(get_db),
):
    """修改定时采集配置"""
    interval = db.query(SystemConfig).filter(SystemConfig.config_key == "crawler_interval_minutes").first()
    if interval:
        interval.config_value = str(config.interval_minutes)
    else:
        db.add(SystemConfig(config_key="crawler_interval_minutes", config_value=str(config.interval_minutes)))
    
    enabled = db.query(SystemConfig).filter(SystemConfig.config_key == "crawler_enabled").first()
    if enabled:
        enabled.config_value = "true" if config.is_enabled else "false"
    else:
        db.add(SystemConfig(config_key="crawler_enabled", config_value="true" if config.is_enabled else "false"))
    
    db.commit()
    
    # TODO: 重启定时任务
    
    return {
        "code": 200,
        "data": config,
        "message": "Schedule updated successfully",
    }
