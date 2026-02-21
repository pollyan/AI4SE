"""
系统健康检查和监控API测试
测试系统状态、错误监控、性能指标等接口
"""

import time

class TestHealthCheckAPI:
    """基础健康检查API测试"""

    def test_should_return_basic_health_status(self, api_client):
        """测试基础健康检查端点"""
        response = api_client.get("/health")
        
        # 健康检查返回简单的JSON，不遵循标准API包装
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert data["message"] == "Service is running"


class TestHealthAPIErrorHandling:
    """健康检查API错误处理测试"""

    def test_should_handle_service_unavailable(self, api_client):
        """测试处理服务不可用情况"""
        # 测试访问不存在的健康检查端点
        response = api_client.get("/health/nonexistent-service")
        assert response.status_code == 404

    def test_should_maintain_health_check_performance(self, api_client):
        """测试健康检查接口的响应性能"""
        
        # 健康检查应该快速响应（< 1秒）
        start_time = time.time()
        response = api_client.get("/health")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 健康检查应该在1秒内响应
