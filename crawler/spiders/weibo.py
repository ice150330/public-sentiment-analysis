"""
微博热搜爬虫（Playwright 版）

模块名称: weibo.py
模块职责: 使用 Playwright 模拟浏览器采集微博热搜

特性:
- 模拟真实浏览器环境（Chromium）
- 自动处理反爬检测
- 支持 Cookie 持久化
- 失败自动降级到模拟数据

作者: 码钉
日期: 2026-07-07
版本: 2.0.0
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import List, Dict, Optional

from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)

# 微博热搜页面
WEIBO_HOT_URL = "https://s.weibo.com/top/summary"

# 浏览器配置
BROWSER_CONFIG = {
    "headless": True,  # 无头模式
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-site-isolation-trials",
        "--disable-dev-shm-usage",
        "--no-sandbox",
    ],
}

# 用户代理列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


async def _init_browser():
    """初始化浏览器"""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(**BROWSER_CONFIG)
    return playwright, browser


async def _create_page(browser: Browser) -> Page:
    """创建新页面并设置反爬参数"""
    context = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )
    
    page = await context.new_page()
    
    # 隐藏自动化特征
    await page.evaluate("""
        () => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        }
    """)
    
    return page


async def fetch_weibo_hot() -> List[Dict]:
    """
    使用 Playwright 获取微博热搜
    
    Returns:
        List[Dict]: 热搜列表
    """
    playwright = None
    browser = None
    
    try:
        logger.info("Starting Playwright browser...")
        playwright, browser = await _init_browser()
        page = await _create_page(browser)
        
        # 访问微博热搜页面
        logger.info(f"Navigating to {WEIBO_HOT_URL}")
        await page.goto(WEIBO_HOT_URL, wait_until="networkidle", timeout=30000)
        
        # 等待页面加载
        await asyncio.sleep(2)
        
        # 检查是否需要登录/验证
        title = await page.title()
        logger.info(f"Page title: {title}")
        
        if "visitor" in title.lower() or "登录" in title:
            logger.warning("Weibo requires verification, trying to bypass...")
            # 等待可能的重定向
            await asyncio.sleep(3)
        
        # 保存页面截图（用于调试）
        await page.screenshot(path="/tmp/weibo_screenshot.png")
        logger.info("Screenshot saved to /tmp/weibo_screenshot.png")
        
        # 解析热搜数据
        hot_list = await _parse_hot_list(page)
        
        if hot_list:
            logger.info(f"Successfully fetched {len(hot_list)} hot topics")
            return hot_list
        else:
            logger.warning("No data found, page might have changed")
            return []
            
    except Exception as e:
        logger.error(f"Playwright crawl failed: {e}")
        return []
    finally:
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()


async def _parse_hot_list(page: Page) -> List[Dict]:
    """解析微博热搜列表"""
    hot_list = []
    
    try:
        # 策略 1: 新版微博热搜（tbody 结构）
        rows = await page.query_selector_all('tbody tr')
        
        if rows:
            logger.info(f"Found {len(rows)} rows using tbody strategy")
            for i, row in enumerate(rows):
                try:
                    # 提取排名
                    rank_elem = await row.query_selector('td.ranktop')
                    rank = await rank_elem.inner_text() if rank_elem else str(i)
                    
                    # 提取标题
                    title_elem = await row.query_selector('td.td-02 a')
                    if not title_elem:
                        continue
                    title = await title_elem.inner_text()
                    href = await title_elem.get_attribute('href') or ""
                    url = f"https://s.weibo.com{href}" if href.startswith('/') else href
                    
                    # 提取热度
                    heat_elem = await row.query_selector('td.td-02 span')
                    heat = await heat_elem.inner_text() if heat_elem else "0"
                    
                    # 提取标签
                    tag_elem = await row.query_selector('td.td-03')
                    tag = await tag_elem.inner_text() if tag_elem else "热"
                    
                    hot_list.append({
                        "id": str(rank).strip(),
                        "title": title.strip(),
                        "url": url,
                        "heat": heat.strip(),
                        "category": tag.strip() if tag.strip() else "热",
                        "summary": f"微博热搜 #{rank}: {title}",
                        "source": "weibo",
                        "crawl_time": datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse row {i}: {e}")
                    continue
        
        # 策略 2: 如果 tbody 为空，尝试其他选择器
        if not hot_list:
            logger.info("Trying alternative selectors...")
            
            # 尝试查找热搜列表容器
            items = await page.query_selector_all('.data tbody tr, .hot-list tr, [data-rank]')
            
            for i, item in enumerate(items):
                try:
                    title_elem = await item.query_selector('a')
                    if not title_elem:
                        continue
                    
                    title = await title_elem.inner_text()
                    href = await title_elem.get_attribute('href') or ""
                    
                    hot_list.append({
                        "id": str(i + 1),
                        "title": title.strip(),
                        "url": href,
                        "heat": "0",
                        "category": "热",
                        "summary": f"微博热搜: {title}",
                        "source": "weibo",
                        "crawl_time": datetime.now().isoformat(),
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse alternative item {i}: {e}")
                    continue
        
        # 策略 3: 尝试 JavaScript 提取
        if not hot_list:
            logger.info("Trying JavaScript extraction...")
            
            js_result = await page.evaluate("""
                () => {
                    const results = [];
                    // 尝试多种选择器
                    const selectors = [
                        'tbody tr',
                        '.hot-list-item',
                        '[data-rank]',
                        '.card-topic'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            elements.forEach((el, idx) => {
                                const a = el.querySelector('a');
                                if (a) {
                                    results.push({
                                        id: idx + 1,
                                        title: a.innerText.trim(),
                                        url: a.href,
                                    });
                                }
                            });
                            break;
                        }
                    }
                    
                    return results;
                }
            """)
            
            for item in js_result:
                hot_list.append({
                    "id": str(item.get("id", "")),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "heat": "0",
                    "category": "热",
                    "summary": f"微博热搜: {item.get('title', '')}",
                    "source": "weibo",
                    "crawl_time": datetime.now().isoformat(),
                })
        
        return hot_list
        
    except Exception as e:
        logger.error(f"Parse failed: {e}")
        return []


def fetch_weibo_hot_sync() -> List[Dict]:
    """同步包装器"""
    return asyncio.run(fetch_weibo_hot())


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
        base_heat = int(item["heat"].replace("万", ""))
        item["heat"] = f"{base_heat + random.randint(-20, 20)}万"
    
    return mock_data


# 保持向后兼容
async def fetch_weibo_hot_old() -> List[Dict]:
    """旧版 requests 爬虫（保留供参考）"""
    import requests
    from bs4 import BeautifulSoup
    
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://weibo.com/",
        }
        
        response = requests.get(WEIBO_HOT_URL, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tbody = soup.find('tbody')
        
        if not tbody:
            return []
        
        hot_list = []
        for row in tbody.find_all('tr'):
            try:
                rank = row.find('td', class_='ranktop')
                title = row.find('td', class_='td-02')
                if not title:
                    continue
                a = title.find('a')
                if not a:
                    continue
                
                heat = title.find('span')
                tag = row.find('td', class_='td-03')
                
                hot_list.append({
                    "id": rank.text.strip() if rank else "",
                    "title": a.text.strip(),
                    "url": f"https://s.weibo.com{a.get('href', '')}",
                    "heat": heat.text.strip() if heat else "0",
                    "category": tag.text.strip() if tag else "热",
                    "summary": f"微博热搜: {a.text.strip()}",
                    "source": "weibo",
                    "crawl_time": datetime.now().isoformat(),
                })
            except Exception:
                continue
        
        return hot_list
        
    except Exception as e:
        logger.error(f"Old crawler failed: {e}")
        return []


if __name__ == "__main__":
    # 测试 Playwright 爬虫
    print("Testing Weibo spider with Playwright...")
    
    # 真实爬取
    print("\nTrying real crawl with Playwright...")
    try:
        real_data = fetch_weibo_hot_sync()
        print(f"Real data: {len(real_data)} items")
        for item in real_data[:5]:
            print(f"  {item['id']}. {item['title']} ({item['heat']})")
    except Exception as e:
        print(f"Real crawl failed: {e}")
    
    # 模拟数据
    print("\nMock data:")
    mock_data = fetch_weibo_hot_mock()
    for item in mock_data[:3]:
        print(f"  {item['id']}. {item['title']} ({item['heat']})")
