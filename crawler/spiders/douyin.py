#!/usr/bin/env python3
"""
抖音热榜爬虫

模块名称: douyin.py
模块职责: 采集抖音热榜数据

注意: 抖音接口需要 Cookie，当前为占位实现
"""

import logging
from datetime import datetime
from typing import List, Dict

import requests

logger = logging.getLogger(__name__)

DOUYIN_HOT_API = (
    "https://www.douyin.com/aweme/v1/web/hot/search/list/"
    "?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.douyin.com",
}


def fetch_douyin_hot() -> List[Dict]:
    """
    获取抖音热榜列表

    Returns:
        List[Dict]: 热榜数据列表
    """
    try:
        resp = requests.get(DOUYIN_HOT_API, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("data") or not data["data"].get("word_list"):
            logger.warning("Douyin API returned empty data")
            return []

        results = []
        for item in data["data"]["word_list"]:
            results.append({
                "id": str(item.get("sentence_id", "")),
                "title": item.get("word", ""),
                "url": f"https://www.douyin.com/hot/{item.get('sentence_id', '')}",
                "heat": str(item.get("hot_value", 0)),
                "category": "热",
                "summary": item.get("word", ""),
                "source": "douyin",
                "crawl_time": datetime.now().isoformat(),
            })

        logger.info(f"Fetched {len(results)} hot topics from Douyin")
        return results

    except requests.RequestException as e:
        logger.error(f"Douyin API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Douyin parse failed: {e}")
        return []
