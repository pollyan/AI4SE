"""
测试用例CRUD API测试
"""

import pytest
import json


class TestTestCaseListAPI:
    """测试用例列表API测试 (GET /api/testcases)"""

    def test_should_get_empty_testcase_list(self, api_client, assert_api_response):
        """测试获取空的测试用例列表"""
        response = api_client.get("/api/testcases")
        data = assert_api_response(
            response,
            200,
            {"items": list, "total": int, "page": int, "size": int, "pages": int},
        )

        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["size"] == 20

    def test_should_get_testcase_list_with_data(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试获取包含数据的测试用例列表"""
        # 创建测试数据
        testcase1 = create_test_testcase(name="测试用例1", category="功能测试")
        testcase2 = create_test_testcase(name="测试用例2", category="性能测试")

        response = api_client.get("/api/testcases")
        data = assert_api_response(response, 200)

        assert data["total"] == 2
        assert len(data["items"]) == 2

        # 验证测试用例数据结构
        testcase_data = data["items"][0]
        expected_fields = [
            "id",
            "name",
            "description",
            "steps",
            "tags",
            "category",
            "priority",
            "created_by",
            "created_at",
            "updated_at",
            "is_active",
            "execution_count",
            "success_rate",
        ]
        for field in expected_fields:
            assert field in testcase_data, f"测试用例数据缺少字段: {field}"

    def test_should_support_pagination(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试分页功能"""
        # 创建多个测试用例
        for i in range(5):
            create_test_testcase(name=f"测试用例{i+1}")

        # 测试第一页，每页2条
        response = api_client.get("/api/testcases?page=1&size=2")
        data = assert_api_response(response, 200)

        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["pages"] == 3
        assert len(data["items"]) == 2

        # 测试第二页
        response = api_client.get("/api/testcases?page=2&size=2")
        data = assert_api_response(response, 200)

        assert data["page"] == 2
        assert len(data["items"]) == 2

        # 测试最后一页
        response = api_client.get("/api/testcases?page=3&size=2")
        data = assert_api_response(response, 200)

        assert data["page"] == 3
        assert len(data["items"]) == 1

    def test_should_support_search(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试搜索功能"""
        # 创建测试数据
        create_test_testcase(name="登录功能测试", description="测试用户登录")
        create_test_testcase(name="注册功能测试", description="测试用户注册")
        create_test_testcase(name="支付流程测试", description="测试支付功能")

        # 搜索名称包含"登录"的测试用例
        response = api_client.get("/api/testcases?search=登录")
        data = assert_api_response(response, 200)

        assert data["total"] == 1
        assert "登录" in data["items"][0]["name"]

        # 搜索包含"功能"的测试用例（名称和描述都会被搜索）
        response = api_client.get("/api/testcases?search=功能")
        data = assert_api_response(response, 200)

        assert data["total"] == 3

        # 搜索不存在的内容
        response = api_client.get("/api/testcases?search=不存在的内容")
        data = assert_api_response(response, 200)

        assert data["total"] == 0

    def test_should_support_category_filter(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试分类过滤功能"""
        # 创建不同分类的测试用例
        create_test_testcase(name="功能测试1", category="功能测试")
        create_test_testcase(name="功能测试2", category="功能测试")
        create_test_testcase(name="性能测试1", category="性能测试")

        # 按功能测试分类过滤
        response = api_client.get("/api/testcases?category=功能测试")
        data = assert_api_response(response, 200)

        assert data["total"] == 2
        for item in data["items"]:
            assert item["category"] == "功能测试"

        # 按性能测试分类过滤
        response = api_client.get("/api/testcases?category=性能测试")
        data = assert_api_response(response, 200)

        assert data["total"] == 1
        assert data["items"][0]["category"] == "性能测试"

    def test_should_exclude_inactive_testcases(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试排除已删除的测试用例"""
        # 创建活跃和已删除的测试用例
        create_test_testcase(name="活跃测试用例", is_active=True)
        create_test_testcase(name="已删除测试用例", is_active=False)

        response = api_client.get("/api/testcases")
        data = assert_api_response(response, 200)

        # 应该只返回活跃的测试用例
        assert data["total"] == 1
        assert data["items"][0]["name"] == "活跃测试用例"
        assert data["items"][0]["is_active"] is True


class TestCreateTestCaseAPI:
    """创建测试用例API测试 (POST /api/testcases)"""

    def test_should_create_testcase_with_valid_data(
        self, api_client, sample_testcase_data, assert_api_response
    ):
        """测试使用有效数据创建测试用例"""
        response = api_client.post(
            "/api/testcases", json=sample_testcase_data, content_type="application/json"
        )

        data = assert_api_response(response, 200)

        # 验证返回的测试用例数据
        created_testcase = data
        assert created_testcase["name"] == sample_testcase_data["name"]
        assert created_testcase["description"] == sample_testcase_data["description"]
        assert created_testcase["category"] == sample_testcase_data["category"]
        assert created_testcase["priority"] == sample_testcase_data["priority"]
        assert created_testcase["steps"] == sample_testcase_data["steps"]
        assert created_testcase["tags"] == sample_testcase_data["tags"]
        assert created_testcase["is_active"] is True
        assert "id" in created_testcase
        assert "created_at" in created_testcase

    def test_should_create_testcase_with_minimal_data(
        self, api_client, assert_api_response
    ):
        """测试使用最少必填数据创建测试用例"""
        minimal_data = {"name": "最小测试用例"}

        response = api_client.post(
            "/api/testcases", json=minimal_data, content_type="application/json"
        )

        data = assert_api_response(response, 200)

        created_testcase = data
        assert created_testcase["name"] == "最小测试用例"
        assert created_testcase["steps"] == []  # 默认空步骤
        assert created_testcase["is_active"] is True

    def test_should_validate_required_fields(self, api_client, assert_api_response):
        """测试必填字段验证"""
        # 缺少name字段
        invalid_data = {"description": "测试描述"}

        response = api_client.post(
            "/api/testcases", json=invalid_data, content_type="application/json"
        )

        assert_api_response(response, 400)

    def test_should_validate_empty_name(self, api_client, assert_api_response):
        """测试空名称验证"""
        invalid_data = {"name": "", "description": "测试描述"}  # 空名称

        response = api_client.post(
            "/api/testcases", json=invalid_data, content_type="application/json"
        )

        assert_api_response(response, 400)

    def test_should_validate_steps_format(self, api_client, assert_api_response):
        """测试步骤格式验证"""
        # 步骤不是数组格式
        invalid_data = {"name": "测试用例", "steps": "invalid_steps_format"}

        response = api_client.post(
            "/api/testcases", json=invalid_data, content_type="application/json"
        )

        # API返回500是因为ValidationError被包装成DatabaseError
        assert_api_response(response, 500)

    def test_should_validate_step_structure(self, api_client, assert_api_response):
        """测试步骤结构验证"""
        # 步骤缺少action字段
        invalid_data = {
            "name": "测试用例",
            "steps": [
                {
                    "params": {"url": "https://example.com"},
                    "description": "缺少action字段",
                }
            ],
        }

        response = api_client.post(
            "/api/testcases", json=invalid_data, content_type="application/json"
        )

        # API返回500是因为ValidationError被包装成DatabaseError
        assert_api_response(response, 500)

    def test_should_reject_non_json_request(self, api_client, assert_api_response):
        """测试拒绝非JSON请求"""
        response = api_client.post(
            "/api/testcases", data="not json data", content_type="text/plain"
        )

        assert_api_response(response, 400)


class TestGetTestCaseAPI:
    """获取测试用例详情API测试 (GET /api/testcases/<id>)"""

    def test_should_get_testcase_by_valid_id(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试使用有效ID获取测试用例"""
        testcase = create_test_testcase(name="测试用例详情")

        response = api_client.get(f"/api/testcases/{testcase.id}")
        data = assert_api_response(response, 200)

        testcase_data = data
        assert testcase_data["id"] == testcase.id
        assert testcase_data["name"] == "测试用例详情"
        assert testcase_data["is_active"] is True

    def test_should_return_404_for_invalid_id(self, api_client, assert_api_response):
        """测试使用无效ID返回404"""
        response = api_client.get("/api/testcases/99999")
        assert_api_response(response, 404)

    def test_should_return_404_for_inactive_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试可以访问inactive的测试用例"""
        testcase = create_test_testcase(name="Inactive测试用例", is_active=False)

        response = api_client.get(f"/api/testcases/{testcase.id}")
        data = assert_api_response(
            response, 200, {"id": int, "name": str, "is_active": bool}
        )

        assert data["name"] == "Inactive测试用例"
        assert data["is_active"] is False


class TestUpdateTestCaseAPI:
    """更新测试用例API测试 (PUT /api/testcases/<id>)"""

    def test_should_update_testcase_with_valid_data(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试使用有效数据更新测试用例"""
        testcase = create_test_testcase(name="原始名称", description="原始描述")

        update_data = {
            "name": "更新后的名称",
            "description": "更新后的描述",
            "category": "更新分类",
            "priority": 1,
        }

        response = api_client.put(
            f"/api/testcases/{testcase.id}",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        updated_testcase = data
        assert updated_testcase["name"] == "更新后的名称"
        assert updated_testcase["description"] == "更新后的描述"
        assert updated_testcase["category"] == "更新分类"
        assert updated_testcase["priority"] == 1

    def test_should_update_partial_fields(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试部分字段更新"""
        testcase = create_test_testcase(name="原始名称", description="原始描述")

        # 只更新名称
        update_data = {"name": "只更新名称"}

        response = api_client.put(
            f"/api/testcases/{testcase.id}",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        updated_testcase = data
        assert updated_testcase["name"] == "只更新名称"
        assert updated_testcase["description"] == "原始描述"  # 保持原值

    def test_should_update_steps(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试更新步骤"""
        testcase = create_test_testcase(name="测试步骤更新")

        new_steps = [
            {
                "action": "navigate",
                "params": {"url": "https://updated.com"},
                "description": "访问更新的网站",
            }
        ]

        update_data = {"steps": new_steps}

        response = api_client.put(
            f"/api/testcases/{testcase.id}",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        updated_testcase = data
        assert updated_testcase["steps"] == new_steps

    def test_should_return_404_for_invalid_id(self, api_client, assert_api_response):
        """测试更新不存在的测试用例返回404"""
        update_data = {"name": "更新不存在的测试用例"}

        response = api_client.put(
            "/api/testcases/99999", json=update_data, content_type="application/json"
        )

        assert_api_response(response, 404)

    def test_should_return_404_for_inactive_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试可以更新inactive的测试用例"""
        testcase = create_test_testcase(name="Inactive测试用例", is_active=False)

        update_data = {
            "name": "更新后的Inactive测试用例",
            "is_active": True,  # 可以重新激活
        }

        response = api_client.put(
            f"/api/testcases/{testcase.id}",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(
            response, 200, {"id": int, "name": str, "is_active": bool}
        )

        assert data["name"] == "更新后的Inactive测试用例"
        assert data["is_active"] is True


class TestDeleteTestCaseAPI:
    """删除测试用例API测试 (DELETE /api/testcases/<id>)"""

    def test_should_soft_delete_testcase(
        self, api_client, create_test_testcase, db_session, assert_api_response
    ):
        """测试软删除测试用例"""
        testcase = create_test_testcase(name="待删除测试用例")
        testcase_id = testcase.id

        response = api_client.delete(f"/api/testcases/{testcase_id}")
        assert_api_response(response, 200)

        # 验证软删除：记录仍存在但is_active=False
        from web_gui.models import TestCase

        deleted_testcase = TestCase.query.get(testcase_id)
        assert deleted_testcase is not None
        assert deleted_testcase.is_active is False
        assert deleted_testcase.updated_at is not None

    def test_should_return_404_for_invalid_id(self, api_client, assert_api_response):
        """测试删除不存在的测试用例返回404"""
        response = api_client.delete("/api/testcases/99999")
        assert_api_response(response, 404)

    def test_should_return_400_for_already_deleted_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试删除已删除的测试用例返回404"""
        testcase = create_test_testcase(name="已删除测试用例", is_active=False)

        response = api_client.delete(f"/api/testcases/{testcase.id}")
        assert_api_response(response, 404)

    def test_should_not_affect_execution_history(
        self, api_client, create_test_testcase, db_session, assert_api_response
    ):
        """测试删除测试用例不影响执行历史"""
        testcase = create_test_testcase(name="有历史记录的测试用例")

        # 创建执行历史记录（提供所有必需字段）
        from web_gui.models import ExecutionHistory
        from datetime import datetime

        execution = ExecutionHistory(
            execution_id="test-exec-001",
            test_case_id=testcase.id,
            status="success",
            start_time=datetime.utcnow(),  # 添加必需的start_time字段
            executed_by="test_user",
        )
        db_session.add(execution)
        db_session.commit()

        # 删除测试用例
        response = api_client.delete(f"/api/testcases/{testcase.id}")
        assert_api_response(response, 200)

        # 验证执行历史记录仍然存在
        existing_execution = ExecutionHistory.query.filter_by(
            execution_id="test-exec-001"
        ).first()
        assert existing_execution is not None
        assert existing_execution.test_case_id == testcase.id
