"""模型解释相关请求 Schema

模块名称: model_explanation.py
模块职责: 模型解释生成接口的请求参数校验
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelExplanationGenerateRequest(BaseModel):
    """模型解释生成请求（sentiment_result_id 与 text 至少提供一个）"""
    sentiment_result_id: Optional[int] = Field(None, ge=1, description="已入库情感分析结果ID")
    text: Optional[str] = Field(None, max_length=4096, description="即时解释的原始文本")
    n_samples: int = Field(200, ge=20, le=1000, description="扰动采样数量")
