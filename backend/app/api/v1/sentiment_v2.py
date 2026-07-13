from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from app.ml.sentiment_transformers import get_analyzer

router = APIRouter()

class SentimentAnalyzeRequest(BaseModel):
    text: str

class BatchAnalyzeRequest(BaseModel):
    texts: List[str]

class SentimentAnalyzeResponse(BaseModel):
    code: int
    data: Dict
    message: str

class BatchAnalyzeResponse(BaseModel):
    code: int
    data: List[Dict]
    message: str


@router.post("/v2/analyze", response_model=SentimentAnalyzeResponse, tags=["情感分析"])
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
            "data": result,
            "message": "success",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/v2/batch", response_model=BatchAnalyzeResponse, tags=["情感分析"])
async def analyze_batch_v2(request: BatchAnalyzeRequest):
    """批量 Transformers 情感分析"""
    try:
        analyzer = get_analyzer()
        results = await analyzer.analyze_batch_async(request.texts)
        return {
            "code": 200,
            "data": results,
            "message": "success",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")
