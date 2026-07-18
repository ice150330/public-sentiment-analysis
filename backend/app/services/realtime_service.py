"""
实时推送服务

模块名称: realtime_service.py
模块职责: WebSocket 连接管理、事件广播、在线状态统计
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import WebSocket

from app.core.security import TokenError, decode_access_token

logger = logging.getLogger(__name__)


@dataclass
class _Connection:
    """单个用户 WebSocket 连接记录"""

    websocket: WebSocket
    user_id: int
    username: str
    role: str


class RealtimeConnectionManager:
    """进程内 WebSocket 连接管理器"""

    def __init__(self) -> None:
        self._connections: dict[int, _Connection] = {}

    @property
    def active_count(self) -> int:
        return len(self._connections)

    def get_status(self) -> dict[str, Any]:
        return {
            "active_connections": self.active_count,
            "users": [
                {"user_id": c.user_id, "username": c.username, "role": c.role}
                for c in self._connections.values()
            ],
        }

    async def connect(self, websocket: WebSocket, token: str) -> bool:
        try:
            payload = decode_access_token(token)
        except TokenError as exc:
            await websocket.close(code=1008, reason=str(exc))
            return False

        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token payload")
            return False

        await websocket.accept()
        username = payload.get("username", str(user_id))
        role = payload.get("role", "visitor")
        self._connections[int(user_id)] = _Connection(
            websocket=websocket,
            user_id=int(user_id),
            username=username,
            role=role,
        )
        logger.info(f"Realtime websocket connected: user={username}({user_id})")
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        for user_id, conn in list(self._connections.items()):
            if conn.websocket == websocket:
                del self._connections[user_id]
                logger.info(f"Realtime websocket disconnected: user={conn.username}({user_id})")
                break

    async def send_to_user(self, user_id: int, message: dict[str, Any]) -> None:
        conn = self._connections.get(user_id)
        if not conn:
            return
        try:
            await conn.websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as exc:
            logger.warning(f"Failed to send realtime message to user {user_id}: {exc}")
            self._connections.pop(user_id, None)

    async def broadcast(self, message: dict[str, Any]) -> None:
        text = json.dumps(message, ensure_ascii=False)
        dead: list[int] = []
        for user_id, conn in self._connections.items():
            try:
                await conn.websocket.send_text(text)
            except Exception as exc:
                logger.warning(f"Broadcast failed for user {user_id}: {exc}")
                dead.append(user_id)
        for user_id in dead:
            self._connections.pop(user_id, None)


# 全局单例（单机部署，进程内广播即可满足需求）
_manager = RealtimeConnectionManager()


def get_realtime_manager() -> RealtimeConnectionManager:
    return _manager


def _safe_schedule(coro: Any) -> None:
    """在事件循环中安全调度协程；无事件循环时静默跳过"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    try:
        loop.create_task(coro)
    except Exception as exc:
        logger.warning(f"Failed to schedule realtime broadcast: {exc}")


async def broadcast_event(event_type: str, payload: dict[str, Any]) -> None:
    manager = get_realtime_manager()
    message = {
        "type": event_type,
        "payload": payload,
        "timestamp": datetime.now().isoformat(),
    }
    await manager.broadcast(message)


def broadcast_event_sync(event_type: str, payload: dict[str, Any]) -> None:
    """同步上下文调用的事件广播入口；推送失败不影响主流程"""
    try:
        message = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat(),
        }
        _safe_schedule(get_realtime_manager().broadcast(message))
    except Exception as exc:
        logger.warning(f"Realtime broadcast skipped: {exc}")

