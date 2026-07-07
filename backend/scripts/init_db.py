"""
数据库初始化脚本

模块名称: init_db.py
模块职责: 创建所有表 + 插入初始平台数据

使用方式:
    python scripts/init_db.py
"""

import os
import sys

# 将 backend 目录加入 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import engine, Base, SessionLocal
from app.models import Platform


def init_database():
    """初始化数据库：创建表 + 插入初始数据"""
    
    # 创建数据目录
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    # 创建所有表
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
    
    # 插入初始平台数据
    db = SessionLocal()
    try:
        # 检查是否已有数据
        existing = db.query(Platform).first()
        if existing:
            print("Platforms already initialized, skipping.")
            return
        
        platforms = [
            Platform(name="weibo", display_name="微博", base_url="https://weibo.com", sort_order=1),
            Platform(name="douyin", display_name="抖音", base_url="https://www.douyin.com", sort_order=2),
            Platform(name="toutiao", display_name="今日头条", base_url="https://www.toutiao.com", sort_order=3),
            Platform(name="baidu", display_name="百度", base_url="https://www.baidu.com", sort_order=4),
            Platform(name="bilibili", display_name="B站", base_url="https://www.bilibili.com", sort_order=5),
            Platform(name="zhihu", display_name="知乎", base_url="https://www.zhihu.com", sort_order=6),
        ]
        
        db.add_all(platforms)
        db.commit()
        print(f"Initialized {len(platforms)} platforms.")
        
    except Exception as e:
        db.rollback()
        print(f"Error initializing platforms: {e}")
        raise
    finally:
        db.close()
    
    print("Database initialization completed.")


if __name__ == "__main__":
    init_database()
