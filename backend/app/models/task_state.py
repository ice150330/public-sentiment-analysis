"""
Task state models for UI-facing operational workflows.

These tables keep crawler jobs, sentiment batch jobs, and archive runs visible
to the management screens without requiring an external queue service.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CrawlerTask(Base):
    """Crawler task queue/status table."""
    __tablename__ = "crawler_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), nullable=False, unique=True)
    status = Column(String(24), nullable=False, default="queued")
    progress = Column(Integer, default=0)
    platforms_json = Column(Text)
    result_json = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    events = relationship("CrawlerTaskEvent", back_populates="task", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CrawlerTask(task_id={self.task_id}, status={self.status})>"


class CrawlerTaskEvent(Base):
    """Crawler task event timeline."""
    __tablename__ = "crawler_task_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_ref_id = Column(Integer, ForeignKey("crawler_tasks.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(32), nullable=False)
    message = Column(Text)
    payload_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    task = relationship("CrawlerTask", back_populates="events")

    def __repr__(self) -> str:
        return f"<CrawlerTaskEvent(task_ref_id={self.task_ref_id}, type={self.event_type})>"


class SentimentJob(Base):
    """Sentiment batch job status table."""
    __tablename__ = "sentiment_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), nullable=False, unique=True)
    status = Column(String(24), nullable=False, default="queued")
    total_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0)
    payload_json = Column(Text)
    result_json = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<SentimentJob(job_id={self.job_id}, status={self.status})>"


class DataArchiveRun(Base):
    """Non-destructive data archive run table."""
    __tablename__ = "data_archive_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    archive_id = Column(String(64), nullable=False, unique=True)
    status = Column(String(24), nullable=False, default="running")
    retention_days = Column(Integer)
    archived_count = Column(Integer, default=0)
    archive_path = Column(Text)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<DataArchiveRun(archive_id={self.archive_id}, status={self.status})>"
