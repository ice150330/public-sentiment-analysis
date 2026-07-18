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

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from fastapi import status

import app.main as main_module
from app.core.database import SessionLocal
from app.main import app
from app.models import HotTopic, Platform, SentimentResult
from app.services.sqlite_backup_service import resolve_backup_dir
from auth_test_utils import TEST_PASSWORD, ensure_test_user, make_auth_headers

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def async_client():
    """创建异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers.update(make_auth_headers())
        yield client


@pytest_asyncio.fixture
async def unauthenticated_client():
    """创建未认证异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def create_low_confidence_result(tag: str = "review") -> int:
    """Create a deterministic low-confidence sentiment result for review tests."""
    db = SessionLocal()
    try:
        platform = db.query(Platform).filter(Platform.name == "weibo").first()
        if not platform:
            platform = Platform(name="weibo", display_name="微博", sort_order=1, is_active=True)
            db.add(platform)
            db.flush()

        now = datetime.now()
        topic = HotTopic(
            platform_id=platform.id,
            topic_id=f"{tag}-{int(now.timestamp() * 1000)}",
            title=f"低置信复核测试 {tag}",
            heat_score=123,
            category="测试",
            crawl_time=now,
            crawl_date=date.today(),
        )
        db.add(topic)
        db.flush()

        result = SentimentResult(
            topic_id=topic.id,
            sentiment_label="neutral",
            confidence=0.23,
            positive_score=0.31,
            negative_score=0.29,
            neutral_score=0.40,
            model_version="pytest-low-confidence",
        )
        db.add(result)
        db.commit()
        return result.id
    finally:
        db.close()


def create_cluster_topics(tag: str = "cluster") -> list[int]:
    """Create deterministic recent topics for clustering tests."""
    db = SessionLocal()
    try:
        platform = db.query(Platform).filter(Platform.name == "weibo").first()
        if not platform:
            platform = Platform(name="weibo", display_name="微博", sort_order=1, is_active=True)
            db.add(platform)
            db.flush()

        now = datetime.now()
        titles = [
            ("新能源汽车 销量 增长 政策 支持", "positive"),
            ("新能源汽车 充电 桩 建设 提速", "positive"),
            ("新能源汽车 补贴 讨论 市场", "neutral"),
            ("演唱会 门票 争议 黄牛 加价", "negative"),
            ("演唱会 场馆 服务 改善", "positive"),
            ("演唱会 出行 交通 拥堵", "negative"),
        ]
        topic_ids = []
        for index, (title, label) in enumerate(titles):
            topic = HotTopic(
                platform_id=platform.id,
                topic_id=f"{tag}-{int(now.timestamp() * 1000)}-{index}",
                title=title,
                heat_score=900_000_000 - index * 10_000,
                category="聚类测试",
                content_summary=f"{title} 相关舆情样本",
                crawl_time=now,
                crawl_date=date.today(),
            )
            db.add(topic)
            db.flush()
            score = 0.82 if label == "positive" else 0.18 if label == "negative" else 0.50
            db.add(SentimentResult(
                topic_id=topic.id,
                sentiment_label=label,
                confidence=0.86,
                positive_score=score,
                negative_score=1 - score if label != "neutral" else 0.25,
                neutral_score=0.50 if label == "neutral" else 0.08,
                model_version="pytest-cluster",
            ))
            topic_ids.append(topic.id)
        db.commit()
        return topic_ids
    finally:
        db.close()


def create_propagation_topics(tag: str = "propagation") -> int:
    """Create cross-platform similar topics for propagation tests."""
    db = SessionLocal()
    try:
        platforms = {}
        for name, display_name, sort_order in [
            ("weibo", "微博", 1),
            ("douyin", "抖音", 2),
            ("bilibili", "B站", 3),
        ]:
            platform = db.query(Platform).filter(Platform.name == name).first()
            if not platform:
                platform = Platform(name=name, display_name=display_name, sort_order=sort_order, is_active=True)
                db.add(platform)
                db.flush()
            platforms[name] = platform

        now = datetime.now()
        topics = [
            ("weibo", "暴雨 城市 内涝 救援 交通", "negative", now),
            ("douyin", "城市 暴雨 内涝 救援 现场", "negative", now + timedelta(hours=1)),
            ("bilibili", "暴雨 内涝 交通 恢复 救援", "neutral", now + timedelta(hours=3)),
            ("weibo", "苹果 手机 新品 发布 价格", "neutral", now + timedelta(hours=2)),
        ]
        root_id = None
        for index, (platform_name, title, label, crawl_time) in enumerate(topics):
            topic = HotTopic(
                platform_id=platforms[platform_name].id,
                topic_id=f"{tag}-{int(now.timestamp() * 1000)}-{index}",
                title=title,
                heat_score=800_000 - index * 50_000,
                category="传播测试",
                content_summary=f"{title} 跨平台传播样本",
                crawl_time=crawl_time,
                crawl_date=date.today(),
            )
            db.add(topic)
            db.flush()
            db.add(SentimentResult(
                topic_id=topic.id,
                sentiment_label=label,
                confidence=0.88,
                positive_score=0.12 if label == "negative" else 0.4,
                negative_score=0.76 if label == "negative" else 0.2,
                neutral_score=0.12 if label == "negative" else 0.4,
                model_version="pytest-propagation",
            ))
            if index == 0:
                root_id = topic.id
        db.commit()
        return root_id
    finally:
        db.close()


def create_forecast_topics(tag: str = "forecast") -> int:
    """Create a multi-day topic series for trend forecasting tests."""
    db = SessionLocal()
    try:
        platform = db.query(Platform).filter(Platform.name == "weibo").first()
        if not platform:
            platform = Platform(name="weibo", display_name="微博", sort_order=1, is_active=True)
            db.add(platform)
            db.flush()

        now = datetime.now()
        base_day = date.today() - timedelta(days=9)
        platform_topic_id = f"{tag}-{int(now.timestamp() * 1000)}"
        target_id = None
        for index in range(10):
            crawl_day = base_day + timedelta(days=index)
            heat = 100_000 + index * 18_000 + (index % 3) * 3_000
            topic = HotTopic(
                platform_id=platform.id,
                topic_id=platform_topic_id,
                title=f"趋势预测测试 {tag}",
                heat_score=heat,
                category="预测测试",
                content_summary="趋势预测 多日 热度 情感 样本",
                crawl_time=datetime.combine(crawl_day, datetime.min.time()) + timedelta(hours=9),
                crawl_date=crawl_day,
            )
            db.add(topic)
            db.flush()
            target_id = topic.id
            db.add(SentimentResult(
                topic_id=topic.id,
                sentiment_label="negative" if index >= 7 else "neutral",
                confidence=0.72,
                positive_score=max(0.1, 0.45 - index * 0.015),
                negative_score=min(0.75, 0.2 + index * 0.035),
                neutral_score=0.25,
                model_version="pytest-forecast",
                analyzed_at=topic.crawl_time,
            ))
        db.commit()
        assert target_id is not None
        return target_id
    finally:
        db.close()


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


class TestAuthEndpoints:
    """认证接口测试"""

    async def test_protected_api_requires_token(self, unauthenticated_client):
        """测试数据接口默认需要登录"""
        response = await unauthenticated_client.get("/api/v1/topics")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_and_current_user(self, unauthenticated_client):
        """测试登录和当前用户接口"""
        ensure_test_user("login_case", role="analyst")
        response = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "login_case", "password": TEST_PASSWORD},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "analyst"

        me_response = await unauthenticated_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["data"]["username"] == "login_case"

    async def test_password_reset_flow(self, unauthenticated_client):
        """测试密码重置令牌流程"""
        ensure_test_user("reset_case", role="analyst")
        request_response = await unauthenticated_client.post(
            "/api/v1/auth/password/reset/request",
            json={"username": "reset_case"},
        )
        assert request_response.status_code == status.HTTP_200_OK
        reset_token = request_response.json()["data"]["reset_token"]
        assert reset_token

        confirm_response = await unauthenticated_client.post(
            "/api/v1/auth/password/reset/confirm",
            json={"token": reset_token, "new_password": "ChangedPass123!"},
        )
        assert confirm_response.status_code == status.HTTP_200_OK

        login_response = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "reset_case", "password": "ChangedPass123!"},
        )
        assert login_response.status_code == status.HTTP_200_OK

    async def test_current_user_audit_logs(self, unauthenticated_client):
        """测试当前用户可查看自己的审计记录"""
        ensure_test_user("audit_case", role="analyst")
        login_response = await unauthenticated_client.post(
            "/api/v1/auth/login",
            json={"username": "audit_case", "password": TEST_PASSWORD},
        )
        token = login_response.json()["data"]["access_token"]
        audit_response = await unauthenticated_client.get(
            "/api/v1/auth/audit-logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert audit_response.status_code == status.HTTP_200_OK
        items = audit_response.json()["data"]["items"]
        assert items
        assert all(item["operator"] == "audit_case" for item in items)

    async def test_admin_can_manage_users_and_audit_is_recorded(self, async_client):
        """测试管理员用户管理与审计落库"""
        managed = ensure_test_user("managed_case", role="visitor", platform_scope="weibo")
        response = await async_client.get("/api/v1/auth/users")
        assert response.status_code == status.HTTP_200_OK
        assert any(item["username"] == "managed_case" for item in response.json()["data"]["items"])

        update_response = await async_client.patch(
            f"/api/v1/auth/users/{managed.id}",
            json={"role": "analyst", "platform_scope": "weibo,douyin", "is_active": True},
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()["data"]
        assert updated["role"] == "analyst"
        assert updated["platform_scope"] == "weibo,douyin"

        audit_response = await async_client.get("/api/v1/system/audit-logs?action=update_user&page_size=5")
        assert audit_response.status_code == status.HTTP_200_OK
        assert any(str(item["target_id"]) == str(managed.id) for item in audit_response.json()["data"]["items"])

    async def test_analyst_cannot_manage_users(self):
        """测试分析师不能管理用户"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test", headers=make_auth_headers("analyst_case", "analyst")) as client:
            response = await client.get("/api/v1/auth/users")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_api_rate_limit(self, unauthenticated_client):
        """测试基础限流"""
        old_limit = main_module.RATE_LIMIT_PER_MINUTE
        main_module.RATE_LIMIT_PER_MINUTE = 2
        main_module._RATE_LIMIT_BUCKETS.clear()
        try:
            first = await unauthenticated_client.get("/api/v1/auth/me")
            second = await unauthenticated_client.get("/api/v1/auth/me")
            third = await unauthenticated_client.get("/api/v1/auth/me")
            assert first.status_code == status.HTTP_401_UNAUTHORIZED
            assert second.status_code == status.HTTP_401_UNAUTHORIZED
            assert third.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert third.headers["X-RateLimit-Remaining"] == "0"
        finally:
            main_module.RATE_LIMIT_PER_MINUTE = old_limit
            main_module._RATE_LIMIT_BUCKETS.clear()


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

    async def test_list_topics_rejects_sort_injection_shape(self, async_client):
        """测试异常排序参数不会触发动态 SQL 或 500"""
        response = await async_client.get(
            "/api/v1/topics?sort_by=__table__&sort_order=desc%3BDROP%20TABLE%20hot_topics&page_size=5"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]


class TestTopicClusterEndpoints:
    """主题聚类接口测试"""

    async def test_run_clustering_persists_keywords_and_members(self, async_client):
        """测试真实聚类运行、关键词提取和成员持久化"""
        fixture_topic_ids = set(create_cluster_topics("kmeans"))
        response = await async_client.post(
            "/api/v1/topic-clusters/run",
            params={"algorithm": "kmeans", "n_clusters": 2, "time_window_hours": 24},
        )
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["code"] == 200
        data = payload["data"]
        assert data["algorithm"] == "kmeans"
        assert data["embedding_provider"] in {"tfidf", "sentence-transformers"}
        assert data["clusters"]
        assert any(item["keywords"] for item in data["clusters"])

        list_response = await async_client.get("/api/v1/topic-clusters?algorithm=kmeans&page_size=10")
        assert list_response.status_code == status.HTTP_200_OK
        clusters = list_response.json()["data"]["items"]
        cluster = next(item for item in clusters if item["id"] == data["clusters"][0]["id"])
        assert cluster["keywords"]
        assert cluster["embedding_provider"] in {"tfidf", "sentence-transformers"}

        matched_detail = None
        for created in data["clusters"]:
            detail_response = await async_client.get(f"/api/v1/topic-clusters/{created['id']}?page_size=100")
            assert detail_response.status_code == status.HTTP_200_OK
            detail = detail_response.json()["data"]
            if any(member["topic_id"] in fixture_topic_ids for member in detail["members"]):
                matched_detail = detail
                break
            for page_number in range(2, detail["pagination"]["total_pages"] + 1):
                page_response = await async_client.get(
                    f"/api/v1/topic-clusters/{created['id']}?page={page_number}&page_size=100"
                )
                assert page_response.status_code == status.HTTP_200_OK
                page_detail = page_response.json()["data"]
                if any(member["topic_id"] in fixture_topic_ids for member in page_detail["members"]):
                    matched_detail = page_detail
                    break
            if matched_detail is not None:
                break

        assert matched_detail is not None
        assert matched_detail["cluster"]["keywords"]
        assert matched_detail["members"]
        assert isinstance(matched_detail["members"][0]["features"], dict)

    async def test_run_clustering_rejects_unknown_algorithm(self, async_client):
        """测试未知聚类算法返回 400"""
        response = await async_client.post(
            "/api/v1/topic-clusters/run",
            params={"algorithm": "unsupported", "n_clusters": 2, "time_window_hours": 24},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPropagationPathEndpoints:
    """传播路径分析接口测试"""

    async def test_analyze_propagation_uses_similarity_and_persists_features(self, async_client):
        """测试跨平台相似话题传播路径和节点特征持久化"""
        root_topic_id = create_propagation_topics("similarity")
        response = await async_client.post(
            f"/api/v1/propagation-paths/analyze/{root_topic_id}",
            params={"time_window_hours": 24, "similarity_threshold": 0.12, "max_nodes": 10},
        )
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert payload["code"] == 200
        data = payload["data"]
        assert data["path_id"]
        assert data["total_nodes"] >= 3
        assert data["platform_transitions"] >= 1
        assert isinstance(data["platforms_involved"], list)
        assert data["edges"]
        assert any((node.get("similarity_score") or 0) >= 0.12 for node in data["nodes"] if node["topic_id"] != root_topic_id)
        assert not any("苹果 手机" in (node.get("topic_title") or "") for node in data["nodes"])

        detail_response = await async_client.get(f"/api/v1/propagation-paths/{data['path_id']}")
        assert detail_response.status_code == status.HTTP_200_OK
        detail = detail_response.json()["data"]
        assert detail["path"]["root_topic_id"] == root_topic_id
        assert detail["tree"]
        assert detail["nodes"][0]["match_method"] in {"tfidf", "sentence-transformers"}

        list_response = await async_client.get(f"/api/v1/propagation-paths?root_topic_id={root_topic_id}")
        assert list_response.status_code == status.HTTP_200_OK
        items = list_response.json()["data"]["items"]
        assert items
        assert isinstance(items[0]["platforms_involved"], list)

    async def test_analyze_propagation_missing_topic_returns_404(self, async_client):
        """测试不存在话题返回 404"""
        response = await async_client.post("/api/v1/propagation-paths/analyze/99999999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTrendForecastEndpoints:
    """趋势预测接口测试"""

    async def test_create_heat_prediction_persists_forecast_metrics_and_features(self, async_client):
        """测试热度预测生成 ARIMA/EMA 结果、回测指标和特征贡献"""
        target_id = create_forecast_topics("heat")
        response = await async_client.post(
            "/api/v1/trend-predictions/predict",
            params={
                "target_type": "heat",
                "target_id": target_id,
                "model_type": "arima",
                "horizon_hours": 72,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["prediction_id"]
        assert data["model"] in {"arima", "ema"}
        assert len(data["forecast"]) == 3
        assert data["metrics"]["backtest_points"] > 0
        assert data["features"]
        assert data["confidence_upper"] >= data["confidence_lower"]

        detail_response = await async_client.get(f"/api/v1/trend-predictions/{data['prediction_id']}")
        assert detail_response.status_code == status.HTTP_200_OK
        detail = detail_response.json()["data"]
        assert detail["forecast"]
        assert detail["history"]
        assert len(detail["features"]) >= 3

        list_response = await async_client.get("/api/v1/trend-predictions?target_type=heat&page_size=5")
        assert list_response.status_code == status.HTTP_200_OK
        assert any(item["id"] == data["prediction_id"] for item in list_response.json()["data"]["items"])

    async def test_forecast_heat_compat_uses_trend_service(self, async_client):
        """测试前端兼容预测接口返回模型、置信区间和信号"""
        target_id = create_forecast_topics("compat")
        response = await async_client.post(
            "/api/v1/forecast/heat",
            json={"topic_id": target_id, "horizon_days": 3},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert data["model"] in {"arima", "ema", "baseline"}
        assert len(data["forecast"]) == 3
        assert data["forecast"][0]["confidence_upper"] >= data["forecast"][0]["confidence_lower"]
        assert data["signals"]
        assert any(item["name"] == "heat_momentum" for item in data["signals"])


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


class TestModelReviewEndpoints:
    """模型低置信人工复核接口测试"""

    async def test_review_queue_materializes_and_updates_item(self, async_client):
        """测试低置信结果入队并完成人工复核"""
        result_id = create_low_confidence_result("queue")

        queue_response = await async_client.get(
            f"/api/v1/model/review-queue?threshold=0.6&status=pending&sentiment_result_id={result_id}"
        )
        assert queue_response.status_code == status.HTTP_200_OK
        queue_items = queue_response.json()["data"]["items"]
        review_item = next(item for item in queue_items if item["sentiment_result_id"] == result_id)
        assert review_item["status"] == "pending"
        assert review_item["confidence_snapshot"] < 0.6

        update_response = await async_client.patch(
            f"/api/v1/model/review-queue/{review_item['id']}",
            json={
                "status": "reviewed",
                "corrected_label": "negative",
                "note": "人工复核确认负面",
            },
        )
        assert update_response.status_code == status.HTTP_200_OK
        updated = update_response.json()["data"]
        assert updated["status"] == "reviewed"
        assert updated["corrected_label"] == "negative"
        assert updated["reviewer"] == "pytest_admin"
        assert updated["reviewed_at"]

        audit_response = await async_client.get(
            "/api/v1/system/audit-logs?action=review_sentiment_result&page_size=10"
        )
        assert audit_response.status_code == status.HTTP_200_OK
        assert any(
            str(item["target_id"]) == str(review_item["id"])
            for item in audit_response.json()["data"]["items"]
        )

    async def test_low_confidence_results_include_review_state(self, async_client):
        """测试旧低置信列表兼容返回复核状态"""
        result_id = create_low_confidence_result("low-confidence")

        response = await async_client.get("/api/v1/model/low-confidence?threshold=0.6&page_size=100")
        assert response.status_code == status.HTTP_200_OK
        item = next(row for row in response.json()["data"]["items"] if row["id"] == result_id)
        assert item["review_id"]
        assert item["review_status"] == "pending"


class TestModelVersionEndpoints:
    """模型版本管理接口测试"""

    async def test_model_versions_are_seeded_and_activation_routes_analyze(self, async_client):
        """测试默认版本种子、激活和情感入口跟随当前版本"""
        classic_id = None
        response = await async_client.get("/api/v1/model/versions")
        assert response.status_code == status.HTTP_200_OK
        versions = response.json()["data"]["items"]
        classic = next(item for item in versions if item["version"] == "classic-v1")
        enhanced = next(item for item in versions if item["version"] == "transformers-v2")
        classic_id = classic["id"]

        try:
            activate_response = await async_client.post(
                f"/api/v1/model/versions/{enhanced['id']}/activate",
                json={"traffic_percent": 100},
            )
            assert activate_response.status_code == status.HTTP_200_OK
            activated = activate_response.json()["data"]
            assert activated["version"] == "transformers-v2"
            assert activated["traffic_percent"] == 100
            assert activated["is_active"] is True

            analyze_response = await async_client.post(
                "/api/v1/sentiment/analyze",
                json={"text": "这个服务非常满意，体验很棒"},
            )
            assert analyze_response.status_code == status.HTTP_200_OK
            assert analyze_response.json()["data"]["model_version"] == "transformers-v2"

            status_response = await async_client.get("/api/v1/model/status")
            assert status_response.status_code == status.HTTP_200_OK
            active_versions = status_response.json()["data"]["active_versions"]
            assert any(item["version"] == "transformers-v2" for item in active_versions)

            audit_response = await async_client.get(
                "/api/v1/system/audit-logs?action=activate_model_version&page_size=10"
            )
            assert audit_response.status_code == status.HTTP_200_OK
            assert any(
                str(item["target_id"]) == str(enhanced["id"])
                for item in audit_response.json()["data"]["items"]
            )
        finally:
            if classic_id is not None:
                await async_client.post(
                    f"/api/v1/model/versions/{classic_id}/activate",
                    json={"traffic_percent": 100},
                )

    async def test_analyst_cannot_activate_model_version(self, async_client):
        """测试非管理员不能切换模型版本"""
        versions_response = await async_client.get("/api/v1/model/versions")
        assert versions_response.status_code == status.HTTP_200_OK
        version_id = versions_response.json()["data"]["items"][0]["id"]

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=make_auth_headers("model_analyst", "analyst"),
        ) as client:
            response = await client.post(
                f"/api/v1/model/versions/{version_id}/activate",
                json={"traffic_percent": 100},
            )
        assert response.status_code == status.HTTP_403_FORBIDDEN


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


class TestExportEndpoints:
    """数据导出接口测试"""

    async def test_export_topics_csv(self, async_client):
        """测试热榜 CSV 导出"""
        response = await async_client.get("/api/v1/exports/topics.csv?limit=5")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/csv")
        assert "hot-topics-" in response.headers["content-disposition"]
        assert response.content.startswith(b"\xef\xbb\xbf")
        text = response.content.decode("utf-8-sig")
        assert "标题" in text
        assert "平台" in text

    async def test_export_alerts_csv(self, async_client):
        """测试预警事件 CSV 导出"""
        response = await async_client.get("/api/v1/exports/alerts.csv?limit=5")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/csv")
        assert "alert-events-" in response.headers["content-disposition"]
        text = response.content.decode("utf-8-sig")
        assert "处置时间线" in text
        assert "级别" in text

    async def test_export_sentiment_report_pdf(self, async_client):
        """测试情感分析 PDF 报告导出"""
        response = await async_client.get("/api/v1/exports/sentiment-report.pdf?topic_limit=5")
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("application/pdf")
        assert "sentiment-report-" in response.headers["content-disposition"]
        assert response.content.startswith(b"%PDF")
        assert b"%%EOF" in response.content[-64:]


class TestSystemDatabaseEndpoints:
    """系统数据库备份接口测试"""

    async def test_admin_can_create_list_and_download_database_backup(self, async_client):
        """测试管理员创建、查询并下载 SQLite 备份"""
        filename = None
        try:
            create_response = await async_client.post("/api/v1/system/database/backup")
            assert create_response.status_code == status.HTTP_201_CREATED
            data = create_response.json()["data"]
            filename = data["filename"]
            assert filename.startswith("sentiment-backup-")
            assert filename.endswith(".db")
            assert data["size_bytes"] > 0
            assert data["download_url"].endswith(filename)

            list_response = await async_client.get("/api/v1/system/database/backups")
            assert list_response.status_code == status.HTTP_200_OK
            items = list_response.json()["data"]["items"]
            assert any(item["filename"] == filename for item in items)

            download_response = await async_client.get(f"/api/v1/system/database/backups/{filename}")
            assert download_response.status_code == status.HTTP_200_OK
            assert download_response.headers["content-type"].startswith("application/octet-stream")
            assert len(download_response.content) == data["size_bytes"]
        finally:
            if filename:
                backup_path = Path(resolve_backup_dir()) / filename
                backup_path.unlink(missing_ok=True)

    async def test_analyst_cannot_create_database_backup(self):
        """测试分析师不能创建数据库备份"""
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers=make_auth_headers("backup_analyst", "analyst"),
        ) as client:
            response = await client.post("/api/v1/system/database/backup")
        assert response.status_code == status.HTTP_403_FORBIDDEN


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
