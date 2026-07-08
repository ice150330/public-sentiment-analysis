"""
爬虫导出模块

模块名称: __init__.py
模块职责: 统一导出所有平台爬虫入口
"""

from crawler.spiders.weibo_api import fetch_weibo_hot
from crawler.spiders.douyin import fetch_douyin_hot
from crawler.spiders.toutiao import fetch_toutiao_hot
from crawler.spiders.baidu import fetch_baidu_hot
from crawler.spiders.bilibili import fetch_bilibili_hot, fetch_bilibili_videos
from crawler.spiders.zhihu import fetch_zhihu_hot

__all__ = [
    "fetch_weibo_hot",
    "fetch_douyin_hot",
    "fetch_toutiao_hot",
    "fetch_baidu_hot",
    "fetch_bilibili_hot",
    "fetch_bilibili_videos",
    "fetch_zhihu_hot",
]
