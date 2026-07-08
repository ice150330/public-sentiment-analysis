#!/usr/bin/env python3
"""
百度热搜爬虫

模块名称: baidu.py
模块职责: 采集百度热搜数据

特性:
- 解析 embedded JSON 数据
- 无需额外 API 调用
"""

import json
import logging
import re
from datetime import datetime
from typing import List, Dict

import requests

from crawler.http_client import get as crawler_get

logger = logging.getLogger(__name__)

BAIDU_HOT_URL = "https://top.baidu.com/board?tab=realtime"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://top.baidu.com",
}


def fetch_baidu_hot() -> List[Dict]:
    """
    获取百度热搜列表

    Returns:
        List[Dict]: 热搜数据列表
    """
    try:
        resp = crawler_get(BAIDU_HOT_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        html = resp.text

        # 解析 embedded JSON
        sdata_match = re.search(r'<!--s-data:({.*?})-->', html, re.DOTALL)
        if not sdata_match:
            logger.warning("Baidu embedded JSON not found")
            return []

        sdata = json.loads(sdata_match.group(1))
        if not sdata.get("data") or not sdata["data"].get("cards"):
            logger.warning("Baidu data structure unexpected")
            return []

        results = []
        for item in sdata["data"]["cards"][0].get("content", []):
            word = item.get("word", "").strip()
            results.append({
                "id": word or str(item.get("index", 0)),
                "title": word,
                "url": item.get("rawUrl", ""),
                "heat": str(item.get("hotScore", "")),
                "category": "热" if item.get("isTop") else "新",
                "summary": item.get("desc", ""),
                "source": "baidu",
                "crawl_time": datetime.now().isoformat(),
            })

        logger.info(f"Fetched {len(results)} hot topics from Baidu")
        return results

    except requests.RequestException as e:
        logger.error(f"Baidu request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Baidu JSON decode failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Baidu parse failed: {e}")
        return []
