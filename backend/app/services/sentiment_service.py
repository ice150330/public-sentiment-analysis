"""
情感分析服务层（生产环境版）

模块名称: sentiment_service.py
模块职责: 情感分析模型调用、批量分析、结果保存

当前使用 Sklearn 轻量模型（无 GPU/无网络环境）。
可替换为 BERT 模型（需下载预训练权重）。
"""

import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from app.models import HotTopic, SentimentResult

# 尝试加载 Sklearn 模型（如果存在）
_model = None

def _get_model():
    """懒加载模型"""
    global _model
    if _model is None:
        model_path = os.path.join(os.path.dirname(__file__), '../../model_output/sklearn_model.pkl')
        if os.path.exists(model_path):
            from app.ml.sklearn_model import SklearnSentimentModel
            _model = SklearnSentimentModel(model_path)
            logging.info(f"Loaded sentiment model from {model_path}")
        else:
            logging.warning("Sentiment model not found, using mock predictions")
    return _model

logger = logging.getLogger(__name__)


class SentimentService:
    """情感分析服务"""
    
    def __init__(self, db: Session):
        self.db = db
        self.model = _get_model()
    
    def analyze_text(self, text: str) -> Dict:
        """
        分析单条文本情感
        
        Args:
            text: 待分析文本
            
        Returns:
            Dict: 分析结果
        """
        if self.model:
            return self.model.predict([text])[0]
        else:
            return self._mock_analyze(text)
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        批量分析文本
        
        Args:
            texts: 文本列表
            
        Returns:
            List[Dict]: 分析结果列表
        """
        if self.model:
            return self.model.predict(texts)
        else:
            return [self._mock_analyze(text) for text in texts]
    
    def analyze_unprocessed_topics(self, limit: int = 100) -> int:
        """
        分析未处理的热榜数据
        
        Args:
            limit: 最大处理数量
            
        Returns:
            int: 实际处理数量
        """
        # 查询未分析的热榜数据
        unprocessed = self.db.query(HotTopic).outerjoin(
            SentimentResult
        ).filter(
            SentimentResult.id == None
        ).limit(limit).all()
        
        count = 0
        for topic in unprocessed:
            try:
                # 分析标题 + 摘要
                text = f"{topic.title} {topic.content_summary or ''}"
                result = self.analyze_text(text)
                
                # 保存结果
                sentiment = SentimentResult(
                    topic_id=topic.id,
                    sentiment_label=result["sentiment_label"],
                    confidence=result["confidence"],
                    positive_score=result["scores"]["positive"],
                    negative_score=result["scores"]["negative"],
                    neutral_score=result["scores"]["neutral"],
                    model_version="sklearn-v1",
                    analyzed_at=datetime.now(),
                )
                
                self.db.add(sentiment)
                count += 1
                
            except Exception as e:
                logger.error(f"Failed to analyze topic {topic.id}: {e}")
                continue
        
        self.db.commit()
        return count
    
    def _mock_analyze(self, text: str) -> Dict:
        """
        模拟情感分析（备用）
        """
        import random
        
        labels = ["positive", "negative", "neutral"]
        label = random.choice(labels)
        
        if label == "positive":
            scores = {"positive": 0.85, "negative": 0.05, "neutral": 0.10}
        elif label == "negative":
            scores = {"positive": 0.10, "negative": 0.80, "neutral": 0.10}
        else:
            scores = {"positive": 0.20, "negative": 0.15, "neutral": 0.65}
        
        return {
            "label": label,
            "confidence": max(scores.values()),
            "scores": scores,
        }
