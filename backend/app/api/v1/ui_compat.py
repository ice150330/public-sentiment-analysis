"""
UI contract compatibility API routes.

These routes map UI.pen-era endpoint names onto the current backend models and
services. They return real database-derived data and normalize operational
state for the current UI.
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import (
    AlertAction,
    AlertEvent,
    AlertRule,
    AuditLog,
    ClusterMember,
    CrawlLog,
    CrawlerTask,
    CrawlerTaskEvent,
    DataArchiveRun,
    HotTopic,
    ModelExplanation,
    ModelVersion,
    Platform,
    PropagationNode,
    PropagationPath,
    SentimentResult,
    SentimentJob,
    SystemLog,
    TopicCluster,
    TopicRelation,
    TopicSample,
)
from app.schemas import UnifiedResponse
from app.services.data_quality_service import DataQualityService
from app.services.sentiment_service import SentimentService
from app.services.task_state_service import expire_stale_crawler_tasks
from app.services.trend_forecast_service import TrendForecastService

router = APIRouter()
trend_forecast_service = TrendForecastService()


def _pagination(page: int, page_size: int, total: int) -> dict:
    total_pages = (total + page_size - 1) // page_size
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


def _platform_monitoring_matrix(db: Session) -> dict:
    platforms = db.query(Platform).filter(Platform.is_active == True).order_by(Platform.sort_order).all()
    last_24h = datetime.now() - timedelta(hours=24)
    matrix = []

    for platform in platforms:
        last_log = db.query(CrawlLog).filter(
            CrawlLog.platform_id == platform.id
        ).order_by(desc(CrawlLog.completed_at)).first()
        topic_count = db.query(HotTopic).filter(
            HotTopic.platform_id == platform.id,
            HotTopic.crawl_time >= last_24h,
        ).count()
        avg_heat = db.query(func.avg(HotTopic.heat_score)).filter(
            HotTopic.platform_id == platform.id,
            HotTopic.crawl_time >= last_24h,
        ).scalar()
        negative_count = db.query(HotTopic).join(SentimentResult).filter(
            HotTopic.platform_id == platform.id,
            HotTopic.crawl_time >= last_24h,
            SentimentResult.sentiment_label == "negative",
        ).count()
        delay_minutes = None
        if last_log and last_log.completed_at:
            delay_minutes = int((datetime.now() - last_log.completed_at).total_seconds() / 60)

        status = "healthy"
        if not last_log:
            status = "never"
        elif last_log.status == "failed":
            status = "error"
        elif delay_minutes is not None and delay_minutes > 120:
            status = "stale"

        matrix.append({
            "platform_id": platform.id,
            "platform_name": platform.name,
            "display_name": platform.display_name,
            "topic_count": topic_count,
            "avg_heat": round(avg_heat, 2) if avg_heat else 0,
            "negative_ratio": round(negative_count * 100 / topic_count, 2) if topic_count else 0,
            "delay_minutes": delay_minutes,
            "last_crawl": last_log.completed_at.isoformat() if last_log and last_log.completed_at else None,
            "status": status,
            "is_healthy": status == "healthy",
        })

    return {
        "matrix": matrix,
        "total_platforms": len(matrix),
        "healthy_count": sum(1 for item in matrix if item["is_healthy"]),
    }


def _data_freshness(db: Session) -> dict:
    platforms = db.query(Platform).filter(Platform.is_active == True).order_by(Platform.sort_order).all()
    freshness = []

    for platform in platforms:
        latest_topic = db.query(HotTopic).filter(
            HotTopic.platform_id == platform.id
        ).order_by(desc(HotTopic.crawl_time)).first()
        latest_log = db.query(CrawlLog).filter(
            CrawlLog.platform_id == platform.id
        ).order_by(desc(CrawlLog.completed_at)).first()

        delay_minutes = None
        if latest_topic and latest_topic.crawl_time:
            delay_minutes = int((datetime.now() - latest_topic.crawl_time).total_seconds() / 60)

        gap_status = "normal"
        if not latest_topic:
            gap_status = "missing"
        elif delay_minutes is not None and delay_minutes > 180:
            gap_status = "critical"
        elif delay_minutes is not None and delay_minutes > 60:
            gap_status = "warning"

        freshness.append({
            "platform_id": platform.id,
            "platform_name": platform.name,
            "display_name": platform.display_name,
            "latest_topic_time": latest_topic.crawl_time.isoformat() if latest_topic else None,
            "latest_crawl_time": latest_log.completed_at.isoformat() if latest_log and latest_log.completed_at else None,
            "delay_minutes": delay_minutes,
            "gap_status": gap_status,
            "has_data": latest_topic is not None,
        })

    return {
        "freshness": freshness,
        "overall_status": (
            "critical" if any(item["gap_status"] == "critical" for item in freshness)
            else "warning" if any(item["gap_status"] == "warning" for item in freshness)
            else "normal"
        ),
    }


def _alert_event_payload(event: AlertEvent, include_actions: bool = False) -> dict:
    item = {
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
    }
    if include_actions:
        item["actions"] = [
            {
                "id": action.id,
                "action_type": action.action_type,
                "operator": action.operator,
                "note": action.note,
                "created_at": action.created_at.isoformat() if action.created_at else None,
            }
            for action in event.actions
        ]
    return item


def _rule_payload(rule: AlertRule) -> dict:
    return {
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
    }


def _sentiment_numeric(label: Optional[str]) -> float:
    return {"positive": 1.0, "neutral": 0.0, "negative": -1.0}.get(label or "", 0.0)


def _keywords_from_topics(topics: list[HotTopic], limit: int) -> list[dict]:
    counter: Counter[str] = Counter()
    stopwords = {"一个", "这个", "什么", "怎么", "为何", "如何", "今天", "最新", "话题"}

    for topic in topics:
        text = f"{topic.title or ''} {topic.category or ''}"
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", text)
        for token in tokens:
            if token not in stopwords:
                counter[token] += 1

    return [
        {"keyword": keyword, "count": count, "weight": count}
        for keyword, count in counter.most_common(limit)
    ]


def _topic_sample_items(query) -> list[dict]:
    return [
        {
            "id": sample.id,
            "platform_name": sample.platform.display_name if sample.platform else None,
            "sample_type": sample.sample_type,
            "content": sample.content,
            "sentiment_label": sample.sentiment_label,
            "confidence": sample.confidence,
            "source_url": sample.source_url,
            "author": sample.author,
            "created_at": sample.created_at.isoformat() if sample.created_at else None,
        }
        for sample in query
    ]


def _crawler_task_payload(task: CrawlerTask, include_events: bool = False) -> dict:
    item = {
        "id": task.id,
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "platforms": json.loads(task.platforms_json or "[]"),
        "results": json.loads(task.result_json or "{}") if task.result_json else None,
        "error_message": task.error_message,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }
    if include_events:
        item["events"] = [
            {
                "id": event.id,
                "event_type": event.event_type,
                "message": event.message,
                "payload_json": event.payload_json,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in sorted(task.events, key=lambda event: event.created_at or datetime.min)
        ]
    return item


def _sentiment_job_payload(job: SentimentJob) -> dict:
    return {
        "id": job.id,
        "job_id": job.job_id,
        "status": job.status,
        "total_count": job.total_count,
        "success_count": job.success_count,
        "failed_count": job.failed_count,
        "avg_latency_ms": job.avg_latency_ms,
        "payload": json.loads(job.payload_json or "{}") if job.payload_json else None,
        "results": json.loads(job.result_json or "[]") if job.result_json else None,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


def _active_sync_state(db: Session) -> dict:
    expire_stale_crawler_tasks(db)

    active_statuses = ["queued", "running", "paused", "retry_queued"]
    active_task = db.query(CrawlerTask).filter(
        CrawlerTask.status.in_(active_statuses)
    ).order_by(desc(CrawlerTask.created_at)).first()
    queue_length = db.query(CrawlerTask).filter(
        CrawlerTask.status.in_(["queued", "retry_queued"])
    ).count()

    return {
        "is_syncing": bool(active_task and active_task.status in {"queued", "running", "retry_queued"}),
        "queue_length": queue_length,
        "active_task": _crawler_task_payload(active_task) if active_task else None,
    }


@router.get("/api/v1/sync/status", response_model=UnifiedResponse[dict])
async def get_sync_status(db: Session = Depends(get_db)):
    last_topic = db.query(HotTopic).order_by(desc(HotTopic.crawl_time)).first()
    last_sentiment = db.query(SentimentResult).order_by(desc(SentimentResult.analyzed_at)).first()
    last_crawl = db.query(CrawlLog).order_by(desc(CrawlLog.completed_at)).first()
    last_updated = last_crawl.completed_at if last_crawl and last_crawl.completed_at else None
    sync_state = _active_sync_state(db)

    return {
        "code": 200,
        "data": {
            "last_updated": last_updated.isoformat() if last_updated else None,
            "sync_delay_seconds": int((datetime.now() - last_updated).total_seconds()) if last_updated else None,
            "is_syncing": sync_state["is_syncing"],
            "active_task": sync_state["active_task"],
            "queue_length": sync_state["queue_length"],
            "modules": {
                "hot_topics": {
                    "last_updated": last_topic.crawl_time.isoformat() if last_topic else None,
                    "count": db.query(HotTopic).count(),
                },
                "sentiment": {
                    "last_updated": last_sentiment.analyzed_at.isoformat() if last_sentiment else None,
                    "count": db.query(SentimentResult).count(),
                },
                "crawler": {
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "today_count": db.query(CrawlLog).filter(
                        func.date(CrawlLog.started_at) == datetime.now().date()
                    ).count(),
                },
            },
        },
        "message": "success",
    }


@router.get("/api/v1/search", response_model=UnifiedResponse[dict])
async def global_search(
    q: str = Query("", description="Search keyword"),
    scope: str = Query("all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    keyword = q.strip()
    results = []

    if scope in {"all", "topics"}:
        query = db.query(HotTopic).join(Platform)
        if keyword:
            query = query.filter(HotTopic.title.contains(keyword))
        total = query.count()
        topics = query.order_by(desc(HotTopic.crawl_time)).offset((page - 1) * page_size).limit(page_size).all()
        for topic in topics:
            results.append({
                "type": "topic",
                "id": topic.id,
                "title": topic.title,
                "summary": topic.content_summary,
                "platform_name": topic.platform.display_name if topic.platform else None,
                "url": topic.url,
                "created_at": topic.created_at.isoformat() if topic.created_at else None,
            })
        pagination = _pagination(page, page_size, total)
    else:
        pagination = _pagination(page, page_size, 0)

    return {
        "code": 200,
        "data": {
            "query": keyword,
            "scope": scope,
            "items": results,
            "pagination": pagination,
        },
        "message": "success",
    }


@router.get("/api/v1/dashboard/overview", response_model=UnifiedResponse[dict])
async def dashboard_overview(db: Session = Depends(get_db)):
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    today_topics = db.query(HotTopic).filter(func.date(HotTopic.crawl_time) == today).count()
    yesterday_topics = db.query(HotTopic).filter(func.date(HotTopic.crawl_time) == yesterday).count()
    active_platforms = db.query(Platform).filter(Platform.is_active == True).count()
    sentiment_counts = dict(
        db.query(SentimentResult.sentiment_label, func.count(SentimentResult.id)).group_by(
            SentimentResult.sentiment_label
        ).all()
    )
    today_logs = db.query(CrawlLog).filter(func.date(CrawlLog.started_at) == today).all()
    success_count = sum(1 for log in today_logs if log.status == "success")
    last_log = db.query(CrawlLog).order_by(desc(CrawlLog.started_at)).first()

    return {
        "code": 200,
        "data": {
            "today": {
                "total_topics": today_topics,
                "active_platforms": active_platforms,
                "sentiment_distribution": sentiment_counts,
                "negative_ratio": round(sentiment_counts.get("negative", 0) * 100 / max(1, sum(sentiment_counts.values())), 2),
            },
            "deltas": {
                "topics_vs_yesterday": today_topics - yesterday_topics,
                "topics_change_rate": round((today_topics - yesterday_topics) * 100 / yesterday_topics, 2) if yesterday_topics else 0,
            },
            "crawler": {
                "last_run": last_log.started_at.isoformat() if last_log else None,
                "today_success_rate": round(success_count * 100 / len(today_logs), 2) if today_logs else 0,
            },
            "sentiment": {
                "total_analyzed": db.query(SentimentResult).count(),
                "total_analyzed_today": db.query(SentimentResult).filter(func.date(SentimentResult.analyzed_at) == today).count(),
            },
            "last_updated": datetime.now().isoformat(),
        },
        "message": "success",
    }


@router.get("/api/v1/stats/platform-matrix", response_model=UnifiedResponse[dict])
async def stats_platform_matrix(db: Session = Depends(get_db)):
    return {"code": 200, "data": _platform_monitoring_matrix(db), "message": "success"}


@router.get("/api/v1/data-quality/freshness", response_model=UnifiedResponse[dict])
async def data_quality_freshness(db: Session = Depends(get_db)):
    return {"code": 200, "data": _data_freshness(db), "message": "success"}


@router.get("/api/v1/alerts", response_model=UnifiedResponse[dict])
async def list_alerts_alias(
    status: str = None,
    severity: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(AlertEvent).join(AlertRule)
    if status:
        query = query.filter(AlertEvent.status == status)
    if severity:
        query = query.filter(AlertEvent.severity == severity)
    total = query.count()
    events = query.order_by(desc(AlertEvent.triggered_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 200,
        "data": {"items": [_alert_event_payload(event) for event in events], "pagination": _pagination(page, page_size, total)},
        "message": "success",
    }


@router.get("/api/v1/alerts/{event_id:int}", response_model=UnifiedResponse[dict])
async def get_alert_alias(event_id: int, db: Session = Depends(get_db)):
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")
    return {"code": 200, "data": _alert_event_payload(event, include_actions=True), "message": "success"}


@router.get("/api/v1/alerts/{event_id:int}/actions", response_model=UnifiedResponse[dict])
async def get_alert_actions_alias(event_id: int, db: Session = Depends(get_db)):
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")
    actions = [
        {
            "id": action.id,
            "action_type": action.action_type,
            "operator": action.operator,
            "note": action.note,
            "created_at": action.created_at.isoformat() if action.created_at else None,
        }
        for action in event.actions
    ]
    return {"code": 200, "data": {"items": actions, "total": len(actions)}, "message": "success"}


def _apply_alert_action(db: Session, event_id: int, action_type: str, note: str = "") -> dict:
    event = db.query(AlertEvent).filter(AlertEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Alert event not found")
    if action_type == "acknowledge":
        event.status = "acknowledged"
        event.acknowledged_at = datetime.now()
    elif action_type == "resolve":
        event.status = "resolved"
        event.resolved_at = datetime.now()

    db.add(AlertAction(event_id=event_id, action_type=action_type, operator="user", note=note))
    db.commit()
    return {"id": event_id, "status": event.status}


@router.post("/api/v1/alerts/{event_id:int}/ack", response_model=UnifiedResponse[dict])
async def acknowledge_alert_alias(event_id: int, payload: dict | None = None, db: Session = Depends(get_db)):
    return {"code": 200, "data": _apply_alert_action(db, event_id, "acknowledge", (payload or {}).get("note", "")), "message": "Alert acknowledged"}


@router.post("/api/v1/alerts/{event_id:int}/resolve", response_model=UnifiedResponse[dict])
async def resolve_alert_alias(event_id: int, payload: dict | None = None, db: Session = Depends(get_db)):
    return {"code": 200, "data": _apply_alert_action(db, event_id, "resolve", (payload or {}).get("note", "")), "message": "Alert resolved"}


@router.get("/api/v1/alert-rules", response_model=UnifiedResponse[dict])
async def list_alert_rules_alias(
    is_active: bool = None,
    severity: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(AlertRule)
    if is_active is not None:
        query = query.filter(AlertRule.is_active == is_active)
    if severity:
        query = query.filter(AlertRule.severity == severity)
    total = query.count()
    rules = query.order_by(desc(AlertRule.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 200, "data": {"items": [_rule_payload(rule) for rule in rules], "pagination": _pagination(page, page_size, total)}, "message": "success"}


@router.post("/api/v1/alert-rules", response_model=UnifiedResponse[dict], status_code=201)
async def create_alert_rule_alias(rule_data: dict, db: Session = Depends(get_db)):
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
    return {"code": 201, "data": {"id": rule.id, "name": rule.name}, "message": "Alert rule created successfully"}


@router.get("/api/v1/alert-rules/{rule_id:int}", response_model=UnifiedResponse[dict])
async def get_alert_rule_alias(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return {"code": 200, "data": _rule_payload(rule), "message": "success"}


@router.put("/api/v1/alert-rules/{rule_id:int}", response_model=UnifiedResponse[dict])
async def update_alert_rule_alias(rule_id: int, rule_data: dict, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    for key, value in rule_data.items():
        if hasattr(rule, key) and value is not None:
            setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return {"code": 200, "data": {"id": rule.id, "name": rule.name}, "message": "Alert rule updated successfully"}


@router.patch("/api/v1/alert-rules/{rule_id:int}", response_model=UnifiedResponse[dict])
async def patch_alert_rule_alias(rule_id: int, rule_data: dict, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    for key, value in rule_data.items():
        if hasattr(rule, key):
            setattr(rule, key, value)
    db.commit()
    db.refresh(rule)
    return {"code": 200, "data": {"id": rule.id, "is_active": rule.is_active}, "message": "Alert rule updated successfully"}


@router.delete("/api/v1/alert-rules/{rule_id:int}", response_model=UnifiedResponse[dict])
async def delete_alert_rule_alias(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    db.delete(rule)
    db.commit()
    return {"code": 200, "data": {"id": rule_id}, "message": "Alert rule deleted successfully"}


@router.post("/api/v1/alert-rules/{rule_id:int}/simulate", response_model=UnifiedResponse[dict])
async def simulate_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    sample_count = db.query(HotTopic).count()
    try:
        condition = json.loads(rule.condition_expr or "{}")
    except json.JSONDecodeError:
        condition = {}

    field = condition.get("field") or condition.get("metric") or rule.condition_type
    operator = condition.get("operator", ">")
    threshold = condition.get("value", condition.get("threshold", 0))
    matched_count = 0

    if field in {"heat_score", "heat_spike"}:
        query = db.query(HotTopic)
        if operator in {">", "gt"}:
            query = query.filter(HotTopic.heat_score > threshold)
        elif operator in {">=", "gte"}:
            query = query.filter(HotTopic.heat_score >= threshold)
        elif operator in {"<", "lt"}:
            query = query.filter(HotTopic.heat_score < threshold)
        elif operator in {"<=", "lte"}:
            query = query.filter(HotTopic.heat_score <= threshold)
        else:
            query = query.filter(HotTopic.heat_score == threshold)
        matched_count = query.count()
    elif field in {"negative_ratio", "negative_sentiment"}:
        negative_topics = db.query(HotTopic).join(SentimentResult).filter(
            SentimentResult.sentiment_label == "negative"
        ).count()
        ratio = negative_topics * 100 / sample_count if sample_count else 0
        matched_count = negative_topics if ratio >= float(threshold or 0) else 0

    false_positive_rate = round(max(0, matched_count - sample_count * 0.1) * 100 / max(1, matched_count), 2) if matched_count else 0
    return {
        "code": 200,
        "data": {
            "rule_id": rule_id,
            "sample_count": sample_count,
            "matched_count": matched_count,
            "estimated_false_positive_rate": false_positive_rate,
            "condition": {
                "field": field,
                "operator": operator,
                "threshold": threshold,
            },
        },
        "message": "success",
    }


@router.get("/api/v1/alert-rules/{rule_id:int}/history", response_model=UnifiedResponse[dict])
async def get_alert_rule_history(
    rule_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(AlertEvent).filter(AlertEvent.rule_id == rule_id)
    total = query.count()
    events = query.order_by(desc(AlertEvent.triggered_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {"code": 200, "data": {"items": [_alert_event_payload(event) for event in events], "pagination": _pagination(page, page_size, total)}, "message": "success"}


@router.get("/api/v1/topics/facets", response_model=UnifiedResponse[dict])
async def topic_facets_alias(db: Session = Depends(get_db)):
    categories = db.query(HotTopic.category, func.count(HotTopic.id)).group_by(HotTopic.category).all()
    platforms = db.query(Platform.name, Platform.display_name, func.count(HotTopic.id)).select_from(Platform).join(
        HotTopic, HotTopic.platform_id == Platform.id
    ).group_by(Platform.id, Platform.name, Platform.display_name).all()
    return {
        "code": 200,
        "data": {
            "categories": [{"name": category or "未分类", "count": count} for category, count in categories],
            "platforms": [{"name": name, "display_name": display_name, "count": count} for name, display_name, count in platforms],
            "total": db.query(HotTopic).count(),
        },
        "message": "success",
    }


@router.get("/api/v1/topics/keywords/cloud", response_model=UnifiedResponse[dict])
async def topic_keywords_cloud(
    limit: int = Query(50, ge=1, le=200),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    since = datetime.now() - timedelta(days=days)
    topics = db.query(HotTopic).filter(HotTopic.crawl_time >= since).all()
    return {"code": 200, "data": {"period": f"最近 {days} 天", "keywords": _keywords_from_topics(topics, limit)}, "message": "success"}


@router.get("/api/v1/topics/clusters", response_model=UnifiedResponse[dict])
async def topic_clusters_alias(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(TopicCluster).count()
    if total:
        clusters = db.query(TopicCluster).order_by(desc(TopicCluster.topic_count)).offset((page - 1) * page_size).limit(page_size).all()
        items = [
            {
                "id": cluster.id,
                "cluster_name": cluster.cluster_name,
                "description": cluster.description,
                "algorithm": cluster.algorithm,
                "topic_count": cluster.topic_count,
                "dominant_sentiment": cluster.dominant_sentiment,
                "created_at": cluster.created_at.isoformat() if cluster.created_at else None,
            }
            for cluster in clusters
        ]
    else:
        grouped = db.query(HotTopic.category, func.count(HotTopic.id), func.sum(HotTopic.heat_score)).group_by(HotTopic.category).all()
        items = [
            {
                "id": index + 1,
                "cluster_name": category or "未分类",
                "description": "按分类字段生成的轻量主题簇",
                "algorithm": "category-facet",
                "topic_count": count,
                "total_heat": total_heat or 0,
                "dominant_sentiment": None,
            }
            for index, (category, count, total_heat) in enumerate(grouped)
        ][(page - 1) * page_size: page * page_size]
        total = len(grouped)

    return {"code": 200, "data": {"items": items, "pagination": _pagination(page, page_size, total)}, "message": "success"}


@router.get("/api/v1/topics/clusters/{cluster_id:int}/keywords", response_model=UnifiedResponse[dict])
async def topic_cluster_keywords(cluster_id: int, db: Session = Depends(get_db)):
    cluster = db.query(TopicCluster).filter(TopicCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    topics = [member.topic for member in cluster.members if member.topic]
    return {"code": 200, "data": {"cluster_id": cluster_id, "keywords": _keywords_from_topics(topics, 30)}, "message": "success"}


@router.get("/api/v1/topics/clusters/{cluster_id:int}/topics", response_model=UnifiedResponse[dict])
async def topic_cluster_topics(
    cluster_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    cluster = db.query(TopicCluster).filter(TopicCluster.id == cluster_id).first()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    query = db.query(ClusterMember).filter(ClusterMember.cluster_id == cluster_id)
    total = query.count()
    members = query.offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "topic_id": member.topic_id,
            "topic_title": member.topic.title if member.topic else None,
            "weight": member.weight,
            "distance_to_center": member.distance_to_center,
        }
        for member in members
    ]
    return {"code": 200, "data": {"items": items, "pagination": _pagination(page, page_size, total)}, "message": "success"}


@router.get("/api/v1/topics/{topic_id:int}/samples", response_model=UnifiedResponse[dict])
async def topic_samples_alias(
    topic_id: int,
    platform: str = None,
    sample_type: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    query = db.query(TopicSample).join(Platform, isouter=True).filter(TopicSample.topic_id == topic_id)
    if platform:
        query = query.filter(Platform.name == platform)
    if sample_type:
        query = query.filter(TopicSample.sample_type == sample_type)
    total = query.count()
    samples = query.order_by(desc(TopicSample.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 200,
        "data": {
            "topic_id": topic_id,
            "topic_title": topic.title,
            "items": _topic_sample_items(samples),
            "pagination": _pagination(page, page_size, total),
        },
        "message": "success",
    }


@router.get("/api/v1/topics/{topic_id:int}/related", response_model=UnifiedResponse[dict])
async def related_topics_alias(topic_id: int, relation_type: str = None, db: Session = Depends(get_db)):
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    query = db.query(TopicRelation).filter(TopicRelation.source_topic_id == topic_id)
    if relation_type:
        query = query.filter(TopicRelation.relation_type == relation_type)
    relations = query.order_by(desc(TopicRelation.score)).all()
    return {
        "code": 200,
        "data": {
            "topic_id": topic_id,
            "topic_title": topic.title,
            "relations": [
                {
                    "id": rel.id,
                    "target_topic_id": rel.target_topic_id,
                    "target_title": rel.target_topic.title if rel.target_topic else None,
                    "relation_type": rel.relation_type,
                    "score": rel.score,
                    "description": rel.description,
                }
                for rel in relations
            ],
        },
        "message": "success",
    }


@router.get("/api/v1/topics/{topic_id:int}/propagation", response_model=UnifiedResponse[dict])
async def topic_propagation_alias(topic_id: int, db: Session = Depends(get_db)):
    topic = db.query(HotTopic).filter(HotTopic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    paths = db.query(PropagationPath).filter(PropagationPath.root_topic_id == topic_id).order_by(desc(PropagationPath.created_at)).all()
    if paths:
        path = paths[0]
        nodes = db.query(PropagationNode).filter(PropagationNode.path_id == path.id).all()
        return {
            "code": 200,
            "data": {
                "path": {
                    "id": path.id,
                    "root_topic_id": path.root_topic_id,
                    "depth": path.depth,
                    "total_nodes": path.total_nodes,
                    "platforms_involved": path.platforms_involved,
                },
                "nodes": [
                    {
                        "id": node.id,
                        "topic_id": node.topic_id,
                        "topic_title": node.topic.title if node.topic else None,
                        "platform_name": node.platform.display_name if node.platform else None,
                        "level": node.level,
                        "parent_node_id": node.parent_node_id,
                        "discovered_at": node.discovered_at.isoformat() if node.discovered_at else None,
                    }
                    for node in nodes
                ],
                "edges": [
                    {"source": node.parent_node_id, "target": node.id, "strength": node.influence_score}
                    for node in nodes if node.parent_node_id
                ],
            },
            "message": "success",
        }

    return {
        "code": 200,
        "data": {
            "path": {
                "id": None,
                "root_topic_id": topic.id,
                "root_topic_title": topic.title,
                "depth": 0,
                "total_nodes": 1,
                "platforms_involved": [topic.platform.name if topic.platform else None],
            },
            "nodes": [{
                "id": f"topic-{topic.id}",
                "topic_id": topic.id,
                "topic_title": topic.title,
                "platform_name": topic.platform.display_name if topic.platform else None,
                "level": 0,
                "parent_node_id": None,
                "discovered_at": topic.crawl_time.isoformat() if topic.crawl_time else None,
            }],
            "edges": [],
        },
        "message": "success",
    }


@router.get("/api/v1/topics/propagation/strength", response_model=UnifiedResponse[dict])
async def propagation_strength(db: Session = Depends(get_db)):
    rows = db.query(Platform.name, Platform.display_name, HotTopic.category, func.count(HotTopic.id)).select_from(Platform).join(
        HotTopic, HotTopic.platform_id == Platform.id
    ).group_by(Platform.id, Platform.name, Platform.display_name, HotTopic.category).all()
    by_category: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for name, display_name, category, count in rows:
        by_category[category or "未分类"].append((name, display_name, count))

    edges = []
    for category, platforms in by_category.items():
        for index, source in enumerate(platforms):
            for target in platforms[index + 1:]:
                strength = min(source[2], target[2])
                if strength:
                    edges.append({
                        "source_platform": source[0],
                        "target_platform": target[0],
                        "source_display_name": source[1],
                        "target_display_name": target[1],
                        "category": category,
                        "strength": strength,
                    })
    return {"code": 200, "data": {"edges": edges, "total": len(edges)}, "message": "success"}


@router.get("/api/v1/models/current", response_model=UnifiedResponse[dict])
async def models_current(db: Session = Depends(get_db)):
    active = db.query(ModelVersion).filter(ModelVersion.is_active == True).first()
    training_results_path = Path(__file__).resolve().parents[3] / "model_output" / "training_results.json"
    training_results = None
    if training_results_path.exists():
        try:
            training_results = json.loads(training_results_path.read_text(encoding="utf-8"))
        except Exception:
            training_results = None
    return {
        "code": 200,
        "data": {
            "version": active.version if active else None,
            "model_name": active.model_name if active else "sklearn-sentiment",
            "task_type": active.task_type if active else "sentiment-classification",
            "device": active.device if active else "cpu",
            "is_loaded": active is not None,
            "metrics": training_results,
            "updated_at": active.updated_at.isoformat() if active and active.updated_at else None,
        },
        "message": "success",
    }


@router.get("/api/v1/models/{version}/metrics", response_model=UnifiedResponse[dict])
async def model_metrics(version: str, db: Session = Depends(get_db)):
    model = db.query(ModelVersion).filter(ModelVersion.version == version).first()
    metrics = None
    if model and model.metrics_json:
        try:
            metrics = json.loads(model.metrics_json)
        except Exception:
            metrics = {"raw": model.metrics_json}
    return {
        "code": 200,
        "data": {
            "version": version,
            "metrics": metrics or {},
            "confusion_matrix": [],
            "source": "model_versions.metrics_json" if model else "not_found",
        },
        "message": "success",
    }


@router.get("/api/v1/sentiment/trend", response_model=UnifiedResponse[dict])
async def sentiment_trend(days: int = Query(14, ge=1, le=90), db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(days=days)
    rows = db.query(
        func.date(SentimentResult.analyzed_at).label("date"),
        SentimentResult.sentiment_label,
        func.count(SentimentResult.id).label("count"),
        func.avg(SentimentResult.confidence).label("avg_confidence"),
    ).filter(SentimentResult.analyzed_at >= since).group_by(
        func.date(SentimentResult.analyzed_at), SentimentResult.sentiment_label
    ).all()

    points = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "avg_confidence": 0})
    for row in rows:
        points[str(row.date)][row.sentiment_label] = row.count
        points[str(row.date)]["avg_confidence"] = round(row.avg_confidence or 0, 4)

    return {
        "code": 200,
        "data": {
            "period": f"最近 {days} 天",
            "series": [{"date": date, **values} for date, values in sorted(points.items())],
        },
        "message": "success",
    }


@router.get("/api/v1/sentiment/summary", response_model=UnifiedResponse[dict])
async def sentiment_summary(db: Session = Depends(get_db)):
    today = datetime.now().date()
    total_today = db.query(SentimentResult).filter(func.date(SentimentResult.analyzed_at) == today).count()
    total = db.query(SentimentResult).count()
    low_conf = db.query(SentimentResult).filter(SentimentResult.confidence < 0.5).count()
    negative = db.query(SentimentResult).filter(SentimentResult.sentiment_label == "negative").count()
    avg_conf = db.query(func.avg(SentimentResult.confidence)).scalar() or 0
    return {
        "code": 200,
        "data": {
            "today_analyzed": total_today,
            "total_analyzed": total,
            "success_rate": 100 if total else 0,
            "low_confidence": low_conf,
            "negative_samples": negative,
            "avg_confidence": round(avg_conf, 4),
            "avg_latency_ms": 0,
        },
        "message": "success",
    }


@router.get("/api/v1/sentiment/jobs", response_model=UnifiedResponse[dict])
async def sentiment_jobs(
    status: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(SentimentJob)
    if status:
        query = query.filter(SentimentJob.status == status)
    total = query.count()
    jobs = query.order_by(desc(SentimentJob.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    queue_length = db.query(SentimentJob).filter(SentimentJob.status.in_(["queued", "running", "retry_queued"])).count()
    return {
        "code": 200,
        "data": {
            "items": [_sentiment_job_payload(job) for job in jobs],
            "pagination": _pagination(page, page_size, total),
            "queue_length": queue_length,
        },
        "message": "success",
    }


@router.post("/api/v1/sentiment/jobs", response_model=UnifiedResponse[dict])
async def create_sentiment_job(payload: dict | None = None, db: Session = Depends(get_db)):
    payload = payload or {}
    texts = [str(item).strip() for item in payload.get("texts", []) if str(item).strip()]
    job_id = f"sentiment_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    job = SentimentJob(
        job_id=job_id,
        status="running",
        total_count=len(texts),
        payload_json=json.dumps({"texts": texts}, ensure_ascii=False),
        started_at=datetime.now(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    started = datetime.now()
    try:
        service = SentimentService(db=None)
        results = service.analyze_batch(texts) if texts else []
        elapsed_ms = (datetime.now() - started).total_seconds() * 1000
        job.status = "completed"
        job.success_count = len(results)
        job.failed_count = max(0, len(texts) - len(results))
        job.avg_latency_ms = round(elapsed_ms / len(texts), 2) if texts else 0
        job.result_json = json.dumps(results, ensure_ascii=False, default=str)
        job.completed_at = datetime.now()
    except Exception as exc:
        job.status = "failed"
        job.failed_count = len(texts)
        job.error_message = str(exc)
        job.completed_at = datetime.now()
    db.commit()
    db.refresh(job)

    return {"code": 200, "data": _sentiment_job_payload(job), "message": "success"}


@router.get("/api/v1/sentiment/jobs/{job_id}", response_model=UnifiedResponse[dict])
async def sentiment_job_detail(job_id: str, db: Session = Depends(get_db)):
    if job_id == "current":
        job = db.query(SentimentJob).order_by(desc(SentimentJob.created_at)).first()
        if not job:
            return {
                "code": 200,
                "data": {"job_id": "current", "status": "idle", "total_count": 0, "success_count": 0, "failed_count": 0},
                "message": "success",
            }
        return {"code": 200, "data": _sentiment_job_payload(job), "message": "success"}

    job = db.query(SentimentJob).filter(SentimentJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Sentiment job not found")
    return {"code": 200, "data": _sentiment_job_payload(job), "message": "success"}


@router.post("/api/v1/sentiment/jobs/{job_id}/retry", response_model=UnifiedResponse[dict])
async def retry_sentiment_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(SentimentJob).filter(SentimentJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Sentiment job not found")

    payload = json.loads(job.payload_json or "{}")
    texts = [str(item).strip() for item in payload.get("texts", []) if str(item).strip()]
    job.status = "retry_queued"
    job.error_message = None
    db.commit()

    started = datetime.now()
    try:
        service = SentimentService(db=None)
        results = service.analyze_batch(texts) if texts else []
        elapsed_ms = (datetime.now() - started).total_seconds() * 1000
        job.status = "completed"
        job.success_count = len(results)
        job.failed_count = max(0, len(texts) - len(results))
        job.avg_latency_ms = round(elapsed_ms / len(texts), 2) if texts else 0
        job.result_json = json.dumps(results, ensure_ascii=False, default=str)
        job.started_at = started
        job.completed_at = datetime.now()
    except Exception as exc:
        job.status = "failed"
        job.failed_count = len(texts)
        job.error_message = str(exc)
        job.completed_at = datetime.now()
    db.commit()
    db.refresh(job)
    return {"code": 200, "data": _sentiment_job_payload(job), "message": "success"}


@router.get("/api/v1/sentiment/low-confidence", response_model=UnifiedResponse[dict])
async def sentiment_low_confidence(
    threshold: float = Query(0.5, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(SentimentResult).join(HotTopic).filter(SentimentResult.confidence < threshold)
    total = query.count()
    results = query.order_by(SentimentResult.confidence.asc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": result.id,
            "topic_id": result.topic_id,
            "topic_title": result.hot_topic.title if result.hot_topic else None,
            "sentiment_label": result.sentiment_label,
            "confidence": result.confidence,
            "analyzed_at": result.analyzed_at.isoformat() if result.analyzed_at else None,
        }
        for result in results
    ]
    return {"code": 200, "data": {"items": items, "pagination": _pagination(page, page_size, total), "threshold": threshold}, "message": "success"}


@router.post("/api/v1/sentiment/explain", response_model=UnifiedResponse[dict])
async def explain_sentiment_text(payload: dict):
    text = (payload or {}).get("text", "")
    service = SentimentService(db=None)
    result = service.analyze_text(text)
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", text)
    return {
        "code": 200,
        "data": {
            "text": text,
            "sentiment_label": result["sentiment_label"],
            "confidence": result["confidence"],
            "scores": result["scores"],
            "method": "keyword-contribution",
            "tokens": [
                {"token": token, "contribution": _sentiment_numeric(result["sentiment_label"]) * result["confidence"]}
                for token in tokens[:20]
            ],
        },
        "message": "success",
    }


@router.get("/api/v1/sentiment/results/{result_id:int}/explanation", response_model=UnifiedResponse[dict])
async def sentiment_result_explanation(result_id: int, db: Session = Depends(get_db)):
    result = db.query(SentimentResult).filter(SentimentResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Sentiment result not found")
    explanation = db.query(ModelExplanation).filter(ModelExplanation.sentiment_result_id == result_id).order_by(
        desc(ModelExplanation.created_at)
    ).first()
    topic_text = ""
    if result.hot_topic:
        topic_text = f"{result.hot_topic.title or ''} {result.hot_topic.content_summary or ''}"
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", topic_text)
    generated_summary = (
        f"该结果判定为 {result.sentiment_label}，置信度 {round((result.confidence or 0) * 100, 1)}%。"
        "当前解释基于话题标题、摘要关键词和三分类分数生成。"
    )
    return {
        "code": 200,
        "data": {
            "sentiment_result_id": result_id,
            "explanation_id": explanation.id if explanation else None,
            "summary": explanation.summary if explanation else generated_summary,
            "method": explanation.method if explanation else "keyword-contribution",
            "tokens": [
                {
                    "token": token,
                    "contribution": round(_sentiment_numeric(result.sentiment_label) * (result.confidence or 0), 4),
                }
                for token in tokens[:20]
            ],
        },
        "message": "success",
    }


@router.post("/api/v1/forecast/heat", response_model=UnifiedResponse[dict])
async def forecast_heat(payload: dict | None = None, db: Session = Depends(get_db)):
    payload = payload or {}
    topic_id = payload.get("topic_id")
    horizon_days = int(payload.get("horizon_days", 7))
    data = trend_forecast_service.forecast_heat(db, topic_id=topic_id, horizon_days=horizon_days)
    return {"code": 200, "data": data, "message": "success"}


@router.get("/api/v1/forecast/signals", response_model=UnifiedResponse[dict])
async def forecast_signals(topic_id: int = None, db: Session = Depends(get_db)):
    data = trend_forecast_service.forecast_signals(db, topic_id=topic_id)
    return {"code": 200, "data": data, "message": "success"}


@router.get("/api/v1/forecast/scenarios", response_model=UnifiedResponse[dict])
async def forecast_scenarios(topic_id: int = None, db: Session = Depends(get_db)):
    data = trend_forecast_service.forecast_scenarios(db, topic_id=topic_id)
    return {"code": 200, "data": data, "message": "success"}


@router.get("/api/v1/platforms/monitoring", response_model=UnifiedResponse[dict])
async def platform_monitoring_alias(db: Session = Depends(get_db)):
    return {"code": 200, "data": _platform_monitoring_matrix(db), "message": "success"}


@router.get("/api/v1/platforms/{platform_id:int}/config", response_model=UnifiedResponse[dict])
async def get_platform_config(platform_id: int, db: Session = Depends(get_db)):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    return {
        "code": 200,
        "data": {
            "platform_id": platform.id,
            "name": platform.name,
            "display_name": platform.display_name,
            "base_url": platform.base_url,
            "crawl_config": platform.crawl_config or {},
            "is_active": platform.is_active,
            "sort_order": platform.sort_order,
        },
        "message": "success",
    }


@router.patch("/api/v1/platforms/{platform_id:int}/config", response_model=UnifiedResponse[dict])
async def patch_platform_config(platform_id: int, payload: dict, db: Session = Depends(get_db)):
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    before = {"base_url": platform.base_url, "crawl_config": platform.crawl_config, "is_active": platform.is_active}
    for field in ["base_url", "crawl_config", "is_active", "sort_order"]:
        if field in payload:
            setattr(platform, field, payload[field])
    db.add(AuditLog(
        operator="system",
        action="update",
        target_type="platform_config",
        target_id=str(platform_id),
        before_json=json.dumps(before, ensure_ascii=False),
        after_json=json.dumps(payload, ensure_ascii=False),
    ))
    db.commit()
    db.refresh(platform)
    return {"code": 200, "data": {"platform_id": platform.id, "name": platform.name}, "message": "Platform config updated successfully"}


@router.get("/api/v1/crawler/tasks/summary", response_model=UnifiedResponse[dict])
async def crawler_tasks_summary(db: Session = Depends(get_db)):
    today = datetime.now().date()
    task_query = db.query(CrawlerTask).filter(func.date(CrawlerTask.created_at) == today)
    task_rows = task_query.all()
    logs = db.query(CrawlLog).filter(func.date(CrawlLog.started_at) == today).all()
    completed = sum(1 for task in task_rows if task.status == "completed") or sum(1 for log in logs if log.status == "success")
    failed = sum(1 for task in task_rows if task.status == "failed") or sum(1 for log in logs if log.status == "failed")
    avg_duration = [
        (task.completed_at - (task.started_at or task.created_at)).total_seconds()
        for task in task_rows if task.completed_at and (task.started_at or task.created_at)
    ]
    if not avg_duration:
        avg_duration = [
            (log.completed_at - log.started_at).total_seconds()
            for log in logs if log.completed_at and log.started_at
        ]
    return {
        "code": 200,
        "data": {
            "running": sum(1 for task in task_rows if task.status == "running"),
            "queued": sum(1 for task in task_rows if task.status in {"queued", "retry_queued"}),
            "paused": sum(1 for task in task_rows if task.status == "paused"),
            "cancelled": sum(1 for task in task_rows if task.status == "cancelled"),
            "completed": completed,
            "failed": failed,
            "avg_duration_seconds": round(sum(avg_duration) / len(avg_duration), 2) if avg_duration else 0,
            "next_run": None,
        },
        "message": "success",
    }


@router.get("/api/v1/crawler/tasks/{task_id}", response_model=UnifiedResponse[dict])
async def crawler_task_detail(task_id: str, db: Session = Depends(get_db)):
    if task_id == "current":
        task = db.query(CrawlerTask).order_by(desc(CrawlerTask.created_at)).first()
        if not task:
            return {
                "code": 200,
                "data": {"task_id": "current", "status": "idle", "progress": 0, "events": []},
                "message": "success",
            }
        return {"code": 200, "data": _crawler_task_payload(task, include_events=True), "message": "success"}

    task = db.query(CrawlerTask).filter(CrawlerTask.task_id == task_id).first()
    if task:
        return {"code": 200, "data": _crawler_task_payload(task, include_events=True), "message": "success"}

    log_id_match = re.search(r"\d+", task_id)
    log = db.query(CrawlLog).filter(CrawlLog.id == int(log_id_match.group(0))).first() if log_id_match else None
    if not log:
        raise HTTPException(status_code=404, detail="Crawler task not found")
    progress = 100 if log.completed_at else 50
    return {
        "code": 200,
        "data": {
            "task_id": task_id,
            "status": log.status,
            "progress": progress,
            "platform": log.platform.display_name if log.platform else None,
            "records_count": log.records_count,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
        },
        "message": "success",
    }


@router.post("/api/v1/crawler/tasks/{task_id}/retry", response_model=UnifiedResponse[dict])
async def retry_crawler_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(CrawlerTask).filter(CrawlerTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Crawler task not found")
    task.status = "retry_queued"
    task.progress = 0
    task.error_message = None
    db.add(CrawlerTaskEvent(
        task_ref_id=task.id,
        event_type="retry_queued",
        message="Retry requested from UI",
    ))
    db.commit()
    db.refresh(task)
    return {"code": 200, "data": _crawler_task_payload(task), "message": "Task retry queued"}


@router.post("/api/v1/crawler/tasks/{task_id}/pause", response_model=UnifiedResponse[dict])
async def pause_crawler_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(CrawlerTask).filter(CrawlerTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Crawler task not found")
    task.status = "paused"
    db.add(CrawlerTaskEvent(task_ref_id=task.id, event_type="paused", message="Task paused from UI"))
    db.commit()
    db.refresh(task)
    return {"code": 200, "data": _crawler_task_payload(task), "message": "Task paused"}


@router.post("/api/v1/crawler/tasks/{task_id}/resume", response_model=UnifiedResponse[dict])
async def resume_crawler_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(CrawlerTask).filter(CrawlerTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Crawler task not found")
    task.status = "queued"
    db.add(CrawlerTaskEvent(task_ref_id=task.id, event_type="resumed", message="Task resumed from UI"))
    db.commit()
    db.refresh(task)
    return {"code": 200, "data": _crawler_task_payload(task), "message": "Task resumed"}


@router.post("/api/v1/crawler/tasks/{task_id}/cancel", response_model=UnifiedResponse[dict])
async def cancel_crawler_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(CrawlerTask).filter(CrawlerTask.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Crawler task not found")
    task.status = "cancelled"
    task.completed_at = datetime.now()
    db.add(CrawlerTaskEvent(task_ref_id=task.id, event_type="cancelled", message="Task cancelled from UI"))
    db.commit()
    db.refresh(task)
    return {"code": 200, "data": _crawler_task_payload(task), "message": "Task cancelled"}


@router.get("/api/v1/crawler/timeline", response_model=UnifiedResponse[dict])
async def crawler_timeline(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    since = datetime.now() - timedelta(days=days)
    logs = db.query(CrawlLog).filter(CrawlLog.started_at >= since).order_by(desc(CrawlLog.started_at)).all()
    tasks = db.query(CrawlerTask).filter(CrawlerTask.created_at >= since).order_by(desc(CrawlerTask.created_at)).all()
    task_items = [
        {
            "id": task.id,
            "type": "crawler_task",
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "platforms": json.loads(task.platforms_json or "[]"),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
        for task in tasks
    ]
    log_items = [
        {
            "id": log.id,
            "type": "crawl",
            "platform_name": log.platform.display_name if log.platform else None,
            "status": log.status,
            "records_count": log.records_count,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "created_at": log.started_at.isoformat() if log.started_at else None,
        }
        for log in logs
    ]
    items = sorted(task_items + log_items, key=lambda item: item.get("created_at") or item.get("started_at") or "", reverse=True)
    return {
        "code": 200,
        "data": {
            "period": f"最近 {days} 天",
            "items": items,
            "future": [],
        },
        "message": "success",
    }


@router.post("/api/v1/data-quality/run", response_model=UnifiedResponse[dict])
async def run_data_quality(run_type: str = "manual", db: Session = Depends(get_db)):
    result = DataQualityService(db).run_quality_check(run_type)
    return {"code": 200, "data": result, "message": f"Quality check {result['status']}"}


@router.post("/api/v1/data/archive", response_model=UnifiedResponse[dict])
async def archive_data(payload: dict | None = None, db: Session = Depends(get_db)):
    payload = payload or {}
    retention_days = int(payload.get("retention_days", 30))
    cutoff = datetime.now() - timedelta(days=retention_days)
    archive_id = f"archive_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    run = DataArchiveRun(
        archive_id=archive_id,
        status="running",
        retention_days=retention_days,
        started_at=datetime.now(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    topics = db.query(HotTopic).filter(HotTopic.crawl_time < cutoff).all()
    archive_dir = Path(__file__).resolve().parents[3] / "data" / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{archive_id}.json"
    archive_payload = {
        "archive_id": archive_id,
        "retention_days": retention_days,
        "cutoff": cutoff.isoformat(),
        "topics": [
            {
                "id": topic.id,
                "platform_id": topic.platform_id,
                "topic_id": topic.topic_id,
                "title": topic.title,
                "url": topic.url,
                "heat_score": topic.heat_score,
                "category": topic.category,
                "content_summary": topic.content_summary,
                "crawl_time": topic.crawl_time.isoformat() if topic.crawl_time else None,
                "created_at": topic.created_at.isoformat() if topic.created_at else None,
            }
            for topic in topics
        ],
    }
    archive_path.write_text(json.dumps(archive_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    run.status = "completed"
    run.archived_count = len(topics)
    run.archive_path = str(archive_path)
    run.completed_at = datetime.now()
    db.add(AuditLog(
        operator="system",
        action="archive",
        target_type="hot_topics",
        target_id=archive_id,
        after_json=json.dumps({"retention_days": retention_days, "archived_count": len(topics)}, ensure_ascii=False),
        note="Non-destructive JSON archive generated",
    ))
    db.commit()
    return {
        "code": 200,
        "data": {
            "archive_id": archive_id,
            "status": run.status,
            "archived_count": run.archived_count,
            "retention_days": retention_days,
            "archive_path": run.archive_path,
        },
        "message": "Archive completed",
    }


@router.get("/api/v1/audit-logs", response_model=UnifiedResponse[dict])
async def audit_logs_alias(
    operator: str = None,
    action: str = None,
    target_type: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if operator:
        query = query.filter(AuditLog.operator == operator)
    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)
    total = query.count()
    logs = query.order_by(desc(AuditLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": log.id,
            "operator": log.operator,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "before_json": log.before_json,
            "after_json": log.after_json,
            "note": log.note,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    return {"code": 200, "data": {"items": items, "pagination": _pagination(page, page_size, total)}, "message": "success"}


@router.get("/api/v1/system/errors/{error_id:int}", response_model=UnifiedResponse[dict])
async def system_error_detail(error_id: int, db: Session = Depends(get_db)):
    log = db.query(SystemLog).filter(SystemLog.id == error_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="System error not found")
    return {
        "code": 200,
        "data": {
            "id": log.id,
            "level": log.level,
            "module": log.module,
            "event": log.event,
            "message": log.message,
            "payload_json": log.payload_json,
            "request_id": log.request_id,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "retry_strategy": "manual_review" if log.level in {"ERROR", "CRITICAL"} else "none",
        },
        "message": "success",
    }
