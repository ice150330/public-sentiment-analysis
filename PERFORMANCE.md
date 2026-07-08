# 性能限制与优化指南

## 当前性能限制

### 1. 单任务执行时间
- **限制**: 单次任务执行超过 ~60-120 秒可能被系统 SIGKILL 终止
- **影响**: 全量测试（23个接口串行执行）会触发此限制
- **解决方案**: 测试按模块分批执行，单次不超过 10 个接口

### 2. 内存占用
- **限制**: 单进程内存上限约 2GB
- **影响**: 同时加载 18 个 SQLAlchemy 模型 + 全量路由表可能触发 OOM
- **解决方案**: 懒加载模型，启动时不全量 import

### 3. 并发处理
- **限制**: 当前为单进程单线程模式（SQLite 限制）
- **影响**: 高并发请求会排队处理
- **解决方案**: 生产环境建议切换到 PostgreSQL + Gunicorn 多进程

## 已实施的优化

### 1. 后台调度器 (`app/core/scheduler.py`)
- 预警评估和数据质量检查改为后台定时任务
- 不再阻塞主进程或请求线程
- 调度周期：预警 5 分钟、质量检查 60 分钟

### 2. 测试拆分策略
```bash
# 方案 A：按模块分批测试
bash run_tests.sh --module=core        # 核心接口
bash run_tests.sh --module=alerts      # 预警模块
bash run_tests.sh --module=analytics   # 高级分析

# 方案 B：快速冒烟测试（5个核心接口）
bash run_tests.sh --smoke
```

### 3. 启动优化
- FastAPI 路由懒加载：非核心路由按需注册
- 数据库连接池限制：SQLite 最大连接数设为 5
- 模型导入优化：`__init__.py` 中使用延迟导入

## 生产环境建议

### 数据库迁移
```bash
# 从 SQLite 切换到 PostgreSQL
DATABASE_URL=postgresql://user:pass@localhost/sentiment
```

### 部署架构
```
Nginx (负载均衡)
    ├── Gunicorn Worker 1 (Uvicorn)
    ├── Gunicorn Worker 2 (Uvicorn)
    └── Gunicorn Worker 3 (Uvicorn)
```

### 环境变量配置
```env
# 性能调优
MAX_WORKERS=4
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# 缓存
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300
```

## 监控指标

| 指标 | 健康阈值 | 告警阈值 |
|------|----------|----------|
| 启动时间 | < 5s | > 10s |
| 内存占用 | < 500MB | > 1GB |
| 接口响应时间 | < 200ms | > 1s |
| 数据库连接数 | < 10 | > 20 |

## 故障排查

### 启动失败（SIGKILL）
```bash
# 检查内存使用
free -h

# 分批启动路由
python -c "from app.main import app; print(len(app.routes))"

# 使用 TestClient 轻量测试
python tests/test_smoke.py
```

### 数据库锁定（SQLite）
```bash
# 检查并发写入
lsof data/sentiment.db

# 切换到 WAL 模式
sqlite3 data/sentiment.db "PRAGMA journal_mode=WAL;"
```

---

*最后更新: 2026-07-08*
