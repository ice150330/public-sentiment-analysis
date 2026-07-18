# P3 工程化与运维优化（精简版）

本阶段补齐毕设展示所需的工程化基础能力，保持单机部署、不引入复杂监控栈。

## 已完成内容

### 1. Docker Compose 全栈编排

- `docker-compose.yml`：启动 `sentiment-backend` + `sentiment-frontend`。
- `backend/Dockerfile`：基于 `python:3.12-slim`，WORKDIR `/app/backend`，`PYTHONPATH=/app` 保证 `crawler/` 可被导入。
- `frontend/Dockerfile`：多阶段构建，最终用 `nginx:1.26-alpine` 托管静态产物。
- `frontend/nginx.conf`：单页应用路由回退 + 静态资源缓存。
- `.dockerignore`：排除 `node_modules`、缓存、SQLite journal、敏感配置等。

### 2. GitHub Actions CI

- `.github/workflows/ci.yml`：
  - 后端：Python 3.12 安装依赖后运行 `pytest tests -q`。
  - 前端：Node 20 安装依赖后执行 `tsc --noEmit` 与 `npm run build`。

### 3. 结构化日志

- `backend/app/core/logging.py`：
  - `JsonFormatter` 输出单行 JSON，字段包括 `timestamp/level/logger/message/source/function/thread`。
  - 支持 `extra` 字段透传，便于后续接入 trace_id。
  - `setup_logging()` 在应用启动时调用，日志级别通过环境变量 `LOG_LEVEL` 控制。
  - 默认降低 `uvicorn.access` 与 `sqlalchemy.engine` 噪音。

## 使用方式

```bash
# 构建并启动全栈
docker-compose up --build -d

# 访问
# 前端: http://localhost:3000
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

## 验证

```bash
python -m pytest backend/tests -q
cd frontend && npx tsc --noEmit && npm run build
git diff --check
```

当前验证结果：

- `pytest backend\tests -q`：**85 passed**。
- `npx tsc --noEmit`：零错误。
- `git diff --check`：通过。

## 已知限制与后续建议

- 未引入 Prometheus/Grafana：单机演示场景下日志 + 健康检查足够。
- 未引入 Redis：实时推送当前为进程内广播，多实例部署需替换为 Redis Pub/Sub。
- 爬虫稳定性（代理池/Cookie 池/反爬）超出毕设范围，保持现有学术场景采集频率。
- 数据库使用 SQLite，未引入 Alembic；Schema 变更由 `Base.metadata.create_all` 自动补齐，生产环境建议迁移到 PostgreSQL + Alembic。
