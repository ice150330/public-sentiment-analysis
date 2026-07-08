#!/usr/bin/env python3
"""
头条热榜爬虫

模块名称: toutiao.py
模块职责: 采集今日头条热榜数据
"""

import logging
from datetime import datetime
from typing import List, Dict

import requests

from crawler.http_client import get as crawler_get

logger = logging.getLogger(__name__)

TOUTIAO_HOT_API = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.toutiao.com",
}


def fetch_toutiao_hot() -> List[Dict]:
    """
    获取头条热榜列表

    Returns:
        List[Dict]: 热榜数据列表
    """
    try:
        resp = crawler_get(TOUTIAO_HOT_API, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("data"):
            logger.warning("Toutiao API returned empty data")
            return []

        results = []
        for item in data["data"]:
            results.append({
                "id": str(item.get("ClusterId", "")),
                "title": item.get("Title", ""),
                "url": item.get("Url", ""),
                "heat": str(item.get("HotValue", 0)),
                "category": item.get("Label", "热"),
                "summary": item.get("Title", ""),
                "source": "toutiao",
                "crawl_time": datetime.now().isoformat(),
            })

        logger.info(f"Fetched {len(results)} hot topics from Toutiao")
        return results

    except requests.RequestException as e:
        logger.error(f"Toutiao API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Toutiao parse failed: {e}")
        return []
