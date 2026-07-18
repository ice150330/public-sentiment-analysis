"""Service helpers for the sentiment manual review queue."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import get_allowed_platforms
from app.models import HotTopic, Platform, SentimentResult, SentimentReviewItem, User


DEFAULT_REVIEW_THRESHOLD = 0.6


def apply_review_platform_scope(query, current_user: User):
    allowed_platforms = get_allowed_platforms(current_user)
    if not allowed_platforms:
        return query
    return query.filter(Platform.name.in_(allowed_platforms))


def ensure_review_queue(
    db: Session,
    *,
    threshold: float = DEFAULT_REVIEW_THRESHOLD,
    current_user: User | None = None,
) -> int:
    """Materialize missing low-confidence results as pending review items."""
    existing_ids = {
        row[0]
        for row in db.query(SentimentReviewItem.sentiment_result_id).all()
    }

    query = db.query(SentimentResult).join(HotTopic).join(Platform)
    query = query.filter(SentimentResult.confidence < threshold)
    if current_user is not None:
        query = apply_review_platform_scope(query, current_user)

    created = 0
    for result in query.all():
        if result.id in existing_ids:
            continue
        db.add(
            SentimentReviewItem(
                sentiment_result_id=result.id,
                status="pending",
                original_label=result.sentiment_label,
                suggested_label=result.sentiment_label,
                confidence_snapshot=result.confidence,
            )
        )
        created += 1
    if created:
        db.flush()
    return created


def pending_review_count(db: Session, *, threshold: float = DEFAULT_REVIEW_THRESHOLD) -> int:
    """Count low-confidence results that still need human review."""
    return db.query(SentimentResult).outerjoin(SentimentReviewItem).filter(
        SentimentResult.confidence < threshold,
        or_(SentimentReviewItem.id.is_(None), SentimentReviewItem.status == "pending"),
    ).count()


def review_item_payload(item: SentimentReviewItem) -> dict:
    result = item.sentiment_result
    topic = result.hot_topic if result else None
    platform = topic.platform if topic and topic.platform else None
    return {
        "id": item.id,
        "sentiment_result_id": item.sentiment_result_id,
        "topic_id": result.topic_id if result else None,
        "topic_title": topic.title if topic else None,
        "platform_name": platform.display_name if platform else None,
        "sentiment_label": result.sentiment_label if result else item.suggested_label,
        "original_label": item.original_label,
        "suggested_label": item.suggested_label,
        "corrected_label": item.corrected_label,
        "confidence": result.confidence if result else item.confidence_snapshot,
        "confidence_snapshot": item.confidence_snapshot,
        "status": item.status,
        "reviewer": item.reviewer,
        "note": item.note,
        "analyzed_at": result.analyzed_at.isoformat() if result and result.analyzed_at else None,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def mark_review_item(
    item: SentimentReviewItem,
    *,
    status: str,
    reviewer: str,
    corrected_label: str | None = None,
    note: str | None = None,
) -> SentimentReviewItem:
    item.status = status
    item.corrected_label = corrected_label if status == "reviewed" else None
    item.note = note
    item.reviewer = reviewer
    item.reviewed_at = datetime.now() if status in {"reviewed", "ignored"} else None
    return item
