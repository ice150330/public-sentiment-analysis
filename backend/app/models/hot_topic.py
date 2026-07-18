"""
热榜数据模型

模块名称: hot_topic.py
模块职责: 热榜数据 ORM 模型
"""

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class HotTopic(Base):
    """热榜数据表"""
    __tablename__ = "hot_topics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String(128), nullable=False, comment="平台原始话题ID")
    title = Column(String(512), nullable=False, comment="话题标题")
    url = Column(String(1024), comment="详情链接")
    heat_score = Column(Integer, comment="热度值（平台原始值）")
    category = Column(String(64), comment="分类标签")
    content_summary = Column(Text, comment="正文摘要（前500字）")
    raw_data = Column(JSON, comment="原始数据备份(JSON)")
    crawl_time = Column(DateTime, nullable=False, comment="采集时间")
    crawl_date = Column(Date, nullable=False, comment="采集日期(用于去重)")
    created_at = Column(DateTime, server_default=func.now())
    
    # 联合唯一键：同一平台同一话题同一天只存一次
    __table_args__ = (
        UniqueConstraint("platform_id", "topic_id", "crawl_date", name="uix_platform_topic_date"),
        Index("idx_hot_topics_platform_crawl_time", "platform_id", "crawl_time"),
        Index("idx_hot_topics_crawl_time", "crawl_time"),
        Index("idx_hot_topics_heat_score", "heat_score"),
        Index("idx_hot_topics_category_crawl_time", "category", "crawl_time"),
        Index("idx_hot_topics_crawl_date", "crawl_date"),
    )
    
    # 关系
    platform = relationship("Platform", backref="hot_topics")
    sentiment_result = relationship("SentimentResult", back_populates="hot_topic", uselist=False)
    
    def __repr__(self) -> str:
        return f"<HotTopic(id={self.id}, title={self.title[:30]}...)>"
