#!/usr/bin/env python3
"""
知乎热榜爬虫

模块名称: zhihu.py
模块职责: 采集知乎热榜数据
"""

import logging
from datetime import datetime
from typing import List, Dict

import requests

logger = logging.getLogger(__name__)

ZHIHU_HOT_API = "https://www.zhihu.com/api/v3/feed/topstory/hot-list-web?limit=20&desktop=true"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.zhihu.com",
}


def fetch_zhihu_hot() -> List[Dict]:
    """
    获取知乎热榜列表

    Returns:
        List[Dict]: 热榜数据列表
    """
    try:
        resp = requests.get(ZHIHU_HOT_API, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("data"):
            logger.warning("Zhihu API returned empty data")
            return []

        results = []
        for item in data["data"]:
            target = item.get("target", {})
            results.append({
                "id": str(target.get("id", "")),
                "title": target.get("title_area", {}).get("text", ""),
                "url": target.get("link", {}).get("url", ""),
                "heat": target.get("metrics_area", {}).get("text", ""),
                "category": "问答",
                "summary": target.get("excerpt_area", {}).get("text", ""),
                "source": "zhihu",
                "crawl_time": datetime.now().isoformat(),
            })

        logger.info(f"Fetched {len(results)} hot topics from Zhihu")
        return results

    except requests.RequestException as e:
        logger.error(f"Zhihu API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Zhihu parse failed: {e}")
        return []
