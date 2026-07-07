"""
FastAPI 应用主入口

模块名称: main.py
模块职责: 应用初始化、路由注册、异常处理、中间件配置
"""

import uuid
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.api.v1 import platforms, topics, sentiment, stats, crawler


# 应用元信息
APP_NAME = "PublicSentimentAnalysis"
APP_VERSION = "1.0.0"

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
    topics.router,
    prefix="/api/v1/topics",
    tags=["热榜数据"],
)

app.include_router(
    sentiment.router,
    prefix="/api/v1/sentiment",
    tags=["情感分析"],
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
