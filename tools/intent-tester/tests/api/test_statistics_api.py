"""
统计分析API测试
测试测试报告、统计数据和分析功能接口
"""

import pytest
import json
from datetime import datetime, timedelta


class TestStatisticsReportsAPI:
    """统计报告API测试"""

    def test_should_get_failure_analysis_report_empty(
        self, api_client, assert_api_response
    ):
        """测试获取空的失败分析报告"""
        response = api_client.get("/api/reports/failure-analysis")
        data = assert_api_response(
            response,
            200,
            {
                "total_failures": int,
                "failure_rate": (int, float),
                "common_failures": list,
                "failure_trends": list,
            },
        )

        assert data["total_failures"] == 0
        assert data["failure_rate"] == 0
        assert data["common_failures"] == []

    def test_should_get_failure_analysis_with_data(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试获取包含数据的失败分析报告"""
        # 创建失败的执行记录
        testcase = create_test_testcase(
            {
                "name": "失败分析测试用例",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        create_test_execution(
            {
                "test_case_id": testcase["id"],
                "status": "failed",
                "error_message": "Element not found: 搜索按钮",
                "error_stack": "Stack trace...",
            }
        )

        create_test_execution(
            {
                "test_case_id": testcase["id"],
                "status": "failed",
                "error_message": "Timeout waiting for element",
                "error_stack": "Timeout error stack...",
            }
        )

        response = api_client.get("/api/reports/failure-analysis")
        data = assert_api_response(response, 200)

        assert data["total_failures"] >= 2
        assert data["failure_rate"] > 0
        assert len(data["common_failures"]) >= 1

    def test_should_support_date_range_filtering(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试支持日期范围过滤"""
        testcase = create_test_testcase(
            {
                "name": "日期过滤测试用例",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        create_test_execution({"test_case_id": testcase["id"], "status": "success"})

        # 测试最近7天的报告
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        response = api_client.get(
            f"/api/reports/failure-analysis?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200

        # 测试最近30天的报告 - 使用现有的failure-analysis端点
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        response = api_client.get(
            f"/api/reports/failure-analysis?start_date={start_date}&end_date={end_date}"
        )
        assert response.status_code == 200


class TestStatisticsErrorHandling:
    """统计API错误处理测试"""

    def test_should_handle_invalid_date_range(self, api_client):
        """测试处理无效的日期范围"""
        # 无效的日期格式
        response = api_client.get(
            "/api/reports/failure-analysis?start_date=invalid&end_date=2023-12-31"
        )
        # 应该容错处理或返回400错误
        assert response.status_code in [200, 400]

        # 结束日期早于开始日期
        response = api_client.get(
            "/api/reports/failure-analysis?start_date=2023-12-31&end_date=2023-01-01"
        )
        assert response.status_code in [200, 400]

    def test_should_handle_large_data_queries(
        self, api_client, create_test_testcase, create_test_execution
    ):
        """测试处理大数据量查询的性能"""
        # 创建大量测试数据（适量，避免测试超时）
        testcase = create_test_testcase(
            {
                "name": "大数据测试用例",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        # 创建50个执行记录
        for i in range(50):
            status = "success" if i % 2 == 0 else "failed"
            create_test_execution(
                {
                    "test_case_id": testcase["id"],
                    "status": status,
                    "duration": 1000 + i * 100,
                }
            )

        # 测试各个统计API是否能处理大数据量
        response = api_client.get("/api/reports/failure-analysis")
        assert response.status_code == 200

    def test_should_handle_nonexistent_endpoints(self, api_client):
        """测试处理不存在的统计端点"""
        response = api_client.get("/api/statistics/nonexistent")
        assert response.status_code == 404

        response = api_client.get("/api/reports/nonexistent")
        assert response.status_code == 404
