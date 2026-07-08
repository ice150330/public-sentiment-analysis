"""
全量接口验证测试（支持按模块分批执行）

测试内容:
1. 所有新增模块的接口连通性
2. 数据库表创建验证
3. 关键业务逻辑验证

用法:
    python test_full_validation.py              # 全量测试
    python test_full_validation.py --module=core    # 核心模块
    python test_full_validation.py --module=alerts  # 预警模块
    python test_full_validation.py --module=analytics  # 高级分析
"""

import asyncio
import sys
import argparse
from pathlib import Path

import httpx

repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "backend"))

from app.main import app


class ASGITestClient:
    """Small sync wrapper around httpx ASGITransport for httpx>=0.28."""

    async def _request(self, method: str, path: str, **kwargs):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    def get(self, path: str, **kwargs):
        return asyncio.run(self._request("GET", path, **kwargs))

    def post(self, path: str, **kwargs):
        return asyncio.run(self._request("POST", path, **kwargs))

    def patch(self, path: str, **kwargs):
        return asyncio.run(self._request("PATCH", path, **kwargs))

    def delete(self, path: str, **kwargs):
        return asyncio.run(self._request("DELETE", path, **kwargs))


client = ASGITestClient()

# 解析命令行参数
parser = argparse.ArgumentParser(description='API validation tests')
parser.add_argument('--module', default='', help='Test module: core, alerts, analytics')
args, _ = parser.parse_known_args()
MODULE = args.module

def test_health():
    """测试健康检查"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    print("✅ Health check passed")

def test_alert_rules():
    """测试预警规则接口"""
    # 创建规则
    rule_data = {
        "name": "测试规则",
        "description": "测试预警规则",
        "condition_type": "heat_spike",
        "condition_expr": '{"field": "heat_score", "operator": ">", "value": 10000}',
        "severity": "P2",
        "platform_scope": "all",
        "cooldown_minutes": 30,
        "is_active": True,
    }
    response = client.post("/api/v1/alerts/rules", json=rule_data)
    assert response.status_code == 201
    rule_id = response.json()["data"]["id"]
    print(f"✅ Alert rule created: {rule_id}")
    
    # 查询规则
    response = client.get(f"/api/v1/alerts/rules/{rule_id}")
    assert response.status_code == 200
    print("✅ Alert rule get passed")
    
    # 更新规则
    response = client.patch(f"/api/v1/alerts/rules/{rule_id}", json={"is_active": False})
    assert response.status_code == 200
    print("✅ Alert rule patch passed")
    
    # 删除规则
    response = client.delete(f"/api/v1/alerts/rules/{rule_id}")
    assert response.status_code == 200
    print("✅ Alert rule delete passed")

def test_platform_monitoring():
    """测试平台监测接口"""
    response = client.get("/api/v1/platforms/monitoring/matrix")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "matrix" in data
    print("✅ Platform monitoring matrix passed")
    
    response = client.get("/api/v1/platforms/monitoring/freshness")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "freshness" in data
    print("✅ Data freshness passed")

def test_data_quality():
    """测试数据质量接口"""
    response = client.get("/api/v1/data-quality/funnel")
    assert response.status_code == 200
    print("✅ Data quality funnel passed")
    
    response = client.get("/api/v1/data-quality/checks")
    assert response.status_code == 200
    print("✅ Data quality checks passed")
    
    response = client.get("/api/v1/data-quality/summary")
    assert response.status_code == 200
    print("✅ Data quality summary passed")

def test_system():
    """测试系统管理接口"""
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "overall_status" in data
    print("✅ System health passed")
    
    response = client.get("/api/v1/system/logs")
    assert response.status_code == 200
    print("✅ System logs passed")
    
    response = client.get("/api/v1/system/audit-logs")
    assert response.status_code == 200
    print("✅ Audit logs passed")

def test_model_status():
    """测试模型管理接口"""
    response = client.get("/api/v1/model/status")
    assert response.status_code == 200
    print("✅ Model status passed")
    
    response = client.get("/api/v1/model/versions")
    assert response.status_code == 200
    print("✅ Model versions passed")
    
    response = client.get("/api/v1/model/low-confidence")
    assert response.status_code == 200
    print("✅ Low confidence results passed")

def test_alert_engine():
    """测试预警引擎"""
    # 先创建一个规则
    rule_data = {
        "name": "热度测试规则",
        "description": "测试热度预警",
        "condition_type": "heat_spike",
        "condition_expr": '{"threshold": 0, "time_window_hours": 24}',
        "severity": "P3",
        "platform_scope": "all",
        "cooldown_minutes": 1,
        "is_active": True,
    }
    response = client.post("/api/v1/alerts/rules", json=rule_data)
    assert response.status_code == 201
    
    # 触发评估
    response = client.post("/api/v1/alerts/evaluate")
    assert response.status_code == 200
    data = response.json()
    assert "triggered" in data["data"]
    print("✅ Alert engine evaluation passed")
    
    # 查询待处理预警摘要
    response = client.get("/api/v1/alerts/pending-summary")
    assert response.status_code == 200
    print("✅ Alert pending summary passed")


def test_data_quality_check():
    """测试数据质量检查"""
    response = client.post("/api/v1/data-quality/check", params={"run_type": "manual"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] in ["completed", "failed"]
    print("✅ Data quality check passed")


def test_topic_clusters():
    """测试主题聚类"""
    response = client.post("/api/v1/topic-clusters/run", params={"algorithm": "kmeans", "n_clusters": 3, "time_window_hours": 24})
    assert response.status_code == 200
    data = response.json()
    assert "clusters" in data["data"]
    print("✅ Topic clustering passed")
    
    # 查询聚类列表
    response = client.get("/api/v1/topic-clusters")
    assert response.status_code == 200
    print("✅ Topic clusters list passed")


def test_propagation_paths():
    """测试传播路径分析"""
    # 先获取一个话题ID
    response = client.get("/api/v1/topics")
    assert response.status_code == 200
    data = response.json()
    
    if data["data"]["items"]:
        topic_id = data["data"]["items"][0]["id"]
        
        # 分析传播路径
        response = client.post(f"/api/v1/propagation-paths/analyze/{topic_id}")
        assert response.status_code == 200
        print("✅ Propagation analysis passed")
        
        # 查询传播路径列表
        response = client.get("/api/v1/propagation-paths")
        assert response.status_code == 200
        print("✅ Propagation paths list passed")
    else:
        print("⚠️ Skipping propagation test (no topics available)")


def test_trend_predictions():
    """测试趋势预测"""
    response = client.post("/api/v1/trend-predictions/predict", params={"target_type": "sentiment", "model_type": "ema", "horizon_hours": 24})
    assert response.status_code == 200
    data = response.json()
    
    # 可能因为没有历史数据返回 400
    if data["code"] == 400:
        print("⚠️ Skipping trend prediction test (no historical data)")
        return
    
    assert "prediction_id" in data["data"]
    print("✅ Trend prediction creation passed")
    
    # 查询预测列表
    response = client.get("/api/v1/trend-predictions")
    assert response.status_code == 200
    print("✅ Trend predictions list passed")


def test_model_explanations():
    """测试模型解释"""
    # 先获取一个情感分析结果
    response = client.get("/api/v1/sentiment/results")
    assert response.status_code == 200
    data = response.json()
    
    if data["data"]["items"]:
        sentiment_id = data["data"]["items"][0]["id"]
        
        # 生成解释
        response = client.post(f"/api/v1/model-explanations/explain/{sentiment_id}", params={"method": "attention"})
        assert response.status_code == 200
        print("✅ Model explanation generation passed")
        
        # 查询解释列表
        response = client.get("/api/v1/model-explanations")
        assert response.status_code == 200
        print("✅ Model explanations list passed")
    else:
        print("⚠️ Skipping explanation test (no sentiment results available)")


if __name__ == "__main__":
    print("🚀 Starting API validation tests...\n")
    
    if MODULE:
        print(f"📦 Module filter: {MODULE}\n")
    
    try:
        # 核心模块（所有测试都运行）
        test_health()
        
        if not MODULE or MODULE == "alerts":
            test_alert_rules()
        
        if not MODULE or MODULE == "core":
            test_platform_monitoring()
            test_data_quality()
            test_system()
            test_model_status()
        
        if not MODULE or MODULE == "alerts":
            test_alert_engine()
            test_data_quality_check()
        
        if not MODULE or MODULE == "analytics":
            test_topic_clusters()
            test_propagation_paths()
            test_trend_predictions()
            test_model_explanations()
        
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
