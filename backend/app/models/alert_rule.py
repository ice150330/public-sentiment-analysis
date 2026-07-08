"""
预警规则模型

模块名称: alert_rule.py
模块职责: 预警规则配置 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class AlertRule(Base):
    """预警规则配置表"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, comment="规则名称")
    description = Column(Text, comment="规则描述")
    
    # 触发条件（JSON 表达式或简化字段）
    condition_type = Column(String(32), nullable=False, comment="条件类型: heat_spike/negative_ratio/low_confidence/etc")
    condition_expr = Column(Text, nullable=False, comment="条件表达式(JSON)")
    
    # 严重程度: P1(紧急) / P2(高) / P3(中) / P4(低)
    severity = Column(String(8), nullable=False, default="P3", comment="严重程度")
    
    # 适用平台范围（JSON 数组或 all）
    platform_scope = Column(Text, default="all", comment="适用平台: all 或 [weibo,douyin,...]")
    
    # 冷却时间（分钟）
    cooldown_minutes = Column(Integer, default=60, comment="冷却时间(分钟)")
    
    # 是否启用
    is_active = Column(Boolean, default=True, comment="是否启用")
    
    # 创建/更新时间
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 关系
    events = relationship("AlertEvent", back_populates="rule", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<AlertRule(id={self.id}, name={self.name}, severity={self.severity}, active={self.is_active})>"
