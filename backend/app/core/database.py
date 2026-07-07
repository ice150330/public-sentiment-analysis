"""
数据库核心模块

模块名称: database.py
模块职责: SQLite 连接引擎、Session 管理、依赖注入
作者: 码钉
日期: 2026-07-07
版本: 1.0.0
"""

import os
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base, Session

# 数据库 URL，从环境变量读取，默认本地 SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/sentiment.db")

# 创建引擎
# SQLite 单线程模式下，需要 check_same_thread=False 配合 FastAPI 的异步处理
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_pre_ping=True,
)

# 监听引擎事件：SQLite 启用外键约束（默认关闭）
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """SQLite 连接时启用外键约束"""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Session 工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM 基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入：获取数据库 Session
    
    Yields:
        Session: SQLAlchemy 数据库会话
        
    Example:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
