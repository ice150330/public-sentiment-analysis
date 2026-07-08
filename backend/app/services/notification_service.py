"""
通知服务

模块名称: notification_service.py
模块职责: 预警通知发送（站内、Webhook、邮件等）
"""

import json
import logging
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.models import AlertEvent, SystemConfig

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
        - Webhook 回调（通过 system_configs 启用）
        - 邮件通知配置状态（未配置 SMTP 时保持禁用）
        
        Returns:
            {"sent": bool, "channels": list, "error": str}
        """
        channels = []
        error = None
        
        try:
            # 1. 站内通知 - 记录到系统日志
            self._send_internal_notification(event)
            channels.append("internal")
            
            config = self.get_notification_config()
            if config["webhook_enabled"] and config["webhook_url"]:
                self._send_webhook_notification(event, config["webhook_url"])
                channels.append("webhook")
            if config["email_enabled"]:
                logger.warning("Email notification is enabled but SMTP delivery is not configured")
            
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
        """发送 Webhook 通知。"""
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
        """获取通知配置。"""
        rows = self.db.query(SystemConfig).filter(
            SystemConfig.config_key.in_([
                "notification_webhook_enabled",
                "notification_webhook_url",
                "notification_email_enabled",
                "notification_email_recipients",
            ])
        ).all()
        config = {row.config_key: row.config_value for row in rows}
        email_recipients = config.get("notification_email_recipients") or ""
        return {
            "webhook_enabled": config.get("notification_webhook_enabled", "false").lower() == "true",
            "webhook_url": config.get("notification_webhook_url"),
            "email_enabled": config.get("notification_email_enabled", "false").lower() == "true",
            "email_recipients": [item.strip() for item in email_recipients.split(",") if item.strip()],
            "internal_enabled": True,
        }
