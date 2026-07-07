"""
情感分析结果模型

模块名称: sentiment.py
模块职责: 情感分析结果 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class SentimentResult(Base):
    """情感分析结果表"""
    __tablename__ = "sentiment_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="CASCADE"), nullable=False)
    sentiment_label = Column(String(16), nullable=False, comment="positive | negative | neutral")
    confidence = Column(Float, nullable=False, comment="置信度 0.0 ~ 1.0")
    positive_score = Column(Float, default=0, comment="正面分数")
    negative_score = Column(Float, default=0, comment="负面分数")
    neutral_score = Column(Float, default=0, comment="中性分数")
    model_version = Column(String(32), comment="模型版本，如 'bert-sentiment-v1'")
    analyzed_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
    
    # 每条话题只分析一次
    __table_args__ = (
        UniqueConstraint("topic_id", name="uix_topic_sentiment"),
    )
    
    # 关系
    hot_topic = relationship("HotTopic", back_populates="sentiment_result")
    
    def __repr__(self) -> str:
        return f"<SentimentResult(id={self.id}, label={self.sentiment_label}, confidence={self.confidence:.2f})>"
