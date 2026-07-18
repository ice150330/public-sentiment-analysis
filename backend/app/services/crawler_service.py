"""
爬虫服务层

模块名称: crawler_service.py
模块职责: 爬虫调度、数据入库、日志记录
"""

import logging
from datetime import datetime
from typing import List, Dict

from sqlalchemy.orm import Session

from app.models import Platform
from app.services.realtime_service import broadcast_event_sync
from crawler.pipeline import CrawlPipeline

logger = logging.getLogger(__name__)


class CrawlerService:
    """爬虫服务"""

    def __init__(self, db: Session):
        self.db = db
        self.pipeline = CrawlPipeline(db)

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

                # 使用管道执行采集
                topics = self.pipeline.crawl_platform(platform_name, use_mock=False)
                saved_count = self.pipeline.save_results(topics)

                if topics:
                    results["total"] += saved_count
                    results["success"] += 1
                    results["details"].append({
                        "platform": platform_name,
                        "status": "success" if saved_count > 0 else "no_new_data",
                        "fetched": len(topics),
                        "records": saved_count,
                    })
                else:
                    results["failed"] += 1
                    results["details"].append({
                        "platform": platform_name,
                        "status": "failed",
                        "error": "No data saved",
                    })

            except Exception as e:
                logger.error(f"Crawl failed for {platform_name}: {e}")
                results["failed"] += 1
                results["details"].append({
                    "platform": platform_name,
                    "status": "failed",
                    "error": str(e),
                })

        # 实时推送采集完成事件
        try:
            broadcast_event_sync(
                "crawl_complete",
                {
                    "total": results["total"],
                    "success": results["success"],
                    "failed": results["failed"],
                    "details": results["details"],
                },
            )
        except Exception as exc:
            logger.warning(f"Failed to broadcast crawl complete event: {exc}")

        return results
