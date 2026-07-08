"""
高级分析模型 - 主题聚类

模块名称: topic_cluster.py
模块职责: 话题聚类结果、主题提取 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TopicCluster(Base):
    """话题聚类结果表"""
    __tablename__ = "topic_clusters"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_name = Column(String(128), nullable=False, comment="聚类名称/主题")
    description = Column(Text, comment="主题描述")
    
    # 聚类参数
    algorithm = Column(String(32), default="kmeans", comment="聚类算法: kmeans/dbscan/hierarchical")
    params_json = Column(Text, comment="聚类参数(JSON)")
    
    # 统计信息
    topic_count = Column(Integer, default=0, comment="包含话题数")
    avg_sentiment = Column(Float, comment="平均情感倾向")
    dominant_sentiment = Column(String(16), comment="主导情感: positive/negative/neutral")
    
    # 时间范围
    start_time = Column(DateTime, comment="聚类数据起始时间")
    end_time = Column(DateTime, comment="聚类数据结束时间")
    
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    members = relationship("ClusterMember", back_populates="cluster", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<TopicCluster(id={self.id}, name={self.cluster_name}, topics={self.topic_count})>"


class ClusterMember(Base):
    """聚类成员表"""
    __tablename__ = "cluster_members"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("topic_clusters.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="CASCADE"), nullable=False)
    
    # 成员在聚类中的权重/距离
    weight = Column(Float, default=1.0, comment="成员权重")
    distance_to_center = Column(Float, comment="到聚类中心距离")
    
    # 成员特征
    features_json = Column(Text, comment="特征向量(JSON)")
    
    created_at = Column(DateTime, server_default=func.now())
    
    cluster = relationship("TopicCluster", back_populates="members")
    topic = relationship("HotTopic")
    
    def __repr__(self) -> str:
        return f"<ClusterMember(cluster={self.cluster_id}, topic={self.topic_id})>"
