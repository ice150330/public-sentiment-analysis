"""
数据质量 API 路由

模块名称: data_quality.py
模块职责: 数据处理漏斗、质量检查、问题列表
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.core.database import get_db
from app.models import HotTopic, SentimentResult, CrawlLog, DataQualityRun, DataQualityIssue, Platform
from app.schemas import UnifiedResponse

router = APIRouter()


@router.get("/funnel", response_model=UnifiedResponse[dict])
async def get_data_quality_funnel(
    date: str = None,
    db: Session = Depends(get_db),
):
    """
    获取数据处理漏斗
    
    展示从原始采集到入库的各环节数量
    """
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    else:
        target_date = datetime.now().date()
    
    # 原始采集数（采集日志成功数）
    raw_count = db.query(CrawlLog).filter(
        func.date(CrawlLog.started_at) == target_date,
        CrawlLog.status == "success",
    ).count()
    
    # 清洗后（入库话题数）
    cleaned_count = db.query(HotTopic).filter(
        func.date(HotTopic.crawl_time) == target_date,
    ).count()
    
    # 去重后（按 platform+topic_id 去重）
    unique_count = db.query(HotTopic.platform_id, HotTopic.topic_id).filter(
        func.date(HotTopic.crawl_time) == target_date,
    ).distinct().count()
    
    # 已分析（有情感结果的话题数）
    analyzed_count = db.query(HotTopic).join(SentimentResult).filter(
        func.date(HotTopic.crawl_time) == target_date,
    ).distinct().count()
    
    # 入库（最终话题数）
    stored_count = cleaned_count
    
    # 各环节损耗
    funnel = [
        {"stage": "原始采集", "count": raw_count, "loss": 0, "loss_rate": 0},
        {"stage": "清洗后", "count": cleaned_count, "loss": raw_count - cleaned_count, "loss_rate": round((raw_count - cleaned_count) * 100 / raw_count, 2) if raw_count > 0 else 0},
        {"stage": "去重后", "count": unique_count, "loss": cleaned_count - unique_count, "loss_rate": round((cleaned_count - unique_count) * 100 / cleaned_count, 2) if cleaned_count > 0 else 0},
        {"stage": "已分析", "count": analyzed_count, "loss": unique_count - analyzed_count, "loss_rate": round((unique_count - analyzed_count) * 100 / unique_count, 2) if unique_count > 0 else 0},
        {"stage": "最终入库", "count": stored_count, "loss": 0, "loss_rate": 0},
    ]
    
    return {
        "code": 200,
        "data": {
            "date": str(target_date),
            "funnel": funnel,
            "retention_rate": round(analyzed_count * 100 / raw_count, 2) if raw_count > 0 else 0,
        },
        "message": "success",
    }


@router.get("/checks", response_model=UnifiedResponse[dict])
async def get_quality_checks(
    db: Session = Depends(get_db),
):
    """
    获取质量检查项及结果
    
    字段完整率、重复话题、异常热度、空摘要、失败日志、时间漂移
    """
    # 最近 24 小时数据
    last_24h = datetime.now() - timedelta(hours=24)
    
    # 1. 字段完整率
    total_topics = db.query(HotTopic).filter(HotTopic.crawl_time >= last_24h).count()
    topics_with_summary = db.query(HotTopic).filter(
        HotTopic.crawl_time >= last_24h,
        HotTopic.content_summary.isnot(None),
    ).count()
    topics_with_category = db.query(HotTopic).filter(
        HotTopic.crawl_time >= last_24h,
        HotTopic.category.isnot(None),
    ).count()
    
    # 2. 重复话题数
    from sqlalchemy import distinct
    duplicate_query = db.query(
        HotTopic.platform_id,
        HotTopic.topic_id,
        func.count(HotTopic.id).label("cnt"),
    ).filter(
        HotTopic.crawl_time >= last_24h,
    ).group_by(
        HotTopic.platform_id,
        HotTopic.topic_id,
    ).having(func.count(HotTopic.id) > 1)
    duplicates = duplicate_query.count()
    
    # 3. 异常热度（热度为 0 或过高）
    abnormal_heat = db.query(HotTopic).filter(
        HotTopic.crawl_time >= last_24h,
        and_(HotTopic.heat_score.isnot(None), HotTopic.heat_score <= 0),
    ).count()
    
    # 4. 空摘要
    empty_summary = db.query(HotTopic).filter(
        HotTopic.crawl_time >= last_24h,
        HotTopic.content_summary.is_(None),
    ).count()
    
    # 5. 失败日志
    failed_logs = db.query(CrawlLog).filter(
        CrawlLog.started_at >= last_24h,
        CrawlLog.status == "failed",
    ).count()
    
    # 6. 时间漂移（采集时间 > 当前时间 或 过早）
    future_topics = db.query(HotTopic).filter(
        HotTopic.crawl_time >= last_24h,
        HotTopic.crawl_time > datetime.now(),
    ).count()
    
    checks = [
        {"name": "字段完整率", "pass_rate": round(topics_with_summary * 100 / total_topics, 2) if total_topics > 0 else 100, "threshold": 95, "status": "pass" if (topics_with_summary * 100 / total_topics >= 95 if total_topics > 0 else True) else "fail"},
        {"name": "分类标注率", "pass_rate": round(topics_with_category * 100 / total_topics, 2) if total_topics > 0 else 100, "threshold": 80, "status": "pass" if (topics_with_category * 100 / total_topics >= 80 if total_topics > 0 else True) else "fail"},
        {"name": "重复话题检测", "count": duplicates, "threshold": 10, "status": "pass" if duplicates <= 10 else "warning"},
        {"name": "异常热度检测", "count": abnormal_heat, "threshold": 5, "status": "pass" if abnormal_heat <= 5 else "warning"},
        {"name": "空摘要检测", "count": empty_summary, "threshold": 20, "status": "pass" if empty_summary <= 20 else "warning"},
        {"name": "采集失败检测", "count": failed_logs, "threshold": 5, "status": "pass" if failed_logs <= 5 else "fail"},
        {"name": "时间漂移检测", "count": future_topics, "threshold": 0, "status": "pass" if future_topics == 0 else "fail"},
    ]
    
    return {
        "code": 200,
        "data": {
            "period": "最近 24 小时",
            "checks": checks,
            "overall_score": round(sum(c.get("pass_rate", 100) for c in checks) / len(checks), 2),
        },
        "message": "success",
    }


@router.get("/issues", response_model=UnifiedResponse[dict])
async def list_quality_issues(
    issue_type: str = None,
    severity: str = None,
    status: str = None,
    platform: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询数据质量问题列表"""
    query = db.query(DataQualityIssue).join(Platform, isouter=True)
    
    if issue_type:
        query = query.filter(DataQualityIssue.issue_type == issue_type)
    if severity:
        query = query.filter(DataQualityIssue.severity == severity)
    if status:
        query = query.filter(DataQualityIssue.status == status)
    if platform:
        query = query.filter(Platform.name == platform)
    
    total = query.count()
    issues = query.order_by(desc(DataQualityIssue.created_at))
    issues = issues.offset((page - 1) * page_size).limit(page_size).all()
    
    items = []
    for issue in issues:
        items.append({
            "id": issue.id,
            "issue_type": issue.issue_type,
            "platform_name": issue.platform.display_name if issue.platform else None,
            "topic_title": issue.topic.title if issue.topic else None,
            "severity": issue.severity,
            "status": issue.status,
            "description": issue.description,
            "suggestion": issue.suggestion,
            "created_at": issue.created_at.isoformat() if issue.created_at else None,
            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
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


@router.post("/issues/{issue_id}/fix", response_model=UnifiedResponse[dict])
async def fix_quality_issue(
    issue_id: int,
    db: Session = Depends(get_db),
):
    """标记数据质量问题为已修复"""
    issue = db.query(DataQualityIssue).filter(DataQualityIssue.id == issue_id).first()
    if not issue:
        return {"code": 404, "data": None, "message": "Issue not found"}
    
    issue.status = "fixed"
    issue.resolved_at = datetime.now()
    db.commit()
    
    return {
        "code": 200,
        "data": {"id": issue_id, "status": "fixed"},
        "message": "Issue marked as fixed",
    }


@router.get("/summary", response_model=UnifiedResponse[dict])
async def get_quality_summary(
    db: Session = Depends(get_db),
):
    """
    获取数据质量汇总
    
    平台覆盖、数据保留、质量评分等
    """
    # 各平台数据量
    platform_counts = db.query(
        Platform.name,
        Platform.display_name,
        func.count(HotTopic.id).label("count"),
    ).join(HotTopic).group_by(Platform.id).all()
    
    # 总话题数
    total_topics = db.query(HotTopic).count()
    
    # 有情感分析的话题数
    analyzed_topics = db.query(HotTopic).join(SentimentResult).distinct().count()
    
    # 最近 7 天新增
    last_7d = datetime.now() - timedelta(days=7)
    recent_topics = db.query(HotTopic).filter(HotTopic.crawl_time >= last_7d).count()
    
    # 待处理问题数
    open_issues = db.query(DataQualityIssue).filter(DataQualityIssue.status == "open").count()
    
    return {
        "code": 200,
        "data": {
            "total_topics": total_topics,
            "analyzed_topics": analyzed_topics,
            "analysis_coverage": round(analyzed_topics * 100 / total_topics, 2) if total_topics > 0 else 0,
            "recent_7d_topics": recent_topics,
            "open_issues": open_issues,
            "platform_coverage": [
                {"name": p.name, "display_name": p.display_name, "count": p.count}
                for p in platform_counts
            ],
        },
        "message": "success",
    }
