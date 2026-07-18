"""
Sentiment low-confidence review queue model.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class SentimentReviewItem(Base):
    """Manual review record for a low-confidence sentiment result."""

    __tablename__ = "sentiment_review_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sentiment_result_id = Column(Integer, ForeignKey("sentiment_results.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(16), nullable=False, default="pending", comment="pending | reviewed | ignored")
    original_label = Column(String(16), nullable=False)
    suggested_label = Column(String(16), nullable=False)
    corrected_label = Column(String(16))
    confidence_snapshot = Column(Float, nullable=False)
    reviewer = Column(String(64))
    note = Column(Text)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("sentiment_result_id", name="uix_sentiment_review_result"),
        Index("idx_sentiment_review_status_created_at", "status", "created_at"),
        Index("idx_sentiment_review_reviewer", "reviewer"),
    )

    sentiment_result = relationship("SentimentResult", back_populates="review_item")

    def __repr__(self) -> str:
        return f"<SentimentReviewItem(id={self.id}, result={self.sentiment_result_id}, status={self.status})>"
