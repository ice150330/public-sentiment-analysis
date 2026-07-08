"""
话题扩展 API 路由（样本、关联话题）

模块名称: topic_ext.py
模块职责: 话题样本、关联话题查询
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import HotTopic, TopicSample, TopicRelation, Platform
from app.schemas import UnifiedResponse

router = APIRouter()


@router.get("/{topic_id}/samples", response_model=UnifiedResponse[dict])
async def get_topic_samples(
    topic_id: int,
    platform: str = None,
    sample_type: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取话题证据样本"""
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    query = db.query(TopicSample).join(Platform, isouter=True)
    query = query.filter(TopicSample.topic_id == topic_id)
    
    if platform:
        query = query.filter(Platform.name == platform)
    if sample_type:
        query = query.filter(TopicSample.sample_type == sample_type)
    
    total = query.count()
    samples = query.order_by(desc(TopicSample.created_at))
    samples = samples.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for sample in samples:
        items.append({
            "id": sample.id,
            "platform_name": sample.platform.display_name if sample.platform else None,
            "sample_type": sample.sample_type,
            "content": sample.content,
            "sentiment_label": sample.sentiment_label,
            "confidence": sample.confidence,
            "source_url": sample.source_url,
            "author": sample.author,
            "created_at": sample.created_at.isoformat() if sample.created_at else None,
        })
    
    total_pages = (total + page_size - 1) // page_size
    
    return {
        "code": 200,
        "data": {
            "topic_id": topic_id,
            "topic_title": topic.title,
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


@router.get("/{topic_id}/related", response_model=UnifiedResponse[dict])
async def get_related_topics(
    topic_id: int,
    relation_type: str = None,
    db: Session = Depends(get_db),
):
    """获取关联话题"""
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    query = db.query(TopicRelation).filter(
        TopicRelation.source_topic_id == topic_id
    )
    
    if relation_type:
        query = query.filter(TopicRelation.relation_type == relation_type)
    
    relations = query.order_by(desc(TopicRelation.score)).all()
    
    items = []
    for rel in relations:
        target = rel.target_topic
        items.append({
            "id": rel.id,
            "target_topic_id": rel.target_topic_id,
            "target_title": target.title if target else None,
            "relation_type": rel.relation_type,
            "score": rel.score,
            "description": rel.description,
        })
    
    return {
        "code": 200,
        "data": {
            "topic_id": topic_id,
            "topic_title": topic.title,
            "relations": items,
        },
        "message": "success",
    }
