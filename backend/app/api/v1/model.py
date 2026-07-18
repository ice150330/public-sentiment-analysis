"""
模型管理 API 路由

模块名称: model.py
模块职责: 模型版本状态、低置信复核
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.auth import require_admin, require_analyst
from app.core.database import get_db
from app.models import ModelVersion, SentimentResult, SentimentReviewItem, HotTopic, Platform, User
from app.schemas import ModelActivationRequest, SentimentReviewUpdateRequest, UnifiedResponse
from app.services.audit_service import write_audit_log
from app.services.model_registry_service import (
    activate_model_version,
    ensure_default_model_versions,
    model_version_payload,
)
from app.services.sentiment_review_service import (
    DEFAULT_REVIEW_THRESHOLD,
    apply_review_platform_scope,
    ensure_review_queue,
    mark_review_item,
    pending_review_count,
    review_item_payload,
)

router = APIRouter()


@router.get("/versions", response_model=UnifiedResponse[dict])
async def list_model_versions(
    is_active: bool = None,
    db: Session = Depends(get_db),
):
    """查询模型版本列表"""
    if ensure_default_model_versions(db):
        db.commit()

    query = db.query(ModelVersion)
    
    if is_active is not None:
        query = query.filter(ModelVersion.is_active == is_active)
    
    versions = query.order_by(desc(ModelVersion.created_at)).all()
    
    items = [model_version_payload(v) for v in versions]
    
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
    if ensure_default_model_versions(db):
        db.commit()
    active_models = db.query(ModelVersion).filter(ModelVersion.is_active == True).all()
    active_model = active_models[0] if active_models else None
    
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
    
    # 待复核数（低置信且未被人工处理）
    pending_review = pending_review_count(db, threshold=0.5)
    
    return {
        "code": 200,
        "data": {
            "model": {
                "version": active_model.version if active_model else None,
                "model_name": active_model.model_name if active_model else None,
                "device": active_model.device if active_model else "cpu",
                "is_loaded": active_model is not None,
                "provider": model_version_payload(active_model)["provider"] if active_model else None,
                "traffic_percent": model_version_payload(active_model)["traffic_percent"] if active_model else 0,
            } if active_model else {"is_loaded": False},
            "active_versions": [model_version_payload(item) for item in active_models],
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
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """
    获取低置信度结果（待复核）
    
    Args:
        threshold: 置信度阈值，低于此值的返回
    """
    ensure_review_queue(db, threshold=threshold, current_user=current_user)
    db.commit()

    query = db.query(SentimentResult).join(HotTopic).join(Platform)
    query = query.filter(SentimentResult.confidence < threshold)
    query = apply_review_platform_scope(query, current_user)
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
            "review_id": r.review_item.id if r.review_item else None,
            "review_status": r.review_item.status if r.review_item else "pending",
            "corrected_label": r.review_item.corrected_label if r.review_item else None,
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


@router.get("/review-queue", response_model=UnifiedResponse[dict])
async def list_review_queue(
    threshold: float = Query(DEFAULT_REVIEW_THRESHOLD, ge=0, le=1),
    status_filter: str | None = Query(None, alias="status"),
    sentiment_result_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """查询低置信度人工复核队列"""
    if status_filter and status_filter not in {"pending", "reviewed", "ignored"}:
        raise HTTPException(status_code=400, detail="Invalid review status")

    created = ensure_review_queue(db, threshold=threshold, current_user=current_user)
    if created:
        db.commit()

    query = db.query(SentimentReviewItem).join(SentimentResult).join(HotTopic).join(Platform)
    query = apply_review_platform_scope(query, current_user)
    if status_filter:
        query = query.filter(SentimentReviewItem.status == status_filter)
    if sentiment_result_id:
        query = query.filter(SentimentReviewItem.sentiment_result_id == sentiment_result_id)

    total = query.count()
    items = query.order_by(desc(SentimentReviewItem.created_at))
    items = items.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size

    return {
        "code": 200,
        "data": {
            "items": [review_item_payload(item) for item in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "threshold": threshold,
            "created": created,
        },
        "message": "success",
    }


@router.post("/versions/{version_id}/activate", response_model=UnifiedResponse[dict])
async def activate_version(
    version_id: int,
    payload: ModelActivationRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """激活模型版本，支持灰度流量比例"""
    ensure_default_model_versions(db)
    before = [model_version_payload(item) for item in db.query(ModelVersion).all()]
    try:
        version = activate_model_version(db, version_id, traffic_percent=payload.traffic_percent)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    after = [model_version_payload(item) for item in db.query(ModelVersion).all()]
    write_audit_log(
        db,
        operator=current_user.username,
        action="activate_model_version",
        target_type="model_version",
        target_id=version.id,
        before=before,
        after=after,
    )
    db.commit()
    db.refresh(version)

    return {
        "code": 200,
        "data": model_version_payload(version),
        "message": "Model version activated",
    }


@router.patch("/review-queue/{review_id}", response_model=UnifiedResponse[dict])
async def update_review_item(
    review_id: int,
    payload: SentimentReviewUpdateRequest,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """人工复核低置信度情感结果"""
    item = (
        db.query(SentimentReviewItem)
        .join(SentimentResult)
        .join(HotTopic)
        .join(Platform)
        .filter(SentimentReviewItem.id == review_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    scoped = (
        apply_review_platform_scope(
            db.query(SentimentReviewItem)
            .join(SentimentResult)
            .join(HotTopic)
            .join(Platform)
            .filter(SentimentReviewItem.id == review_id),
            current_user,
        )
        .first()
    )
    if not scoped:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient platform permissions")

    before = review_item_payload(item)
    mark_review_item(
        item,
        status=payload.status,
        corrected_label=payload.corrected_label,
        reviewer=current_user.username,
        note=payload.note,
    )
    write_audit_log(
        db,
        operator=current_user.username,
        action="review_sentiment_result",
        target_type="sentiment_review",
        target_id=item.id,
        before=before,
        after=review_item_payload(item),
    )
    db.commit()
    db.refresh(item)

    return {
        "code": 200,
        "data": review_item_payload(item),
        "message": "Review item updated",
    }
