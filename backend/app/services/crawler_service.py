"""
爬虫服务层

模块名称: crawler_service.py
模块职责: 爬虫调度、数据入库、日志记录
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from app.models import HotTopic, CrawlLog, Platform

logger = logging.getLogger(__name__)


class CrawlerService:
    """爬虫服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def run_crawl(self, platform_names: List[str]) -> Dict:
        """
        执行采集任务
        
        Args:
            platform_names: 要采集的平台名称列表
            
        Returns:
            Dict: 采集结果统计
        """
        results = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "details": [],
        }
        
        for platform_name in platform_names:
            try:
                # 查询平台配置
                platform = self.db.query(Platform).filter(
                    Platform.name == platform_name
                ).first()
                
                if not platform or not platform.is_active:
                    logger.warning(f"Platform {platform_name} not found or inactive")
                    continue
                
                # 记录采集开始
                log = CrawlLog(
                    platform_id=platform.id,
                    status="running",
                    started_at=datetime.now(),
                )
                self.db.add(log)
                self.db.commit()
                
                # TODO: 调用实际爬虫模块
                # 当前为占位实现
                crawl_result = self._mock_crawl(platform_name)
                
                # 保存数据
                records = self._save_topics(crawl_result, platform.id)
                
                # 更新日志
                log.status = "success" if records > 0 else "partial"
                log.records_count = records
                log.completed_at = datetime.now()
                self.db.commit()
                
                results["total"] += records
                results["success"] += 1
                results["details"].append({
                    "platform": platform_name,
                    "status": "success",
                    "records": records,
                })
                
            except Exception as e:
                logger.error(f"Crawl failed for {platform_name}: {e}")
                
                # 更新日志为失败
                if 'log' in locals():
                    log.status = "failed"
                    log.error_message = str(e)
                    log.completed_at = datetime.now()
                    self.db.commit()
                
                results["failed"] += 1
                results["details"].append({
                    "platform": platform_name,
                    "status": "failed",
                    "error": str(e),
                })
        
        return results
    
    def _mock_crawl(self, platform_name: str) -> List[Dict]:
        """
        模拟爬虫采集（占位实现）
        
        TODO: 替换为实际爬虫调用
        """
        import random
        
        # 模拟返回 5-10 条数据
        count = random.randint(5, 10)
        mock_data = []
        
        for i in range(count):
            mock_data.append({
                "topic_id": f"{platform_name}_{i}_{datetime.now().strftime('%Y%m%d')}",
                "title": f"[{platform_name}] 模拟话题 #{i+1}",
                "url": f"https://example.com/{platform_name}/{i}",
                "heat_score": random.randint(10000, 5000000),
                "category": "娱乐" if random.random() > 0.5 else "社会",
                "content_summary": f"这是 {platform_name} 的模拟内容摘要...",
                "raw_data": {"source": "mock"},
            })
        
        return mock_data
    
    def _save_topics(self, topics: List[Dict], platform_id: int) -> int:
        """
        保存热榜数据到数据库
        
        Args:
            topics: 采集到的热榜数据列表
            platform_id: 平台ID
            
        Returns:
            int: 保存的记录数
        """
        count = 0
        crawl_time = datetime.now()
        
        for topic_data in topics:
            try:
                # 检查是否已存在（联合唯一键）
                existing = self.db.query(HotTopic).filter(
                    HotTopic.platform_id == platform_id,
                    HotTopic.topic_id == topic_data["topic_id"],
                    HotTopic.crawl_time == crawl_time,
                ).first()
                
                if existing:
                    continue
                
                # 创建新记录
                hot_topic = HotTopic(
                    platform_id=platform_id,
                    topic_id=topic_data["topic_id"],
                    title=topic_data["title"],
                    url=topic_data.get("url"),
                    heat_score=topic_data.get("heat_score"),
                    category=topic_data.get("category"),
                    content_summary=topic_data.get("content_summary"),
                    raw_data=topic_data.get("raw_data"),
                    crawl_time=crawl_time,
                )
                
                self.db.add(hot_topic)
                count += 1
                
            except Exception as e:
                logger.error(f"Failed to save topic: {e}")
                continue
        
        self.db.commit()
        return count
