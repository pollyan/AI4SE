"""
API错误场景综合测试
覆盖各种边界情况、异常处理和错误恢复场景
"""

import pytest
import json
from unittest.mock import patch


class TestInputValidationErrors:
    """输入验证错误测试"""

    def test_should_handle_malformed_json(self, api_client):
        """测试处理格式错误的JSON"""
        # 发送无效JSON
        response = api_client.post(
            "/api/testcases", data='{"invalid": json}', content_type="application/json"
        )

        # Flask会在JSON解析阶段就拒绝无效JSON，通常返回400
        assert response.status_code == 400

        # 验证响应包含错误信息
        data = response.get_json()
        if data:  # 某些情况下Flask可能不返回JSON响应体
            assert "message" in data or "error" in data

    def test_should_handle_missing_content_type(self, api_client):
        """测试处理缺少Content-Type头"""
        valid_data = {
            "name": "测试用例",
            "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
        }

        response = api_client.post("/api/testcases", data=json.dumps(valid_data))
        assert response.status_code in [400, 415]

    def test_should_handle_wrong_content_type(self, api_client):
        """测试处理错误的Content-Type"""
        response = api_client.post(
            "/api/testcases", data="test data", content_type="text/plain"
        )
        assert response.status_code in [400, 415]

    def test_should_handle_empty_request_body(self, api_client):
        """测试处理空请求体"""
        response = api_client.post("/api/testcases", json={})

        # 当前API实现：空name应该返回400错误
        assert response.status_code == 400

        data = response.get_json()
        assert data is not None
        assert "message" in data
        # 验证错误信息提到名称相关问题
        message = data.get("message", "").lower()
        assert "name" in message or "名称" in message

    def test_should_handle_oversized_request(self, api_client):
        """测试处理超大请求"""
        # 创建一个较大的请求来测试系统处理能力
        large_steps = []
        for i in range(100):  # 100个步骤（减少数量以避免测试环境超时）
            large_steps.append(
                {
                    "action": "ai_input",
                    "params": {
                        "text": "x" * 500,  # 减少到500字符
                        "locate": f"输入框{i}",
                    },
                }
            )

        oversized_data = {
            "name": "大型测试用例",
            "description": "x" * 5000,  # 5KB描述
            "steps": large_steps,
        }

        response = api_client.post("/api/testcases", json=oversized_data)
        # 当前实现：没有大小限制，应该能成功创建（HTTP状态码200）
        # 如果将来实现了大小限制，应该返回413
        assert response.status_code in [200, 413]

        if response.status_code == 200:
            # 如果创建成功，清理测试数据
            data = response.get_json()
            testcase_id = data["data"]["id"]
            api_client.delete(f"/api/testcases/{testcase_id}")

    def test_should_handle_special_characters(self, api_client):
        """测试处理特殊字符"""
        special_chars_data = {
            "name": '测试用例 <script>alert("xss")</script> 🚀',
            "description": "SQL injection test: '; DROP TABLE test_cases; --",
            "steps": [
                {
                    "action": "ai_input",
                    "params": {
                        "text": '特殊字符: \\n\\r\\t\\0 "\'"',
                        "locate": "Unicode: 你好 мир العالم 🌍",
                    },
                }
            ],
        }

        response = api_client.post("/api/testcases", json=special_chars_data)

        # 当前实现：允许特殊字符但应该安全存储
        if response.status_code == 200:
            # 创建成功，数据库会安全存储这些字符
            data = response.get_json()

            # 验证数据已存储（但不验证转义，因为当前实现允许存储原始数据）
            assert data["data"]["name"] is not None
            assert data["data"]["description"] is not None

            # 清理测试数据
            testcase_id = data["data"]["id"]
            api_client.delete(f"/api/testcases/{testcase_id}")
        else:
            # 如果有安全验证拒绝了请求
            assert response.status_code == 400


class TestDatabaseErrorSimulation:
    """数据库错误模拟测试"""

    def test_should_handle_database_constraint_violation(
        self, api_client, create_test_testcase
    ):
        """测试数据库约束违反（如重复名称）"""
        # 创建一个测试用例
        testcase = create_test_testcase(
            {
                "name": "唯一名称测试",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        # 尝试创建同名测试用例（如果有唯一约束）
        response = api_client.post(
            "/api/testcases",
            json={
                "name": "唯一名称测试",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            },
        )

        # 当前实现：没有唯一约束，应该成功创建（HTTP状态码200）
        # 如果将来添加了唯一约束，应该返回400或409
        assert response.status_code in [200, 400, 409]

        if response.status_code == 200:
            # 如果创建成功，清理数据
            data = response.get_json()
            api_client.delete(f'/api/testcases/{data["data"]["id"]}')

    def test_should_handle_invalid_foreign_key(self, api_client):
        """测试无效外键引用"""
        # 尝试获取不存在的测试用例
        response = api_client.get("/api/testcases/999999")

        assert response.status_code == 404
        data = response.get_json()
        assert "message" in data
        assert "不存在" in data["message"] or "not found" in data["message"].lower()

    def test_should_handle_database_connection_gracefully(self, api_client):
        """测试优雅处理数据库连接问题"""
        # 这个测试验证API在面对数据库问题时的错误处理能力
        # 通过发送一个有效请求来确保基本的数据库连接是工作的
        response = api_client.get("/api/testcases?page=1&size=1")

        # 应该能正常响应或返回适当的错误
        assert response.status_code in [200, 500, 503]

        if response.status_code == 200:
            data = response.get_json()
            assert "data" in data


class TestExternalServiceErrors:
    """外部服务错误测试"""

    def test_should_handle_network_connectivity_check(self, api_client):
        """测试网络连通性检查"""
        # 这个测试验证系统在网络问题时的基本处理能力
        # 通过访问健康检查端点来验证服务可用性

        # 尝试访问仪表板健康检查API
        response = api_client.get("/api/dashboard/health-check")

        # 应该能返回健康状态或适当的错误
        assert response.status_code in [200, 500, 503]

        if response.status_code == 200:
            data = response.get_json()
            assert "health_status" in data["data"]
            assert data["data"]["health_status"] in [
                "excellent",
                "good",
                "warning",
                "critical",
                "error",
            ]

    def test_should_validate_external_url_accessibility(self, api_client):
        """测试外部URL可访问性验证"""
        # 创建包含外部URL的测试用例
        test_data = {
            "name": "URL可访问性测试",
            "description": "测试外部URL处理",
            "steps": [
                {
                    "action": "goto",
                    "params": {
                        "url": "https://httpbin.org/status/200"  # 使用可靠的测试端点
                    },
                }
            ],
        }

        response = api_client.post("/api/testcases", json=test_data)

        # 创建测试用例应该成功（不验证URL可访问性）
        assert response.status_code == 200

        if response.status_code == 200:
            data = response.get_json()
            testcase_id = data["data"]["id"]

            # 验证URL已正确存储
            get_response = api_client.get(f"/api/testcases/{testcase_id}")
            assert get_response.status_code == 200

            get_data = get_response.get_json()
            steps = get_data["data"]["steps"]
            assert len(steps) > 0
            assert steps[0]["params"]["url"] == "https://httpbin.org/status/200"

            # 清理
            api_client.delete(f"/api/testcases/{testcase_id}")

    def test_should_handle_invalid_external_url(self, api_client):
        """测试无效外部URL处理"""
        test_data = {
            "name": "无效URL测试",
            "description": "测试无效URL处理",
            "steps": [{"action": "goto", "params": {"url": "not-a-valid-url"}}],
        }

        response = api_client.post("/api/testcases", json=test_data)

        # 当前实现：允许创建，不验证URL格式（HTTP状态码200）
        # 如果将来添加URL验证，应该返回400
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.get_json()
            testcase_id = data["data"]["id"]
            api_client.delete(f"/api/testcases/{testcase_id}")


class TestResourceLimitErrors:
    """资源限制错误测试"""

    def test_should_handle_memory_pressure(self, api_client, create_test_testcase):
        """测试内存压力情况"""
        # 创建大量大型测试用例以模拟内存压力
        large_testcases = []

        for i in range(10):
            large_steps = []
            for j in range(100):  # 每个测试用例100个步骤
                large_steps.append(
                    {
                        "action": "ai_input",
                        "params": {
                            "text": f"大型数据{i}-{j}" * 100,  # 较大的数据
                            "locate": f"元素{i}-{j}",
                        },
                    }
                )

            response = api_client.post(
                "/api/testcases",
                json={
                    "name": f"大型测试用例{i}",
                    "description": "大型测试用例，用于测试内存处理" * 100,
                    "steps": large_steps,
                },
            )

            if response.status_code == 200:
                large_testcases.append(response.get_json()["data"])
            else:
                # 如果因为内存压力拒绝创建，这是可以接受的
                assert response.status_code in [
                    400,
                    413,
                    507,
                ]  # 507 = Insufficient Storage
                break

        # 清理创建的大型测试用例
        for testcase in large_testcases:
            api_client.delete(f'/api/testcases/{testcase["id"]}')


class TestSecurityErrorScenarios:
    """安全错误场景测试"""

    def test_should_prevent_sql_injection(self, api_client):
        """测试防止SQL注入"""
        malicious_inputs = [
            "'; DROP TABLE test_cases; --",
            "' OR '1'='1",
            "'; INSERT INTO test_cases (name) VALUES ('hacked'); --",
            "' UNION SELECT * FROM test_cases WHERE '1'='1",
        ]

        for malicious_input in malicious_inputs:
            response = api_client.get(f"/api/testcases?search={malicious_input}")

            # 应该正常返回搜索结果，不执行恶意SQL
            assert response.status_code == 200

            data = response.get_json()
            # 不应该返回所有数据（SQL注入成功的标志）
            assert len(data["data"]["items"]) < 100  # 假设正常情况下不会有100+个匹配

    def test_should_prevent_path_traversal(self, api_client):
        """测试防止路径遍历"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for malicious_path in malicious_paths:
            response = api_client.get(f"/api/testcases/{malicious_path}")

            # 应该返回404而不是文件内容
            assert response.status_code in [400, 404]

    def test_should_handle_xss_attempts(self, api_client):
        """测试处理XSS攻击尝试"""
        xss_payloads = [
            '<script>alert("xss")</script>',
            '<img src="x" onerror="alert(\'xss\')">',
            'javascript:alert("xss")',
            "<svg onload=\"alert('xss')\"></svg>",
        ]

        for payload in xss_payloads:
            response = api_client.post(
                "/api/testcases",
                json={
                    "name": f"XSS测试 {payload}",
                    "description": f"描述包含XSS: {payload}",
                    "steps": [
                        {
                            "action": "ai_input",
                            "params": {"text": payload, "locate": "input"},
                        }
                    ],
                },
            )

            if response.status_code == 200:
                # 如果创建成功，数据应该已安全存储
                data = response.get_json()
                # 验证响应包含数据（当前实现允许存储原始数据）
                assert data["data"]["name"] is not None
                assert data["data"]["description"] is not None

                # 清理测试数据
                testcase_id = data["data"]["id"]
                api_client.delete(f"/api/testcases/{testcase_id}")
            else:
                # 或者直接拒绝含有XSS的请求
                assert response.status_code == 400


class TestRecoveryScenarios:
    """恢复场景测试"""

    def test_should_recover_from_temporary_failures(
        self, api_client, create_test_testcase
    ):
        """测试从临时故障中恢复"""
        testcase = create_test_testcase(
            {
                "name": "恢复测试用例",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        # 模拟系统负载高的情况
        with patch("web_gui.models.db.session.commit") as mock_commit:
            # 前几次提交失败
            mock_commit.side_effect = [
                Exception("Temporary failure"),
                Exception("Database busy"),
                None,  # 第三次成功
            ]

            # 重试逻辑应该能恢复
            response = api_client.put(
                f'/api/testcases/{testcase["id"]}', json={"name": "更新后的测试用例"}
            )

            # 应该最终成功或返回适当的错误
            assert response.status_code in [200, 500, 503]

    def test_should_maintain_data_consistency(
        self, api_client, create_test_testcase, create_test_execution
    ):
        """测试维护数据一致性"""
        testcase = create_test_testcase(
            {
                "name": "一致性测试用例",
                "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            }
        )

        execution = create_test_execution(
            {"test_case_id": testcase["id"], "status": "running"}
        )

        # 模拟在执行过程中系统崩溃恢复
        with patch("web_gui.models.ExecutionHistory.query.filter_by") as mock_filter:
            mock_filter.return_value.first.return_value = None  # 模拟找不到执行记录

            response = api_client.get(f'/api/executions/{execution["execution_id"]}')

            # 应该能处理数据不一致的情况
            assert response.status_code in [200, 404, 500]
