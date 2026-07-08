"""
爬虫控制 API 路由

模块名称: crawler.py
模块职责: 手动触发采集、查询状态、查看日志、配置定时任务、同步状态
"""

import json
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import CrawlLog, Platform, SystemConfig, HotTopic, SentimentResult, CrawlerTask, CrawlerTaskEvent
from app.schemas import (
    CrawlerTriggerRequest,
    CrawlerTriggerResponse,
    CrawlLogResponse,
    CrawlerScheduleConfig,
    PaginatedResponse,
    UnifiedResponse,
)
from app.services.crawler_service import CrawlerService
from app.services.task_state_service import expire_stale_crawler_tasks

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
    now = datetime.now()
    task_id = f"task_{now.strftime('%Y%m%d%H%M%S%f')}"
    task = CrawlerTask(
        task_id=task_id,
        status="queued" if request.is_async else "running",
        progress=0 if request.is_async else 10,
        platforms_json=json.dumps(platforms, ensure_ascii=False),
        started_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    db.add(CrawlerTaskEvent(
        task_ref_id=task.id,
        event_type="queued" if request.is_async else "started",
        message="Crawler task created",
        payload_json=json.dumps({"platforms": platforms, "is_async": request.is_async}, ensure_ascii=False),
    ))
    db.commit()
    
    if request.is_async:
        return {
            "code": 202,
            "data": {
                "task_id": task_id,
                "status": task.status,
                "platforms": platforms,
                "started_at": task.started_at,
            },
            "message": "Crawler task queued",
        }
    else:
        # 同步执行：等待完成
        try:
            results = service.run_crawl(platforms)
            task.status = "completed"
            task.progress = 100
            task.result_json = json.dumps(results, ensure_ascii=False, default=str)
            task.completed_at = datetime.now()
            db.add(CrawlerTaskEvent(
                task_ref_id=task.id,
                event_type="completed",
                message="Crawler task completed",
                payload_json=task.result_json,
            ))
            db.commit()
        except Exception as exc:
            task.status = "failed"
            task.progress = 100
            task.error_message = str(exc)
            task.completed_at = datetime.now()
            db.add(CrawlerTaskEvent(
                task_ref_id=task.id,
                event_type="failed",
                message=str(exc),
            ))
            db.commit()
            raise
        return {
            "code": 200,
            "data": {
                "task_id": task_id,
                "status": task.status,
                "platforms": platforms,
                "started_at": task.started_at,
                "results": results,
            },
            "message": "Crawler task completed",
        }


@router.get("/status", response_model=UnifiedResponse[dict])
async def get_crawler_status(
    db: Session = Depends(get_db),
):
    """
    查询当前爬虫运行状态
    
    扩展：返回各平台最近采集状态、进度、队列信息
    """
    expire_stale_crawler_tasks(db)

    # 查询最新采集日志
    last_log = db.query(CrawlLog).order_by(desc(CrawlLog.started_at)).first()
    active_task = db.query(CrawlerTask).filter(
        CrawlerTask.status.in_(["queued", "running", "paused", "retry_queued"])
    ).order_by(desc(CrawlerTask.created_at)).first()
    queue_length = db.query(CrawlerTask).filter(
        CrawlerTask.status.in_(["queued", "retry_queued"])
    ).count()
    
    is_running = False
    current_task = None
    
    if active_task:
        is_running = active_task.status == "running"
        platforms = json.loads(active_task.platforms_json or "[]")
        started_at = active_task.started_at or active_task.created_at
        current_task = {
            "task_id": active_task.task_id,
            "platforms": platforms,
            "status": active_task.status,
            "progress": active_task.progress,
            "started_at": started_at.isoformat() if started_at else None,
            "elapsed_seconds": (datetime.now() - started_at).seconds if started_at else 0,
        }
    elif last_log and last_log.completed_at is None:
        # 有未完成的日志，认为正在运行
        is_running = True
        current_task = {
            "task_id": f"task_{last_log.started_at.strftime('%Y%m%d%H%M%S')}",
            "platforms": [last_log.platform.display_name] if last_log.platform else [],
            "started_at": last_log.started_at.isoformat() if last_log.started_at else None,
            "elapsed_seconds": (datetime.now() - last_log.started_at).seconds if last_log.started_at else 0,
        }
    
    # 各平台最近采集状态
    platform_status = []
    platforms = db.query(Platform).filter(Platform.is_active == True).all()
    
    for platform in platforms:
        last_platform_log = db.query(CrawlLog).filter(
            CrawlLog.platform_id == platform.id
        ).order_by(desc(CrawlLog.started_at)).first()
        
        if last_platform_log:
            # 计算距上次采集的分钟数
            minutes_ago = int((datetime.now() - last_platform_log.completed_at).total_seconds() / 60) if last_platform_log.completed_at else None
            
            platform_status.append({
                "platform_id": platform.id,
                "platform_name": platform.name,
                "display_name": platform.display_name,
                "last_crawl": last_platform_log.completed_at.isoformat() if last_platform_log.completed_at else None,
                "minutes_ago": minutes_ago,
                "status": last_platform_log.status,
                "records_count": last_platform_log.records_count,
                "is_healthy": last_platform_log.status == "success" and (minutes_ago is None or minutes_ago < 120),
            })
        else:
            platform_status.append({
                "platform_id": platform.id,
                "platform_name": platform.name,
                "display_name": platform.display_name,
                "last_crawl": None,
                "minutes_ago": None,
                "status": "never",
                "records_count": 0,
                "is_healthy": False,
            })
    
    # 今日采集统计
    today = datetime.now().date()
    today_logs = db.query(CrawlLog).filter(
        func.date(CrawlLog.started_at) == today
    ).all()
    
    today_total = len(today_logs)
    today_success = sum(1 for log in today_logs if log.status == "success")
    today_failed = sum(1 for log in today_logs if log.status == "failed")
    
    # 下次采集时间
    next_crawl = None
    schedule = db.query(SystemConfig).filter(SystemConfig.config_key == "crawler_interval_minutes").first()
    if schedule and last_log and last_log.completed_at:
        interval = int(schedule.config_value)
        next_crawl_time = last_log.completed_at + timedelta(minutes=interval)
        next_crawl = next_crawl_time.isoformat()
    
    return {
        "code": 200,
        "data": {
            "is_running": is_running,
            "current_task": current_task,
            "queue_length": queue_length,
            "platform_status": platform_status,
            "today_summary": {
                "total": today_total,
                "success": today_success,
                "failed": today_failed,
                "success_rate": round(today_success * 100 / today_total, 2) if today_total > 0 else 0,
            },
            "next_crawl": next_crawl,
        },
        "message": "success",
    }


@router.get("/logs", response_model=UnifiedResponse[PaginatedResponse[CrawlLogResponse]])
async def list_crawl_logs(
    platform: str = None,
    status: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询采集日志列表（支持分页）"""
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
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "code": 200,
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
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
    
    return {
        "code": 200,
        "data": config,
        "message": "Schedule config persisted successfully",
    }


# ========== 新增：同步状态接口 ==========

@router.get("/sync/status", response_model=UnifiedResponse[dict])
async def get_sync_status(
    db: Session = Depends(get_db),
):
    """
    获取系统同步状态（顶栏显示用）
    
    返回各模块最新数据更新时间
    """
    expire_stale_crawler_tasks(db)

    # 最新热榜采集时间
    last_hot_topic = db.query(HotTopic).order_by(desc(HotTopic.crawl_time)).first()
    last_hot_topic_time = last_hot_topic.crawl_time.isoformat() if last_hot_topic else None
    
    # 最新情感分析时间
    last_sentiment = db.query(SentimentResult).order_by(desc(SentimentResult.analyzed_at)).first()
    last_sentiment_time = last_sentiment.analyzed_at.isoformat() if last_sentiment else None
    
    # 最新采集日志时间
    last_crawl = db.query(CrawlLog).order_by(desc(CrawlLog.completed_at)).first()
    last_crawl_time = last_crawl.completed_at.isoformat() if last_crawl and last_crawl.completed_at else None
    active_task = db.query(CrawlerTask).filter(
        CrawlerTask.status.in_(["queued", "running", "paused", "retry_queued"])
    ).order_by(desc(CrawlerTask.created_at)).first()
    queue_length = db.query(CrawlerTask).filter(
        CrawlerTask.status.in_(["queued", "retry_queued"])
    ).count()
    
    # 计算同步延迟（秒）
    sync_delay = None
    if last_crawl_time:
        last_crawl_dt = datetime.fromisoformat(last_crawl_time.replace('Z', '+00:00'))
        sync_delay = int((datetime.now() - last_crawl_dt.replace(tzinfo=None)).total_seconds())
    
    return {
        "code": 200,
        "data": {
            "last_updated": last_crawl_time,
            "sync_delay_seconds": sync_delay,
            "modules": {
                "hot_topics": {
                    "last_updated": last_hot_topic_time,
                    "count": db.query(HotTopic).count(),
                },
                "sentiment": {
                    "last_updated": last_sentiment_time,
                    "count": db.query(SentimentResult).count(),
                },
                "crawler": {
                    "last_updated": last_crawl_time,
                    "today_count": db.query(CrawlLog).filter(
                        func.date(CrawlLog.started_at) == datetime.now().date()
                    ).count(),
                },
            },
            "is_syncing": bool(active_task and active_task.status in {"queued", "running", "retry_queued"}),
            "queue_length": queue_length,
            "active_task": {
                "task_id": active_task.task_id,
                "status": active_task.status,
                "progress": active_task.progress,
                "platforms": json.loads(active_task.platforms_json or "[]"),
                "started_at": (active_task.started_at or active_task.created_at).isoformat()
                if (active_task.started_at or active_task.created_at) else None,
            } if active_task else None,
        },
        "message": "success",
    }
