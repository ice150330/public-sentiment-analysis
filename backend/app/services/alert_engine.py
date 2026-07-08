"""
预警引擎服务

模块名称: alert_engine.py
模块职责: 预警规则评估、事件触发、冷却管理
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.models import AlertRule, AlertEvent, AlertAction, HotTopic, SentimentResult, Platform
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class AlertEngine:
    """预警引擎"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)
    
    def evaluate_all_rules(self) -> Dict[str, Any]:
        """
        评估所有启用的预警规则
        
        Returns:
            {"triggered": int, "skipped": int, "errors": int, "details": list}
        """
        rules = self.db.query(AlertRule).filter(AlertRule.is_active == True).all()
        
        triggered = 0
        skipped = 0
        errors = 0
        details = []
        
        for rule in rules:
            try:
                # 检查冷却期
                if self._is_in_cooldown(rule):
                    skipped += 1
                    details.append({"rule_id": rule.id, "status": "cooldown"})
                    continue
                
                # 评估规则
                result = self._evaluate_rule(rule)
                
                if result["triggered"]:
                    # 创建预警事件
                    event = self._create_alert_event(rule, result)
                    triggered += 1
                    details.append({
                        "rule_id": rule.id,
                        "status": "triggered",
                        "event_id": event.id,
                        "severity": rule.severity,
                    })
                    logger.warning(f"Alert triggered: rule={rule.name}, event={event.id}")
                else:
                    skipped += 1
                    details.append({"rule_id": rule.id, "status": "not_triggered"})
                    
            except Exception as e:
                errors += 1
                details.append({"rule_id": rule.id, "status": "error", "error": str(e)})
                logger.error(f"Error evaluating rule {rule.id}: {e}")
        
        return {
            "triggered": triggered,
            "skipped": skipped,
            "errors": errors,
            "details": details,
            "evaluated_at": datetime.now().isoformat(),
        }
    
    def _is_in_cooldown(self, rule: AlertRule) -> bool:
        """检查规则是否在冷却期内"""
        if not rule.cooldown_minutes:
            return False
        
        # 查询该规则最近触发的事件
        latest_event = self.db.query(AlertEvent).filter(
            AlertEvent.rule_id == rule.id,
        ).order_by(desc(AlertEvent.triggered_at)).first()
        
        if not latest_event:
            return False
        
        cooldown_end = latest_event.triggered_at + timedelta(minutes=rule.cooldown_minutes)
        return datetime.now() < cooldown_end
    
    def _evaluate_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """
        评估单个规则
        
        支持的条件类型:
        - heat_spike: 热度飙升 (热度超过阈值)
        - negative_ratio: 负面占比 (负面情感占比超过阈值)
        - low_confidence: 低置信度 (置信度低于阈值)
        - volume_spike: 话题量激增 (话题数超过阈值)
        
        Returns:
            {"triggered": bool, "context": dict}
        """
        condition = self._parse_condition(rule.condition_expr)
        condition_type = rule.condition_type or condition.get("type", "heat_spike")
        
        if condition_type == "heat_spike":
            return self._evaluate_heat_spike(condition)
        elif condition_type == "negative_ratio":
            return self._evaluate_negative_ratio(condition)
        elif condition_type == "low_confidence":
            return self._evaluate_low_confidence(condition)
        elif condition_type == "volume_spike":
            return self._evaluate_volume_spike(condition)
        else:
            # 默认使用热度检查
            return self._evaluate_heat_spike(condition)
    
    def _parse_condition(self, condition_expr: str) -> Dict[str, Any]:
        """解析条件表达式"""
        try:
            return json.loads(condition_expr) if condition_expr else {}
        except json.JSONDecodeError:
            # 如果不是 JSON，尝试解析简单表达式
            return {"type": "heat_spike", "threshold": 10000}
    
    def _evaluate_heat_spike(self, condition: Dict) -> Dict[str, Any]:
        """评估热度飙升规则"""
        threshold = condition.get("threshold", 10000)
        time_window_hours = condition.get("time_window_hours", 1)
        
        since = datetime.now() - timedelta(hours=time_window_hours)
        
        # 查询最近时间窗口内热度超过阈值的话题
        hot_topics = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= since,
            HotTopic.heat_score >= threshold,
        ).all()
        
        triggered = len(hot_topics) > 0
        context = {
            "threshold": threshold,
            "time_window_hours": time_window_hours,
            "matched_topics": [
                {"id": t.id, "title": t.title, "heat_score": t.heat_score}
                for t in hot_topics[:5]  # 最多取 5 个
            ],
            "matched_count": len(hot_topics),
        }
        
        return {"triggered": triggered, "context": context}
    
    def _evaluate_negative_ratio(self, condition: Dict) -> Dict[str, Any]:
        """评估负面占比规则"""
        threshold = condition.get("threshold", 50)  # 默认 50%
        time_window_hours = condition.get("time_window_hours", 24)
        platform = condition.get("platform")
        
        since = datetime.now() - timedelta(hours=time_window_hours)
        
        query = self.db.query(HotTopic).filter(HotTopic.crawl_time >= since)
        
        if platform:
            platform_obj = self.db.query(Platform).filter(Platform.name == platform).first()
            if platform_obj:
                query = query.filter(HotTopic.platform_id == platform_obj.id)
        
        # 获取有情感分析的话题
        topics_with_sentiment = query.join(SentimentResult).all()
        
        if not topics_with_sentiment:
            return {"triggered": False, "context": {"message": "No sentiment data"}}
        
        negative_count = sum(
            1 for t in topics_with_sentiment
            if t.sentiment_result and t.sentiment_result.sentiment_label == "negative"
        )
        
        negative_ratio = (negative_count / len(topics_with_sentiment)) * 100
        triggered = negative_ratio >= threshold
        
        context = {
            "threshold": threshold,
            "negative_ratio": round(negative_ratio, 2),
            "negative_count": negative_count,
            "total_count": len(topics_with_sentiment),
            "time_window_hours": time_window_hours,
            "platform": platform,
        }
        
        return {"triggered": triggered, "context": context}
    
    def _evaluate_low_confidence(self, condition: Dict) -> Dict[str, Any]:
        """评估低置信度规则"""
        threshold = condition.get("threshold", 0.5)
        min_count = condition.get("min_count", 10)
        time_window_hours = condition.get("time_window_hours", 24)
        
        since = datetime.now() - timedelta(hours=time_window_hours)
        
        low_conf_results = self.db.query(SentimentResult).filter(
            SentimentResult.analyzed_at >= since,
            SentimentResult.confidence < threshold,
        ).all()
        
        triggered = len(low_conf_results) >= min_count
        
        context = {
            "threshold": threshold,
            "min_count": min_count,
            "low_confidence_count": len(low_conf_results),
            "time_window_hours": time_window_hours,
        }
        
        return {"triggered": triggered, "context": context}
    
    def _evaluate_volume_spike(self, condition: Dict) -> Dict[str, Any]:
        """评估话题量激增规则"""
        threshold = condition.get("threshold", 100)
        time_window_hours = condition.get("time_window_hours", 1)
        
        since = datetime.now() - timedelta(hours=time_window_hours)
        
        topic_count = self.db.query(HotTopic).filter(
            HotTopic.crawl_time >= since,
        ).count()
        
        triggered = topic_count >= threshold
        
        context = {
            "threshold": threshold,
            "topic_count": topic_count,
            "time_window_hours": time_window_hours,
        }
        
        return {"triggered": triggered, "context": context}
    
    def _create_alert_event(self, rule: AlertRule, result: Dict) -> AlertEvent:
        """创建预警事件"""
        # 取第一个匹配的话题作为关联话题
        context = result.get("context", {})
        matched_topics = context.get("matched_topics", [])
        topic_id = matched_topics[0]["id"] if matched_topics else None
        
        event = AlertEvent(
            rule_id=rule.id,
            topic_id=topic_id,
            severity=rule.severity,
            status="pending",
            trigger_payload=json.dumps(context, ensure_ascii=False, default=str),
        )
        
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        
        # 发送通知
        self.notification_service.send_alert_notification(event)
        
        return event
    
    def get_pending_alerts_summary(self) -> Dict[str, Any]:
        """获取待处理预警摘要"""
        # 按严重程度分组统计
        severity_counts = self.db.query(
            AlertEvent.severity,
            func.count(AlertEvent.id).label("count"),
        ).filter(AlertEvent.status == "pending").group_by(AlertEvent.severity).all()
        
        severity_dict = {s.severity: s.count for s in severity_counts}
        
        # 按规则分组统计
        rule_counts = self.db.query(
            AlertRule.name,
            func.count(AlertEvent.id).label("count"),
        ).join(AlertEvent).filter(AlertEvent.status == "pending").group_by(AlertRule.id).all()
        
        return {
            "total_pending": sum(severity_dict.values()),
            "by_severity": severity_dict,
            "by_rule": [{"name": r.name, "count": r.count} for r in rule_counts],
            "updated_at": datetime.now().isoformat(),
        }
