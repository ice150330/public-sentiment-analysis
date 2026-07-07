"""
微博热搜爬虫

模块名称: weibo.py
模块职责: 采集微博热搜榜单数据

作者: 码钉
日期: 2026-07-07
版本: 1.0.0
"""

import re
import time
import random
import logging
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 微博热搜页面 URL
WEIBO_HOT_URL = "https://s.weibo.com/top/summary"

# 请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://weibo.com/",
}


def fetch_weibo_hot() -> List[Dict]:
    """
    获取微博热搜数据
    
    Returns:
        List[Dict]: 热搜列表，每条包含:
            - id: 排名
            - title: 话题标题
            - url: 链接
            - heat: 热度值
            - category: 分类标签
            - summary: 内容摘要
    """
    try:
        # 发送请求
        response = requests.get(
            WEIBO_HOT_URL,
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        # 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取热搜列表
        hot_list = []
        
        # 微博热搜页面结构可能会变化，这里提供两种解析方式
        # 方式 1: 新版微博热搜
        tbody = soup.find('tbody')
        if tbody:
            rows = tbody.find_all('tr')
            for row in rows:
                try:
                    # 提取排名
                    rank_td = row.find('td', class_='ranktop')
                    if not rank_td:
                        continue
                    rank = rank_td.text.strip()
                    
                    # 提取标题和链接
                    title_td = row.find('td', class_='td-02')
                    if not title_td:
                        continue
                    a_tag = title_td.find('a')
                    if not a_tag:
                        continue
                    
                    title = a_tag.text.strip()
                    url = "https://s.weibo.com" + a_tag.get('href', '')
                    
                    # 提取热度
                    heat_span = title_td.find('span')
                    heat = heat_span.text.strip() if heat_span else "0"
                    
                    # 提取标签
                    tag_td = row.find('td', class_='td-03')
                    tag = tag_td.text.strip() if tag_td else ""
                    
                    hot_list.append({
                        "id": str(rank),
                        "title": title,
                        "url": url,
                        "heat": heat,
                        "category": tag if tag else "热",
                        "summary": f"微博热搜 #{rank}: {title}",
                        "source": "weibo",
                        "crawl_time": datetime.now().isoformat(),
                    })
                    
                except Exception as e:
                    logger.warning(f"Failed to parse row: {e}")
                    continue
        
        # 方式 2: 如果 tbody 不存在，尝试其他选择器
        if not hot_list:
            # 尝试查找所有包含热搜数据的元素
            items = soup.select('.data tbody tr') or soup.select('table tbody tr')
            for item in items:
                try:
                    tds = item.find_all('td')
                    if len(tds) >= 2:
                        rank = tds[0].text.strip()
                        title_a = tds[1].find('a')
                        if title_a:
                            hot_list.append({
                                "id": str(rank),
                                "title": title_a.text.strip(),
                                "url": title_a.get('href', ''),
                                "heat": tds[1].find('span').text.strip() if tds[1].find('span') else "0",
                                "category": "热",
                                "summary": f"微博热搜: {title_a.text.strip()}",
                                "source": "weibo",
                                "crawl_time": datetime.now().isoformat(),
                            })
                except Exception as e:
                    logger.warning(f"Failed to parse item: {e}")
                    continue
        
        logger.info(f"Fetched {len(hot_list)} hot topics from Weibo")
        return hot_list
        
    except requests.RequestException as e:
        logger.error(f"Network error when fetching Weibo hot: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []


def fetch_weibo_hot_mock() -> List[Dict]:
    """
    模拟微博热搜数据（用于测试）
    
    Returns:
        List[Dict]: 模拟热搜数据
    """
    mock_data = [
        {
            "id": "1",
            "title": "高考加油",
            "url": "https://s.weibo.com/weibo?q=高考加油",
            "heat": "500万",
            "category": "爆",
            "summary": "全国高考首日，各地考生奔赴考场",
            "source": "weibo",
        },
        {
            "id": "2",
            "title": "新电影上映",
            "url": "https://s.weibo.com/weibo?q=新电影上映",
            "heat": "300万",
            "category": "热",
            "summary": "暑期档电影竞争激烈",
            "source": "weibo",
        },
        {
            "id": "3",
            "title": "科技公司发布新品",
            "url": "https://s.weibo.com/weibo?q=科技公司发布新品",
            "heat": "200万",
            "category": "热",
            "summary": "多家科技公司发布新产品",
            "source": "weibo",
        },
        {
            "id": "4",
            "title": "体育赛事结果",
            "url": "https://s.weibo.com/weibo?q=体育赛事结果",
            "heat": "150万",
            "category": "新",
            "summary": "重要体育赛事结果公布",
            "source": "weibo",
        },
        {
            "id": "5",
            "title": "娱乐明星动态",
            "url": "https://s.weibo.com/weibo?q=娱乐明星动态",
            "heat": "120万",
            "category": "热",
            "summary": "明星最新动态",
            "source": "weibo",
        },
    ]
    
    # 添加随机变化
    for item in mock_data:
        item["crawl_time"] = datetime.now().isoformat()
        # 随机调整热度
        base_heat = int(item["heat"].replace("万", ""))
        item["heat"] = f"{base_heat + random.randint(-20, 20)}万"
    
    return mock_data


if __name__ == "__main__":
    # 测试爬虫
    print("Testing Weibo spider...")
    
    # 尝试真实爬取
    print("\nTrying real crawl...")
    real_data = fetch_weibo_hot()
    print(f"Real data: {len(real_data)} items")
    for item in real_data[:3]:
        print(f"  {item['id']}. {item['title']} ({item['heat']})")
    
    # 模拟数据
    print("\nMock data:")
    mock_data = fetch_weibo_hot_mock()
    for item in mock_data[:3]:
        print(f"  {item['id']}. {item['title']} ({item['heat']})")
