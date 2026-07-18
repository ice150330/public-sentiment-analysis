"""
情感分析 API 路由

模块名称: sentiment.py
模块职责: 情感分析、结果查询接口
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.ml.sentiment_transformers import get_analyzer
from app.models import HotTopic, SentimentResult, Platform
from app.schemas import (
    SentimentAnalyzeRequest,
    SentimentAnalyzeBatchRequest,
    SentimentAnalyzeResponse,
    SentimentResultResponse,
    SentimentQueryParams,
    UnifiedResponse,
)
from app.services.model_registry_service import model_version_payload, select_sentiment_model_version
from app.services.sentiment_service import SentimentService

router = APIRouter()


@router.post("/analyze", response_model=UnifiedResponse[SentimentAnalyzeResponse])
async def analyze_text(
    request: SentimentAnalyzeRequest,
    db: Session = Depends(get_db),
):
    """
    分析单条文本的情感倾向

    Args:
        request: 包含待分析文本
    """
    model_version = select_sentiment_model_version(db)
    model_payload = model_version_payload(model_version)
    if model_payload["provider"] == "transformers":
        raw = await get_analyzer().analyze_async(request.text)
        positive = float(raw.get("positive_score") or 0)
        negative = float(raw.get("negative_score") or 0)
        neutral = float(raw.get("neutral_score") or max(0.0, 1 - positive - negative))
        label = raw.get("sentiment") or "neutral"
        result = {
            "sentiment_label": label if label in {"positive", "negative", "neutral"} else "neutral",
            "confidence": float(raw.get("confidence") or max(positive, negative, neutral)),
            "scores": {
                "positive": round(max(0.0, min(1.0, positive)), 4),
                "negative": round(max(0.0, min(1.0, negative)), 4),
                "neutral": round(max(0.0, min(1.0, neutral)), 4),
            },
        }
    else:
        service = SentimentService(db=None)  # 纯文本分析不需要数据库写入
        result = service.analyze_text(request.text)

    label = result.get("sentiment_label") or result.get("label")

    return {
        "code": 200,
        "data": {
            "text": request.text,
            "sentiment_label": label,
            "confidence": result["confidence"],
            "scores": result["scores"],
            "model_version": model_version.version,
            "analyzed_at": datetime.now(),
        },
        "message": "success",
    }


@router.post("/analyze/batch", response_model=UnifiedResponse[List[SentimentAnalyzeResponse]])
async def analyze_batch(
    request: SentimentAnalyzeBatchRequest,
    db: Session = Depends(get_db),
):
    """批量分析文本情感"""
    model_version = select_sentiment_model_version(db)
    model_payload = model_version_payload(model_version)
    if model_payload["provider"] == "transformers":
        raw_results = await get_analyzer().analyze_batch_async(request.texts)
        results = []
        for raw in raw_results:
            positive = float(raw.get("positive_score") or 0)
            negative = float(raw.get("negative_score") or 0)
            neutral = float(raw.get("neutral_score") or max(0.0, 1 - positive - negative))
            label = raw.get("sentiment") or "neutral"
            results.append({
                "sentiment_label": label if label in {"positive", "negative", "neutral"} else "neutral",
                "confidence": float(raw.get("confidence") or max(positive, negative, neutral)),
                "scores": {
                    "positive": round(max(0.0, min(1.0, positive)), 4),
                    "negative": round(max(0.0, min(1.0, negative)), 4),
                    "neutral": round(max(0.0, min(1.0, neutral)), 4),
                },
            })
    else:
        service = SentimentService(db=None)
        results = service.analyze_batch(request.texts)

    data = []
    for text, result in zip(request.texts, results):
        data.append({
            "text": text,
            "sentiment_label": result.get("sentiment_label") or result.get("label"),
            "confidence": result["confidence"],
            "scores": result["scores"],
            "model_version": model_version.version,
            "analyzed_at": datetime.now(),
        })

    return {
        "code": 200,
        "data": data,
        "message": "success",
    }


@router.get("/results", response_model=UnifiedResponse[dict])
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
    """查询情感分析结果列表（支持分页）"""
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

    # 组装响应数据
    items = []
    for result in results:
        item = SentimentResultResponse.from_orm(result).dict()
        item["topic_title"] = result.hot_topic.title if result.hot_topic else None
        item["platform_name"] = result.hot_topic.platform.display_name if result.hot_topic and result.hot_topic.platform else None
        items.append(item)

    total_pages = (total + page_size - 1) // page_size

    return {
        "code": 200,
        "data": {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        },
        "message": "success",
    }
