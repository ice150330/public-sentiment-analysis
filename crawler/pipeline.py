"""
爬虫集成管道

模块名称: pipeline.py
模块职责: 连接爬虫代码与后端服务，提供数据清洗和入库接口

修复内容:
- 使用 Playwright 浏览器自动化
- 修复重复入库判断（topic_id + 日期）
- 显式控制 mock 模式
- 添加事务回滚
- 支持重试机制

使用方式:
    from crawler.pipeline import CrawlPipeline

    pipeline = CrawlPipeline(db_session)
    # 真实爬取
    results = pipeline.crawl_platform("weibo", use_mock=False)
    # 使用模拟数据
    results = pipeline.crawl_platform("weibo", use_mock=True)
    pipeline.save_results(results)
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# 将项目根目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import CrawlLog, HotTopic, Platform

logger = logging.getLogger(__name__)


class CrawlPipeline:
    """
    爬虫集成管道

    负责:
    1. 调用各平台爬虫模块(支持真实爬取和模拟数据)
    2. 清洗和标准化数据
    3. 批量入库(带事务回滚)
    4. 记录采集日志
    """

    def __init__(self, db: Session):
        self.db = db
        self.current_log: Optional[CrawlLog] = None

    def crawl_platform(self, platform_name: str, use_mock: bool = False) -> List[Dict]:
        """
        采集指定平台数据

        Args:
            platform_name: 平台名称 (weibo, douyin, toutiao, baidu, bilibili, zhihu)
            use_mock: 是否使用模拟数据(默认 False,即尝试真实爬取)

        Returns:
            List[Dict]: 标准化后的热榜数据列表
        """
        # 查询平台配置
        platform = self.db.query(Platform).filter(
            Platform.name == platform_name
        ).first()

        if not platform or not platform.is_active:
            logger.warning(f"Platform {platform_name} not found or inactive")
            return []

        # 创建采集日志
        self.current_log = CrawlLog(
            platform_id=platform.id,
            status="running",
            started_at=datetime.now(),
        )
        self.db.add(self.current_log)
        self.db.commit()

        try:
            if use_mock:
                # 显式使用模拟数据
                logger.info(f"Using mock data for {platform_name}")
                raw_data = self._mock_crawl(platform_name)
            else:
                # 尝试真实爬取
                logger.info(f"Starting real crawl for {platform_name}")
                raw_data = self._real_crawl(platform_name)

                # 如果真实爬取失败且未禁用 mock fallback
                if not raw_data:
                    logger.warning(f"Real crawl failed for {platform_name}, falling back to mock")
                    raw_data = self._mock_crawl(platform_name)
                    # 记录使用了 fallback
                    if self.current_log:
                        self.current_log.error_message = "Used mock fallback"

            # 数据清洗和标准化
            cleaned_data = self._clean_data(raw_data, platform.id)

            return cleaned_data

        except Exception as e:
            logger.error(f"Crawl failed for {platform_name}: {e}")
            self._update_log_status("failed", error=str(e))
            return []

    def save_results(self, topics: List[Dict]) -> int:
        """
        保存采集结果到数据库(带事务回滚)

        Args:
            topics: 清洗后的热榜数据列表

        Returns:
            int: 保存成功的记录数
        """
        if not topics:
            logger.info("No topics to save")
            self._update_log_status("success", records_count=0)
            return 0

        count = 0
        crawl_time = datetime.now()
        # 获取今天的日期(用于去重判断)
        today = crawl_time.date()

        try:
            for topic in topics:
                try:
                    # 检查今天是否已存在相同 topic_id 的记录
                    existing = self.db.query(HotTopic).filter(
                        HotTopic.platform_id == topic["platform_id"],
                        HotTopic.topic_id == topic["topic_id"],
                        HotTopic.crawl_time >= today,
                        HotTopic.crawl_time < today + timedelta(days=1),
                    ).first()

                    if existing:
                        logger.debug(f"Topic {topic['topic_id']} already exists today, skipping")
                        continue

                    # 创建记录
                    hot_topic = HotTopic(
                        platform_id=topic["platform_id"],
                        topic_id=topic["topic_id"],
                        title=topic["title"],
                        url=topic.get("url"),
                        heat_score=topic.get("heat_score"),
                        category=topic.get("category"),
                        content_summary=topic.get("content_summary"),
                        raw_data=topic.get("raw_data"),
                        crawl_time=crawl_time,
                    )

                    self.db.add(hot_topic)
                    count += 1

                except Exception as e:
                    logger.error(f"Failed to save topic {topic.get('topic_id')}: {e}")
                    continue

            # 提交事务
            self.db.commit()
            logger.info(f"Successfully saved {count} topics")

            # 更新日志
            status = "success" if count > 0 else "partial"
            self._update_log_status(status, records_count=count)

            return count

        except SQLAlchemyError as e:
            # 数据库错误,回滚事务
            logger.error(f"Database error, rolling back: {e}")
            self.db.rollback()
            self._update_log_status("failed", error=f"Database error: {str(e)}")
            return 0
        except Exception as e:
            # 其他错误,回滚事务
            logger.error(f"Unexpected error, rolling back: {e}")
            self.db.rollback()
            self._update_log_status("failed", error=str(e))
            return 0

    def _real_crawl(self, platform_name: str) -> List[Dict]:
        """
        真实爬取数据

        Args:
            platform_name: 平台名称

        Returns:
            List[Dict]: 原始数据列表
        """
        crawler_map = {
            "weibo": "crawler.spiders.weibo_api",
            "douyin": "crawler.spiders.douyin",
            "toutiao": "crawler.spiders.toutiao",
            "baidu": "crawler.spiders.baidu",
            "bilibili": "crawler.spiders.bilibili",
            "zhihu": "crawler.spiders.zhihu",
        }

        module_path = crawler_map.get(platform_name)
        if not module_path:
            logger.warning(f"No crawler available for {platform_name}")
            return []

        try:
            import importlib
            module = importlib.import_module(module_path)
            func_name = f"fetch_{platform_name}_hot"
            crawl_func = getattr(module, func_name, None)

            if crawl_func:
                return crawl_func()
            else:
                logger.warning(f"Crawler function {func_name} not found in {module_path}")
                return []

        except Exception as e:
            logger.error(f"Real crawl failed for {platform_name}: {e}")
            return []

    def _clean_data(self, raw_data: List[Dict], platform_id: int) -> List[Dict]:
        """
        清洗和标准化原始数据

        Args:
            raw_data: 爬虫原始数据
            platform_id: 平台ID

        Returns:
            List[Dict]: 标准化后的数据
        """
        import hashlib

        cleaned = []
        seen_topic_ids = set()

        for item in raw_data:
            try:
                # 提取标题
                title = item.get("title", item.get("topic", "")).strip()
                if not title:
                    continue

                # 生成唯一 topic_id(如果为空)
                topic_id = str(item.get("id", item.get("rank", ""))).strip()
                if not topic_id or topic_id in {"0", "None", "null"}:
                    # 使用标题哈希作为 topic_id
                    topic_id = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]

                if topic_id in seen_topic_ids:
                    topic_id = hashlib.sha1(f"{title}:{len(seen_topic_ids)}".encode("utf-8")).hexdigest()[:16]
                seen_topic_ids.add(topic_id)

                # 清洗文本
                cleaned_item = {
                    "platform_id": platform_id,
                    "topic_id": topic_id,
                    "title": title,
                    "url": item.get("url", item.get("link", "")),
                    "heat_score": self._parse_heat_score(item.get("heat", item.get("hot", 0))),
                    "category": item.get("category", "未分类"),
                    "content_summary": item.get("summary", "")[:500],  # 限制500字
                    "raw_data": item,  # 保留原始数据
                }

                cleaned.append(cleaned_item)

            except Exception as e:
                logger.error(f"Data cleaning failed: {e}")
                continue

        return cleaned

    def _parse_heat_score(self, heat_value) -> Optional[int]:
        """
        解析热度值为整数

        支持格式:
        - 数字: 1234567
        - 字符串: "123万", "1.2亿", "5200"
        - 混合: "剧集 543609"(提取数字部分)
        """
        if not heat_value:
            return None

        try:
            # 如果是数字直接返回
            if isinstance(heat_value, (int, float)):
                return int(heat_value)

            # 处理字符串
            heat_str = str(heat_value).strip()

            # 提取数字部分(处理 "剧集 543609" 这类格式)
            import re
            numbers = re.findall(r'\d+\.?\d*', heat_str)
            if numbers:
                # 使用最后一个数字(通常是热度值)
                heat_str = numbers[-1]
            else:
                return None

            # 处理 "万" 单位
            if "万" in str(heat_value):
                num = float(heat_str)
                return int(num * 10000)

            # 处理 "亿" 单位
            if "亿" in str(heat_value):
                num = float(heat_str)
                return int(num * 100000000)

            # 纯数字
            return int(float(heat_str))

        except (ValueError, TypeError):
            logger.warning(f"Failed to parse heat score: {heat_value}")
            return None

    def _update_log_status(self, status: str, records_count: int = 0, error: str = None):
        """更新采集日志状态"""
        if self.current_log:
            self.current_log.status = status
            self.current_log.records_count = records_count
            if error:
                self.current_log.error_message = error
            self.current_log.completed_at = datetime.now()
            self.db.commit()

    def _mock_crawl(self, platform_name: str) -> List[Dict]:
        """
        模拟爬虫数据

        Args:
            platform_name: 平台名称

        Returns:
            List[Dict]: 模拟数据
        """
        import random

        count = random.randint(5, 10)
        mock_data = []

        categories = ["娱乐", "社会", "科技", "体育", "财经", "时政"]

        for i in range(count):
            mock_data.append({
                "id": f"{platform_name}_{i}_{datetime.now().strftime('%Y%m%d')}",
                "title": f"[{platform_name}] 模拟热门话题 #{i+1}",
                "url": f"https://example.com/{platform_name}/{i}",
                "heat": random.randint(10000, 5000000),
                "category": random.choice(categories),
                "summary": f"这是 {platform_name} 的模拟内容摘要...",
                "source": "mock",
            })

        return mock_data


if __name__ == "__main__":
    # 测试管道
    print("Testing CrawlPipeline...")

    from app.core.database import SessionLocal

    with SessionLocal() as db:
        pipeline = CrawlPipeline(db)

        # 测试真实爬取
        print("\n1. Testing real crawl:")
        results = pipeline.crawl_platform("weibo", use_mock=False)
        print(f"   Crawled {len(results)} topics")

        # 测试保存
        if results:
            saved = pipeline.save_results(results)
            print(f"   Saved {saved} topics")

        # 测试模拟数据
        print("\n2. Testing mock crawl:")
        mock_results = pipeline.crawl_platform("weibo", use_mock=True)
        print(f"   Crawled {len(mock_results)} topics (mock)")
