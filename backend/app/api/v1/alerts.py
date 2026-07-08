"""
预警中心 API 路由

模块名称: alerts.py
模块职责: 预警规则管理、预警事件队列、预警处置
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.core.database import get_db
from app.models import AlertRule, AlertEvent, AlertAction, HotTopic
from app.schemas import UnifiedResponse
from app.services.alert_engine import AlertEngine

router = APIRouter()


# ========== 预警规则管理 ==========

@router.get("/rules", response_model=UnifiedResponse[dict])
async def list_alert_rules(
    is_active: bool = None,
    severity: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询预警规则列表"""
    query = db.query(AlertRule)
    
    if is_active is not None:
        query = query.filter(AlertRule.is_active == is_active)
    if severity:
        query = query.filter(AlertRule.severity == severity)
    
    total = query.count()
    rules = query.order_by(desc(AlertRule.created_at))
    rules = rules.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for rule in rules:
        items.append({
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "condition_type": rule.condition_type,
            "condition_expr": rule.condition_expr,
            "severity": rule.severity,
            "platform_scope": rule.platform_scope,
            "cooldown_minutes": rule.cooldown_minutes,
            "is_active": rule.is_active,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
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


@router.get("/rules/{rule_id}", response_model=UnifiedResponse[dict])
async def get_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
):
    """获取预警规则详情"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    return {
        "code": 200,
        "data": {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "condition_type": rule.condition_type,
            "condition_expr": rule.condition_expr,
            "severity": rule.severity,
            "platform_scope": rule.platform_scope,
            "cooldown_minutes": rule.cooldown_minutes,
            "is_active": rule.is_active,
            "created_at": rule.created_at.isoformat() if rule.created_at else None,
            "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
        },
        "message": "success",
    }


@router.post("/rules", response_model=UnifiedResponse[dict], status_code=201)
async def create_alert_rule(
    rule_data: dict,
    db: Session = Depends(get_db),
):
    """创建预警规则"""
    rule = AlertRule(
        name=rule_data.get("name"),
        description=rule_data.get("description"),
        condition_type=rule_data.get("condition_type"),
        condition_expr=rule_data.get("condition_expr"),
        severity=rule_data.get("severity", "P3"),
        platform_scope=rule_data.get("platform_scope", "all"),
        cooldown_minutes=rule_data.get("cooldown_minutes", 60),
        is_active=rule_data.get("is_active", True),
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {
        "code": 201,
        "data": {"id": rule.id, "name": rule.name},
        "message": "Alert rule created successfully",
    }


@router.put("/rules/{rule_id}", response_model=UnifiedResponse[dict])
async def update_alert_rule(
    rule_id: int,
    rule_data: dict,
    db: Session = Depends(get_db),
):
    """更新预警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    for key, value in rule_data.items():
        if hasattr(rule, key) and value is not None:
            setattr(rule, key, value)
    
    db.commit()
    db.refresh(rule)
    
    return {
        "code": 200,
        "data": {"id": rule.id, "name": rule.name},
        "message": "Alert rule updated successfully",
    }


@router.patch("/rules/{rule_id}", response_model=UnifiedResponse[dict])
async def patch_alert_rule(
    rule_id: int,
    rule_data: dict,
    db: Session = Depends(get_db),
):
    """部分更新预警规则（启停等）"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    for key, value in rule_data.items():
        if hasattr(rule, key):
            setattr(rule, key, value)
    
    db.commit()
    db.refresh(rule)
    
    return {
        "code": 200,
        "data": {"id": rule.id, "is_active": rule.is_active},
        "message": "Alert rule updated successfully",
    }


@router.delete("/rules/{rule_id}", response_model=UnifiedResponse[dict])
async def delete_alert_rule(
    rule_id: int,
    db: Session = Depends(get_db),
):
    """删除预警规则"""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    db.delete(rule)
    db.commit()
    
    return {
        "code": 200,
        "data": {"id": rule_id},
        "message": "Alert rule deleted successfully",
    }


# ========== 预警事件队列 ==========

@router.get("/events", response_model=UnifiedResponse[dict])
async def list_alert_events(
    status: str = None,
    severity: str = None,
    rule_id: int = None,
    start_time: datetime = None,
    end_time: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询预警事件列表（预警队列）"""
    query = db.query(AlertEvent).join(AlertRule)
    
    if status:
        query = query.filter(AlertEvent.status == status)
    if severity:
        query = query.filter(AlertEvent.severity == severity)
    if rule_id:
        query = query.filter(AlertEvent.rule_id == rule_id)
    if start_time:
        query = query.filter(AlertEvent.triggered_at >= start_time)
    if end_time:
        query = query.filter(AlertEvent.triggered_at <= end_time)
    
    total = query.count()
    events = query.order_by(desc(AlertEvent.triggered_at))
    events = events.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for event in events:
        items.append({
            "id": event.id,
            "rule_id": event.rule_id,
            "rule_name": event.rule.name if event.rule else None,
            "topic_id": event.topic_id,
            "topic_title": event.topic.title if event.topic else None,
            "severity": event.severity,
            "status": event.status,
            "trigger_payload": event.trigger_payload,
            "triggered_at": event.triggered_at.isoformat() if event.triggered_at else None,
            "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None,
            "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
            "created_at": event.created_at.isoformat() if event.created_at else None,
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


@router.get("/events/{event_id}", response_model=UnifiedResponse[dict])
async def get_alert_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    """获取预警事件详情"""
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")
    
    # 获取处置记录
    actions = []
    for action in event.actions:
        actions.append({
            "id": action.id,
            "action_type": action.action_type,
            "operator": action.operator,
            "note": action.note,
            "created_at": action.created_at.isoformat() if action.created_at else None,
        })
    
    return {
        "code": 200,
        "data": {
            "id": event.id,
            "rule_id": event.rule_id,
            "rule_name": event.rule.name if event.rule else None,
            "topic_id": event.topic_id,
            "topic_title": event.topic.title if event.topic else None,
            "severity": event.severity,
            "status": event.status,
            "trigger_payload": event.trigger_payload,
            "triggered_at": event.triggered_at.isoformat() if event.triggered_at else None,
            "acknowledged_at": event.acknowledged_at.isoformat() if event.acknowledged_at else None,
            "resolved_at": event.resolved_at.isoformat() if event.resolved_at else None,
            "actions": actions,
        },
        "message": "success",
    }


# ========== 预警处置 ==========

@router.post("/events/{event_id}/ack", response_model=UnifiedResponse[dict])
async def acknowledge_alert(
    event_id: int,
    note: str = "",
    db: Session = Depends(get_db),
):
    """确认预警事件"""
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")
    
    event.status = "acknowledged"
    event.acknowledged_at = datetime.now()
    
    # 记录处置操作
    action = AlertAction(
        event_id=event_id,
        action_type="acknowledge",
        operator="user",
        note=note,
    )
    db.add(action)
    db.commit()
    
    return {
        "code": 200,
        "data": {"id": event_id, "status": "acknowledged"},
        "message": "Alert acknowledged",
    }


@router.post("/events/{event_id}/resolve", response_model=UnifiedResponse[dict])
async def resolve_alert(
    event_id: int,
    note: str = "",
    db: Session = Depends(get_db),
):
    """解决预警事件"""
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")
    
    event.status = "resolved"
    event.resolved_at = datetime.now()
    
    action = AlertAction(
        event_id=event_id,
        action_type="resolve",
        operator="user",
        note=note,
    )
    db.add(action)
    db.commit()
    
    return {
        "code": 200,
        "data": {"id": event_id, "status": "resolved"},
        "message": "Alert resolved",
    }


@router.post("/events/{event_id}/ignore", response_model=UnifiedResponse[dict])
async def ignore_alert(
    event_id: int,
    note: str = "",
    db: Session = Depends(get_db),
):
    """忽略预警事件"""
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")
    
    event.status = "ignored"
    event.resolved_at = datetime.now()
    
    action = AlertAction(
        event_id=event_id,
        action_type="ignore",
        operator="user",
        note=note,
    )
    db.add(action)
    db.commit()
    
    return {
        "code": 200,
        "data": {"id": event_id, "status": "ignored"},
        "message": "Alert ignored",
    }


# ========== 预警统计摘要 ==========

@router.get("/summary", response_model=UnifiedResponse[dict])
async def get_alert_summary(
    db: Session = Depends(get_db),
):
    """
    获取预警统计摘要
    
    用于 Dashboard 预警摘要卡片
    """
    # 未处理预警数
    pending_count = db.query(AlertEvent).filter(AlertEvent.status == "pending").count()
    
    # 各严重程度分布
    severity_dist = db.query(
        AlertEvent.severity,
        func.count(AlertEvent.id).label("count"),
    ).filter(AlertEvent.status == "pending").group_by(AlertEvent.severity).all()
    
    severity_dict = {s.severity: s.count for s in severity_dist}
    
    # 最高级别
    max_severity = None
    if severity_dict:
        severity_order = {"P1": 4, "P2": 3, "P3": 2, "P4": 1}
        max_severity = max(severity_dict.keys(), key=lambda x: severity_order.get(x, 0))
    
    # 最近预警
    latest_alert = db.query(AlertEvent).order_by(desc(AlertEvent.triggered_at)).first()
    
    # 今日新增
    today = datetime.now().date()
    today_count = db.query(AlertEvent).filter(
        func.date(AlertEvent.triggered_at) == today
    ).count()
    
    return {
        "code": 200,
        "data": {
            "pending_count": pending_count,
            "severity_distribution": severity_dict,
            "max_severity": max_severity,
            "today_count": today_count,
            "latest_alert": {
                "id": latest_alert.id,
                "severity": latest_alert.severity,
                "triggered_at": latest_alert.triggered_at.isoformat() if latest_alert else None,
            } if latest_alert else None,
        },
        "message": "success",
    }


# ========== 预警引擎触发 ==========

@router.post("/evaluate", response_model=UnifiedResponse[dict])
async def evaluate_alert_rules(
    rule_ids: list = None,
    db: Session = Depends(get_db),
):
    """
    手动触发预警规则评估
    
    Args:
        rule_ids: 指定要评估的规则 ID 列表，None 则评估所有启用规则
    """
    engine = AlertEngine(db)
    result = engine.evaluate_all_rules()
    
    return {
        "code": 200,
        "data": result,
        "message": f"Evaluation completed: {result['triggered']} triggered, {result['skipped']} skipped, {result['errors']} errors",
    }


@router.get("/pending-summary", response_model=UnifiedResponse[dict])
async def get_pending_alert_summary(
    db: Session = Depends(get_db),
):
    """获取待处理预警详细摘要"""
    engine = AlertEngine(db)
    summary = engine.get_pending_alerts_summary()
    
    return {
        "code": 200,
        "data": summary,
        "message": "success",
    }
