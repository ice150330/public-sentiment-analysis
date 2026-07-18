"""
高级分析模型 - 传播路径

模块名称: propagation_path.py
模块职责: 话题传播链路、跨平台传播追踪 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PropagationPath(Base):
    """传播路径表"""
    __tablename__ = "propagation_paths"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    root_topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="CASCADE"), nullable=False, comment="根话题ID")
    
    # 传播统计
    depth = Column(Integer, default=0, comment="传播深度")
    total_nodes = Column(Integer, default=0, comment="总节点数")
    max_breadth = Column(Integer, default=0, comment="最大传播广度")
    
    # 时间跨度
    first_seen_at = Column(DateTime, comment="首次出现时间")
    last_seen_at = Column(DateTime, comment="最后出现时间")
    
    # 跨平台统计
    platforms_involved = Column(Text, comment="涉及平台列表(JSON数组)")
    platform_transitions = Column(Integer, default=0, comment="跨平台传播次数")
    
    created_at = Column(DateTime, server_default=func.now())
    
    root_topic = relationship("HotTopic")
    nodes = relationship("PropagationNode", back_populates="path", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<PropagationPath(id={self.id}, depth={self.depth}, nodes={self.total_nodes})>"


class PropagationNode(Base):
    """传播节点表"""
    __tablename__ = "propagation_nodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    path_id = Column(Integer, ForeignKey("propagation_paths.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="CASCADE"), nullable=False)
    
    # 节点层级和位置
    level = Column(Integer, default=0, comment="传播层级(0=根)")
    parent_node_id = Column(Integer, ForeignKey("propagation_nodes.id", ondelete="SET NULL"), comment="父节点ID")
    
    # 平台信息
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="SET NULL"))
    
    # 传播指标
    heat_score = Column(Integer, comment="热度值")
    sentiment_label = Column(String(16), comment="情感标签")
    influence_score = Column(Float, comment="影响力分数")
    features_json = Column(Text, comment="传播匹配特征(JSON)")
    
    # 时间
    discovered_at = Column(DateTime, comment="发现时间")
    
    created_at = Column(DateTime, server_default=func.now())
    
    path = relationship("PropagationPath", back_populates="nodes")
    topic = relationship("HotTopic")
    platform = relationship("Platform")
    parent = relationship("PropagationNode", remote_side=[id])
    
    def __repr__(self) -> str:
        return f"<PropagationNode(path={self.path_id}, level={self.level}, topic={self.topic_id})>"
