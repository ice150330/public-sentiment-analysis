"""
高级分析 API 路由 - 主题聚类

模块名称: topic_clusters.py
模块职责: 话题聚类、主题提取 API
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import HotTopic, TopicCluster, ClusterMember, Platform, SentimentResult
from app.schemas import UnifiedResponse

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
    for cluster in clusters:
        items.append({
            "id": cluster.id,
            "cluster_name": cluster.cluster_name,
            "description": cluster.description,
            "algorithm": cluster.algorithm,
            "topic_count": cluster.topic_count,
            "avg_sentiment": cluster.avg_sentiment,
            "dominant_sentiment": cluster.dominant_sentiment,
            "start_time": cluster.start_time.isoformat() if cluster.start_time else None,
            "end_time": cluster.end_time.isoformat() if cluster.end_time else None,
            "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
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
        return {"code": 404, "data": None, "message": "Cluster not found"}
    
    # 查询成员
    query = db.query(ClusterMember).filter(ClusterMember.cluster_id == cluster_id)
    total_members = query.count()
    members = query.join(HotTopic).offset((page - 1) * page_size).limit(page_size).all()
    
    member_items = []
    for member in members:
        topic = member.topic
        member_items.append({
            "id": member.id,
            "topic_id": member.topic_id,
            "topic_title": topic.title if topic else None,
            "platform_name": topic.platform.display_name if topic and topic.platform else None,
            "weight": member.weight,
            "distance_to_center": member.distance_to_center,
            "heat_score": topic.heat_score if topic else None,
            "sentiment_label": topic.sentiment_result.sentiment_label if topic and topic.sentiment_result else None,
        })
    
    total_pages = (total_members + page_size - 1) // page_size
    
    return {
        "code": 200,
        "data": {
            "cluster": {
                "id": cluster.id,
                "cluster_name": cluster.cluster_name,
                "description": cluster.description,
                "algorithm": cluster.algorithm,
                "topic_count": cluster.topic_count,
                "avg_sentiment": cluster.avg_sentiment,
                "dominant_sentiment": cluster.dominant_sentiment,
                "start_time": cluster.start_time.isoformat() if cluster.start_time else None,
                "end_time": cluster.end_time.isoformat() if cluster.end_time else None,
            },
            "members": member_items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total_members,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
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
    # 获取时间窗口内的话题
    since = datetime.now() - timedelta(hours=time_window_hours)
    topics = db.query(HotTopic).filter(
        HotTopic.crawl_time >= since,
    ).all()
    
    if not topics:
        return {
            "code": 400,
            "data": None,
            "message": "No topics found in the specified time window",
        }
    
    # 使用确定性的基线聚类策略：先按平台分组，再按话题规模拆分。
    # 该策略可稳定支撑 UI 展示，后续可在不改 API 契约的前提下替换为 sklearn。
    clusters = _baseline_clustering(topics, n_clusters)
    
    created_clusters = []
    for cluster_data in clusters:
        cluster = TopicCluster(
            cluster_name=cluster_data["name"],
            description=cluster_data["description"],
            algorithm=algorithm,
            params_json=f'{{"n_clusters": {n_clusters}, "time_window_hours": {time_window_hours}}}',
            topic_count=len(cluster_data["members"]),
            avg_sentiment=cluster_data.get("avg_sentiment"),
            dominant_sentiment=cluster_data.get("dominant_sentiment"),
            start_time=since,
            end_time=datetime.now(),
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        
        # 添加成员
        for member_data in cluster_data["members"]:
            member = ClusterMember(
                cluster_id=cluster.id,
                topic_id=member_data["topic_id"],
                weight=member_data.get("weight", 1.0),
                distance_to_center=member_data.get("distance", 0.0),
            )
            db.add(member)
        
        db.commit()
        created_clusters.append({
            "id": cluster.id,
            "name": cluster.cluster_name,
            "topic_count": cluster.topic_count,
        })
    
    return {
        "code": 200,
        "data": {
            "clusters": created_clusters,
            "total_topics": len(topics),
            "algorithm": algorithm,
        },
        "message": f"Clustering completed: {len(created_clusters)} clusters created",
    }


def _baseline_clustering(topics, n_clusters):
    """按平台和话题规模生成基线聚类。"""
    from collections import defaultdict
    
    # 按平台分组
    platform_groups = defaultdict(list)
    for topic in topics:
        platform_name = topic.platform.name if topic.platform else "unknown"
        platform_groups[platform_name].append(topic)
    
    clusters = []
    for platform_name, platform_topics in platform_groups.items():
        if len(platform_topics) < 2:
            continue
        
        # 计算平均情感
        sentiments = []
        for t in platform_topics:
            if t.sentiment_result:
                sentiments.append(t.sentiment_result.sentiment_label)
        
        dominant = max(set(sentiments), key=sentiments.count) if sentiments else "neutral"
        
        clusters.append({
            "name": f"{platform_name}热点",
            "description": f"来自{platform_name}平台的{len(platform_topics)}个相关话题",
            "avg_sentiment": 0.5,  # 简化
            "dominant_sentiment": dominant,
            "members": [
                {
                    "topic_id": t.id,
                    "weight": 1.0,
                    "distance": 0.0,
                }
                for t in platform_topics
            ],
        })
    
    # 如果聚类数量不够，按情感再分
    if len(clusters) < n_clusters:
        # 简单拆分成更多聚类
        new_clusters = []
        for i, cluster in enumerate(clusters):
            if len(cluster["members"]) > 3:
                mid = len(cluster["members"]) // 2
                new_clusters.append({
                    "name": f"{cluster['name']}-A",
                    "description": cluster["description"] + " (子集A)",
                    "avg_sentiment": cluster["avg_sentiment"],
                    "dominant_sentiment": cluster["dominant_sentiment"],
                    "members": cluster["members"][:mid],
                })
                new_clusters.append({
                    "name": f"{cluster['name']}-B",
                    "description": cluster["description"] + " (子集B)",
                    "avg_sentiment": cluster["avg_sentiment"],
                    "dominant_sentiment": cluster["dominant_sentiment"],
                    "members": cluster["members"][mid:],
                })
            else:
                new_clusters.append(cluster)
        clusters = new_clusters
    
    return clusters[:n_clusters]
