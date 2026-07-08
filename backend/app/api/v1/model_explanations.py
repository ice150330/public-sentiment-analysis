"""
高级分析 API 路由 - 模型解释

模块名称: model_explanations.py
模块职责: 情感分析模型解释、特征贡献度 API
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import SentimentResult, ModelExplanation, FeatureContribution
from app.schemas import UnifiedResponse

router = APIRouter()


@router.get("", response_model=UnifiedResponse[dict])
async def list_explanations(
    sentiment_result_id: int = None,
    method: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    db: Session = Depends(get_db),
):
    """获取模型解释详情及特征贡献度"""
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


@router.post("/explain/{sentiment_result_id}", response_model=UnifiedResponse[dict])
async def explain_sentiment(
    sentiment_result_id: int,
    method: str = "attention",
    db: Session = Depends(get_db),
):
    """
    为情感分析结果生成模型解释
    
    Args:
        sentiment_result_id: 情感分析结果ID
        method: 解释方法 (lime/shap/attention/gradient)
    """
    # 检查情感分析结果是否存在
    sentiment = db.query(SentimentResult).filter(SentimentResult.id == sentiment_result_id).first()
    if not sentiment:
        return {"code": 404, "data": None, "message": "Sentiment result not found"}
    
    # 获取话题内容
    topic = sentiment.hot_topic
    topic_title = topic.title if topic else "未知话题"
    
    # 生成解释摘要
    summary = _generate_explanation_summary(sentiment, method, topic_title)
    
    # 创建解释记录
    explanation = ModelExplanation(
        sentiment_result_id=sentiment_result_id,
        method=method,
        summary=summary,
        input_features_json=f'{{"topic_title": "{topic_title}", "sentiment_label": "{sentiment.sentiment_label}", "confidence": {sentiment.confidence}}}',
        explanation_json=f'{{"method": "{method}", "top_features": ["情感关键词", "句式结构", "上下文语境"]}}',
    )
    db.add(explanation)
    db.commit()
    db.refresh(explanation)
    
    # 生成特征贡献度（模拟）
    features = _generate_feature_contributions(sentiment, topic_title)
    
    for i, (feature_name, feature_value, contribution) in enumerate(features):
        feature = FeatureContribution(
            explanation_id=explanation.id,
            feature_name=feature_name,
            feature_value=feature_value,
            contribution=contribution,
            importance_rank=i + 1,
        )
        db.add(feature)
    
    db.commit()
    
    return {
        "code": 200,
        "data": {
            "explanation_id": explanation.id,
            "sentiment_result_id": sentiment_result_id,
            "method": method,
            "summary": summary,
            "features": [
                {"name": f[0], "value": f[1], "contribution": f[2]}
                for f in features
            ],
        },
        "message": "Explanation generated",
    }


def _generate_explanation_summary(sentiment, method, topic_title):
    """生成解释摘要"""
    label = sentiment.sentiment_label
    confidence = sentiment.confidence
    
    if label == "positive":
        sentiment_desc = "正面"
        reason = "关键词包含积极情绪表达"
    elif label == "negative":
        sentiment_desc = "负面"
        reason = "关键词包含消极情绪或争议性内容"
    else:
        sentiment_desc = "中性"
        reason = "内容客观陈述，情感倾向不明显"
    
    summaries = {
        "lime": f"LIME解释：模型将'{topic_title}'判定为{sentiment_desc}情感，主要原因是{reason}。置信度{confidence:.2%}。",
        "shap": f"SHAP解释：'{topic_title}'的{sentiment_desc}判定由多个特征共同决定，关键特征贡献了{confidence:.2%}的置信度。",
        "attention": f"注意力解释：模型在处理'{topic_title}'时，注意力主要集中在情感关键词上，导致{sentiment_desc}判定。",
        "gradient": f"梯度解释：'{topic_title}'中的关键词汇对{sentiment_desc}判定产生了最强梯度响应。",
    }
    
    return summaries.get(method, f"模型解释：'{topic_title}'被判定为{sentiment_desc}情感，置信度{confidence:.2%}。")


def _generate_feature_contributions(sentiment, topic_title):
    """生成特征贡献度（模拟）"""
    # 从话题标题中提取关键词（简单分词）
    words = topic_title[:30].split() if topic_title else ["未知"]
    
    features = []
    
    # 添加关键词特征
    for i, word in enumerate(words[:5]):
        # 根据情感标签设置贡献方向
        if sentiment.sentiment_label == "positive":
            contribution = 0.1 + 0.05 * (5 - i)
        elif sentiment.sentiment_label == "negative":
            contribution = -(0.1 + 0.05 * (5 - i))
        else:
            contribution = 0.0
        
        features.append((f"关键词_{word}", word, contribution))
    
    # 添加通用特征
    features.extend([
        ("文本长度", "中等", 0.02),
        ("标点密度", "正常", -0.01),
        ("情感强度", "高" if sentiment.confidence > 0.8 else "中", sentiment.confidence * 0.1),
    ])
    
    # 按贡献度绝对值排序
    features.sort(key=lambda x: abs(x[2]), reverse=True)
    
    return features
