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
from datetime import datetime
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
        
        # 去除 emoji（精确匹配 Unicode emoji 范围，不覆盖中文字符）
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"   # 表情符号
            "\U0001F300-\U0001F5FF"   # 符号和象形文字
            "\U0001F680-\U0001F6FF"   # 交通和地图符号
            "\U0001F1E0-\U0001F1FF"   # 国旗
            "\U00002702-\U000027B0"   # dingbats
            "\U0001F900-\U0001F9FF"   # 补充符号和象形文字
            "\U0001FA00-\U0001FA6F"   # 扩展A
            "\U0001FA70-\U0001FAFF"   # 扩展B
            "\U00002600-\U000026FF"   # 杂项符号
            "\U00002500-\U00002BEF"   # 其他符号
            "\U0000FE00-\U0000FE0F"   # 变体选择器
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
    def extract_heat_tag(cls, title: str) -> Tuple[str, Optional[str]]:
        """
        从标题中提取运营标签
        
        Args:
            title: 原始标题
            
        Returns:
            Tuple[净化后的标题, 运营标签]
        """
        heat_tag = None
        
        # 检查标题开头是否有运营标签
        for tag in cls.HEAT_TAGS:
            # 匹配开头标签 + 分隔符
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
