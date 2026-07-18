"""
FastAPI 应用主入口

模块名称: main.py
模块职责: 应用初始化、路由注册、异常处理、中间件配置
"""

import uuid
import time
import os
from collections import defaultdict, deque
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.database import engine, Base
from app.core.scheduler import get_scheduler
from app.core.security import TokenError, decode_access_token
from app.services.sqlite_maintenance import ensure_sqlite_indexes
from app.api.v1 import platforms, topics, sentiment, stats, crawler, alerts, data_quality, system, topic_ext, model, ui_compat, sentiment_v2, exports, auth
from app.api.v1 import topic_clusters, propagation_paths, trend_predictions, model_explanations


# 应用启动时创建所有表（包括新增表）
Base.metadata.create_all(bind=engine)
ensure_sqlite_indexes(engine)


# 应用元信息
APP_NAME = "PublicSentimentAnalysis"
APP_VERSION = "1.1.0"

# 创建 FastAPI 应用
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="公众情绪智能分析系统 - 后端 API",
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """记录请求处理时间"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    return response


# 统一响应包装中间件
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """为每个请求生成唯一 ID"""
    request_id = str(uuid.uuid4())[:12]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


PUBLIC_API_PREFIXES = ("/api/v1/auth/",)
PUBLIC_PATHS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
RATE_LIMIT_WINDOW_SECONDS = 60
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit_key(request: Request) -> str:
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("user_id")
            if user_id:
                return f"user:{user_id}"
        except TokenError:
            pass

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return f"ip:{forwarded_for.split(',')[0].strip()}"
    return f"ip:{request.client.host if request.client else 'unknown'}"


@app.middleware("http")
async def apply_rate_limit(request: Request, call_next):
    """Apply a lightweight per-minute request limit to API endpoints."""
    path = request.url.path
    if request.method != "OPTIONS" and path.startswith("/api/v1") and RATE_LIMIT_PER_MINUTE > 0:
        now = time.time()
        bucket = _RATE_LIMIT_BUCKETS[_rate_limit_key(request)]
        while bucket and now - bucket[0] >= RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()

        remaining = max(0, RATE_LIMIT_PER_MINUTE - len(bucket))
        if remaining <= 0:
            retry_after = max(1, int(RATE_LIMIT_WINDOW_SECONDS - (now - bucket[0]))) if bucket else RATE_LIMIT_WINDOW_SECONDS
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"code": 429, "data": None, "message": "Too many requests"},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Remaining": "0",
                },
            )

        bucket.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining - 1))
        return response

    return await call_next(request)


@app.middleware("http")
async def require_api_authentication(request: Request, call_next):
    """Require Bearer token authentication for API data endpoints."""
    path = request.url.path
    is_public = (
        request.method == "OPTIONS"
        or path in PUBLIC_PATHS
        or path.startswith(PUBLIC_API_PREFIXES)
        or path.startswith("/docs/")
        or path.startswith("/redoc/")
    )

    if not is_public and path.startswith("/api/v1"):
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"code": 401, "data": None, "message": "Not authenticated"},
            )
        try:
            payload = decode_access_token(token)
        except TokenError as exc:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"code": 401, "data": None, "message": str(exc)},
            )
        request.state.auth_payload = payload
        request.state.auth_role = payload.get("role")
        request.state.auth_user_id = payload.get("user_id")

    return await call_next(request)


# 全局异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数校验错误处理"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "data": None,
            "message": f"参数校验错误: {exc.errors()[0]['msg'] if exc.errors() else '未知错误'}",
            "error_type": "ValidationError",
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "data": None,
            "message": f"服务器内部错误: {str(exc)}",
            "error_type": type(exc).__name__,
            "request_id": getattr(request.state, "request_id", None),
            "timestamp": datetime.now().isoformat(),
        },
    )


# 生命周期事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    if os.getenv("DISABLE_SCHEDULER", "false").lower() == "true":
        return
    # 启动后台任务调度器
    scheduler = get_scheduler()
    await scheduler.start()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    if os.getenv("DISABLE_SCHEDULER", "false").lower() == "true":
        return
    # 停止后台任务调度器
    scheduler = get_scheduler()
    await scheduler.stop()


# 健康检查
@app.get("/health", tags=["系统"])
async def health_check():
    """服务健康检查"""
    return {
        "code": 200,
        "data": {
            "status": "healthy",
            "version": APP_VERSION,
            "timestamp": datetime.now().isoformat(),
        },
        "message": "success",
    }


# 根路径
@app.get("/", tags=["系统"])
async def root():
    """API 根路径"""
    return {
        "code": 200,
        "data": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "docs": "/docs",
        },
        "message": "欢迎使用公众情绪智能分析系统 API",
    }


# 注册 API 路由
app.include_router(
    platforms.router,
    prefix="/api/v1/platforms",
    tags=["平台管理"],
)

app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["用户认证"],
)

app.include_router(
    topics.router,
    prefix="/api/v1/topics",
    tags=["热榜数据"],
)

app.include_router(
    sentiment.router,
    prefix="/api/v1/sentiment",
    tags=["情感分析"],
)

# Transformers V2 情感分析（增强版）
app.include_router(
    sentiment_v2.router,
    prefix="/api/v1/sentiment",
    tags=["情感分析V2"],
)

app.include_router(
    stats.router,
    prefix="/api/v1/stats",
    tags=["统计分析"],
)

app.include_router(
    crawler.router,
    prefix="/api/v1/crawler",
    tags=["爬虫控制"],
)

app.include_router(
    alerts.router,
    prefix="/api/v1/alerts",
    tags=["预警中心"],
)

app.include_router(
    exports.router,
    prefix="/api/v1/exports",
    tags=["数据导出"],
)

app.include_router(
    data_quality.router,
    prefix="/api/v1/data-quality",
    tags=["数据质量"],
)

app.include_router(
    system.router,
    prefix="/api/v1/system",
    tags=["系统管理"],
)

app.include_router(
    topic_ext.router,
    prefix="/api/v1/topic-ext",
    tags=["话题扩展"],
)

app.include_router(
    model.router,
    prefix="/api/v1/model",
    tags=["模型管理"],
)

app.include_router(
    topic_clusters.router,
    prefix="/api/v1/topic-clusters",
    tags=["主题聚类"],
)

app.include_router(
    propagation_paths.router,
    prefix="/api/v1/propagation-paths",
    tags=["传播路径"],
)

app.include_router(
    trend_predictions.router,
    prefix="/api/v1/trend-predictions",
    tags=["趋势预测"],
)

app.include_router(
    model_explanations.router,
    prefix="/api/v1/model-explanations",
    tags=["模型解释"],
)

app.include_router(
    ui_compat.router,
    tags=["UI 兼容接口"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
