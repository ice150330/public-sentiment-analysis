#!/usr/bin/env python3
"""
B站热搜爬虫

模块名称: bilibili.py
模块职责: 采集 Bilibili 热搜和热门视频数据
"""

import logging
from datetime import datetime
from typing import List, Dict

import requests

logger = logging.getLogger(__name__)

BILIBILI_HOT_API = "https://s.search.bilibili.com/main/hotword?limit=30"
BILIBILI_POPULAR_API = "https://api.bilibili.com/x/web-interface/popular"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://search.bilibili.com",
}


def fetch_bilibili_hot() -> List[Dict]:
    """
    获取 B 站热搜列表

    Returns:
        List[Dict]: 热搜数据列表
    """
    try:
        resp = requests.get(BILIBILI_HOT_API, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("list"):
            logger.warning("Bilibili API returned empty data")
            return []

        results = []
        for item in data["list"]:
            results.append({
                "id": str(item.get("keyword", "")),
                "title": item.get("show_name", ""),
                "url": (
                    f"https://search.bilibili.com/all?"
                    f"keyword={requests.utils.quote(item.get('keyword', ''))}"
                ),
                "heat": str(item.get("heat_score", 0)),
                "category": "热",
                "summary": item.get("show_name", ""),
                "source": "bilibili",
                "crawl_time": datetime.now().isoformat(),
            })

        logger.info(f"Fetched {len(results)} hot topics from Bilibili")
        return results

    except requests.RequestException as e:
        logger.error(f"Bilibili API request failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Bilibili parse failed: {e}")
        return []


def fetch_bilibili_videos(pages: int = 3, per_page: int = 20) -> List[Dict]:
    """
    获取 B 站热门视频

    Args:
        pages: 页数
        per_page: 每页数量

    Returns:
        List[Dict]: 视频数据列表
    """
    results = []
    for pn in range(1, pages + 1):
        try:
            resp = requests.get(
                BILIBILI_POPULAR_API,
                headers=HEADERS,
                params={"pn": pn, "ps": per_page},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if not data.get("data") or not data["data"].get("list"):
                continue

            for item in data["data"]["list"]:
                stat = item.get("stat", {})
                owner = item.get("owner", {})
                pub_ts = item.get("pubdate", 0)
                pub_date = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M:%S") if pub_ts else ""
                duration = item.get("duration", 0)
                view = stat.get("view", 0) or 1

                results.append({
                    "id": item.get("bvid", ""),
                    "title": item.get("title", ""),
                    "url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    "heat": str(view),
                    "category": item.get("tname", "视频"),
                    "summary": item.get("desc", "").replace("\n", " ")[:300],
                    "source": "bilibili",
                    "crawl_time": datetime.now().isoformat(),
                    "extra": {
                        "up_name": owner.get("name", ""),
                        "pub_date": pub_date,
                        "duration_seconds": duration,
                        "view_count": stat.get("view", 0),
                        "danmaku_count": stat.get("danmaku", 0),
                        "reply_count": stat.get("reply", 0),
                        "like_count": stat.get("like", 0),
                        "coin_count": stat.get("coin", 0),
                    },
                })

        except requests.RequestException as e:
            logger.error(f"Bilibili video page {pn} request failed: {e}")
        except Exception as e:
            logger.error(f"Bilibili video parse failed: {e}")

    logger.info(f"Fetched {len(results)} popular videos from Bilibili")
    return results
