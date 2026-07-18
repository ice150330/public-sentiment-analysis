"""
高级分析 API 路由 - 趋势预测

模块名称: trend_predictions.py
模块职责: 情感/热度趋势预测 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import TrendPrediction
from app.schemas import UnifiedResponse
from app.services.trend_forecast_service import TrendForecastService

router = APIRouter()
forecast_service = TrendForecastService()


@router.get("", response_model=UnifiedResponse[dict])
async def list_predictions(
    target_type: str = None,
    target_id: int = None,
    model_type: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询预测结果列表"""
    query = db.query(TrendPrediction)
    
    if target_type:
        query = query.filter(TrendPrediction.target_type == target_type)
    if target_id:
        query = query.filter(TrendPrediction.target_id == target_id)
    if model_type:
        query = query.filter(TrendPrediction.model_type == model_type)
    
    total = query.count()
    predictions = query.order_by(desc(TrendPrediction.created_at))
    predictions = predictions.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for pred in predictions:
        items.append({
            "id": pred.id,
            "target_type": pred.target_type,
            "target_id": pred.target_id,
            "model_type": pred.model_type,
            "horizon_hours": pred.horizon_hours,
            "current_value": pred.current_value,
            "predicted_value": pred.predicted_value,
            "confidence_lower": pred.confidence_lower,
            "confidence_upper": pred.confidence_upper,
            "confidence_level": pred.confidence_level,
            "trend_direction": pred.trend_direction,
            "trend_strength": pred.trend_strength,
            "mse": pred.mse,
            "mae": pred.mae,
            "r2_score": pred.r2_score,
            "created_at": pred.created_at.isoformat() if pred.created_at else None,
        })
    
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


@router.get("/{prediction_id}", response_model=UnifiedResponse[dict])
async def get_prediction(
    prediction_id: int,
    db: Session = Depends(get_db),
):
    """获取预测详情及特征重要性"""
    detail = forecast_service.get_prediction_detail(db, prediction_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return {
        "code": 200,
        "data": detail,
        "message": "success",
    }


@router.post("/predict", response_model=UnifiedResponse[dict])
async def create_prediction(
    target_type: str = "sentiment",
    target_id: int = None,
    model_type: str = "ema",
    horizon_hours: int = 24,
    db: Session = Depends(get_db),
):
    """
    创建趋势预测
    
    Args:
        target_type: 预测目标类型 (sentiment/heat/volume)
        target_id: 目标ID(话题ID或平台ID)
        model_type: 预测模型 (linear/ema/arima)
        horizon_hours: 预测 horizon(小时)
    """
    try:
        prediction = forecast_service.create_prediction(
            db,
            target_type=target_type,
            target_id=target_id,
            model_type=model_type,
            horizon_hours=horizon_hours,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "code": 200,
        "data": prediction,
        "message": "Prediction created",
    }
