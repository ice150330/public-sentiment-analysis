"""
全量接口验证测试

测试内容:
1. 所有新增模块的接口连通性
2. 数据库表创建验证
3. 关键业务逻辑验证
"""

import sys
sys.path.insert(0, '/root/.openclaw/workspace/sentiment-analysis')
sys.path.insert(0, '/root/.openclaw/workspace/sentiment-analysis/backend')

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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

if __name__ == "__main__":
    print("🚀 Starting full API validation tests...\n")
    
    try:
        test_health()
        test_alert_rules()
        test_platform_monitoring()
        test_data_quality()
        test_system()
        test_model_status()
        
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
