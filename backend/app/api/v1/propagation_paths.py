"""
高级分析 API 路由 - 传播路径分析

模块名称: propagation_paths.py
模块职责: 话题传播链路追踪、跨平台传播分析 API
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import HotTopic, PropagationPath, PropagationNode, Platform
from app.schemas import UnifiedResponse

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
    
    items = []
    for path in paths:
        root_topic = path.root_topic
        items.append({
            "id": path.id,
            "root_topic_id": path.root_topic_id,
            "root_topic_title": root_topic.title if root_topic else None,
            "depth": path.depth,
            "total_nodes": path.total_nodes,
            "max_breadth": path.max_breadth,
            "platforms_involved": path.platforms_involved,
            "platform_transitions": path.platform_transitions,
            "first_seen_at": path.first_seen_at.isoformat() if path.first_seen_at else None,
            "last_seen_at": path.last_seen_at.isoformat() if path.last_seen_at else None,
            "created_at": path.created_at.isoformat() if path.created_at else None,
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


@router.get("/{path_id}", response_model=UnifiedResponse[dict])
async def get_propagation_path(
    path_id: int,
    db: Session = Depends(get_db),
):
    """获取传播路径详情（树形结构）"""
    path = db.query(PropagationPath).filter(PropagationPath.id == path_id).first()
    if not path:
        return {"code": 404, "data": None, "message": "Propagation path not found"}
    
    # 获取所有节点
    nodes = db.query(PropagationNode).filter(
        PropagationNode.path_id == path_id,
    ).all()
    
    # 构建树形结构
    node_map = {}
    root_nodes = []
    
    for node in nodes:
        node_data = {
            "id": node.id,
            "topic_id": node.topic_id,
            "topic_title": node.topic.title if node.topic else None,
            "platform_name": node.platform.display_name if node.platform else None,
            "level": node.level,
            "heat_score": node.heat_score,
            "sentiment_label": node.sentiment_label,
            "influence_score": node.influence_score,
            "discovered_at": node.discovered_at.isoformat() if node.discovered_at else None,
            "children": [],
        }
        node_map[node.id] = node_data
    
    # 构建父子关系
    for node in nodes:
        node_data = node_map[node.id]
        if node.parent_node_id and node.parent_node_id in node_map:
            parent = node_map[node.parent_node_id]
            parent["children"].append(node_data)
        else:
            root_nodes.append(node_data)
    
    return {
        "code": 200,
        "data": {
            "path": {
                "id": path.id,
                "root_topic_id": path.root_topic_id,
                "root_topic_title": path.root_topic.title if path.root_topic else None,
                "depth": path.depth,
                "total_nodes": path.total_nodes,
                "max_breadth": path.max_breadth,
                "platforms_involved": path.platforms_involved,
                "platform_transitions": path.platform_transitions,
                "first_seen_at": path.first_seen_at.isoformat() if path.first_seen_at else None,
                "last_seen_at": path.last_seen_at.isoformat() if path.last_seen_at else None,
            },
            "tree": root_nodes,
        },
        "message": "success",
    }


@router.post("/analyze/{topic_id}", response_model=UnifiedResponse[dict])
async def analyze_propagation(
    topic_id: int,
    time_window_hours: int = 24,
    db: Session = Depends(get_db),
):
    """
    分析话题传播路径
    
    Args:
        topic_id: 根话题ID
        time_window_hours: 时间窗口(小时)
    """
    # 检查话题是否存在
    root_topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not root_topic:
        return {"code": 404, "data": None, "message": "Topic not found"}
    
    # 获取时间窗口内相似话题（模拟传播路径）
    since = datetime.now() - timedelta(hours=time_window_hours)
    
    # 查找相同话题ID或相似标题的话题
    related_topics = db.query(HotTopic).filter(
        HotTopic.crawl_time >= since,
        HotTopic.id != topic_id,
    ).all()
    
    # 模拟传播：按平台和时间排序
    platform_order = {}
    for t in related_topics:
        platform_name = t.platform.name if t.platform else "unknown"
        if platform_name not in platform_order:
            platform_order[platform_name] = []
        platform_order[platform_name].append(t)
    
    # 创建传播路径
    path = PropagationPath(
        root_topic_id=topic_id,
        depth=min(len(platform_order), 3),
        total_nodes=len(related_topics) + 1,
        max_breadth=max(len(v) for v in platform_order.values()) if platform_order else 0,
        platforms_involved=str(list(platform_order.keys())),
        platform_transitions=len(platform_order) - 1 if len(platform_order) > 1 else 0,
        first_seen_at=root_topic.crawl_time,
        last_seen_at=max((t.crawl_time for t in related_topics), default=root_topic.crawl_time),
    )
    db.add(path)
    db.commit()
    db.refresh(path)
    
    # 创建根节点
    root_node = PropagationNode(
        path_id=path.id,
        topic_id=topic_id,
        level=0,
        platform_id=root_topic.platform_id,
        heat_score=root_topic.heat_score,
        sentiment_label=root_topic.sentiment_result.sentiment_label if root_topic.sentiment_result else None,
        influence_score=100.0,  # 根节点默认最高影响力
        discovered_at=root_topic.crawl_time,
    )
    db.add(root_node)
    db.commit()
    db.refresh(root_node)
    
    # 创建子节点（按平台分组）
    level = 1
    parent_id = root_node.id
    for platform_name, topics in platform_order.items():
        for topic in topics[:5]:  # 每平台最多5个
            node = PropagationNode(
                path_id=path.id,
                topic_id=topic.id,
                level=level,
                parent_node_id=parent_id,
                platform_id=topic.platform_id,
                heat_score=topic.heat_score,
                sentiment_label=topic.sentiment_result.sentiment_label if topic.sentiment_result else None,
                influence_score=max(0, 100.0 - level * 20),  # 影响力逐层递减
                discovered_at=topic.crawl_time,
            )
            db.add(node)
        level += 1
        # 更新父节点为最后一个节点
        last_node = db.query(PropagationNode).filter(
            PropagationNode.path_id == path.id,
        ).order_by(desc(PropagationNode.id)).first()
        if last_node:
            parent_id = last_node.id
    
    db.commit()
    
    return {
        "code": 200,
        "data": {
            "path_id": path.id,
            "root_topic_id": topic_id,
            "root_topic_title": root_topic.title,
            "depth": path.depth,
            "total_nodes": path.total_nodes,
            "platforms_involved": list(platform_order.keys()),
            "platform_transitions": path.platform_transitions,
        },
        "message": "Propagation analysis completed",
    }
