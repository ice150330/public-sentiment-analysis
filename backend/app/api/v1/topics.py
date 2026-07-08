"""
热榜数据 API 路由

模块名称: topics.py
模块职责: 热榜查询、详情获取、分类统计接口
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import HotTopic, Platform, SentimentResult
from app.schemas import HotTopicResponse, HotTopicListResponse, UnifiedResponse

router = APIRouter()


@router.get("", response_model=UnifiedResponse[HotTopicListResponse])
async def list_topics(
    platform: str = None,
    keyword: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    category: str = None,
    sentiment_label: str = None,
    sort_by: str = "heat_score",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    查询热榜列表（支持分页、筛选、排序、情感筛选）
    """
    # 联表查询：HotTopic → Platform → SentimentResult
    query = db.query(HotTopic).join(Platform)
    
    # 如果需要按情感标签筛选，外联 SentimentResult
    if sentiment_label:
        query = query.outerjoin(SentimentResult)
        query = query.filter(SentimentResult.sentiment_label == sentiment_label)
    
    # 筛选条件
    if platform:
        query = query.filter(Platform.name == platform)
    if keyword:
        query = query.filter(HotTopic.title.contains(keyword))
    if start_time:
        query = query.filter(HotTopic.crawl_time >= start_time)
    if end_time:
        query = query.filter(HotTopic.crawl_time <= end_time)
    if category:
        query = query.filter(HotTopic.category == category)
    
    # 排序
    sort_field = getattr(HotTopic, sort_by, HotTopic.heat_score)
    if sort_order == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(sort_field)
    
    # 分页
    total = query.count()
    topics = query.offset((page - 1) * page_size).limit(page_size).all()
    
    # 组装响应数据（附加平台名 + 情感结果）
    items = []
    for topic in topics:
        topic_data = HotTopicResponse.from_orm(topic).dict()
        topic_data["platform_name"] = topic.platform.display_name if topic.platform else None
        
        # 附加情感分析结果（如果存在）
        if topic.sentiment_result:
            topic_data["sentiment"] = {
                "id": topic.sentiment_result.id,
                "topic_id": topic.sentiment_result.topic_id,
                "sentiment_label": topic.sentiment_result.sentiment_label,
                "confidence": topic.sentiment_result.confidence,
                "positive_score": topic.sentiment_result.positive_score,
                "negative_score": topic.sentiment_result.negative_score,
                "neutral_score": topic.sentiment_result.neutral_score,
                "model_version": topic.sentiment_result.model_version,
                "analyzed_at": topic.sentiment_result.analyzed_at.isoformat() if topic.sentiment_result.analyzed_at else None,
                "created_at": topic.sentiment_result.created_at.isoformat() if topic.sentiment_result.created_at else None,
            }
        else:
            topic_data["sentiment"] = None
        
        items.append(topic_data)
    
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


@router.get("/{topic_id}", response_model=UnifiedResponse[HotTopicResponse])
async def get_topic(
    topic_id: int,
    db: Session = Depends(get_db),
):
    """查询热榜详情（含情感分析结果）"""
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    topic_data = HotTopicResponse.from_orm(topic).dict()
    topic_data["platform_name"] = topic.platform.display_name if topic.platform else None
    
    # 附加情感分析结果
    if topic.sentiment_result:
        topic_data["sentiment"] = {
            "id": topic.sentiment_result.id,
            "topic_id": topic.sentiment_result.topic_id,
            "sentiment_label": topic.sentiment_result.sentiment_label,
            "confidence": topic.sentiment_result.confidence,
            "positive_score": topic.sentiment_result.positive_score,
            "negative_score": topic.sentiment_result.negative_score,
            "neutral_score": topic.sentiment_result.neutral_score,
            "model_version": topic.sentiment_result.model_version,
            "analyzed_at": topic.sentiment_result.analyzed_at.isoformat() if topic.sentiment_result.analyzed_at else None,
            "created_at": topic.sentiment_result.created_at.isoformat() if topic.sentiment_result.created_at else None,
        }
    else:
        topic_data["sentiment"] = None
    
    return {
        "code": 200,
        "data": topic_data,
        "message": "success",
    }


@router.get("/facets/categories", response_model=UnifiedResponse[dict])
async def get_topic_facets(
    platform: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    db: Session = Depends(get_db),
):
    """
    获取热榜分类统计（facet）
    
    返回各分类的话题数量，用于顶部分类标签筛选
    """
    query = db.query(HotTopic).join(Platform)
    
    if platform:
        query = query.filter(Platform.name == platform)
    if start_time:
        query = query.filter(HotTopic.crawl_time >= start_time)
    if end_time:
        query = query.filter(HotTopic.crawl_time <= end_time)
    
    # 按分类统计
    category_counts = query.with_entities(
        HotTopic.category,
        func.count(HotTopic.id).label("count"),
    ).group_by(HotTopic.category).all()
    
    # 按情感统计
    sentiment_query = db.query(HotTopic).join(Platform).outerjoin(SentimentResult)
    if platform:
        sentiment_query = sentiment_query.filter(Platform.name == platform)
    if start_time:
        sentiment_query = sentiment_query.filter(HotTopic.crawl_time >= start_time)
    if end_time:
        sentiment_query = sentiment_query.filter(HotTopic.crawl_time <= end_time)
    
    sentiment_counts = sentiment_query.with_entities(
        SentimentResult.sentiment_label,
        func.count(HotTopic.id).label("count"),
    ).group_by(SentimentResult.sentiment_label).all()
    
    return {
        "code": 200,
        "data": {
            "categories": [
                {"name": cat or "未分类", "count": count}
                for cat, count in category_counts
            ],
            "sentiments": [
                {"label": label or "未分析", "count": count}
                for label, count in sentiment_counts
            ],
            "total": sum(c for _, c in category_counts),
        },
        "message": "success",
    }
