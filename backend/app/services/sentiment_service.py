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

import jieba
from sqlalchemy.orm import Session

from app.models import HotTopic, SentimentResult

logger = logging.getLogger(__name__)

# 轻量级规则兜底情感词库（确定性、离线可用）
_POSITIVE_WORDS = {
    "好", "棒", "赞", "优秀", "喜欢", "爱", "支持", "成功", "惊喜", "满意",
    "开心", "快乐", "幸福", "美好", "顺利", "值得", "推荐", "优秀", "出色",
}
_NEGATIVE_WORDS = {
    "坏", "差", "糟", "失败", "讨厌", "恨", "反对", "失望", "愤怒", "难过",
    "悲伤", "恐惧", "垃圾", "恶心", "可怕", "糟糕", "悲剧", "遗憾", "不满",
}


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
            logger.info(f"Loaded sentiment model from {model_path}")
        else:
            logger.warning("Sentiment model not found, using rule-based fallback")
    return _model


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
            try:
                return self._normalize_result(self.model.predict([text])[0])
            except Exception as e:
                logger.warning(f"Sentiment model prediction failed, using rule-based fallback: {e}")

        return self._normalize_result(self._rule_fallback(text))
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        批量分析文本
        
        Args:
            texts: 文本列表
            
        Returns:
            List[Dict]: 分析结果列表
        """
        if self.model:
            try:
                return [self._normalize_result(item) for item in self.model.predict(texts)]
            except Exception as e:
                logger.warning(f"Sentiment batch prediction failed, using rule-based fallback: {e}")

        return [self._normalize_result(self._rule_fallback(text)) for text in texts]
    
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
                label = result.get("sentiment_label") or result.get("label")
                sentiment = SentimentResult(
                    topic_id=topic.id,
                    sentiment_label=label,
                    confidence=result["confidence"],
                    positive_score=result["scores"]["positive"],
                    negative_score=result["scores"]["negative"],
                    neutral_score=result["scores"]["neutral"],
                    model_version=result.get("model_version", "classic-v1"),
                    analyzed_at=datetime.now(),
                )
                
                self.db.add(sentiment)
                count += 1
                
            except Exception as e:
                logger.error(f"Failed to analyze topic {topic.id}: {e}")
                continue
        
        self.db.commit()
        return count

    def _normalize_result(self, result: Dict) -> Dict:
        """Keep model and fallback outputs compatible with API and DB callers."""
        if "label" not in result and "sentiment_label" in result:
            result["label"] = result["sentiment_label"]
        if "sentiment_label" not in result and "label" in result:
            result["sentiment_label"] = result["label"]
        return result

    def _rule_fallback(self, text: str) -> Dict:
        """
        基于轻量级词库的规则情感分析（确定性兜底）

        当 Sklearn 模型不可用时使用，保证结果稳定可复现。
        """
        if not text:
            return {
                "label": "neutral",
                "confidence": 1.0,
                "scores": {"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                "model_version": "rule-fallback-v1",
            }

        tokens = set(jieba.lcut(text))
        pos = len(tokens & _POSITIVE_WORDS)
        neg = len(tokens & _NEGATIVE_WORDS)

        if pos > neg:
            label = "positive"
            confidence = min(0.95, 0.55 + 0.08 * (pos - neg))
        elif neg > pos:
            label = "negative"
            confidence = min(0.95, 0.55 + 0.08 * (neg - pos))
        else:
            label = "neutral"
            confidence = 0.75

        if label == "positive":
            scores = {"positive": confidence, "negative": (1 - confidence) * 0.3, "neutral": (1 - confidence) * 0.7}
        elif label == "negative":
            scores = {"positive": (1 - confidence) * 0.3, "negative": confidence, "neutral": (1 - confidence) * 0.7}
        else:
            scores = {"positive": (1 - confidence) * 0.45, "negative": (1 - confidence) * 0.45, "neutral": confidence}

        total = sum(scores.values())
        scores = {k: round(v / total, 4) for k, v in scores.items()}

        return {
            "label": label,
            "confidence": round(confidence, 4),
            "scores": scores,
            "model_version": "rule-fallback-v1",
        }
