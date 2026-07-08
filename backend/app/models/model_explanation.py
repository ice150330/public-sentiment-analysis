"""
高级分析模型 - 模型解释

模块名称: model_explanation.py
模块职责: 情感分析模型解释结果 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ModelExplanation(Base):
    """模型解释结果表"""
    __tablename__ = "model_explanations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sentiment_result_id = Column(Integer, ForeignKey("sentiment_results.id", ondelete="CASCADE"), nullable=False, comment="关联情感分析结果")
    
    # 解释方法
    method = Column(String(32), nullable=False, comment="解释方法: lime/shap/attention/gradient")
    
    # 解释摘要
    summary = Column(Text, comment="解释摘要")
    
    # 原始输入特征
    input_features_json = Column(Text, comment="输入特征(JSON)")
    
    # 解释结果
    explanation_json = Column(Text, comment="解释结果(JSON)")
    
    created_at = Column(DateTime, server_default=func.now())
    
    sentiment_result = relationship("SentimentResult")
    
    def __repr__(self) -> str:
        return f"<ModelExplanation(id={self.id}, method={self.method}, result_id={self.sentiment_result_id})>"


class FeatureContribution(Base):
    """特征贡献度表"""
    __tablename__ = "feature_contributions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    explanation_id = Column(Integer, ForeignKey("model_explanations.id", ondelete="CASCADE"), nullable=False)
    
    feature_name = Column(String(128), nullable=False, comment="特征名称/词")
    feature_value = Column(Text, comment="特征值/词文本")
    contribution = Column(Float, comment="贡献度(-1到1, 负=负面贡献)")
    importance_rank = Column(Integer, comment="重要性排序")
    
    created_at = Column(DateTime, server_default=func.now())
    
    explanation = relationship("ModelExplanation")
    
    def __repr__(self) -> str:
        return f"<FeatureContribution(explanation={self.explanation_id}, feature={self.feature_name}, contribution={self.contribution})>"
