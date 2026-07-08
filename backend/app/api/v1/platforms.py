"""
平台管理 API 路由

模块名称: platforms.py
模块职责: 平台查询、状态切换接口
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Platform
from app.schemas import PlatformResponse, PlatformUpdate, UnifiedResponse

router = APIRouter()


@router.get("", response_model=UnifiedResponse[List[PlatformResponse]])
async def list_platforms(
    is_active: bool = None,
    db: Session = Depends(get_db),
):
    """
    查询平台列表
    
    Args:
        is_active: 按状态筛选，不传则返回全部
    """
    query = db.query(Platform)
    if is_active is not None:
        query = query.filter(Platform.is_active == is_active)
    
    platforms = query.order_by(Platform.sort_order).all()
    
    return {
        "code": 200,
        "data": platforms,
        "message": "success",
    }


@router.get("/{platform_id}", response_model=UnifiedResponse[PlatformResponse])
async def get_platform(
    platform_id: int,
    db: Session = Depends(get_db),
):
    """查询平台详情"""
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    return {
        "code": 200,
        "data": platform,
        "message": "success",
    }


@router.patch("/{platform_id}", response_model=UnifiedResponse[PlatformResponse])
async def update_platform(
    platform_id: int,
    update: PlatformUpdate,
    db: Session = Depends(get_db),
):
    """
    更新平台配置（切换状态等）
    
    Args:
        update: 可部分更新，只需传要修改的字段
    """
    platform = db.query(Platform).filter(Platform.id == platform_id).first()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    # 只更新传入的字段
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(platform, field, value)
    
    db.commit()
    db.refresh(platform)
    
    return {
        "code": 200,
        "data": platform,
        "message": "Platform updated successfully",
    }
