"""
数据质量检查服务

模块名称: data_quality_service.py
模块职责: 自动化数据质量检查、问题发现、报告生成
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct

from app.models import HotTopic, SentimentResult, CrawlLog, DataQualityRun, DataQualityIssue, Platform

logger = logging.getLogger(__name__)


class DataQualityService:
    """数据质量检查服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def run_quality_check(self, run_type: str = "manual") -> Dict[str, Any]:
        """
        执行数据质量检查
        
        Args:
            run_type: 检查类型 (daily/weekly/manual)
        
        Returns:
            检查结果摘要
        """
        # 创建检查批次
        run = DataQualityRun(
            run_type=run_type,
            status="running",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        
        issues_found = []
        
        try:
            # 执行各项检查
            issues_found.extend(self._check_missing_fields())
            issues_found.extend(self._check_duplicate_topics())
            issues_found.extend(self._check_abnormal_heat())
            issues_found.extend(self._check_empty_summary())
            issues_found.extend(self._check_failed_crawls())
            issues_found.extend(self._check_time_drift())
            
            # 关联到检查批次
            for issue_data in issues_found:
                issue = DataQualityIssue(
                    run_id=run.id,
                    **issue_data,
                )
                self.db.add(issue)
            
            # 更新检查批次状态
            run.status = "completed"
            run.completed_at = datetime.now()
            run.summary_json = json.dumps({
                "total_issues": len(issues_found),
                "by_severity": self._count_by_severity(issues_found),
                "by_type": self._count_by_type(issues_found),
            }, ensure_ascii=False)
            
            self.db.commit()
            
            logger.info(f"Quality check completed: {len(issues_found)} issues found")
            
            return {
                "run_id": run.id,
                "status": "completed",
                "issues_found": len(issues_found),
                "details": issues_found,
            }
            
        except Exception as e:
            run.status = "failed"
            run.completed_at = datetime.now()
            self.db.commit()
            
            logger.error(f"Quality check failed: {e}")
            return {
                "run_id": run.id,
                "status": "failed",
                "error": str(e),
            }
    
    def _check_missing_fields(self) -> List[Dict]:
        """检查缺失字段"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        # 检查缺失摘要
        missing_summary = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
            HotTopic.content_summary.is_(None),
        ).all()
        
        for topic in missing_summary[:10]:  # 最多记录 10 个
            issues.append({
                "issue_type": "missing_field",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "warning",
                "description": f"话题 '{topic.title[:50]}' 缺失内容摘要",
                "suggestion": "检查爬虫是否正确提取正文内容",
            })
        
        return issues
    
    def _check_duplicate_topics(self) -> List[Dict]:
        """检查重复话题"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        duplicates = self.db.query(
            HotTopic.platform_id,
            HotTopic.topic_id,
            func.count(HotTopic.id).label("cnt"),
        ).filter(
            HotTopic.crawl_time >= last_24h,
        ).group_by(
            HotTopic.platform_id,
            HotTopic.topic_id,
        ).having(func.count(HotTopic.id) > 1).all()
        
        for dup in duplicates[:5]:
            platform = self.db.query(Platform).filter(Platform.id == dup.platform_id).first()
            issues.append({
                "issue_type": "duplicate",
                "platform_id": dup.platform_id,
                "severity": "info",
                "description": f"平台 '{platform.display_name if platform else dup.platform_id}' 话题 '{dup.topic_id}' 重复 {dup.cnt} 次",
                "suggestion": "检查去重逻辑是否正常",
            })
        
        return issues
    
    def _check_abnormal_heat(self) -> List[Dict]:
        """检查异常热度"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        # 热度为 0 的话题
        zero_heat = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
            HotTopic.heat_score == 0,
        ).all()
        
        for topic in zero_heat[:5]:
            issues.append({
                "issue_type": "abnormal_heat",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "warning",
                "description": f"话题 '{topic.title[:50]}' 热度为 0",
                "suggestion": "检查热度值是否正确提取",
            })
        
        return issues
    
    def _check_empty_summary(self) -> List[Dict]:
        """检查空摘要"""
        # 与 missing_fields 类似，但关注空字符串
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        empty_summary = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
            HotTopic.content_summary == "",
        ).all()
        
        for topic in empty_summary[:5]:
            issues.append({
                "issue_type": "empty_summary",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "info",
                "description": f"话题 '{topic.title[:50]}' 摘要为空字符串",
                "suggestion": "优化内容提取逻辑",
            })
        
        return issues
    
    def _check_failed_crawls(self) -> List[Dict]:
        """检查采集失败"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        failed_logs = self.db.query(CrawlLog).filter(
            CrawlLog.started_at >= last_24h,
            CrawlLog.status == "failed",
        ).all()
        
        for log in failed_logs[:5]:
            platform = self.db.query(Platform).filter(Platform.id == log.platform_id).first()
            issues.append({
                "issue_type": "failed_crawl",
                "platform_id": log.platform_id,
                "severity": "critical",
                "description": f"平台 '{platform.display_name if platform else log.platform_id}' 采集失败: {log.error_message[:100] if log.error_message else 'Unknown error'}",
                "suggestion": "检查平台 API 是否可用，更新爬虫配置",
            })
        
        return issues
    
    def _check_time_drift(self) -> List[Dict]:
        """检查时间漂移"""
        issues = []
        future = datetime.now() + timedelta(minutes=5)
        
        future_topics = self.db.query(HotTopic).filter(
            HotTopic.crawl_time > future,
        ).all()
        
        for topic in future_topics[:5]:
            issues.append({
                "issue_type": "time_drift",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "critical",
                "description": f"话题 '{topic.title[:50]}' 采集时间在未来",
                "suggestion": "检查服务器时间和爬虫时间戳设置",
            })
        
        return issues
    
    def _count_by_severity(self, issues: List[Dict]) -> Dict[str, int]:
        """按严重级别统计"""
        counts = {}
        for issue in issues:
            sev = issue.get("severity", "info")
            counts[sev] = counts.get(sev, 0) + 1
        return counts
    
    def _count_by_type(self, issues: List[Dict]) -> Dict[str, int]:
        """按问题类型统计"""
        counts = {}
        for issue in issues:
            typ = issue.get("issue_type", "unknown")
            counts[typ] = counts.get(typ, 0) + 1
        return counts
