"""Helpers for normalizing UI-facing task state."""

from datetime import datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import CrawlerTask, CrawlerTaskEvent


STALE_QUEUE_SECONDS = 120
STALE_RUNNING_SECONDS = 30 * 60


def expire_stale_crawler_tasks(db: Session, now: datetime | None = None) -> int:
    """Close crawler task records that can no longer be backed by a worker."""
    now = now or datetime.now()
    expired_count = 0
    queue_cutoff = now - timedelta(seconds=STALE_QUEUE_SECONDS)
    running_cutoff = now - timedelta(seconds=STALE_RUNNING_SECONDS)

    stale_queued = db.query(CrawlerTask).filter(
        CrawlerTask.status.in_(["queued", "retry_queued"]),
        or_(
            CrawlerTask.started_at <= queue_cutoff,
            and_(CrawlerTask.started_at.is_(None), CrawlerTask.created_at <= queue_cutoff),
        ),
    ).all()

    for task in stale_queued:
        task.status = "expired"
        task.completed_at = now
        task.error_message = "Task expired before a crawler worker started it"
        db.add(CrawlerTaskEvent(
            task_ref_id=task.id,
            event_type="expired",
            message=task.error_message,
        ))
        expired_count += 1

    stale_running = db.query(CrawlerTask).filter(
        CrawlerTask.status == "running",
        or_(
            CrawlerTask.started_at <= running_cutoff,
            and_(CrawlerTask.started_at.is_(None), CrawlerTask.created_at <= running_cutoff),
        ),
    ).all()

    for task in stale_running:
        task.status = "failed"
        task.progress = 100
        task.completed_at = now
        task.error_message = "Task timed out before completion"
        db.add(CrawlerTaskEvent(
            task_ref_id=task.id,
            event_type="failed",
            message=task.error_message,
        ))
        expired_count += 1

    if expired_count:
        db.commit()

    return expired_count
