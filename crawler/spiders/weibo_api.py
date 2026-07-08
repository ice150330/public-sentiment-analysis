#!/usr/bin/env python3
"""
微博热搜爬虫（API 版）

模块名称: weibo_api.py
模块职责: 通过微博 AJAX API 采集热搜数据

特性:
- 直接调用微博官方 AJAX 接口
- 无需浏览器渲染
- 返回结构化 JSON 数据

作者: 码钉
日期: 2026-07-08
版本: 2.1.0
"""

import logging
from datetime import datetime
from typing import List, Dict

import requests

logger = logging.getLogger(__name__)

WEIBO_HOT_API = "https://weibo.com/ajax/side/hotSearch"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://weibo.com/hot/search",
}


def fetch_weibo_hot() -> List[Dict]:
    """
    获取微博热搜列表

    Returns:
        List[Dict]: 热搜数据列表
    """
    try:
        resp = requests.get(WEIBO_HOT_API, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("data") or not data["data"].get("realtime"):
            logger.warning("Weibo API returned empty data")
            return []

        results = []
        for item in data["data"]["realtime"]:
            results.append({
                "id": str(item.get("realpos", 0)),
                "title": item.get("word", ""),
                "url": (
                    f"https://s.weibo.com/weibo?q="
                    f"{requests.utils.quote(item.get('word_scheme', item.get('word', '')))}"
                ),
                "heat": str(item.get("num", 0)),
                "category": item.get("flag_desc", "热"),
                "summary": item.get("word", ""),
                "source": "weibo",
                "crawl_time": datetime.now().isoformat(),
            })

        logger.info(f"Fetched {len(results)} hot topics from Weibo")
        return results

    except requests.RequestException as e:
        logger.error(f"Weibo API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Weibo parse failed: {e}")
        return []
