"""
预警事件模型

模块名称: alert_event.py
模块职责: 预警事件队列 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AlertEvent(Base):
    """预警事件队列表"""
    __tablename__ = "alert_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, comment="触发规则ID")
    topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="SET NULL"), comment="关联话题ID")
    
    # 严重程度（继承规则，但可覆盖）
    severity = Column(String(8), nullable=False, comment="P1/P2/P3/P4")
    
    # 状态: pending(待处理) / acknowledged(已确认) / resolving(处理中) / resolved(已解决) / ignored(已忽略)
    status = Column(String(16), nullable=False, default="pending", comment="处理状态")
    
    # 触发时的上下文数据（JSON）
    trigger_payload = Column(Text, comment="触发上下文: {heat_score, negative_ratio, ...}")
    
    # 触发/确认/解决时间
    triggered_at = Column(DateTime, server_default=func.now(), comment="触发时间")
    acknowledged_at = Column(DateTime, comment="确认时间")
    resolved_at = Column(DateTime, comment="解决时间")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    rule = relationship("AlertRule", back_populates="events")
    topic = relationship("HotTopic")
    actions = relationship("AlertAction", back_populates="event", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<AlertEvent(id={self.id}, rule_id={self.rule_id}, severity={self.severity}, status={self.status})>"
