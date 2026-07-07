"""
采集日志模型

模块名称: crawl_log.py
模块职责: 采集日志 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class CrawlLog(Base):
    """采集日志表"""
    __tablename__ = "crawl_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(16), nullable=False, comment="success | failed | partial")
    records_count = Column(Integer, default=0, comment="采集记录数")
    error_message = Column(Text, comment="错误详情")
    started_at = Column(DateTime, nullable=False, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, server_default=func.now())
    
    # 关系
    platform = relationship("Platform", backref="crawl_logs")
    
    def __repr__(self) -> str:
        return f"<CrawlLog(id={self.id}, platform={self.platform_id}, status={self.status})>"
