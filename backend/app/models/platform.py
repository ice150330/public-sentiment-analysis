"""
平台配置模型

模块名称: platform.py
模块职责: 平台配置 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, func

from app.core.database import Base


class Platform(Base):
    """平台配置表"""
    __tablename__ = "platforms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), nullable=False, unique=True, comment="英文标识: weibo, douyin, etc.")
    display_name = Column(String(64), nullable=False, comment="中文显示名: 微博")
    base_url = Column(String(255), comment="平台首页URL")
    crawl_config = Column(JSON, comment="爬虫配置(JSON): headers, selectors, ...")
    is_active = Column(Boolean, default=True, comment="是否启用采集")
    sort_order = Column(Integer, default=0, comment="排序权重")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Platform(id={self.id}, name={self.name}, active={self.is_active})>"
