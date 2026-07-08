"""
通知服务

模块名称: notification_service.py
模块职责: 预警通知发送（站内、Webhook、邮件等）
"""

import json
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.models import AlertEvent, AlertRule

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def send_alert_notification(self, event: AlertEvent) -> Dict[str, Any]:
        """
        发送预警通知
        
        目前支持:
        - 站内通知（记录到系统日志）
        - Webhook 回调（TODO）
        - 邮件通知（TODO）
        
        Returns:
            {"sent": bool, "channels": list, "error": str}
        """
        channels = []
        error = None
        
        try:
            # 1. 站内通知 - 记录到系统日志
            self._send_internal_notification(event)
            channels.append("internal")
            
            # 2. Webhook 通知（TODO: 从配置中读取 webhook URL）
            # self._send_webhook_notification(event)
            # channels.append("webhook")
            
            # 3. 邮件通知（TODO）
            # self._send_email_notification(event)
            # channels.append("email")
            
            logger.info(f"Alert notification sent for event {event.id}, channels: {channels}")
            
            return {
                "sent": True,
                "channels": channels,
                "error": None,
            }
            
        except Exception as e:
            logger.error(f"Failed to send notification for event {event.id}: {e}")
            return {
                "sent": False,
                "channels": channels,
                "error": str(e),
            }
    
    def _send_internal_notification(self, event: AlertEvent):
        """发送站内通知（记录到系统日志表）"""
        from app.models import SystemLog
        
        rule = event.rule
        rule_name = rule.name if rule else "Unknown"
        
        log = SystemLog(
            level="WARNING",
            module="alert_engine",
            event="alert_triggered",
            message=f"预警触发: [{event.severity}] {rule_name}",
            payload_json=json.dumps({
                "event_id": event.id,
                "rule_id": event.rule_id,
                "severity": event.severity,
                "topic_id": event.topic_id,
                "trigger_payload": event.trigger_payload,
            }, ensure_ascii=False, default=str),
        )
        
        self.db.add(log)
        self.db.commit()
    
    def _send_webhook_notification(self, event: AlertEvent, webhook_url: str):
        """发送 Webhook 通知（TODO: 实现 HTTP 调用）"""
        import requests
        
        payload = {
            "event_id": event.id,
            "rule_id": event.rule_id,
            "rule_name": event.rule.name if event.rule else None,
            "severity": event.severity,
            "status": event.status,
            "triggered_at": event.triggered_at.isoformat() if event.triggered_at else None,
            "trigger_payload": event.trigger_payload,
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Webhook sent successfully for event {event.id}")
        except Exception as e:
            logger.error(f"Webhook failed for event {event.id}: {e}")
            raise
    
    def get_notification_config(self) -> Dict[str, Any]:
        """获取通知配置（TODO: 从数据库或配置文件读取）"""
        return {
            "webhook_enabled": False,
            "webhook_url": None,
            "email_enabled": False,
            "email_recipients": [],
            "internal_enabled": True,
        }
