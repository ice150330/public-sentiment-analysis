#!/usr/bin/env python3
"""
多平台深度内容采集爬虫 v2.0
整合技术: Aneiang.Pa API设计 + Playwright渲染 + 百度embedded JSON解析
完整链路: 热榜话题 → 文章详情 → 正文 + 评论
支持平台: 微博热搜、抖音热榜、头条热榜、百度热搜、B站视频/评论、知乎热榜
"""

import requests
import pandas as pd
import json
import re
import time
import asyncio
from datetime import datetime
from playwright.async_api import async_playwright


class MultiPlatformSpiderV2:
    """多平台深度内容采集爬虫 v2.0"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        })
        self.results = {
            "hot_topics": [],      # 所有平台热榜
            "articles": [],         # 文章正文
            "comments": [],         # 评论
            "videos": [],           # B站视频
        }

    # ============ 第1层: 热榜话题采集 ============

    def fetch_weibo_hot(self):
        """微博热搜 - 参考Aneiang.Pa配方"""
        print("[热榜] 微博热搜...")
        h = {**self.session.headers, "Referer": "https://weibo.com/hot/search"}
        try:
            resp = self.session.get("https://weibo.com/ajax/side/hotSearch", headers=h, timeout=10)
            d = resp.json()
            if d.get("data") and d["data"].get("realtime"):
                for item in d["data"]["realtime"]:
                    self.results["hot_topics"].append({
                        "platform": "微博", "content_type": "热搜话题",
                        "title": item.get("word", ""),
                        "heat_value": item.get("num", 0),
                        "rank": item.get("realpos", 0),
                        "category": item.get("flag_desc", ""),
                        "label": item.get("label_name", ""),
                        "scheme": item.get("word_scheme", ""),
                        "url": f"https://s.weibo.com/weibo?q={requests.utils.quote(item.get('word_scheme', item.get('word', '')))}",
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                print(f"  ✅ {len(d['data']['realtime'])} 条")
                return True
        except Exception as e:
            print(f"  ❌ {e}")
        return False

    def fetch_douyin_hot(self):
        """抖音热榜 - 参考Aneiang.Pa配方 (需Cookie)"""
        print("[热榜] 抖音热榜...")
        h = {**self.session.headers, "Referer": "https://www.douyin.com"}
        try:
            resp = self.session.get(
                "https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1",
                headers=h, timeout=10
            )
            d = resp.json()
            if d.get("data") and d["data"].get("word_list"):
                for item in d["data"]["word_list"]:
                    self.results["hot_topics"].append({
                        "platform": "抖音", "content_type": "热榜话题",
                        "title": item.get("word", ""),
                        "heat_value": item.get("hot_value", 0),
                        "rank": item.get("position", 0),
                        "video_count": item.get("video_count", 0),
                        "discuss_video_count": item.get("discuss_video_count", 0),
                        "event_time": item.get("event_time", 0),
                        "url": f"https://www.douyin.com/hot/{item.get('sentence_id', '')}",
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                print(f"  ✅ {len(d['data']['word_list'])} 条")
                return True
        except Exception as e:
            print(f"  ❌ {e}")
        return False

    def fetch_toutiao_hot(self):
        """头条热榜"""
        print("[热榜] 头条热榜...")
        h = {**self.session.headers, "Referer": "https://www.toutiao.com"}
        try:
            resp = self.session.get("https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc", headers=h, timeout=10)
            d = resp.json()
            if d.get("data"):
                for item in d["data"]:
                    self.results["hot_topics"].append({
                        "platform": "今日头条", "content_type": "热榜话题",
                        "title": item.get("Title", ""),
                        "heat_value": item.get("HotValue", 0),
                        "article_id": str(item.get("ClusterId", "")),
                        "label": item.get("Label", ""),
                        "label_desc": item.get("LabelDesc", ""),
                        "url": item.get("Url", ""),
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                print(f"  ✅ {len(d['data'])} 条")
                return True
        except Exception as e:
            print(f"  ❌ {e}")
        return False

    def fetch_baidu_hot(self):
        """百度热搜 - 参考Aneiang.Pa embedded JSON解析"""
        print("[热榜] 百度热搜...")
        h = {**self.session.headers, "Referer": "https://top.baidu.com"}
        try:
            resp = self.session.get("https://top.baidu.com/board?tab=realtime", headers=h, timeout=10)
            html = resp.text
            sdata_match = re.search(r'<!--s-data:({.*?})-->', html, re.DOTALL)
            if sdata_match:
                sdata = json.loads(sdata_match.group(1))
                if sdata.get("data") and sdata["data"].get("cards"):
                    for item in sdata["data"]["cards"][0].get("content", []):
                        self.results["hot_topics"].append({
                            "platform": "百度", "content_type": "热搜话题",
                            "title": item.get("word", "").strip(),
                            "heat_value": item.get("hotScore", ""),
                            "rank": item.get("index", 0),
                            "desc": item.get("desc", ""),
                            "url": item.get("rawUrl", ""),
                            "is_top": item.get("isTop", False),
                            "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                    print(f"  ✅ {len(sdata['data']['cards'][0]['content'])} 条")
                    return True
        except Exception as e:
            print(f"  ❌ {e}")
        return False

    def fetch_bilibili_hot(self):
        """B站热搜 - 参考Aneiang.Pa配方"""
        print("[热榜] B站热搜...")
        h = {**self.session.headers, "Referer": "https://s.search.bilibili.com"}
        try:
            resp = self.session.get("https://s.search.bilibili.com/main/hotword?limit=30", headers=h, timeout=10)
            d = resp.json()
            if d.get("list"):
                for item in d["list"]:
                    self.results["hot_topics"].append({
                        "platform": "B站", "content_type": "热搜关键词",
                        "title": item.get("show_name", ""),
                        "keyword": item.get("keyword", ""),
                        "heat_value": item.get("heat_score", 0),
                        "icon": item.get("icon", ""),
                        "url": f"https://search.bilibili.com/all?keyword={requests.utils.quote(item.get('keyword', ''))}",
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                print(f"  ✅ {len(d['list'])} 条")
                return True
        except Exception as e:
            print(f"  ❌ {e}")
        return False

    def fetch_zhihu_hot(self):
        """知乎热榜 - 参考Aneiang.Pa配方 (带摘要)"""
        print("[热榜] 知乎热榜...")
        h = {**self.session.headers, "Referer": "https://www.zhihu.com", "Accept": "application/json"}
        try:
            resp = self.session.get("https://www.zhihu.com/api/v3/feed/topstory/hot-list-web?limit=20&desktop=true", headers=h, timeout=10)
            d = resp.json()
            if d.get("data"):
                for item in d["data"]:
                    target = item.get("target", {})
                    self.results["hot_topics"].append({
                        "platform": "知乎", "content_type": "热榜问答",
                        "title": target.get("title_area", {}).get("text", ""),
                        "excerpt": target.get("excerpt_area", {}).get("text", ""),
                        "heat_value": target.get("metrics_area", {}).get("text", ""),
                        "url": target.get("link", {}).get("url", ""),
                        "image_url": target.get("image_area", {}).get("url", ""),
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                print(f"  ✅ {len(d['data'])} 条")
                return True
        except Exception as e:
            print(f"  ❌ {e}")
        return False

    # ============ 第2层: 文章正文 (Playwright渲染) ============

    async def fetch_toutiao_articles(self, max_articles=10):
        """头条热榜 → 文章详情 → 正文"""
        print("\n[文章] 头条热榜 → 文章正文...")

        # 获取有URL的头条热榜
        toutiao_items = [t for t in self.results["hot_topics"]
                        if t["platform"] == "今日头条" and t.get("url")]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

            for i, item in enumerate(toutiao_items[:max_articles]):
                try:
                    await page.goto(item["url"], wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(2500)

                    # 从页面JS变量提取
                    content = ""
                    initial_state = await page.evaluate("() => window.__INITIAL_STATE__ || null")
                    if initial_state and isinstance(initial_state, dict):
                        for key in ["articleInfo", "article", "content", "detail"]:
                            if key in initial_state and isinstance(initial_state[key], dict):
                                info = initial_state[key]
                                content = info.get("content", info.get("abstract", ""))
                                break

                    # DOM提取回退
                    if not content or len(content) < 50:
                        for sel in ["article", ".article-content", ".content", "main"]:
                            try:
                                el = await page.query_selector(sel)
                                if el:
                                    text = await el.inner_text()
                                    if len(text) > 50:
                                        content = text[:2000]
                                        break
                            except:
                                continue

                    # 清理
                    if content:
                        content = re.sub(r"<[^>]+>", " ", content)
                        content = re.sub(r"\s+", " ", content).strip()[:1500]
                    if not content:
                        content = item["title"]

                    self.results["articles"].append({
                        "platform": "今日头条",
                        "content_type": "文章正文",
                        "topic": item["title"],
                        "article_id": item.get("article_id", ""),
                        "title": item["title"],
                        "content": content,
                        "word_count": len(content),
                        "heat_value": item.get("heat_value", 0),
                        "url": item["url"],
                        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    print(f"  ✓ [{i+1}] {item['title'][:32]}... | {len(content)}字")

                except Exception as e:
                    print(f"  ⚠ [{i+1}] {item['title'][:25]}... | {str(e)[:30]}")

                await page.wait_for_timeout(1000)

            await browser.close()
        print(f"  📊 共 {len(self.results['articles'])} 条头条文章")

    # ============ 第3层: 评论采集 ============

    def fetch_bilibili_comments(self, oid="116870673930307", pages=5):
        """B站视频评论"""
        print(f"\n[评论] B站视频评论...")
        h = {**self.session.headers, "Referer": "https://www.bilibili.com/"}
        count = 0

        for pn in range(1, pages + 1):
            try:
                resp = self.session.get(
                    "https://api.bilibili.com/x/v2/reply",
                    headers=h,
                    params={"type": 1, "oid": oid, "sort": 2, "pn": pn, "ps": 20},
                    timeout=10
                )
                d = resp.json()
                if d.get("data") and d["data"].get("replies"):
                    for r in d["data"]["replies"]:
                        m = r.get("member", {})
                        c = r.get("content", {})
                        ct = r.get("ctime", 0)

                        self.results["comments"].append({
                            "platform": "B站",
                            "content_type": "视频评论",
                            "topic": f"视频_{oid}",
                            "comment_id": str(r.get("rpid", "")),
                            "user_id": str(m.get("mid", "")),
                            "user_name": m.get("uname", ""),
                            "user_sex": m.get("sex", ""),
                            "user_level": m.get("level_info", {}).get("current_level", 0),
                            "is_senior_member": bool(m.get("is_senior_member", 0)),
                            "vip_type": m.get("vip", {}).get("vipType", 0),
                            "official_type": m.get("official_verify", {}).get("type", -1),
                            "comment_content": c.get("message", ""),
                            "comment_time": datetime.fromtimestamp(ct).strftime("%Y-%m-%d %H:%M:%S") if ct else "",
                            "like_count": r.get("like", 0),
                            "reply_count": r.get("rcount", 0),
                            "is_root_reply": r.get("root", 0) == 0,
                        })

                        # 子回复
                        if r.get("replies"):
                            for sub in r["replies"]:
                                sm = sub.get("member", {})
                                sc = sub.get("content", {})
                                sct = sub.get("ctime", 0)
                                self.results["comments"].append({
                                    "platform": "B站",
                                    "content_type": "子回复",
                                    "topic": f"视频_{oid}",
                                    "comment_id": str(sub.get("rpid", "")),
                                    "parent_id": str(r.get("rpid", "")),
                                    "user_name": sm.get("uname", ""),
                                    "comment_content": sc.get("message", ""),
                                    "comment_time": datetime.fromtimestamp(sct).strftime("%Y-%m-%d %H:%M:%S") if sct else "",
                                    "like_count": sub.get("like", 0),
                                    "is_root_reply": False,
                                })
                        count += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠ 第{pn}页: {e}")

        print(f"  ✅ {len(self.results['comments'])} 条评论(含子回复)")

    # ============ B站视频 ============

    def fetch_bilibili_videos(self, pages=3, per_page=20):
        """B站热门视频"""
        print("\n[视频] B站热门视频...")
        h = {**self.session.headers, "Referer": "https://www.bilibili.com"}
        count = 0

        for pn in range(1, pages + 1):
            try:
                resp = self.session.get(
                    "https://api.bilibili.com/x/web-interface/popular",
                    headers=h, params={"pn": pn, "ps": per_page}, timeout=10
                )
                d = resp.json()
                if d.get("data") and d["data"].get("list"):
                    for item in d["data"]["list"]:
                        stat = item.get("stat", {})
                        owner = item.get("owner", {})
                        pub_ts = item.get("pubdate", 0)
                        pub_date = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M:%S") if pub_ts else ""
                        duration = item.get("duration", 0)
                        view = stat.get("view", 0) or 1

                        self.results["videos"].append({
                            "platform": "B站",
                            "content_type": "视频",
                            "video_id": item.get("bvid", ""),
                            "title": item.get("title", ""),
                            "description": item.get("desc", "").replace("\n", " ")[:300],
                            "category_l1": item.get("tname", ""),
                            "category_l2": item.get("tnamev2", ""),
                            "up_name": owner.get("name", ""),
                            "pub_date": pub_date,
                            "duration_seconds": duration,
                            "duration_format": f"{duration//60}:{duration%60:02d}" if duration else "0:00",
                            "view_count": stat.get("view", 0),
                            "danmaku_count": stat.get("danmaku", 0),
                            "reply_count": stat.get("reply", 0),
                            "favorite_count": stat.get("favorite", 0),
                            "coin_count": stat.get("coin", 0),
                            "share_count": stat.get("share", 0),
                            "like_count": stat.get("like", 0),
                            "danmaku_rate": round(stat.get("danmaku", 0) / view * 100, 4),
                            "like_rate": round(stat.get("like", 0) / view * 100, 4),
                            "reply_rate": round(stat.get("reply", 0) / view * 100, 4),
                            "pub_location": item.get("pub_location", ""),
                        })
                        count += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠ 第{pn}页: {e}")

        print(f"  ✅ {count} 条视频")

    # ============ 运行 & 保存 ============

    async def run(self):
        print("=" * 60)
        print("🚀 多平台深度内容采集爬虫 v2.0 启动")
        print("=" * 60)
        print("\n📌 第1层: 热榜话题采集")
        print("-" * 40)

        self.fetch_weibo_hot()
        time.sleep(1)
        self.fetch_douyin_hot()
        time.sleep(1)
        self.fetch_toutiao_hot()
        time.sleep(1)
        self.fetch_baidu_hot()
        time.sleep(1)
        self.fetch_bilibili_hot()
        time.sleep(1)
        self.fetch_zhihu_hot()

        print("\n📌 第2层: 文章正文 (Playwright渲染)")
        print("-" * 40)
        await self.fetch_toutiao_articles(max_articles=10)

        print("\n📌 第3层: 评论采集")
        print("-" * 40)
        self.fetch_bilibili_comments(oid="116870673930307", pages=5)

        print("\n📌 附加: B站热门视频")
        print("-" * 40)
        self.fetch_bilibili_videos(pages=3, per_page=20)

        # 汇总
        print("\n" + "=" * 60)
        print("📊 采集汇总")
        print("=" * 60)
        for name, data in self.results.items():
            print(f"  {name:15s}: {len(data):4d} 条")
        total = sum(len(v) for v in self.results.values())
        print(f"  {'合计':15s}: {total:4d} 条")

    def save_all(self, output_dir="./"):
        print("\n💾 保存数据...")
        saved = []
        for name, data in self.results.items():
            if not data:
                continue
            filepath = f"{output_dir}{name}.csv"
            df = pd.DataFrame(data)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            fields = len(df.columns)
            saved.append((name, filepath, len(df), fields))
            print(f"  {name:15s}: {filepath} ({len(df)}行 × {fields}列)")
        return saved


# ========== 运行入口 ==========
if __name__ == "__main__":
    spider = MultiPlatformSpiderV2()
    asyncio.run(spider.run())
    spider.save_all("./data/")
