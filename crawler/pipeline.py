"""
爬虫集成管道

模块名称: pipeline.py
模块职责: 连接现有爬虫代码与后端服务，提供数据清洗和入库接口

使用方式:
    from crawler.pipeline import CrawlPipeline
    
    pipeline = CrawlPipeline(db_session)
    results = pipeline.crawl_platform("weibo")
    pipeline.save_results(results)
"""

import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional

# 将项目根目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.orm import Session

from app.models import HotTopic, CrawlLog, Platform

logger = logging.getLogger(__name__)


class CrawlPipeline:
    """
    爬虫集成管道
    
    负责:
    1. 调用各平台爬虫模块
    2. 清洗和标准化数据
    3. 批量入库
    4. 记录采集日志
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.current_log: Optional[CrawlLog] = None
    
    def crawl_platform(self, platform_name: str) -> List[Dict]:
        """
        采集指定平台数据
        
        Args:
            platform_name: 平台名称 (weibo, douyin, toutiao, baidu, bilibili, zhihu)
            
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
            # 调用实际爬虫模块
            if platform_name == "weibo":
                from crawler.spiders.weibo import fetch_weibo_hot
                raw_data = fetch_weibo_hot()
                # 如果真实爬取失败，使用模拟数据
                if not raw_data:
                    logger.warning("Real crawl failed, using mock data")
                    from crawler.spiders.weibo import fetch_weibo_hot_mock
                    raw_data = fetch_weibo_hot_mock()
            else:
                # 其他平台使用模拟数据
                raw_data = self._mock_crawl(platform_name)
            
            # 数据清洗和标准化
            cleaned_data = self._clean_data(raw_data, platform.id)
            
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Crawl failed for {platform_name}: {e}")
            self._update_log_status("failed", error=str(e))
            return []
    
    def save_results(self, topics: List[Dict]) -> int:
        """
        保存采集结果到数据库
        
        Args:
            topics: 清洗后的热榜数据列表
            
        Returns:
            int: 保存成功的记录数
        """
        count = 0
        crawl_time = datetime.now()
        
        for topic in topics:
            try:
                # 检查是否已存在
                existing = self.db.query(HotTopic).filter(
                    HotTopic.platform_id == topic["platform_id"],
                    HotTopic.topic_id == topic["topic_id"],
                    HotTopic.crawl_time == crawl_time,
                ).first()
                
                if existing:
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
                logger.error(f"Failed to save topic: {e}")
                continue
        
        self.db.commit()
        
        # 更新日志
        if self.current_log:
            self._update_log_status(
                "success" if count > 0 else "partial",
                records_count=count,
            )
        
        return count
    
    def _clean_data(self, raw_data: List[Dict], platform_id: int) -> List[Dict]:
        """
        清洗和标准化原始数据
        
        Args:
            raw_data: 爬虫原始数据
            platform_id: 平台ID
            
        Returns:
            List[Dict]: 标准化后的数据
        """
        cleaned = []
        
        for item in raw_data:
            try:
                # 提取标题
                title = item.get("title", item.get("topic", "")).strip()
                if not title:
                    continue
                
                # 清洗文本
                cleaned_item = {
                    "platform_id": platform_id,
                    "topic_id": str(item.get("id", item.get("rank", ""))),
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
        """
        if not heat_value:
            return None
        
        try:
            # 如果是数字直接返回
            if isinstance(heat_value, (int, float)):
                return int(heat_value)
            
            # 处理字符串
            heat_str = str(heat_value).strip()
            
            # 处理 "万" 单位
            if "万" in heat_str:
                num = float(heat_str.replace("万", ""))
                return int(num * 10000)
            
            # 处理 "亿" 单位
            if "亿" in heat_str:
                num = float(heat_str.replace("亿", ""))
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
            self.current_log.error_message = error
            self.current_log.completed_at = datetime.now()
            self.db.commit()
    
    def _mock_crawl(self, platform_name: str) -> List[Dict]:
        """
        模拟爬虫数据（占位实现）
        
        TODO: 替换为实际爬虫调用
        """
        import random
        
        # 模拟返回 5-10 条数据
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
                "summary": f"这是 {platform_name} 的模拟内容摘要，用于测试数据清洗和入库功能...",
                "source": "mock",
            })
        
        return mock_data
