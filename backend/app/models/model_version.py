"""
模型版本管理

模块名称: model_version.py
模块职责: 模型版本、评估指标 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, func

from app.core.database import Base


class ModelVersion(Base):
    """模型版本表"""
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(32), nullable=False, comment="版本号: v1.0.0")
    model_name = Column(String(64), nullable=False, comment="模型名称")
    task_type = Column(String(32), comment="任务类型: sentiment/classification/etc")
    device = Column(String(16), comment="运行设备: cpu/cuda")
    
    metrics_json = Column(Text, comment="评估指标(JSON): accuracy/precision/recall/f1")
    config_json = Column(Text, comment="模型配置(JSON)")
    
    is_active = Column(Boolean, default=False, comment="是否当前激活版本")
    description = Column(Text, comment="版本说明")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<ModelVersion(id={self.id}, version={self.version}, active={self.is_active})>"
