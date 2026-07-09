"""
数据质量检查服务

模块名称: data_quality_service.py
模块职责: 自动化数据质量检查、问题发现、报告生成

优化内容:
- 增强分类一致性检查
- 增加情感分析质量检查
- 增加数据新鲜度检查
- 增加平台覆盖率检查
- 增加热度分布异常检查
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import (
    HotTopic, SentimentResult, CrawlLog, DataQualityRun, 
    DataQualityIssue, Platform, AlertEvent
)

logger = logging.getLogger(__name__)


class DataQualityService:
    """数据质量检查服务"""
    
    # 有效内容分类列表（标准化后的分类体系）
    VALID_CATEGORIES = {
        "娱乐", "社会", "科技", "财经", "体育", 
        "时政", "时尚", "美食", "旅游", "文化",
        "搞笑", "其他"
    }
    
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
            issues_found.extend(self._check_category_consistency())  # 新增
            issues_found.extend(self._check_sentiment_quality())  # 新增
            issues_found.extend(self._check_platform_coverage())  # 新增
            issues_found.extend(self._check_data_freshness())  # 新增
            issues_found.extend(self._check_heat_distribution())  # 新增
            
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
        
        for topic in missing_summary[:10]:
            issues.append({
                "issue_type": "missing_field",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "warning",
                "description": f"话题 '{topic.title[:50]}' 缺失内容摘要",
                "suggestion": "检查爬虫是否正确提取正文内容",
            })
        
        # 检查缺失分类
        missing_category = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
            HotTopic.category.is_(None),
        ).all()
        
        for topic in missing_category[:10]:
            issues.append({
                "issue_type": "missing_field",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "warning",
                "description": f"话题 '{topic.title[:50]}' 缺失分类",
                "suggestion": "检查爬虫是否正确提取分类信息",
            })
        
        return issues
    
    def _check_duplicate_topics(self) -> List[Dict]:
        """检查重复话题（增强版：检查1小时窗口内的重复）"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        # 按 topic_id 重复
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
                "severity": "warning",  # 提升为 warning
                "description": f"平台 '{platform.display_name if platform else dup.platform_id}' 话题 '{dup.topic_id}' 重复 {dup.cnt} 次",
                "suggestion": "检查去重逻辑是否正常，考虑缩短去重时间窗口",
            })
        
        # 按标题重复（同一平台同一标题在1小时内出现多次）
        last_1h = datetime.now() - timedelta(hours=1)
        title_dups = self.db.query(
            HotTopic.platform_id,
            HotTopic.title,
            func.count(HotTopic.id).label("cnt"),
        ).filter(
            HotTopic.crawl_time >= last_1h,
        ).group_by(
            HotTopic.platform_id,
            HotTopic.title,
        ).having(func.count(HotTopic.id) > 1).all()
        
        for dup in title_dups[:5]:
            platform = self.db.query(Platform).filter(Platform.id == dup.platform_id).first()
            issues.append({
                "issue_type": "duplicate_title",
                "platform_id": dup.platform_id,
                "severity": "info",
                "description": f"平台 '{platform.display_name if platform else dup.platform_id}' 标题 '{dup.title[:30]}...' 重复 {dup.cnt} 次",
                "suggestion": "同一标题在1小时内多次出现，检查是否是采集频率过高",
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
        
        # 热度超过 1 亿（异常高）
        extreme_heat = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
            HotTopic.heat_score > 100000000,
        ).all()
        
        for topic in extreme_heat[:5]:
            issues.append({
                "issue_type": "abnormal_heat",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "info",
                "description": f"话题 '{topic.title[:50]}' 热度异常高 ({topic.heat_score})",
                "suggestion": "检查热度值单位是否正确（万/亿）",
            })
        
        return issues
    
    def _check_empty_summary(self) -> List[Dict]:
        """检查空摘要"""
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
                "suggestion": "优化内容提取逻辑或启用智能摘要生成",
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
    
    def _check_category_consistency(self) -> List[Dict]:
        """检查分类一致性"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        # 检查无效分类（运营标签混在分类中）
        invalid_categories = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
            HotTopic.category.in_(["热", "新", "爆", "沸"]),
        ).all()
        
        for topic in invalid_categories[:5]:
            issues.append({
                "issue_type": "category_mismatch",
                "platform_id": topic.platform_id,
                "topic_id": topic.id,
                "severity": "warning",
                "description": f"话题 '{topic.title[:50]}' 分类为运营标签 '{topic.category}'，应拆分为独立字段",
                "suggestion": "更新数据处理器，将运营标签（热/新/爆）提取到 heat_tag 字段",
            })
        
        # 检查未知分类
        unknown_categories = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
        ).all()
        
        unknown_count = 0
        for topic in unknown_categories:
            if topic.category not in self.VALID_CATEGORIES:
                unknown_count += 1
                if unknown_count <= 5:
                    issues.append({
                        "issue_type": "unknown_category",
                        "platform_id": topic.platform_id,
                        "topic_id": topic.id,
                        "severity": "info",
                        "description": f"话题 '{topic.title[:50]}' 使用未标准化分类 '{topic.category}'",
                        "suggestion": f"标准化为以下分类之一: {', '.join(sorted(self.VALID_CATEGORIES))}",
                    })
        
        return issues
    
    def _check_sentiment_quality(self) -> List[Dict]:
        """检查情感分析质量"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        # 检查低置信度分析结果
        low_confidence = self.db.query(SentimentResult).join(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
            SentimentResult.confidence < 0.5,
        ).all()
        
        for sr in low_confidence[:5]:
            topic = self.db.query(HotTopic).filter(HotTopic.id == sr.topic_id).first()
            title = topic.title[:50] if topic else f"ID={sr.topic_id}"
            issues.append({
                "issue_type": "low_confidence_sentiment",
                "platform_id": topic.platform_id if topic else None,
                "topic_id": sr.topic_id,
                "severity": "warning",
                "description": f"话题 '{title}' 情感分析置信度过低 ({sr.confidence:.3f})",
                "suggestion": "检查模型质量，考虑重新训练或使用更优模型",
            })
        
        # 检查情感分布是否极度偏斜（>90% 同一情感）
        total = self.db.query(SentimentResult).join(HotTopic).filter(
            HotTopic.crawl_time >= last_24h,
        ).count()
        
        if total > 10:
            for label in ["positive", "negative", "neutral"]:
                count = self.db.query(SentimentResult).join(HotTopic).filter(
                    HotTopic.crawl_time >= last_24h,
                    SentimentResult.sentiment_label == label,
                ).count()
                
                if count / total > 0.9:
                    issues.append({
                        "issue_type": "sentiment_skew",
                        "platform_id": None,
                        "topic_id": None,
                        "severity": "warning",
                        "description": f"最近24小时情感分布极度偏斜: {label} 占比 {(count/total)*100:.1f}% ({count}/{total})",
                        "suggestion": "检查情感分析模型是否存在偏差，考虑校准模型",
                    })
                    break
        
        return issues
    
    def _check_platform_coverage(self) -> List[Dict]:
        """检查平台覆盖率"""
        issues = []
        last_1h = datetime.now() - timedelta(hours=1)
        
        # 检查各平台最近1小时是否有数据
        active_platforms = self.db.query(
            HotTopic.platform_id,
            func.count(HotTopic.id).label("cnt"),
        ).filter(
            HotTopic.crawl_time >= last_1h,
        ).group_by(HotTopic.platform_id).all()
        
        active_platform_ids = {p.platform_id for p in active_platforms}
        
        all_platforms = self.db.query(Platform).filter(Platform.is_active == True).all()
        for platform in all_platforms:
            if platform.id not in active_platform_ids:
                issues.append({
                    "issue_type": "missing_platform_data",
                    "platform_id": platform.id,
                    "severity": "warning",
                    "description": f"平台 '{platform.display_name}' 最近1小时无数据",
                    "suggestion": "检查爬虫调度器是否正常运行，平台API是否可用",
                })
            else:
                # 检查数据量是否过少（<5条）
                platform_data = next((p for p in active_platforms if p.platform_id == platform.id), None)
                if platform_data and platform_data.cnt < 5:
                    issues.append({
                        "issue_type": "insufficient_platform_data",
                        "platform_id": platform.id,
                        "severity": "info",
                        "description": f"平台 '{platform.display_name}' 最近1小时数据量过少 ({platform_data.cnt}条)",
                        "suggestion": "检查爬虫是否完整抓取，或平台本身数据量较少",
                    })
        
        return issues
    
    def _check_data_freshness(self) -> List[Dict]:
        """检查数据新鲜度"""
        issues = []
        
        # 检查最新数据的时间
        latest = self.db.query(HotTopic).order_by(HotTopic.crawl_time.desc()).first()
        if latest:
            time_diff = datetime.now() - latest.crawl_time
            if time_diff > timedelta(hours=2):
                issues.append({
                    "issue_type": "stale_data",
                    "platform_id": None,
                    "severity": "critical" if time_diff > timedelta(hours=4) else "warning",
                    "description": f"数据已过期，最新数据为 {time_diff.total_seconds()/3600:.1f} 小时前",
                    "suggestion": "检查爬虫调度器和后端服务是否正常运行",
                })
        
        return issues
    
    def _check_heat_distribution(self) -> List[Dict]:
        """检查热度分布异常"""
        issues = []
        last_24h = datetime.now() - timedelta(hours=24)
        
        # 检查同一平台内热度差异过大（最高/最低 > 1000倍）
        platforms = self.db.query(Platform).filter(Platform.is_active == True).all()
        
        for platform in platforms:
            topics = self.db.query(HotTopic).filter(
                HotTopic.platform_id == platform.id,
                HotTopic.crawl_time >= last_24h,
                HotTopic.heat_score.isnot(None),
            ).all()
            
            if len(topics) < 5:
                continue
            
            heats = [t.heat_score for t in topics if t.heat_score and t.heat_score > 0]
            if not heats:
                continue
            
            max_heat = max(heats)
            min_heat = min(heats)
            
            if min_heat > 0 and max_heat / min_heat > 10000:
                issues.append({
                    "issue_type": "heat_distribution_anomaly",
                    "platform_id": platform.id,
                    "severity": "info",
                    "description": f"平台 '{platform.display_name}' 热度分布异常: 最高 {max_heat} vs 最低 {min_heat} (差异 {max_heat/min_heat:.0f} 倍)",
                    "suggestion": "检查热度值单位是否统一，是否存在异常值",
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

