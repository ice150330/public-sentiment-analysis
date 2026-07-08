"""
预警处置记录模型

模块名称: alert_action.py
模块职责: 预警处置操作 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AlertAction(Base):
    """预警处置记录表"""
    __tablename__ = "alert_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False, comment="关联事件ID")
    
    # 操作类型: acknowledge(确认) / resolve(解决) / escalate(升级) / ignore(忽略) / comment(备注)
    action_type = Column(String(16), nullable=False, comment="操作类型")
    
    # 操作人（系统或用户标识）
    operator = Column(String(64), default="system", comment="操作人")
    
    # 备注说明
    note = Column(Text, comment="操作备注")
    
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    event = relationship("AlertEvent", back_populates="actions")
    
    def __repr__(self) -> str:
        return f"<AlertAction(id={self.id}, event_id={self.event_id}, type={self.action_type})>"
