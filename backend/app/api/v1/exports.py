"""
CSV export API routes.

This module implements the first P0 data-export slice from ROADMAP_v1.0:
hot topics and alert events can be exported without changing the existing
paginated JSON endpoints.
"""

import csv
import io
import json
from datetime import datetime
from typing import Any, Iterable

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.auth import get_allowed_platforms, require_analyst
from app.core.database import get_db
from app.models import AlertEvent, AlertRule, HotTopic, Platform, SentimentResult, User
from app.services.pdf_report_service import build_sentiment_report_pdf

router = APIRouter()

MAX_EXPORT_LIMIT = 10000


def _format_datetime(value: datetime | None) -> str:
    if not value:
        return ""
    return value.isoformat(sep=" ", timespec="seconds")


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _sentiment_label_text(label: str | None) -> str:
    return {
        "positive": "正面",
        "negative": "负面",
        "neutral": "中性",
    }.get(label or "", label or "")


def _csv_response(filename_prefix: str, headers: list[str], rows: Iterable[list[Any]]) -> Response:
    buffer = io.StringIO(newline="")
    buffer.write("\ufeff")
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows([_format_value(value) for value in row] for row in rows)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{filename_prefix}-{timestamp}.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _apply_topic_filters(
    query,
    platform: str | None,
    keyword: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
    category: str | None,
    sentiment_label: str | None,
):
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
    if sentiment_label:
        query = query.filter(SentimentResult.sentiment_label == sentiment_label)
    return query


def _apply_platform_scope(query, requested_platform: str | None, current_user: User):
    allowed_platforms = get_allowed_platforms(current_user)
    if not allowed_platforms:
        return query
    if requested_platform and requested_platform not in allowed_platforms:
        return query.filter(Platform.name.in_([]))
    return query.filter(Platform.name.in_(allowed_platforms))


def _apply_sentiment_report_filters(
    query,
    platform: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
):
    if platform:
        query = query.filter(Platform.name == platform)
    if start_time:
        query = query.filter(SentimentResult.analyzed_at >= start_time)
    if end_time:
        query = query.filter(SentimentResult.analyzed_at <= end_time)
    return query


@router.get("/topics.csv")
async def export_topics_csv(
    platform: str = None,
    keyword: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    category: str = None,
    sentiment_label: str = None,
    sort_by: str = "heat_score",
    sort_order: str = "desc",
    limit: int = Query(1000, ge=1, le=MAX_EXPORT_LIMIT),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """Export filtered hot topics as UTF-8 CSV."""
    query = db.query(HotTopic).join(Platform).outerjoin(SentimentResult)
    query = _apply_topic_filters(query, platform, keyword, start_time, end_time, category, sentiment_label)
    query = _apply_platform_scope(query, platform, current_user)

    sort_fields = {
        "heat_score": HotTopic.heat_score,
        "crawl_time": HotTopic.crawl_time,
        "created_at": HotTopic.created_at,
        "id": HotTopic.id,
    }
    sort_field = sort_fields.get(sort_by, HotTopic.heat_score)
    query = query.order_by(desc(sort_field) if sort_order == "desc" else sort_field)
    topics = query.limit(limit).all()

    headers = [
        "ID",
        "平台",
        "平台标识",
        "平台话题ID",
        "标题",
        "分类",
        "热度",
        "情感",
        "置信度",
        "采集时间",
        "入库时间",
        "链接",
        "摘要",
    ]
    rows = (
        [
            topic.id,
            topic.platform.display_name if topic.platform else "",
            topic.platform.name if topic.platform else "",
            topic.topic_id,
            topic.title,
            topic.category,
            topic.heat_score,
            topic.sentiment_result.sentiment_label if topic.sentiment_result else "",
            topic.sentiment_result.confidence if topic.sentiment_result else "",
            _format_datetime(topic.crawl_time),
            _format_datetime(topic.created_at),
            topic.url,
            topic.content_summary,
        ]
        for topic in topics
    )
    return _csv_response("hot-topics", headers, rows)


def _format_action_timeline(event: AlertEvent) -> str:
    actions = sorted(event.actions, key=lambda item: item.created_at or datetime.min)
    timeline = [f"triggered@{_format_datetime(event.triggered_at)}"]
    for action in actions:
        note = f": {action.note}" if action.note else ""
        timeline.append(f"{action.action_type}@{_format_datetime(action.created_at)} by {action.operator or 'system'}{note}")
    return " -> ".join(timeline)


@router.get("/sentiment-report.pdf")
async def export_sentiment_report_pdf(
    platform: str = None,
    start_time: datetime = None,
    end_time: datetime = None,
    topic_limit: int = Query(12, ge=1, le=100),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """Export a PDF sentiment analytics report with a chart and key tables."""
    query = db.query(SentimentResult).join(HotTopic).join(Platform)
    query = _apply_sentiment_report_filters(query, platform, start_time, end_time)
    query = _apply_platform_scope(query, platform, current_user)

    total = query.count()
    distribution_rows = query.with_entities(
        SentimentResult.sentiment_label,
        func.count(SentimentResult.id),
    ).group_by(SentimentResult.sentiment_label).all()
    distribution_map = {label: count for label, count in distribution_rows}
    distribution = [
        {
            "label": label,
            "count": distribution_map.get(label, 0),
            "percentage": (distribution_map.get(label, 0) / total) if total else 0,
        }
        for label in ["positive", "neutral", "negative"]
    ]

    avg_confidence = query.with_entities(func.avg(SentimentResult.confidence)).scalar() or 0
    low_confidence = query.filter(SentimentResult.confidence < 0.6).count()
    negative_count = distribution_map.get("negative", 0)

    platform_counts = query.with_entities(
        Platform.display_name,
        func.count(SentimentResult.id).label("sample_count"),
        func.avg(SentimentResult.confidence).label("avg_confidence"),
    ).group_by(Platform.id, Platform.display_name).order_by(desc(func.count(SentimentResult.id))).all()
    platform_negative_counts = dict(
        query.filter(SentimentResult.sentiment_label == "negative").with_entities(
            Platform.display_name,
            func.count(SentimentResult.id),
        ).group_by(Platform.id, Platform.display_name).all()
    )
    platform_rows = [
        [
            display_name,
            sample_count,
            f"{(avg_confidence_value or 0) * 100:.1f}%",
            platform_negative_counts.get(display_name, 0),
        ]
        for display_name, sample_count, avg_confidence_value in platform_counts
    ]

    top_results = query.order_by(desc(HotTopic.heat_score)).limit(topic_limit).all()
    topic_rows = []
    for result in top_results:
        topic = result.hot_topic
        topic_rows.append(
            [
                topic.title if topic else "",
                topic.platform.display_name if topic and topic.platform else "",
                _sentiment_label_text(result.sentiment_label),
                f"{(result.confidence or 0) * 100:.1f}%",
                topic.heat_score if topic else "",
            ]
        )

    report = {
        "generated_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "filters": {
            "platform": platform,
            "start_time": _format_datetime(start_time),
            "end_time": _format_datetime(end_time),
        },
        "summary": {
            "total": total,
            "avg_confidence": avg_confidence,
            "negative_ratio": (negative_count / total) if total else 0,
            "low_confidence": low_confidence,
        },
        "distribution": distribution,
        "platform_rows": platform_rows,
        "topic_rows": topic_rows,
    }
    pdf_bytes = build_sentiment_report_pdf(report)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sentiment-report-{timestamp}.pdf"'},
    )


@router.get("/alerts.csv")
async def export_alerts_csv(
    status: str = None,
    severity: str = None,
    rule_id: int = None,
    start_time: datetime = None,
    end_time: datetime = None,
    limit: int = Query(1000, ge=1, le=MAX_EXPORT_LIMIT),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """Export filtered alert events as UTF-8 CSV with an action timeline."""
    query = db.query(AlertEvent).join(AlertRule).outerjoin(HotTopic).outerjoin(Platform)

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
    query = _apply_platform_scope(query, None, current_user)

    events = query.order_by(desc(AlertEvent.triggered_at)).limit(limit).all()

    headers = [
        "事件ID",
        "规则ID",
        "规则名称",
        "话题ID",
        "话题标题",
        "级别",
        "状态",
        "触发时间",
        "确认时间",
        "解决时间",
        "处置时间线",
    ]
    rows = (
        [
            event.id,
            event.rule_id,
            event.rule.name if event.rule else "",
            event.topic_id,
            event.topic.title if event.topic else "",
            event.severity,
            event.status,
            _format_datetime(event.triggered_at),
            _format_datetime(event.acknowledged_at),
            _format_datetime(event.resolved_at),
            _format_action_timeline(event),
        ]
        for event in events
    )
    return _csv_response("alert-events", headers, rows)
