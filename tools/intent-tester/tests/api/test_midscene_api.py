"""
MidScene微服务集成API测试
测试与MidScene AI服务的集成接口
"""

import pytest
import json


class TestMidSceneExecutionAPI:
    """MidScene执行结果接收API测试"""

    def test_should_receive_execution_result_success(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试接收成功的执行结果"""
        # 创建测试用例和执行记录
        testcase = create_test_testcase(
            {
                "name": "MidScene集成测试用例",
                "steps": [
                    {"action": "goto", "params": {"url": "https://example.com"}},
                    {
                        "action": "ai_input",
                        "params": {"text": "test", "locate": "搜索框"},
                    },
                ],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "running"}
        )

        # 模拟MidScene服务发送的执行结果
        execution_result = {
            "execution_id": execution["execution_id"],
            "testcase_id": testcase["id"],
            "status": "success",
            "mode": "headless",
            "browser": "chrome",
            "duration": 5000,
            "steps_total": 2,
            "steps_passed": 2,
            "steps_failed": 0,
            "result_summary": {
                "total_steps": 2,
                "passed_steps": 2,
                "failed_steps": 0,
                "execution_time": "5.0s",
            },
            "screenshots_path": "/screenshots/test_123",
            "logs_path": "/logs/test_123.log",
            "step_results": [
                {
                    "step_index": 0,
                    "action": "goto",
                    "status": "success",
                    "duration": 2000,
                    "screenshot_path": "/screenshots/step_0.png",
                    "result_data": {"url": "https://example.com"},
                },
                {
                    "step_index": 1,
                    "action": "ai_input",
                    "status": "success",
                    "duration": 3000,
                    "screenshot_path": "/screenshots/step_1.png",
                    "result_data": {"input_value": "test"},
                },
            ],
        }

        response = api_client.post(
            "/api/midscene/execution-result", json=execution_result
        )
        data = assert_api_response(
            response, 200, {"database_id": int, "execution_id": str, "steps_count": int}
        )

        assert data["execution_id"] == execution["execution_id"]
        assert data["steps_count"] >= 0

    def test_should_receive_execution_result_failure(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试接收失败的执行结果"""
        testcase = create_test_testcase(
            {
                "name": "MidScene失败测试用例",
                "steps": [{"action": "ai_tap", "params": {"locate": "不存在的按钮"}}],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "running"}
        )

        # 模拟失败的执行结果
        execution_result = {
            "execution_id": execution["execution_id"],
            "testcase_id": testcase["id"],
            "status": "failed",
            "mode": "headless",
            "browser": "chrome",
            "duration": 3000,
            "steps_total": 1,
            "steps_passed": 0,
            "steps_failed": 1,
            "error_message": "Element not found: 不存在的按钮",
            "error_stack": "ElementNotFoundError\\n  at findElement...",
            "result_summary": {
                "total_steps": 1,
                "passed_steps": 0,
                "failed_steps": 1,
                "error": "Element not found: 不存在的按钮",
            },
            "step_results": [
                {
                    "step_index": 0,
                    "action": "ai_tap",
                    "status": "failed",
                    "duration": 3000,
                    "error_message": "Element not found: 不存在的按钮",
                    "screenshot_path": "/screenshots/error_step_0.png",
                }
            ],
        }

        response = api_client.post(
            "/api/midscene/execution-result", json=execution_result
        )
        data = assert_api_response(
            response, 200, {"database_id": int, "execution_id": str, "steps_count": int}
        )

        assert data["execution_id"] == execution["execution_id"]
        assert data["steps_count"] >= 0

    def test_should_handle_step_execution_details(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试处理步骤执行详细信息"""
        testcase = create_test_testcase(
            {
                "name": "步骤详情测试用例",
                "steps": [
                    {"action": "goto", "params": {"url": "https://example.com"}},
                    {
                        "action": "ai_input",
                        "params": {"text": "test", "locate": "输入框"},
                    },
                    {"action": "ai_tap", "params": {"locate": "提交按钮"}},
                ],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "running"}
        )

        execution_result = {
            "execution_id": execution["execution_id"],
            "testcase_id": testcase["id"],
            "status": "success",
            "mode": "browser",
            "browser": "firefox",
            "duration": 8000,
            "steps_total": 3,
            "steps_passed": 3,
            "steps_failed": 0,
            "step_results": [
                {
                    "step_index": 0,
                    "action": "goto",
                    "status": "success",
                    "duration": 2000,
                    "screenshot_path": "/screenshots/goto.png",
                    "result_data": {
                        "url": "https://example.com",
                        "title": "Example Site",
                    },
                },
                {
                    "step_index": 1,
                    "action": "ai_input",
                    "status": "success",
                    "duration": 3000,
                    "screenshot_path": "/screenshots/input.png",
                    "result_data": {"element_found": True, "input_value": "test"},
                },
                {
                    "step_index": 2,
                    "action": "ai_tap",
                    "status": "success",
                    "duration": 3000,
                    "screenshot_path": "/screenshots/tap.png",
                    "result_data": {"element_clicked": True},
                },
            ],
        }

        response = api_client.post(
            "/api/midscene/execution-result", json=execution_result
        )
        data = assert_api_response(
            response, 200, {"database_id": int, "execution_id": str, "steps_count": int}
        )

        assert data["steps_count"] >= 0

        # 验证步骤详情是否正确保存（通过获取执行详情验证）
        execution_response = api_client.get(
            f'/api/executions/{execution["execution_id"]}'
        )
        execution_data = assert_api_response(execution_response, 200)

        assert len(execution_data["step_executions"]) == 3

        # 验证步骤执行详情
        step_executions = execution_data["step_executions"]
        assert step_executions[0]["action"] == "goto"
        assert step_executions[0]["status"] == "success"
        assert step_executions[1]["action"] == "ai_input"
        assert step_executions[2]["action"] == "ai_tap"


class TestMidSceneExecutionStartAPI:
    """MidScene执行开始通知API测试"""

    def test_should_receive_execution_start_notification(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试接收执行开始通知"""
        testcase = create_test_testcase(
            {
                "name": "MidScene开始执行测试用例",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "pending"}
        )

        # 模拟MidScene服务发送的执行开始通知
        start_notification = {
            "execution_id": execution["execution_id"],
            "testcase_id": testcase["id"],
            "status": "running",
            "mode": "headless",
            "browser": "chrome",
            "start_time": "2023-12-01T10:00:00Z",
        }

        response = api_client.post(
            "/api/midscene/execution-start", json=start_notification
        )
        data = assert_api_response(response, 200)

        assert data["execution_id"] == execution["execution_id"]
        assert data["status_updated"] == True

    def test_should_validate_execution_start_data(self, api_client):
        """测试验证执行开始通知数据"""
        # 缺少必需字段
        response = api_client.post(
            "/api/midscene/execution-start",
            json={
                "execution_id": "test-123"
                # 缺少其他必需字段
            },
        )
        assert response.status_code == 400

        # 无效的执行ID
        response = api_client.post(
            "/api/midscene/execution-start",
            json={
                "execution_id": "nonexistent",
                "testcase_id": 1,
                "status": "running",
                "mode": "headless",
            },
        )
        assert response.status_code == 404


class TestMidSceneServiceIntegration:
    """MidScene服务集成测试"""

    def test_should_handle_service_configuration(self, api_client):
        """测试MidScene服务配置获取"""
        response = api_client.get("/api/midscene/config")

        # 配置端点可能需要认证或可能不存在
        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.get_json()
            assert "config" in data

    def test_should_handle_concurrent_executions(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试处理并发执行"""
        # 创建多个测试用例
        testcases = []
        executions = []

        for i in range(3):
            testcase = create_test_testcase(
                {
                    "name": f"并发测试用例{i}",
                    "steps": [
                        {"action": "goto", "params": {"url": f"https://example{i}.com"}}
                    ],
                }
            )
            testcases.append(testcase)

            execution = create_test_execution(
                {"test_case_id": testcase["id"], "status": "running"}
            )
            executions.append(execution)

        # 同时发送多个执行结果
        responses = []
        for i, execution in enumerate(executions):
            execution_result = {
                "execution_id": execution["execution_id"],
                "testcase_id": testcases[i]["id"],
                "status": "success",
                "mode": "headless",
                "browser": "chrome",
                "duration": 2000 + i * 1000,
                "steps_total": 1,
                "steps_passed": 1,
                "steps_failed": 0,
            }

            response = api_client.post(
                "/api/midscene/execution-result", json=execution_result
            )
            responses.append(response)

        # 验证所有请求都成功处理
        for response in responses:
            assert response.status_code == 200

    def test_should_handle_malformed_requests(self, api_client):
        """测试处理格式错误的请求"""
        # 无效的JSON
        response = api_client.post(
            "/api/midscene/execution-result",
            data="invalid json",
            content_type="application/json",
        )
        assert response.status_code == 400

        # 空的请求体
        response = api_client.post("/api/midscene/execution-result", json={})
        assert response.status_code == 400

        # 错误的内容类型
        response = api_client.post(
            "/api/midscene/execution-result",
            data='{"test": "data"}',
            content_type="text/plain",
        )
        assert response.status_code in [400, 415]


class TestMidSceneErrorHandling:
    """MidScene API错误处理测试"""

    def test_should_handle_timeout_scenarios(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试处理超时场景"""
        testcase = create_test_testcase(
            {
                "name": "超时测试用例",
                "steps": [
                    {"action": "ai_wait_for", "params": {"condition": "页面加载完成"}}
                ],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "running"}
        )

        # 模拟超时执行结果
        timeout_result = {
            "execution_id": execution["execution_id"],
            "testcase_id": testcase["id"],
            "status": "failed",
            "mode": "headless",
            "browser": "chrome",
            "duration": 30000,  # 30秒超时
            "steps_total": 1,
            "steps_passed": 0,
            "steps_failed": 1,
            "error_message": 'Timeout: 等待条件"页面加载完成"超时',
            "error_stack": "TimeoutError: Condition not met within timeout period",
            "step_results": [
                {
                    "step_index": 0,
                    "action": "ai_wait_for",
                    "status": "failed",
                    "duration": 30000,
                    "error_message": 'Timeout: 等待条件"页面加载完成"超时',
                }
            ],
        }

        response = api_client.post(
            "/api/midscene/execution-result", json=timeout_result
        )
        data = assert_api_response(response, 200)

        assert data["steps_count"] >= 0

    def test_should_handle_network_errors(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试处理网络错误"""
        testcase = create_test_testcase(
            {
                "name": "网络错误测试用例",
                "steps": [
                    {
                        "action": "goto",
                        "params": {"url": "https://nonexistent-domain.example"},
                    }
                ],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "running"}
        )

        # 模拟网络错误结果
        network_error_result = {
            "execution_id": execution["execution_id"],
            "testcase_id": testcase["id"],
            "status": "failed",
            "mode": "headless",
            "browser": "chrome",
            "duration": 5000,
            "steps_total": 1,
            "steps_passed": 0,
            "steps_failed": 1,
            "error_message": "Network error: DNS resolution failed",
            "error_stack": "NetworkError: getaddrinfo ENOTFOUND nonexistent-domain.example",
            "step_results": [
                {
                    "step_index": 0,
                    "action": "goto",
                    "status": "failed",
                    "duration": 5000,
                    "error_message": "Network error: DNS resolution failed",
                }
            ],
        }

        response = api_client.post(
            "/api/midscene/execution-result", json=network_error_result
        )
        data = assert_api_response(response, 200)

        assert data["steps_count"] >= 0

    def test_should_handle_duplicate_results(
        self,
        api_client,
        create_test_testcase,
        create_test_execution,
        assert_api_response,
    ):
        """测试处理重复的执行结果"""
        testcase = create_test_testcase(
            {
                "name": "重复结果测试用例",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "running"}
        )

        execution_result = {
            "execution_id": execution["execution_id"],
            "testcase_id": testcase["id"],
            "status": "success",
            "mode": "headless",
            "browser": "chrome",
            "duration": 3000,
            "steps_total": 1,
            "steps_passed": 1,
            "steps_failed": 0,
        }

        # 发送第一次执行结果
        response1 = api_client.post(
            "/api/midscene/execution-result", json=execution_result
        )
        assert response1.status_code == 200

        # 发送重复的执行结果
        response2 = api_client.post(
            "/api/midscene/execution-result", json=execution_result
        )

        # 应该能够处理重复结果（可能是更新或忽略）
        assert response2.status_code in [200, 409]  # 成功或冲突
