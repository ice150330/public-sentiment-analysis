"""
系统管理 API 路由

模块名称: system.py
模块职责: 系统健康检查、系统日志、审计日志
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text

from app.core.auth import require_admin
from app.core.database import get_db, engine
from app.models import CrawlLog, HotTopic, SentimentResult, SystemLog, AuditLog, Platform
from app.schemas import UnifiedResponse
from app.services.audit_service import write_audit_log
from app.services.sqlite_backup_service import (
    SQLiteBackupError,
    create_sqlite_backup,
    get_sqlite_backup_path,
    list_sqlite_backups,
)

router = APIRouter()


@router.get("/health", response_model=UnifiedResponse[dict])
async def get_system_health(
    db: Session = Depends(get_db),
):
    """
    获取系统健康状态
    
    检查 API、数据库、爬虫、模型等组件状态
    """
    # API 状态（本服务运行中）
    api_status = "healthy"
    
    # 数据库状态
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    
    # 爬虫状态（最近采集时间）
    last_crawl = db.query(CrawlLog).order_by(desc(CrawlLog.completed_at)).first()
    crawler_status = "healthy"
    if not last_crawl:
        crawler_status = "warning"
    elif last_crawl.status == "failed":
        crawler_status = "error"
    else:
        delay = (datetime.now() - last_crawl.completed_at).total_seconds() / 60 if last_crawl.completed_at else 0
        if delay > 180:
            crawler_status = "warning"
    
    # 模型状态（情感分析能力）
    model_status = "healthy"
    recent_sentiment = db.query(SentimentResult).order_by(desc(SentimentResult.analyzed_at)).first()
    if not recent_sentiment:
        model_status = "warning"
    elif recent_sentiment.analyzed_at and (datetime.now() - recent_sentiment.analyzed_at).total_seconds() > 86400:
        model_status = "warning"
    
    # 各组件状态汇总
    components = {
        "api": {"status": api_status, "message": "API 服务运行正常"},
        "database": {"status": db_status, "message": "数据库连接正常" if db_status == "healthy" else "数据库连接异常"},
        "crawler": {"status": crawler_status, "message": "爬虫运行正常" if crawler_status == "healthy" else "爬虫可能存在异常"},
        "model": {"status": model_status, "message": "模型服务正常" if model_status == "healthy" else "模型服务可能异常"},
    }
    
    # 整体状态
    overall_status = "healthy"
    if any(c["status"] == "error" for c in components.values()):
        overall_status = "error"
    elif any(c["status"] == "warning" for c in components.values()):
        overall_status = "warning"
    
    return {
        "code": 200,
        "data": {
            "overall_status": overall_status,
            "components": components,
            "checked_at": datetime.now().isoformat(),
        },
        "message": "success",
    }


@router.post("/database/backup", response_model=UnifiedResponse[dict], status_code=201)
async def create_database_backup(
    current_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """创建 SQLite 数据库在线备份"""
    try:
        backup = create_sqlite_backup()
    except SQLiteBackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    data = backup.to_public_dict()
    write_audit_log(
        db,
        operator=current_user.username,
        action="create_database_backup",
        target_type="database",
        target_id=backup.filename,
        after=data,
    )
    db.commit()

    return {
        "code": 201,
        "data": data,
        "message": "Database backup created",
    }


@router.get("/database/backups", response_model=UnifiedResponse[dict])
async def list_database_backups(
    current_user = Depends(require_admin),
):
    """查询可下载的 SQLite 备份文件"""
    try:
        backups = [backup.to_public_dict() for backup in list_sqlite_backups()]
    except SQLiteBackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "code": 200,
        "data": {
            "items": backups,
            "total": len(backups),
        },
        "message": "success",
    }


@router.get("/database/backups/{filename}")
async def download_database_backup(
    filename: str,
    current_user = Depends(require_admin),
):
    """下载指定 SQLite 备份文件"""
    try:
        backup_path = get_sqlite_backup_path(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Backup not found") from exc
    except SQLiteBackupError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(
        path=backup_path,
        media_type="application/octet-stream",
        filename=Path(backup_path).name,
    )


@router.get("/logs", response_model=UnifiedResponse[dict])
async def list_system_logs(
    level: str = None,
    module: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """查询系统日志"""
    query = db.query(SystemLog)
    
    if level:
        query = query.filter(SystemLog.level == level)
    if module:
        query = query.filter(SystemLog.module == module)
    if start_time:
        query = query.filter(SystemLog.created_at >= start_time)
    if end_time:
        query = query.filter(SystemLog.created_at <= end_time)
    
    total = query.count()
    logs = query.order_by(desc(SystemLog.created_at))
    logs = logs.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "level": log.level,
            "module": log.module,
            "event": log.event,
            "message": log.message,
            "payload_json": log.payload_json,
            "request_id": log.request_id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    
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


@router.post("/logs", response_model=UnifiedResponse[dict], status_code=201)
async def create_system_log(
    log_data: dict,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """写入系统日志（供各模块调用）"""
    log = SystemLog(
        level=log_data.get("level", "INFO"),
        module=log_data.get("module"),
        event=log_data.get("event"),
        message=log_data.get("message"),
        payload_json=log_data.get("payload_json"),
        request_id=log_data.get("request_id"),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return {
        "code": 201,
        "data": {"id": log.id},
        "message": "Log created",
    }


# ========== 审计日志 ==========

@router.get("/audit-logs", response_model=UnifiedResponse[dict])
async def list_audit_logs(
    operator: str = None,
    action: str = None,
    target_type: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """查询审计日志"""
    query = db.query(AuditLog)
    
    if operator:
        query = query.filter(AuditLog.operator == operator)
    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    if start_time:
        query = query.filter(AuditLog.created_at >= start_time)
    if end_time:
        query = query.filter(AuditLog.created_at <= end_time)
    
    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at))
    logs = logs.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "operator": log.operator,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "before_json": log.before_json,
            "after_json": log.after_json,
            "note": log.note,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    
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


@router.post("/audit-logs", response_model=UnifiedResponse[dict], status_code=201)
async def create_audit_log(
    log_data: dict,
    current_user = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """写入审计日志（供各模块调用）"""
    log = AuditLog(
        operator=log_data.get("operator", "system"),
        action=log_data.get("action"),
        target_type=log_data.get("target_type"),
        target_id=log_data.get("target_id"),
        before_json=log_data.get("before_json"),
        after_json=log_data.get("after_json"),
        note=log_data.get("note"),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    
    return {
        "code": 201,
        "data": {"id": log.id},
        "message": "Audit log created",
    }
