"""
数据库迁移脚本：修复热榜数据去重

变更内容:
1. 添加 crawl_date 字段 (Date)
2. 修改唯一约束: (platform_id, topic_id, crawl_time) -> (platform_id, topic_id, crawl_date)
3. 清理重复数据：同一 platform + topic_id + crawl_date 只保留最新一条
"""

import os
import sys
import sqlite3
from datetime import datetime

# 数据库路径
DB_PATH = "/root/.openclaw/workspace/sentiment-analysis/backend/data/sentiment.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=== 开始数据库迁移 ===")
    
    # 1. 检查当前表结构
    cursor.execute("PRAGMA table_info(hot_topics)")
    columns = {row[1]: row for row in cursor.fetchall()}
    print(f"当前列: {list(columns.keys())}")
    
    # 2. 如果已有 crawl_date，跳过添加列
    if "crawl_date" not in columns:
        print("添加 crawl_date 列...")
        cursor.execute("ALTER TABLE hot_topics ADD COLUMN crawl_date DATE")
        conn.commit()
        print("✅ crawl_date 列已添加")
    else:
        print("crawl_date 列已存在，跳过")
    
    # 3. 更新现有数据的 crawl_date
    print("更新现有数据的 crawl_date...")
    cursor.execute("""
        UPDATE hot_topics 
        SET crawl_date = DATE(crawl_time) 
        WHERE crawl_date IS NULL
    """)
    updated = cursor.rowcount
    conn.commit()
    print(f"✅ 已更新 {updated} 条记录的 crawl_date")
    
    # 4. 清理重复数据：保留最新的一条
    print("清理重复数据...")
    cursor.execute("""
        SELECT title, platform_id, crawl_date, COUNT(*) as cnt
        FROM hot_topics
        GROUP BY platform_id, topic_id, crawl_date
        HAVING cnt > 1
    """)
    duplicates = cursor.fetchall()
    print(f"发现 {len(duplicates)} 组重复数据")
    
    if duplicates:
        # 删除重复记录，只保留 id 最大（即最新插入）的一条
        cursor.execute("""
            DELETE FROM hot_topics
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM hot_topics
                GROUP BY platform_id, topic_id, crawl_date
            )
        """)
        deleted = cursor.rowcount
        conn.commit()
        print(f"✅ 已删除 {deleted} 条重复记录")
    
    # 5. 重建表以修改唯一约束（SQLite 不支持直接修改约束）
    print("重建表以修改唯一约束...")
    
    # 5.1 创建新表
    cursor.execute("""
        CREATE TABLE hot_topics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform_id INTEGER NOT NULL,
            topic_id VARCHAR(128) NOT NULL,
            title VARCHAR(512) NOT NULL,
            url VARCHAR(1024),
            heat_score INTEGER,
            category VARCHAR(64),
            content_summary TEXT,
            raw_data JSON,
            crawl_time DATETIME NOT NULL,
            crawl_date DATE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (platform_id, topic_id, crawl_date)
        )
    """)
    
    # 5.2 复制数据
    cursor.execute("""
        INSERT INTO hot_topics_new 
        (id, platform_id, topic_id, title, url, heat_score, category, content_summary, raw_data, crawl_time, crawl_date, created_at)
        SELECT id, platform_id, topic_id, title, url, heat_score, category, content_summary, raw_data, crawl_time, crawl_date, created_at
        FROM hot_topics
    """)
    copied = cursor.rowcount
    print(f"✅ 已复制 {copied} 条记录到新表")
    
    # 5.3 删除旧表，重命名新表
    cursor.execute("DROP TABLE hot_topics")
    cursor.execute("ALTER TABLE hot_topics_new RENAME TO hot_topics")
    
    # 5.4 重建索引
    cursor.execute("CREATE INDEX idx_hot_topics_platform ON hot_topics(platform_id)")
    cursor.execute("CREATE INDEX idx_hot_topics_crawl_time ON hot_topics(crawl_time)")
    cursor.execute("CREATE INDEX idx_hot_topics_crawl_date ON hot_topics(crawl_date)")
    cursor.execute("CREATE INDEX idx_hot_topics_topic_id ON hot_topics(topic_id)")
    
    conn.commit()
    print("✅ 表重建完成，唯一约束已更新")
    
    # 6. 验证
    cursor.execute("PRAGMA index_list(hot_topics)")
    indexes = cursor.fetchall()
    print(f"当前索引: {[idx[1] for idx in indexes]}")
    
    cursor.execute("SELECT COUNT(*) FROM hot_topics")
    total = cursor.fetchone()[0]
    print(f"当前总记录数: {total}")
    
    conn.close()
    print("=== 迁移完成 ===")

if __name__ == "__main__":
    migrate()
