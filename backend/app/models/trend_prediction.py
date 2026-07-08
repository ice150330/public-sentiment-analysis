"""
高级分析模型 - 趋势预测

模块名称: trend_prediction.py
模块职责: 情感趋势预测结果 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TrendPrediction(Base):
    """趋势预测结果表"""
    __tablename__ = "trend_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 预测目标
    target_type = Column(String(32), nullable=False, comment="预测目标类型: sentiment/heat/volume")
    target_id = Column(Integer, comment="关联目标ID(话题或平台)")
    
    # 预测参数
    model_type = Column(String(32), default="linear", comment="预测模型: linear/ema/arima/lstm")
    horizon_hours = Column(Integer, default=24, comment="预测 horizon(小时)")
    params_json = Column(Text, comment="模型参数(JSON)")
    
    # 预测结果
    current_value = Column(Float, comment="当前值")
    predicted_value = Column(Float, comment="预测值")
    confidence_lower = Column(Float, comment="置信区间下限")
    confidence_upper = Column(Float, comment="置信区间上限")
    confidence_level = Column(Float, default=0.95, comment="置信水平")
    
    # 趋势方向
    trend_direction = Column(String(16), comment="趋势方向: up/down/stable")
    trend_strength = Column(Float, comment="趋势强度 0-1")
    
    # 历史拟合度
    mse = Column(Float, comment="均方误差")
    mae = Column(Float, comment="平均绝对误差")
    r2_score = Column(Float, comment="R² 分数")
    
    created_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self) -> str:
        return f"<TrendPrediction(id={self.id}, target={self.target_type}, direction={self.trend_direction})>"


class PredictionFeature(Base):
    """预测特征重要性表"""
    __tablename__ = "prediction_features"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, ForeignKey("trend_predictions.id", ondelete="CASCADE"), nullable=False)
    
    feature_name = Column(String(64), nullable=False, comment="特征名称")
    feature_value = Column(Float, comment="特征值")
    importance_score = Column(Float, comment="重要性分数")
    
    created_at = Column(DateTime, server_default=func.now())
    
    prediction = relationship("TrendPrediction")
    
    def __repr__(self) -> str:
        return f"<PredictionFeature(prediction={self.prediction_id}, feature={self.feature_name}, importance={self.importance_score})>"
