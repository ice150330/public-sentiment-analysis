# P2 实时推送模型落地

本阶段补齐 P2「实时推送」能力，数据库继续使用现有 SQLite，不引入 Redis/RabbitMQ。

## 后端实现

- 新增 `RealtimeConnectionManager`（`backend/app/services/realtime_service.py`），进程内单例管理 WebSocket 连接。
  - 每个用户最多一条连接，新连接顶替旧连接。
  - 支持按用户单播和全局广播，发送失败自动清理失效连接。
- WebSocket 入口：`/ws?token=<access_token>`。
  - 使用 query 参数传递 JWT（浏览器 WebSocket 无法自定义 Header）。
  - token 校验复用 `app.core.security.decode_access_token`，无效或过期直接关闭连接。
- 事件挂钩（非侵入，失败不影响主流程）：
  - 新预警：`AlertEngine._create_alert_event` 创建事件并发送通知后广播 `alert`。
  - 采集完成：`CrawlerService.run_crawl` 返回结果前广播 `crawl_complete`。
  - 数据质量异常：`DataQualityService.run_quality_check` 成功完成后广播 `data_quality`。
- 管理接口：`GET /api/v1/system/realtime-status` 返回当前连接数与用户列表，仅管理员。

## 前端实现

- 新增 `frontend/src/hooks/useRealtime.ts`：
  - 登录后建立 WebSocket 连接，支持自动重连（指数退避，最大 30s）与页面可见性恢复。
- 新增 `frontend/src/components/RealtimeNotifier.tsx`：
  - 全局右上角 toast 通知：
    - `alert`：严重/高/中等级别弹窗。
    - `crawl_complete`：采集成功提示。
    - `data_quality`：发现质量问题时警告。
- 大屏自动刷新：`Dashboard.tsx` 监听 `alert` 和 `crawl_complete` 事件，收到后调用 `fetchData` 刷新总览数据。
- 保留现有 30 秒轮询作为兜底。

## 事件消息格式

```json
{
  "type": "alert",
  "payload": { "event_id": 1, "rule_id": 1, "rule_name": "热度飙升", "severity": "high", "topic_id": 123 },
  "timestamp": "2026-07-18T12:00:00+08:00"
}
```

## 验证

```bash
python -m compileall backend\app backend\tests
pytest backend\tests\test_api.py::TestRealtimeEndpoints -q
pytest backend\tests -q
cd frontend && npx tsc --noEmit
npm run build
git diff --check
```

当前验证结果：

- `pytest backend\tests -q`：**79+ passed**。
- `npx tsc --noEmit`：零错误。
- `git diff --check`：通过。

## 已知限制

- 单机进程内广播，多实例部署需要接入 Redis Pub/Sub（路线图 P3 阶段）。
- 当前未做消息持久化，离线用户收不到历史事件。

## 下一步

- 接入 Redis 实现分布式多实例广播。
- 按用户级别和平台权限过滤事件（如分析师只接收授权平台的 crawl_complete）。
