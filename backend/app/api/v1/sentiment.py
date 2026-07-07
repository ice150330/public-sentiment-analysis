"""
情感分析 API 路由

模块名称: sentiment.py
模块职责: 情感分析、结果查询接口

注意: 当前为占位实现，情感分析模型加载后需替换实际分析逻辑
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import HotTopic, SentimentResult, Platform
from app.schemas import (
    SentimentAnalyzeRequest,
    SentimentAnalyzeBatchRequest,
    SentimentAnalyzeResponse,
    SentimentResultResponse,
    SentimentQueryParams,
    UnifiedResponse,
)

router = APIRouter()


# 模拟情感分析（实际实现需加载 BERT 模型）
def mock_analyze(text: str) -> dict:
    """
    模拟情感分析，返回随机结果
    
    TODO: 替换为实际 BERT 模型推理
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


@router.post("/analyze", response_model=UnifiedResponse[SentimentAnalyzeResponse])
async def analyze_text(
    request: SentimentAnalyzeRequest,
):
    """
    分析单条文本的情感倾向
    
    Args:
        request: 包含待分析文本
    """
    result = mock_analyze(request.text)
    
    return {
        "code": 200,
        "data": {
            "text": request.text,
            "sentiment_label": result["label"],
            "confidence": result["confidence"],
            "scores": result["scores"],
            "model_version": "mock-v1",
            "analyzed_at": datetime.now(),
        },
        "message": "success",
    }


@router.post("/analyze/batch", response_model=UnifiedResponse[List[SentimentAnalyzeResponse]])
async def analyze_batch(
    request: SentimentAnalyzeBatchRequest,
):
    """批量分析文本情感"""
    results = []
    for text in request.texts:
        result = mock_analyze(text)
        results.append({
            "text": text,
            "sentiment_label": result["label"],
            "confidence": result["confidence"],
            "scores": result["scores"],
            "model_version": "mock-v1",
            "analyzed_at": datetime.now(),
        })
    
    return {
        "code": 200,
        "data": results,
        "message": "success",
    }


@router.get("/results", response_model=UnifiedResponse[List[SentimentResultResponse]])
async def list_sentiment_results(
    label: str = None,
    platform: str = None,
    min_confidence: float = Query(0.0, ge=0, le=1),
    start_time: datetime = None,
    end_time: datetime = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询情感分析结果列表"""
    query = db.query(SentimentResult).join(HotTopic).join(Platform)
    
    if label:
        query = query.filter(SentimentResult.sentiment_label == label)
    if platform:
        query = query.filter(Platform.name == platform)
    if min_confidence > 0:
        query = query.filter(SentimentResult.confidence >= min_confidence)
    if start_time:
        query = query.filter(SentimentResult.analyzed_at >= start_time)
    if end_time:
        query = query.filter(SentimentResult.analyzed_at <= end_time)
    
    total = query.count()
    results = query.order_by(desc(SentimentResult.analyzed_at))
    results = results.offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "code": 200,
        "data": results,
        "message": "success",
    }
