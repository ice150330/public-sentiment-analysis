"""
系统配置模型

模块名称: system_config.py
模块职责: 系统级配置项 ORM 模型（如爬虫定时配置、全局开关等）
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func

from app.core.database import Base


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(64), nullable=False, unique=True, comment="配置键")
    config_value = Column(Text, nullable=False, comment="配置值")
    description = Column(String(255), comment="配置说明")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<SystemConfig(key={self.config_key}, value={self.config_value[:30]}...)>"
