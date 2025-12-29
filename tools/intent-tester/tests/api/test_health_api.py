"""
系统健康检查和监控API测试
测试系统状态、错误监控、性能指标等接口
"""

import pytest
import time

class TestHealthCheckAPI:
    """基础健康检查API测试"""

    def test_should_return_basic_health_status(self, api_client, assert_api_response):
        """测试基础健康检查端点"""
        response = api_client.get("/api/health")
        data = assert_api_response(
            response, 200, {"status": str, "timestamp": str, "version": str}
        )

        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "version" in data


class TestHealthAPIErrorHandling:
    """健康检查API错误处理测试"""

    def test_should_handle_service_unavailable(self, api_client):
        """测试处理服务不可用情况"""
        # 测试访问不存在的健康检查端点
        response = api_client.get("/api/health/nonexistent-service")
        assert response.status_code == 404

    def test_should_maintain_health_check_performance(self, api_client):
        """测试健康检查接口的响应性能"""
        
        # 健康检查应该快速响应（< 1秒）
        start_time = time.time()
        response = api_client.get("/api/health")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 健康检查应该在1秒内响应

        # 详细健康检查测试 - 考虑到CI环境中监控系统可能不可用
        start_time = time.time()
        response = api_client.get("/api/health/detailed")
        end_time = time.time()

        # CI环境中监控系统不可用时返回503，本地开发环境中返回200
        assert response.status_code in [200, 503]
        assert (end_time - start_time) < 3.0
