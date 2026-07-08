"""
后端 API 测试套件

模块名称: test_api.py
模块职责: 使用 pytest + httpx 测试所有 API 接口

运行方式:
    cd backend
    source venv/bin/activate
    pytest tests/test_api.py -v

作者: 码钉
日期: 2026-07-07
版本: 1.0.0
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import status

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def async_client():
    """创建异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthCheck:
    """健康检查接口测试"""
    
    async def test_health_check(self, async_client):
        """测试健康检查接口"""
        response = await async_client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["status"] == "healthy"
        assert data["message"] == "success"
    
    async def test_root_endpoint(self, async_client):
        """测试根路径接口"""
        response = await async_client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["name"] == "PublicSentimentAnalysis"


class TestPlatformEndpoints:
    """平台管理接口测试"""
    
    async def test_list_platforms(self, async_client):
        """测试查询平台列表"""
        response = await async_client.get("/api/v1/platforms")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 6
        assert data["data"][0]["name"] == "weibo"
    
    async def test_list_platforms_with_filter(self, async_client):
        """测试按状态筛选平台"""
        response = await async_client.get("/api/v1/platforms?is_active=true")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(p["is_active"] for p in data["data"])
    
    async def test_get_platform_detail(self, async_client):
        """测试查询平台详情"""
        response = await async_client.get("/api/v1/platforms/1")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["id"] == 1
        assert data["data"]["name"] == "weibo"
    
    async def test_get_platform_not_found(self, async_client):
        """测试查询不存在的平台"""
        response = await async_client.get("/api/v1/platforms/999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestHotTopicEndpoints:
    """热榜数据接口测试"""
    
    async def test_list_topics(self, async_client):
        """测试查询热榜列表"""
        response = await async_client.get("/api/v1/topics?page=1&page_size=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert "pagination" in data["data"]
    
    async def test_list_topics_with_filter(self, async_client):
        """测试按平台筛选热榜"""
        response = await async_client.get("/api/v1/topics?platform=weibo")
        assert response.status_code == status.HTTP_200_OK
    
    async def test_list_topics_with_keyword(self, async_client):
        """测试按关键词搜索热榜"""
        response = await async_client.get("/api/v1/topics?keyword=测试")
        assert response.status_code == status.HTTP_200_OK


class TestSentimentEndpoints:
    """情感分析接口测试"""
    
    async def test_analyze_single_text(self, async_client):
        """测试单条文本分析"""
        response = await async_client.post(
            "/api/v1/sentiment/analyze",
            json={"text": "这个产品太好用了，非常满意！"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["text"] == "这个产品太好用了，非常满意！"
        assert data["data"]["sentiment_label"] in ["positive", "negative", "neutral"]
        assert 0 <= data["data"]["confidence"] <= 1
    
    async def test_analyze_batch_texts(self, async_client):
        """测试批量文本分析"""
        response = await async_client.post(
            "/api/v1/sentiment/analyze/batch",
            json={"texts": ["很好", "很差", "一般"]}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 3
    
    async def test_analyze_empty_text(self, async_client):
        """测试空文本分析（应返回 400）"""
        response = await async_client.post(
            "/api/v1/sentiment/analyze",
            json={"text": ""}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_list_sentiment_results(self, async_client):
        """测试查询情感分析结果"""
        response = await async_client.get("/api/v1/sentiment/results")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200


class TestStatsEndpoints:
    """统计分析接口测试"""
    
    async def test_get_overview(self, async_client):
        """测试获取数据概览"""
        response = await async_client.get("/api/v1/stats/overview")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "today" in data["data"]
        assert "crawler" in data["data"]
        assert "sentiment" in data["data"]
    
    async def test_get_sentiment_distribution(self, async_client):
        """测试获取情感分布"""
        response = await async_client.get("/api/v1/stats/sentiment-distribution")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "distribution" in data["data"]
    
    async def test_get_heat_trend(self, async_client):
        """测试获取热度趋势"""
        response = await async_client.get("/api/v1/stats/heat-trend?days=7")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "series" in data["data"]
    
    async def test_get_crawl_success_rate(self, async_client):
        """测试获取采集成功率"""
        response = await async_client.get("/api/v1/stats/crawl-success-rate?days=7")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "rates" in data["data"]


class TestCrawlerEndpoints:
    """爬虫控制接口测试"""
    
    async def test_get_crawler_status(self, async_client):
        """测试查询爬虫状态"""
        response = await async_client.get("/api/v1/crawler/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "is_running" in data["data"]
    
    async def test_trigger_crawler_sync(self, async_client):
        """测试同步触发爬虫"""
        response = await async_client.post(
            "/api/v1/crawler/trigger",
            json={"platforms": ["weibo"], "is_async": False}
        )
        # 同步执行返回 200，异步返回 202
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]
        data = response.json()
        assert data["data"]["status"] == "completed"
    
    async def test_trigger_crawler_async(self, async_client):
        """测试异步触发爬虫"""
        response = await async_client.post(
            "/api/v1/crawler/trigger",
            json={"platforms": ["weibo"], "is_async": True}
        )
        assert response.status_code == status.HTTP_202_ACCEPTED
        task_id = response.json()["data"]["task_id"]
        cancel_response = await async_client.post(f"/api/v1/crawler/tasks/{task_id}/cancel")
        assert cancel_response.status_code == status.HTTP_200_OK
    
    async def test_list_crawl_logs(self, async_client):
        """测试查询采集日志"""
        response = await async_client.get("/api/v1/crawler/logs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200


class TestErrorHandling:
    """错误处理测试"""
    
    async def test_not_found_endpoint(self, async_client):
        """测试不存在的端点"""
        response = await async_client.get("/api/v1/not-exist")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_invalid_json(self, async_client):
        """测试无效 JSON 请求"""
        response = await async_client.post(
            "/api/v1/sentiment/analyze",
            content="not-json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    async def test_request_id_header(self, async_client):
        """测试请求 ID 响应头"""
        response = await async_client.get("/health")
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers


class TestCORS:
    """CORS 跨域测试"""
    
    async def test_cors_headers(self, async_client):
        """测试 CORS 响应头"""
        response = await async_client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in response.headers
