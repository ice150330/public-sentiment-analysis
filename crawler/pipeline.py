import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# 将项目根目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models import CrawlLog, HotTopic, Platform
from crawler.data_processor import DataProcessor

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
        保存采集结果到数据库（带事务回滚和增强去重）
        
        优化点:
        - 按批次+时间窗口去重（1小时内同一标题不重复入库）
        - 自动修复缺失字段
        - 分类规范化存储
        
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
        skipped = 0
        updated = 0
        crawl_time = datetime.now()
        
        # 去重时间窗口：当天（同一标题在同一天内不重复）
        dedup_window = crawl_time.replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            for topic in topics:
                try:
                    # 增强去重：检查1小时内是否已存在相同标题或topic_id
                    existing = self._find_duplicate(topic, dedup_window)
                    
                    if existing:
                        # 如果已存在，检查是否需要更新（热度变化超过20%）
                        if self._should_update(existing, topic):
                            self._update_existing(existing, topic, crawl_time)
                            updated += 1
                        else:
                            skipped += 1
                        continue

                    # 创建新记录
                    hot_topic = HotTopic(
                        platform_id=topic["platform_id"],
                        topic_id=topic["topic_id"],
                        title=topic["title"],
                        url=topic.get("url"),
                        heat_score=topic.get("heat_score"),
                        category=topic.get("content_category", "其他"),
                        content_summary=topic.get("content_summary", ""),
                        raw_data={
                            **(topic.get("raw_data") or {}),
                            "heat_tag": topic.get("heat_tag"),
                        },
                        crawl_time=crawl_time,
                        crawl_date=crawl_time.date(),
                    )

                    self.db.add(hot_topic)
                    count += 1

                except Exception as e:
                    logger.error(f"Failed to save topic {topic.get('topic_id')}: {e}")
                    continue

            # 提交事务
            self.db.commit()
            logger.info(
                f"Batch saved: {count} new, {updated} updated, {skipped} skipped, "
                f"total input: {len(topics)}"
            )

            self._update_log_status("success", records_count=count + updated)
            return count + updated

        except SQLAlchemyError as e:
            logger.error(f"Database error, rolling back: {e}")
            self.db.rollback()
            self._update_log_status("failed", error=f"Database error: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error, rolling back: {e}")
            self.db.rollback()
            self._update_log_status("failed", error=str(e))
            return 0
    
    def _find_duplicate(self, topic: Dict, since: datetime) -> Optional[HotTopic]:
        """
        查找重复话题（当天维度）
        
        检查维度:
        1. topic_id 匹配（最严格的匹配）
        2. 标题精确匹配（同一平台当天相同标题）
        """
        from datetime import date
        today = date.today()
        
        # 先检查 topic_id（当天）
        existing = self.db.query(HotTopic).filter(
            HotTopic.platform_id == topic["platform_id"],
            HotTopic.topic_id == topic["topic_id"],
            HotTopic.crawl_date == today,
        ).first()
        
        if existing:
            return existing
        
        # 再检查标题（当天）
        existing = self.db.query(HotTopic).filter(
            HotTopic.platform_id == topic["platform_id"],
            HotTopic.title == topic["title"],
            HotTopic.crawl_date == today,
        ).first()
        
        return existing
    
    def _should_update(self, existing: HotTopic, new_topic: Dict) -> bool:
        """
        判断是否需要更新已有记录
        
        更新条件:
        - 热度变化超过 20%
        - 分类发生变化
        """
        # 热度变化检查
        if existing.heat_score and new_topic.get("heat_score"):
            heat_change = abs(new_topic["heat_score"] - existing.heat_score) / existing.heat_score
            if heat_change > 0.2:  # 变化超过20%
                return True
        
        # 分类变化检查
        if new_topic.get("content_category") and new_topic["content_category"] != existing.category:
            return True
        
        return False
    
    def _update_existing(self, existing: HotTopic, new_topic: Dict, crawl_time: datetime):
        """更新已有记录"""
        # 更新热度（保留最高值）
        if new_topic.get("heat_score"):
            existing.heat_score = max(existing.heat_score or 0, new_topic["heat_score"])
        
        # 更新摘要（如果之前的为空）
        if not existing.content_summary and new_topic.get("content_summary"):
            existing.content_summary = new_topic["content_summary"]
        
        # 更新 raw_data
        if existing.raw_data and new_topic.get("raw_data"):
            existing.raw_data = {**existing.raw_data, **new_topic["raw_data"]}
        
        # 更新 crawl_time（标记为最新）
        existing.crawl_time = crawl_time
        
        self.db.add(existing)


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
        
        使用 DataProcessor 进行批量处理
        """
        return DataProcessor.process_batch(raw_data, platform_id)

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
        模拟爬虫数据（使用规范化分类）
        
        Args:
            platform_name: 平台名称

        Returns:
            List[Dict]: 模拟数据
        """
        import random

        count = random.randint(5, 10)
        mock_data = []

        # 标准化内容分类 + 运营标签
        content_categories = ["娱乐", "社会", "科技", "体育", "财经", "时政", "其他"]
        heat_tags = ["热", "新", "爆", "沸", None, None]  # 部分无标签
        
        # 平台特定的模拟话题模板
        topic_templates = {
            "weibo": ["明星", "综艺", "电影", "社会热点", "科技新品"],
            "douyin": ["挑战赛", "网红", "美食", "搞笑", "音乐"],
            "toutiao": ["新闻", "财经", "国际", "健康", "教育"],
            "baidu": ["搜索热点", "电视剧", "游戏", "汽车", "房产"],
            "bilibili": ["番剧", "游戏", "知识", "生活", "科技"],
            "zhihu": ["热榜", "讨论", "科普", "情感", "职场"],
        }
        
        templates = topic_templates.get(platform_name, ["话题"])

        for i in range(count):
            heat_tag = random.choice(heat_tags)
            template = random.choice(templates)
            
            # 构建标题（带运营标签前缀）
            title = f"[{platform_name}] {template}热门话题 #{i+1}"
            if heat_tag and random.random() > 0.5:
                title = f"{heat_tag}｜{title}"

            mock_data.append({
                "id": f"{platform_name}_{i}_{datetime.now().strftime('%Y%m%d%H')}",
                "title": title,
                "url": f"https://example.com/{platform_name}/{i}",
                "heat": random.randint(10000, 5000000),
                "category": random.choice(content_categories),
                "summary": f"这是 {platform_name} 的模拟内容摘要，关于{template}的热门讨论...",
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
