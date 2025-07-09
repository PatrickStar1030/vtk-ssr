"""
API测试模块
"""

import pytest
from src.trame_server.app import create_app


@pytest.fixture
def app():
    """创建测试应用实例"""
    app = create_app("testing")
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


def test_health_check(client):
    """测试健康检查接口"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "message" in data


def test_get_info(client):
    """测试获取服务器信息接口"""
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Trame Server"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


def test_echo(client):
    """测试回显接口"""
    test_data = {"message": "Hello, World!", "number": 42}
    response = client.post("/api/v1/echo", json=test_data)
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Echo response"
    assert data["data"] == test_data
    assert "timestamp" in data


def test_404_error(client):
    """测试404错误处理"""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "Not Found"
    assert data["status_code"] == 404 