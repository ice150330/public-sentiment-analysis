"""
平台管理 API 路由

模块名称: platforms.py
模块职责: 平台查询、状态切换、平台监测接口
"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import get_db
from app.models import Platform, CrawlLog, HotTopic, SentimentResult
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


@router.get("/{platform_id:int}", response_model=UnifiedResponse[PlatformResponse])
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


@router.patch("/{platform_id:int}", response_model=UnifiedResponse[PlatformResponse])
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


# ========== 平台监测 ==========

@router.get("/monitoring/matrix", response_model=UnifiedResponse[dict])
async def get_platform_monitoring_matrix(
    db: Session = Depends(get_db),
):
    """
    获取六平台监测状态矩阵
    
    返回各平台的话题数、平均热度、负面占比、延迟、状态
    """
    platforms = db.query(Platform).filter(Platform.is_active == True).all()
    
    matrix = []
    for platform in platforms:
        # 最近采集日志
        last_log = db.query(CrawlLog).filter(
            CrawlLog.platform_id == platform.id
        ).order_by(desc(CrawlLog.completed_at)).first()
        
        # 最近 24 小时话题数
        last_24h = datetime.now() - timedelta(hours=24)
        topic_count = db.query(HotTopic).filter(
            HotTopic.platform_id == platform.id,
            HotTopic.crawl_time >= last_24h,
        ).count()
        
        # 平均热度
        avg_heat = db.query(func.avg(HotTopic.heat_score)).filter(
            HotTopic.platform_id == platform.id,
            HotTopic.crawl_time >= last_24h,
        ).scalar()
        
        # 负面占比
        negative_count = db.query(HotTopic).join(SentimentResult).filter(
            HotTopic.platform_id == platform.id,
            HotTopic.crawl_time >= last_24h,
            SentimentResult.sentiment_label == "negative",
        ).count()
        
        negative_ratio = round(negative_count * 100 / topic_count, 2) if topic_count > 0 else 0
        
        # 延迟（分钟）
        delay_minutes = None
        if last_log and last_log.completed_at:
            delay_minutes = int((datetime.now() - last_log.completed_at).total_seconds() / 60)
        
        # 状态判断
        status = "healthy"
        if not last_log:
            status = "never"
        elif last_log.status == "failed":
            status = "error"
        elif delay_minutes and delay_minutes > 120:
            status = "stale"
        
        matrix.append({
            "platform_id": platform.id,
            "platform_name": platform.name,
            "display_name": platform.display_name,
            "topic_count": topic_count,
            "avg_heat": round(avg_heat, 2) if avg_heat else 0,
            "negative_ratio": negative_ratio,
            "delay_minutes": delay_minutes,
            "last_crawl": last_log.completed_at.isoformat() if last_log and last_log.completed_at else None,
            "status": status,
            "is_healthy": status == "healthy",
        })
    
    return {
        "code": 200,
        "data": {
            "matrix": matrix,
            "total_platforms": len(matrix),
            "healthy_count": sum(1 for m in matrix if m["is_healthy"]),
        },
        "message": "success",
    }


@router.get("/monitoring/freshness", response_model=UnifiedResponse[dict])
async def get_data_freshness(
    db: Session = Depends(get_db),
):
    """
    获取数据新鲜度与缺口
    
    返回各平台最新采集时间、延迟分钟数、缺口状态
    """
    platforms = db.query(Platform).filter(Platform.is_active == True).all()
    
    freshness = []
    for platform in platforms:
        # 最新话题
        latest_topic = db.query(HotTopic).filter(
            HotTopic.platform_id == platform.id
        ).order_by(desc(HotTopic.crawl_time)).first()
        
        # 最新采集日志
        latest_log = db.query(CrawlLog).filter(
            CrawlLog.platform_id == platform.id
        ).order_by(desc(CrawlLog.completed_at)).first()
        
        # 计算延迟
        delay_minutes = None
        if latest_topic and latest_topic.crawl_time:
            delay_minutes = int((datetime.now() - latest_topic.crawl_time).total_seconds() / 60)
        
        # 判断缺口状态
        gap_status = "normal"
        if not latest_topic:
            gap_status = "missing"
        elif delay_minutes and delay_minutes > 180:
            gap_status = "critical"
        elif delay_minutes and delay_minutes > 60:
            gap_status = "warning"
        
        freshness.append({
            "platform_id": platform.id,
            "platform_name": platform.name,
            "display_name": platform.display_name,
            "latest_topic_time": latest_topic.crawl_time.isoformat() if latest_topic else None,
            "latest_crawl_time": latest_log.completed_at.isoformat() if latest_log and latest_log.completed_at else None,
            "delay_minutes": delay_minutes,
            "gap_status": gap_status,
            "has_data": latest_topic is not None,
        })
    
    return {
        "code": 200,
        "data": {
            "freshness": freshness,
            "overall_status": "critical" if any(f["gap_status"] == "critical" for f in freshness) else 
                             "warning" if any(f["gap_status"] == "warning" for f in freshness) else "normal",
        },
        "message": "success",
    }
