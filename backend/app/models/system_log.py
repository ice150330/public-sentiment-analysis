"""
系统日志模型

模块名称: system_log.py
模块职责: 系统日志、审计日志 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.core.database import Base


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(16), nullable=False, comment="日志级别: DEBUG/INFO/WARNING/ERROR/CRITICAL")
    module = Column(String(64), comment="模块名")
    event = Column(String(128), comment="事件名")
    message = Column(Text, comment="日志内容")
    payload_json = Column(Text, comment="附加数据(JSON)")
    request_id = Column(String(32), comment="请求ID")
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self) -> str:
        return f"<SystemLog(id={self.id}, level={self.level}, module={self.module})>"


class AuditLog(Base):
    """操作审计日志表"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    operator = Column(String(64), nullable=False, comment="操作人")
    action = Column(String(32), nullable=False, comment="操作类型: create/update/delete/enable/disable/trigger/etc")
    target_type = Column(String(32), comment="操作对象类型: platform/rule/config/etc")
    target_id = Column(String(64), comment="操作对象ID")
    before_json = Column(Text, comment="操作前数据(JSON)")
    after_json = Column(Text, comment="操作后数据(JSON)")
    note = Column(Text, comment="备注")
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, operator={self.operator}, action={self.action})>"
