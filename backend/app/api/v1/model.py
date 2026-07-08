"""
模型管理 API 路由

模块名称: model.py
模块职责: 模型版本状态、低置信复核
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import ModelVersion, SentimentResult, HotTopic
from app.schemas import UnifiedResponse

router = APIRouter()


@router.get("/versions", response_model=UnifiedResponse[dict])
async def list_model_versions(
    is_active: bool = None,
    db: Session = Depends(get_db),
):
    """查询模型版本列表"""
    query = db.query(ModelVersion)
    
    if is_active is not None:
        query = query.filter(ModelVersion.is_active == is_active)
    
    versions = query.order_by(desc(ModelVersion.created_at)).all()
    
    items = []
    for v in versions:
        items.append({
            "id": v.id,
            "version": v.version,
            "model_name": v.model_name,
            "task_type": v.task_type,
            "device": v.device,
            "metrics_json": v.metrics_json,
            "config_json": v.config_json,
            "is_active": v.is_active,
            "description": v.description,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        })
    
    return {
        "code": 200,
        "data": {
            "items": items,
            "total": len(items),
        },
        "message": "success",
    }


@router.get("/status", response_model=UnifiedResponse[dict])
async def get_model_status(
    db: Session = Depends(get_db),
):
    """
    获取当前模型运行状态
    
    返回模型版本、设备、任务数、置信度分布等
    """
    # 当前激活的模型
    active_model = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
    
    # 最近 24 小时分析数
    last_24h = datetime.now() - timedelta(hours=24)
    recent_count = db.query(SentimentResult).filter(
        SentimentResult.analyzed_at >= last_24h,
    ).count()
    
    # 平均置信度
    avg_confidence = db.query(func.avg(SentimentResult.confidence)).filter(
        SentimentResult.analyzed_at >= last_24h,
    ).scalar()
    
    # 置信度分布
    high_conf = db.query(SentimentResult).filter(
        SentimentResult.analyzed_at >= last_24h,
        SentimentResult.confidence >= 0.8,
    ).count()
    mid_conf = db.query(SentimentResult).filter(
        SentimentResult.analyzed_at >= last_24h,
        SentimentResult.confidence.between(0.5, 0.8),
    ).count()
    low_conf = db.query(SentimentResult).filter(
        SentimentResult.analyzed_at >= last_24h,
        SentimentResult.confidence < 0.5,
    ).count()
    
    # 待复核数（低置信）
    pending_review = low_conf
    
    return {
        "code": 200,
        "data": {
            "model": {
                "version": active_model.version if active_model else None,
                "model_name": active_model.model_name if active_model else None,
                "device": active_model.device if active_model else "cpu",
                "is_loaded": active_model is not None,
            } if active_model else {"is_loaded": False},
            "recent_analyzed": recent_count,
            "avg_confidence": round(avg_confidence, 4) if avg_confidence else 0,
            "confidence_distribution": {
                "high": high_conf,
                "medium": mid_conf,
                "low": low_conf,
            },
            "pending_review": pending_review,
            "status": "running" if active_model else "not_loaded",
        },
        "message": "success",
    }


@router.get("/low-confidence", response_model=UnifiedResponse[dict])
async def get_low_confidence_results(
    threshold: float = Query(0.5, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    获取低置信度结果（待复核）
    
    Args:
        threshold: 置信度阈值，低于此值的返回
    """
    query = db.query(SentimentResult).join(HotTopic)
    query = query.filter(SentimentResult.confidence < threshold)
    query = query.order_by(SentimentResult.confidence.asc())
    
    total = query.count()
    results = query.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for r in results:
        items.append({
            "id": r.id,
            "topic_id": r.topic_id,
            "topic_title": r.hot_topic.title if r.hot_topic else None,
            "sentiment_label": r.sentiment_label,
            "confidence": r.confidence,
            "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else None,
            "platform_name": r.hot_topic.platform.display_name if r.hot_topic and r.hot_topic.platform else None,
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
            "threshold": threshold,
        },
        "message": "success",
    }
