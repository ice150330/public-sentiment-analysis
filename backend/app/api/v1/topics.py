"""
热榜数据 API 路由

模块名称: topics.py
模块职责: 热榜查询、详情获取接口
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import HotTopic, Platform
from app.schemas import HotTopicResponse, HotTopicListResponse, HotTopicQueryParams, UnifiedResponse

router = APIRouter()


@router.get("", response_model=UnifiedResponse[HotTopicListResponse])
async def list_topics(
    platform: str = None,
    keyword: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    category: str = None,
    sort_by: str = "heat_score",
    sort_order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    查询热榜列表（支持分页、筛选、排序）
    """
    query = db.query(HotTopic).join(Platform)
    
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
    
    # 组装响应数据（附加平台名）
    items = []
    for topic in topics:
        topic_data = HotTopicResponse.from_orm(topic).dict()
        topic_data["platform_name"] = topic.platform.display_name if topic.platform else None
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
    """查询热榜详情"""
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    topic_data = HotTopicResponse.from_orm(topic).dict()
    topic_data["platform_name"] = topic.platform.display_name if topic.platform else None
    
    return {
        "code": 200,
        "data": topic_data,
        "message": "success",
    }
