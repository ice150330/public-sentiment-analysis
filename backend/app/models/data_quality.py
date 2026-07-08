"""
数据质量模型

模块名称: data_quality.py
模块职责: 数据质量检查批次、问题记录 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class DataQualityRun(Base):
    """数据质量检查批次表"""
    __tablename__ = "data_quality_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(32), nullable=False, comment="检查类型: daily/weekly/manual")
    status = Column(String(16), default="running", comment="状态: running/completed/failed")
    summary_json = Column(Text, comment="检查结果摘要(JSON)")
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    issues = relationship("DataQualityIssue", back_populates="run", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<DataQualityRun(id={self.id}, type={self.run_type}, status={self.status})>"


class DataQualityIssue(Base):
    """数据质量问题表"""
    __tablename__ = "data_quality_issues"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("data_quality_runs.id", ondelete="CASCADE"), comment="关联检查批次")
    
    issue_type = Column(String(32), nullable=False, comment="问题类型: missing_field/duplicate/low_heat/abnormal_time/failed_crawl/etc")
    platform_id = Column(Integer, ForeignKey("platforms.id", ondelete="SET NULL"), comment="关联平台")
    topic_id = Column(Integer, ForeignKey("hot_topics.id", ondelete="SET NULL"), comment="关联话题")
    
    severity = Column(String(8), default="warning", comment="严重级别: critical/warning/info")
    status = Column(String(16), default="open", comment="状态: open/fixed/ignored")
    description = Column(Text, comment="问题描述")
    suggestion = Column(Text, comment="处理建议")
    
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime)
    
    run = relationship("DataQualityRun", back_populates="issues")
    platform = relationship("Platform")
    topic = relationship("HotTopic")
    
    def __repr__(self) -> str:
        return f"<DataQualityIssue(id={self.id}, type={self.issue_type}, status={self.status})>"
