"""
数据处理规范化模块

模块名称: data_processor.py
模块职责: 提供数据清洗、规范化、去重、缺失值填充等通用数据处理功能

优化内容:
- 标题规范化（去除 emoji、特殊字符、标签前缀）
- 分类规范化（区分运营标签和内容分类）
- 缺失字段智能填充
- 热度值标准化解析
- 数据校验与过滤
"""

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class DataProcessor:
    """数据规范化处理器"""
    
    # 运营标签列表（微博/抖音等平台的热度标记）
    HEAT_TAGS = {"热", "新", "爆", "沸", "荐", "荐", "稳"}
    
    # 内容分类映射（标准化分类体系）
    CATEGORY_MAP = {
        # 娱乐
        "娱乐": "娱乐", "综艺": "娱乐", "明星": "娱乐", "影视": "娱乐", "音乐": "娱乐", "游戏": "娱乐",
        # 社会
        "社会": "社会", "民生": "社会", "生活": "社会", "健康": "社会", "教育": "社会", "就业": "社会",
        # 科技
        "科技": "科技", "数码": "科技", "互联网": "科技", "AI": "科技", "人工智能": "科技", "手机": "科技",
        # 财经
        "财经": "财经", "金融": "财经", "股市": "财经", "经济": "财经", "房产": "财经", "汽车": "财经",
        # 体育
        "体育": "体育", "足球": "体育", "篮球": "体育", "奥运": "体育", "赛事": "体育",
        # 时政
        "时政": "时政", "国际": "时政", "军事": "时政", "外交": "时政", "政治": "时政",
        # 其他
        "时尚": "时尚", "美食": "美食", "旅游": "旅游", "文化": "文化", "历史": "文化",
        "搞笑": "搞笑", "萌宠": "搞笑", "段子": "搞笑",
    }
    
    # 默认分类
    DEFAULT_CATEGORY = "其他"
    
    @classmethod
    def normalize_title(cls, title: str) -> str:
        """
        规范化标题
        
        处理内容:
        - 去除首尾空白
        - 去除 emoji 和特殊符号
        - 去除平台标签前缀（如 [微博]、#话题#）
        - 限制长度（100字以内）
        """
        if not title:
            return ""
        
        # 去除首尾空白
        title = title.strip()
        
        # 去除平台标签前缀，如 [微博]、[weibo]
        title = re.sub(r'^\[.*?\]\s*', '', title)
        
        # 去除话题标签 #xxx#
        title = re.sub(r'#.*?#', '', title)
        
        # 去除 @提及
        title = re.sub(r'@\w+\s*', '', title)
        
        # 去除 URL
        title = re.sub(r'https?://\S+', '', title)
        
        # 去除 emoji（Unicode emoji 范围）
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 表情符号
            "\U0001F300-\U0001F5FF"  # 符号和象形文字
            "\U0001F680-\U0001F6FF"  # 交通和地图符号
            "\U0001F1E0-\U0001F1FF"  # 国旗
            "\U00002702-\U000027B0"  #  dingbats
            "\U000024C2-\U0001F251"  # 其他符号
            "]+",
            flags=re.UNICODE
        )
        title = emoji_pattern.sub('', title)
        
        # 去除多余空白
        title = re.sub(r'\s+', ' ', title).strip()
        
        # 限制长度
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title
    
    @classmethod
    def extract_heat_tag(cls, title: str) -> Tuple[str, str]:
        """
        从标题中提取运营标签
        
        Args:
            title: 原始标题
            
        Returns:
            Tuple[净化后的标题, 运营标签]
        """
        heat_tag = None
        
        # 检查标题开头是否有运营标签（如 "爆 话题标题"、"热｜话题标题"）
        for tag in cls.HEAT_TAGS:
            # 匹配开头标签 + 分隔符（空格、｜、|、·、· 等）
            pattern = re.compile(f'^{re.escape(tag)}' + r'[\s｜|·•]+')
            if pattern.search(title):
                heat_tag = tag
                title = pattern.sub('', title, count=1).strip()
                break
            
            # 匹配结尾标签
            pattern_end = re.compile(r'[\s｜|·•]+' + f'{re.escape(tag)}$')
            if pattern_end.search(title):
                heat_tag = tag
                title = pattern_end.sub('', title, count=1).strip()
                break
        
        return title, heat_tag
    
    @classmethod
    def normalize_category(cls, category: str, title: str = "") -> Tuple[str, Optional[str]]:
        """
        规范化分类
        
        区分内容分类和运营标签
        
        Args:
            category: 原始分类
            title: 标题（用于辅助判断）
            
        Returns:
            Tuple[内容分类, 运营标签或 None]
        """
        if not category:
            return cls.DEFAULT_CATEGORY, None
        
        category = category.strip()
        
        # 检查是否是运营标签
        if category in cls.HEAT_TAGS:
            return cls.DEFAULT_CATEGORY, category
        
        # 检查是否是映射表中的分类
        if category in cls.CATEGORY_MAP:
            return cls.CATEGORY_MAP[category], None
        
        # 尝试模糊匹配（如"娱乐榜"→"娱乐"）
        for key, mapped in cls.CATEGORY_MAP.items():
            if key in category:
                return mapped, None
        
        return category, None
    
    @classmethod
    def generate_summary(cls, title: str, content: str = "", max_length: int = 200) -> str:
        """
        智能生成摘要
        
        当 content_summary 缺失时，自动生成摘要
        """
        # 优先使用正文内容
        if content and len(content) > 10:
            # 去除HTML标签
            content = re.sub(r'<[^>]+>', '', content)
            # 去除多余空白
            content = re.sub(r'\s+', ' ', content).strip()
            # 截取前 max_length 字
            if len(content) > max_length:
                return content[:max_length-3] + "..."
            return content
        
        # 使用标题生成摘要
        if title:
            # 如果标题够长，直接作为摘要
            if len(title) > 20:
                return title
            # 否则添加前缀
            return f"关于「{title}」的热门话题"
        
        return "暂无摘要"
    
    @classmethod
    def parse_heat_score(cls, heat_value: Any) -> Optional[int]:
        """
        解析热度值（增强版）
        
        支持格式:
        - 纯数字: 1234567
        - 字符串: "123万", "1.2亿", "5200", "1.5k", "1.2M"
        - 混合文本: "剧集 543609", "热度 123.4万"
        """
        if not heat_value:
            return None
        
        try:
            # 如果是数字直接返回
            if isinstance(heat_value, (int, float)):
                return int(heat_value) if heat_value >= 0 else None
            
            heat_str = str(heat_value).strip()
            
            # 提取数字部分（处理各种格式）
            # 匹配模式：数字 + 可选小数 + 可选单位
            match = re.search(r'(\d+\.?\d*)\s*(万|亿|k|K|m|M|w|W)?', heat_str)
            if not match:
                return None
            
            num_str = match.group(1)
            unit = match.group(2) or ""
            
            num = float(num_str)
            
            # 处理单位
            unit = unit.lower()
            if unit in ("万", "w"):
                num *= 10000
            elif unit in ("亿",):
                num *= 100000000
            elif unit in ("k",):
                num *= 1000
            elif unit in ("m",):
                num *= 1000000
            
            result = int(num)
            
            # 合理性检查
            if result < 0 or result > 10000000000:  # 超过100亿视为异常
                logger.warning(f"Heat score out of range: {heat_value} -> {result}")
                return None
            
            return result
            
        except (ValueError, TypeError, OverflowError):
            logger.warning(f"Failed to parse heat score: {heat_value}")
            return None
    
    @classmethod
    def validate_topic(cls, topic_data: Dict) -> Tuple[bool, List[str]]:
        """
        校验话题数据完整性
        
        Returns:
            Tuple[是否通过, 错误信息列表]
        """
        errors = []
        
        # 标题检查
        title = topic_data.get("title", "").strip()
        if not title:
            errors.append("标题为空")
        elif len(title) < 2:
            errors.append(f"标题过短: {title}")
        elif len(title) > 100:
            errors.append(f"标题过长: {len(title)}字")
        
        # 热度检查
        heat = topic_data.get("heat_score")
        if heat is not None:
            if heat < 0:
                errors.append(f"热度为负数: {heat}")
            elif heat > 10000000000:
                errors.append(f"热度异常高: {heat}")
        
        # URL 检查（如果有的话）
        url = topic_data.get("url")
        if url and not url.startswith(("http://", "https://")):
            errors.append(f"URL 格式不正确: {url}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def process_batch(cls, raw_data: List[Dict], platform_id: int) -> List[Dict]:
        """
        批量处理原始数据
        
        处理流程:
        1. 标题规范化
        2. 提取运营标签
        3. 分类规范化
        4. 热度值解析
        5. 生成摘要
        6. 数据校验
        7. 去重（同一批次内）
        """
        processed = []
        seen_hashes = set()
        
        for item in raw_data:
            try:
                # 提取标题
                title = item.get("title", item.get("topic", ""))
                title = cls.normalize_title(title)
                
                if not title:
                    logger.warning(f"Skipping item with empty title: {item}")
                    continue
                
                # 提取运营标签
                title, heat_tag = cls.extract_heat_tag(title)
                
                # 生成 topic_id
                topic_id = str(item.get("id", item.get("rank", ""))).strip()
                if not topic_id or topic_id in {"0", "None", "null", ""}:
                    topic_id = hashlib.sha1(f"{platform_id}:{title}".encode("utf-8")).hexdigest()[:16]
                
                # 分类规范化
                raw_category = item.get("category", "")
                content_category, extracted_heat_tag = cls.normalize_category(raw_category, title)
                
                # 合并运营标签（优先从标题提取的）
                final_heat_tag = heat_tag or extracted_heat_tag
                
                # 热度解析
                heat_score = cls.parse_heat_score(item.get("heat", item.get("hot", 0)))
                
                # 生成摘要
                summary = item.get("summary", "")
                if not summary:
                    summary = cls.generate_summary(title, item.get("content", ""))
                
                # 构建标准化数据
                processed_item = {
                    "platform_id": platform_id,
                    "topic_id": topic_id,
                    "title": title,
                    "url": item.get("url", item.get("link", "")),
                    "heat_score": heat_score,
                    "content_category": content_category,  # 内容分类
                    "heat_tag": final_heat_tag,  # 运营标签（热/新/爆等）
                    "content_summary": summary[:500],  # 限制500字
                    "raw_data": item,  # 保留原始数据
                }
                
                # 数据校验
                is_valid, errors = cls.validate_topic(processed_item)
                if not is_valid:
                    logger.warning(f"Validation failed for topic {topic_id}: {errors}")
                    # 尝试修复而不是直接丢弃
                    if "标题为空" in errors:
                        continue  # 标题为空无法修复，跳过
                    if "热度为负数" in errors:
                        processed_item["heat_score"] = abs(processed_item["heat_score"])
                
                # 去重检查（同一批次内基于标题+平台）
                content_hash = hashlib.sha1(
                    f"{platform_id}:{title}".encode("utf-8")
                ).hexdigest()[:16]
                
                if content_hash in seen_hashes:
                    logger.debug(f"Duplicate topic in batch: {title[:30]}...")
                    continue
                
                seen_hashes.add(content_hash)
                processed.append(processed_item)
                
            except Exception as e:
                logger.error(f"Data processing failed: {e}")
                continue
        
        return processed


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
        
        # 去重时间窗口：1小时（同一标题在1小时内不重复）
        dedup_window = crawl_time - timedelta(hours=1)

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
                            "heat_tag": topic.get("heat_tag"),  # 运营标签存入 raw_data
                        },
                        crawl_time=crawl_time,
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
        查找重复话题
        
        检查维度:
        1. topic_id 匹配（最严格的匹配）
        2. 标题相似度（同一平台1小时内相同标题）
        """
        # 先检查 topic_id
        existing = self.db.query(HotTopic).filter(
            HotTopic.platform_id == topic["platform_id"],
            HotTopic.topic_id == topic["topic_id"],
            HotTopic.crawl_time >= since,
        ).first()
        
        if existing:
            return existing
        
        # 再检查标题（模糊匹配）
        existing = self.db.query(HotTopic).filter(
            HotTopic.platform_id == topic["platform_id"],
            HotTopic.title == topic["title"],
            HotTopic.crawl_time >= since,
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
