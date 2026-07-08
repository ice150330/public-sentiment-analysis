"""
快速冒烟测试脚本

模块名称: test_smoke.py
模块职责: 5个核心接口快速验证，避免长任务被SIGKILL
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/sentiment-analysis')
sys.path.insert(0, '/root/.openclaw/workspace/sentiment-analysis/backend')

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    """健康检查"""
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    print("✅ Health check passed")


def test_topics_list():
    """热榜列表"""
    response = client.get("/api/v1/topics")
    assert response.status_code == 200
    print("✅ Topics list passed")


def test_sentiment_list():
    """情感分析列表"""
    response = client.get("/api/v1/sentiment/results")
    assert response.status_code == 200
    print("✅ Sentiment list passed")


def test_stats_overview():
    """统计概览"""
    response = client.get("/api/v1/stats/overview")
    assert response.status_code == 200
    print("✅ Stats overview passed")


def test_crawler_status():
    """爬虫状态"""
    response = client.get("/api/v1/crawler/status")
    assert response.status_code == 200
    print("✅ Crawler status passed")


if __name__ == "__main__":
    print("🚀 Running smoke tests (5 endpoints)...\n")
    
    try:
        test_health()
        test_topics_list()
        test_sentiment_list()
        test_stats_overview()
        test_crawler_status()
        
        print("\n✅ Smoke tests passed! System is healthy.")
    except Exception as e:
        print(f"\n❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
