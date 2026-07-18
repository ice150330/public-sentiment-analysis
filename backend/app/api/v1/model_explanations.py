"""
高级分析 API 路由 - 模型解释

模块名称: model_explanations.py
模块职责: 情感分析模型解释、特征贡献度 API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.auth import require_analyst
from app.core.database import get_db
from app.models import ModelExplanation, FeatureContribution, User
from app.schemas import ModelExplanationGenerateRequest, UnifiedResponse
from app.services.audit_service import write_audit_log
from app.services.model_explanation_service import ModelExplanationService

router = APIRouter()


@router.get("", response_model=UnifiedResponse[dict])
async def list_explanations(
    sentiment_result_id: int = None,
    method: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """查询模型解释结果列表"""
    query = db.query(ModelExplanation)

    if sentiment_result_id:
        query = query.filter(ModelExplanation.sentiment_result_id == sentiment_result_id)
    if method:
        query = query.filter(ModelExplanation.method == method)

    total = query.count()
    explanations = query.order_by(desc(ModelExplanation.created_at))
    explanations = explanations.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for exp in explanations:
        items.append({
            "id": exp.id,
            "sentiment_result_id": exp.sentiment_result_id,
            "method": exp.method,
            "summary": exp.summary,
            "created_at": exp.created_at.isoformat() if exp.created_at else None,
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


@router.get("/{explanation_id}", response_model=UnifiedResponse[dict])
async def get_explanation(
    explanation_id: int,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """获取模型解释详情及特征贡献度（需 analyst 及以上权限）"""
    exp = db.query(ModelExplanation).filter(ModelExplanation.id == explanation_id).first()
    if not exp:
        return {"code": 404, "data": None, "message": "Explanation not found"}

    # 获取特征贡献度
    features = db.query(FeatureContribution).filter(
        FeatureContribution.explanation_id == explanation_id,
    ).order_by(desc(FeatureContribution.importance_rank)).all()

    feature_items = []
    for f in features:
        feature_items.append({
            "id": f.id,
            "feature_name": f.feature_name,
            "feature_value": f.feature_value,
            "contribution": f.contribution,
            "importance_rank": f.importance_rank,
        })

    # 获取关联的情感分析结果
    sentiment = exp.sentiment_result

    return {
        "code": 200,
        "data": {
            "explanation": {
                "id": exp.id,
                "sentiment_result_id": exp.sentiment_result_id,
                "method": exp.method,
                "summary": exp.summary,
                "input_features_json": exp.input_features_json,
                "explanation_json": exp.explanation_json,
                "created_at": exp.created_at.isoformat() if exp.created_at else None,
            },
            "sentiment_result": {
                "id": sentiment.id,
                "sentiment_label": sentiment.sentiment_label,
                "confidence": sentiment.confidence,
                "topic_id": sentiment.topic_id,
                "analyzed_at": sentiment.analyzed_at.isoformat() if sentiment.analyzed_at else None,
            } if sentiment else None,
            "features": feature_items,
        },
        "message": "success",
    }


@router.post("/generate", response_model=UnifiedResponse[dict])
async def generate_explanation(
    request: ModelExplanationGenerateRequest,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """
    生成 LIME 风格扰动解释（需 analyst 及以上权限）

    Args:
        request: sentiment_result_id（解释已入库结果）或 text（即时解释）
    """
    service = ModelExplanationService(db)
    try:
        if request.sentiment_result_id is not None:
            result = service.explain_sentiment_result(
                request.sentiment_result_id,
                n_samples=request.n_samples,
            )
            if result is None:
                return {"code": 404, "data": None, "message": "Sentiment result not found"}
        elif request.text:
            result = service.explain_text(request.text, n_samples=request.n_samples)
        else:
            return {"code": 400, "data": None, "message": "text 或 sentiment_result_id 至少提供一个"}
    except ValueError as exc:
        return {"code": 400, "data": None, "message": str(exc)}

    write_audit_log(
        db,
        operator=current_user.username,
        action="generate_model_explanation",
        target_type="model_explanation",
        target_id=result.get("explanation_id") or request.sentiment_result_id,
        note=result.get("summary"),
    )
    db.commit()

    return {
        "code": 200,
        "data": result,
        "message": "Explanation generated",
    }


@router.post("/explain/{sentiment_result_id}", response_model=UnifiedResponse[dict])
async def explain_sentiment(
    sentiment_result_id: int,
    method: str = "lime",
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
):
    """
    为情感分析结果生成模型解释（兼容旧入口，内部走真实扰动解释服务）

    Args:
        sentiment_result_id: 情感分析结果ID
        method: 解释方法（保留兼容参数，当前固定使用 lime 扰动解释）
    """
    service = ModelExplanationService(db)
    try:
        result = service.explain_sentiment_result(sentiment_result_id)
    except ValueError as exc:
        return {"code": 400, "data": None, "message": str(exc)}
    if result is None:
        return {"code": 404, "data": None, "message": "Sentiment result not found"}

    return {
        "code": 200,
        "data": {
            "explanation_id": result["explanation_id"],
            "sentiment_result_id": sentiment_result_id,
            "method": result["method"],
            "summary": result["summary"],
            "features": [
                {"name": item["token"], "value": item["token"], "contribution": item["contribution"]}
                for item in result["tokens"]
            ],
        },
        "message": "Explanation generated",
    }
