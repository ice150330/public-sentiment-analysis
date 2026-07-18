"""
高级分析 API 路由 - 主题聚类

模块名称: topic_clusters.py
模块职责: 话题聚类、主题提取 API
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import TopicCluster
from app.schemas import UnifiedResponse
from app.services.topic_clustering_service import TopicClusteringService

router = APIRouter()


@router.get("", response_model=UnifiedResponse[dict])
async def list_clusters(
    start_time: datetime = None,
    end_time: datetime = None,
    algorithm: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询聚类结果列表"""
    query = db.query(TopicCluster)
    
    if start_time:
        query = query.filter(TopicCluster.created_at >= start_time)
    if end_time:
        query = query.filter(TopicCluster.created_at <= end_time)
    if algorithm:
        query = query.filter(TopicCluster.algorithm == algorithm)
    
    total = query.count()
    clusters = query.order_by(desc(TopicCluster.topic_count))
    clusters = clusters.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    service = TopicClusteringService(db)
    for cluster in clusters:
        items.append(service.list_payload(cluster))
    
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


@router.get("/{cluster_id}", response_model=UnifiedResponse[dict])
async def get_cluster(
    cluster_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取聚类详情及成员"""
    cluster = db.query(TopicCluster).filter(TopicCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")
    service = TopicClusteringService(db)
    
    return {
        "code": 200,
        "data": service.detail_payload(cluster, page=page, page_size=page_size),
        "message": "success",
    }


@router.post("/run", response_model=UnifiedResponse[dict])
async def run_clustering(
    algorithm: str = "kmeans",
    n_clusters: int = 5,
    time_window_hours: int = 24,
    db: Session = Depends(get_db),
):
    """
    执行话题聚类分析
    
    Args:
        algorithm: 聚类算法 (kmeans/dbscan/hierarchical)
        n_clusters: 聚类数量 (kmeans/hierarchical 有效)
        time_window_hours: 时间窗口(小时)
    """
    service = TopicClusteringService(db)
    try:
        result = service.run(
            algorithm=algorithm,
            n_clusters=n_clusters,
            time_window_hours=time_window_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if result["total_topics"] == 0:
        return {
            "code": 400,
            "data": None,
            "message": result["message"],
        }

    return {
        "code": 200,
        "data": result,
        "message": f"Clustering completed: {len(result['clusters'])} clusters created",
    }
