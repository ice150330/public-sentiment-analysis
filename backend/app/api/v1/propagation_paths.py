"""
高级分析 API 路由 - 传播路径分析

模块名称: propagation_paths.py
模块职责: 话题传播链路追踪、跨平台传播分析 API
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import HotTopic, PropagationPath
from app.schemas import UnifiedResponse
from app.services.propagation_analysis_service import PropagationAnalysisService

router = APIRouter()


@router.get("", response_model=UnifiedResponse[dict])
async def list_propagation_paths(
    root_topic_id: int = None,
    platform: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询传播路径列表"""
    query = db.query(PropagationPath).join(HotTopic)
    
    if root_topic_id:
        query = query.filter(PropagationPath.root_topic_id == root_topic_id)
    if start_time:
        query = query.filter(PropagationPath.first_seen_at >= start_time)
    if end_time:
        query = query.filter(PropagationPath.last_seen_at <= end_time)
    
    total = query.count()
    paths = query.order_by(desc(PropagationPath.total_nodes))
    paths = paths.offset((page - 1) * page_size).limit(page_size).all()
    
    service = PropagationAnalysisService(db)
    items = [service.list_payload(path) for path in paths]
    
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


@router.get("/{path_id}", response_model=UnifiedResponse[dict])
async def get_propagation_path(
    path_id: int,
    db: Session = Depends(get_db),
):
    """获取传播路径详情（树形结构）"""
    path = db.query(PropagationPath).filter(PropagationPath.id == path_id).first()
    if not path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propagation path not found")
    service = PropagationAnalysisService(db)
    
    return {
        "code": 200,
        "data": service.detail_payload(path),
        "message": "success",
    }


@router.post("/analyze/{topic_id}", response_model=UnifiedResponse[dict])
async def analyze_propagation(
    topic_id: int,
    time_window_hours: int = Query(24, ge=1, le=720),
    similarity_threshold: float = Query(0.18, ge=0, le=1),
    max_nodes: int = Query(30, ge=2, le=100),
    db: Session = Depends(get_db),
):
    """
    分析话题传播路径
    
    Args:
        topic_id: 根话题ID
        time_window_hours: 时间窗口(小时)
    """
    service = PropagationAnalysisService(db)
    try:
        result = service.analyze(
            topic_id,
            time_window_hours=time_window_hours,
            similarity_threshold=similarity_threshold,
            max_nodes=max_nodes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    path = result["path"]
    
    return {
        "code": 200,
        "data": {
            "path_id": path["id"],
            "root_topic_id": topic_id,
            "root_topic_title": path["root_topic_title"],
            "depth": path["depth"],
            "total_nodes": path["total_nodes"],
            "platforms_involved": path["platforms_involved"],
            "platform_transitions": path["platform_transitions"],
            "nodes": result["nodes"],
            "edges": result["edges"],
            "tree": result["tree"],
        },
        "message": "Propagation analysis completed",
    }
