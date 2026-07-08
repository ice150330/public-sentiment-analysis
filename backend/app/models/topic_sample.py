"""
话题样本与关联话题模型

模块名称: topic_sample.py
模块职责: 话题证据样本、关联话题 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TopicSample(Base):
    """话题证据样本表"""
    __tablename__ = "topic_samples"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="CASCADE"), nullable=False)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="SET NULL"))
    
    sample_type = Column(String(32), comment="样本类型: post/comment/article/video")
    content = Column(Text, comment="样本内容")
    sentiment_label = Column(String(16), comment="样本情感: positive/negative/neutral")
    confidence = Column(Float, comment="置信度")
    source_url = Column(String(1024), comment="来源链接")
    author = Column(String(128), comment="作者")
    
    created_at = Column(DateTime, server_default=func.now())
    
    topic = relationship("HotTopic")
    platform = relationship("Platform")
    
    def __repr__(self) -> str:
        return f"<TopicSample(id={self.id}, topic_id={self.topic_id}, type={self.sample_type})>"


class TopicRelation(Base):
    """关联话题表"""
    __tablename__ = "topic_relations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="CASCADE"), nullable=False)
    target_topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="CASCADE"), nullable=False)
    
    relation_type = Column(String(32), comment="关联类型: similar/trend/comment/gap")
    score = Column(Float, comment="关联强度 0-1")
    description = Column(Text, comment="关联说明")
    
    created_at = Column(DateTime, server_default=func.now())
    
    source_topic = relationship("HotTopic", foreign_keys=[source_topic_id])
    target_topic = relationship("HotTopic", foreign_keys=[target_topic_id])
    
    def __repr__(self) -> str:
        return f"<TopicRelation(id={self.id}, source={self.source_topic_id}, target={self.target_topic_id})>"
