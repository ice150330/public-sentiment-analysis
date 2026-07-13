from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from app.ml.sentiment_transformers import get_analyzer
from app.schemas import (
    SentimentAnalyzeBatchRequest,
    SentimentAnalyzeRequest,
    SentimentAnalyzeResponse,
    UnifiedResponse,
)

router = APIRouter()

def _normalize_result(text: str, result: dict) -> dict:
    positive = float(result.get("positive_score") or 0)
    negative = float(result.get("negative_score") or 0)
    neutral = float(result.get("neutral_score") or max(0.0, 1 - positive - negative))
    label = result.get("sentiment") or result.get("sentiment_label") or "neutral"

    if label not in {"positive", "negative", "neutral"}:
        label = "neutral"

    return {
        "text": text,
        "sentiment_label": label,
        "confidence": float(result.get("confidence") or max(positive, negative, neutral)),
        "scores": {
            "positive": round(max(0.0, min(1.0, positive)), 4),
            "negative": round(max(0.0, min(1.0, negative)), 4),
            "neutral": round(max(0.0, min(1.0, neutral)), 4),
        },
        "model_version": result.get("model") or result.get("model_version") or "transformers-v2-fallback",
        "analyzed_at": datetime.now(),
    }


@router.post("/v2/analyze", response_model=UnifiedResponse[SentimentAnalyzeResponse], tags=["情感分析"])
async def analyze_v2(request: SentimentAnalyzeRequest):
    """
    Transformers 深度学习情感分析（增强版）
    
    - 现有 /analyze: 基于规则/词典，速度快
    - 本接口: 基于 BERT/RoBERTa，准确率更高
    """
    try:
        analyzer = get_analyzer()
        result = await analyzer.analyze_async(request.text)
        return {
            "code": 200,
            "data": _normalize_result(request.text, result),
            "message": "success",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/v2/batch", response_model=UnifiedResponse[List[SentimentAnalyzeResponse]], tags=["情感分析"])
async def analyze_batch_v2(request: SentimentAnalyzeBatchRequest):
    """批量 Transformers 情感分析"""
    try:
        analyzer = get_analyzer()
        results = await analyzer.analyze_batch_async(request.texts)
        return {
            "code": 200,
            "data": [_normalize_result(text, result) for text, result in zip(request.texts, results)],
            "message": "success",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")
