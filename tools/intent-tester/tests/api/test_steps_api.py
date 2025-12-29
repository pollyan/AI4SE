"""
测试用例步骤管理API测试
"""

import pytest
import json


class TestGetStepsAPI:
    """获取步骤列表API测试 (GET /api/testcases/<testcase_id>/steps)"""

    def test_should_get_empty_steps_list(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试获取空的步骤列表"""
        # 创建没有步骤的测试用例
        testcase = create_test_testcase(name="空步骤测试用例", steps="[]")

        response = api_client.get(f"/api/testcases/{testcase.id}/steps")
        data = assert_api_response(response, 200, {"steps": list, "total": int})

        assert data["total"] == 0
        assert data["steps"] == []

    def test_should_get_steps_list_with_data(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试获取包含步骤的列表"""
        testcase = create_testcase_with_steps()

        response = api_client.get(f"/api/testcases/{testcase.id}/steps")
        data = assert_api_response(response, 200)

        assert data["total"] > 0
        assert len(data["steps"]) > 0

        # 验证步骤数据结构
        step = data["steps"][0]
        required_fields = ["action", "params", "description"]
        for field in required_fields:
            assert field in step, f"步骤数据缺少字段: {field}"

    def test_should_return_404_for_nonexistent_testcase(
        self, api_client, assert_api_response
    ):
        """测试不存在的测试用例返回404"""
        response = api_client.get("/api/testcases/99999/steps")
        assert_api_response(response, 404)

    def test_should_return_404_for_inactive_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试已删除的测试用例返回404"""
        testcase = create_test_testcase(name="已删除测试用例", is_active=False)

        response = api_client.get(f"/api/testcases/{testcase.id}/steps")
        assert_api_response(response, 404)


class TestAddStepAPI:
    """添加步骤API测试 (POST /api/testcases/<testcase_id>/steps)"""

    def test_should_add_goto_step(
        self, api_client, create_test_testcase, sample_goto_step, assert_api_response
    ):
        """测试添加goto步骤"""
        testcase = create_test_testcase(
            name="测试添加goto步骤", steps="[]"
        )  # 确保开始时为空步骤

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=sample_goto_step,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        created_step = data["step"]
        assert created_step["action"] == sample_goto_step["action"]
        assert created_step["params"] == sample_goto_step["params"]
        assert created_step["description"] == sample_goto_step["description"]
        assert data["position"] == 0
        assert data["total_steps"] == 1

    def test_should_add_ai_input_step(
        self,
        api_client,
        create_test_testcase,
        sample_ai_input_step,
        assert_api_response,
    ):
        """测试添加ai_input步骤"""
        testcase = create_test_testcase(name="测试添加ai_input步骤")

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=sample_ai_input_step,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        created_step = data["step"]
        assert created_step["action"] == "ai_input"
        assert "locate" in created_step["params"]
        assert "text" in created_step["params"]

    def test_should_add_ai_tap_step(
        self, api_client, create_test_testcase, sample_ai_tap_step, assert_api_response
    ):
        """测试添加ai_tap步骤"""
        testcase = create_test_testcase(name="测试添加ai_tap步骤")

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=sample_ai_tap_step,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        created_step = data["step"]
        assert created_step["action"] == "ai_tap"
        assert "locate" in created_step["params"]

    def test_should_add_ai_assert_step(
        self,
        api_client,
        create_test_testcase,
        sample_ai_assert_step,
        assert_api_response,
    ):
        """测试添加ai_assert步骤"""
        testcase = create_test_testcase(name="测试添加ai_assert步骤")

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=sample_ai_assert_step,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        created_step = data["step"]
        assert created_step["action"] == "ai_assert"
        assert "prompt" in created_step["params"]

    def test_should_insert_step_at_specific_position(
        self,
        api_client,
        create_testcase_with_steps,
        sample_goto_step,
        assert_api_response,
    ):
        """测试在指定位置插入步骤"""
        testcase = create_testcase_with_steps(step_count=3)

        # 在位置1插入新步骤
        new_step = sample_goto_step.copy()
        new_step["position"] = 1

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=new_step,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        assert data["position"] == 1
        assert data["total_steps"] == 4  # 3 + 1

    def test_should_validate_required_action_field(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试验证必需的action字段"""
        testcase = create_test_testcase(name="测试action字段验证")

        invalid_step = {
            "params": {"url": "https://example.com"},
            "description": "缺少action字段",
        }

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=invalid_step,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_validate_action_type(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试验证动作类型"""
        testcase = create_test_testcase(name="测试动作类型验证")

        invalid_step = {
            "action": "invalid_action",
            "params": {},
            "description": "无效的动作类型",
        }

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=invalid_step,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_validate_goto_requires_url(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试验证goto动作需要url参数"""
        testcase = create_test_testcase(name="测试goto参数验证")

        invalid_step = {
            "action": "goto",
            "params": {},  # 缺少url参数
            "description": "goto缺少url参数",
        }

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=invalid_step,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_validate_ai_actions_require_prompt_or_locate(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试验证AI动作需要prompt或locate参数"""
        testcase = create_test_testcase(name="测试AI动作参数验证")

        invalid_step = {
            "action": "ai_input",
            "params": {},  # 缺少prompt或locate参数
            "description": "ai_input缺少必需参数",
        }

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=invalid_step,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_return_404_for_nonexistent_testcase(
        self, api_client, sample_goto_step, assert_api_response
    ):
        """测试不存在的测试用例返回404"""
        response = api_client.post(
            "/api/testcases/99999/steps",
            json=sample_goto_step,
            content_type="application/json",
        )

        assert_api_response(response, 404)

    def test_should_return_404_for_inactive_testcase(
        self, api_client, create_test_testcase, sample_goto_step, assert_api_response
    ):
        """测试已删除的测试用例返回404"""
        testcase = create_test_testcase(name="已删除测试用例", is_active=False)

        response = api_client.post(
            f"/api/testcases/{testcase.id}/steps",
            json=sample_goto_step,
            content_type="application/json",
        )

        assert_api_response(response, 404)


class TestUpdateStepAPI:
    """更新步骤API测试 (PUT /api/testcases/<testcase_id>/steps/<step_index>)"""

    def test_should_update_step_action(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试更新步骤的动作"""
        testcase = create_testcase_with_steps()

        update_data = {"action": "ai_tap"}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/0",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        assert data["step"]["action"] == "ai_tap"
        assert data["index"] == 0

    def test_should_update_step_params(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试更新步骤的参数"""
        testcase = create_testcase_with_steps()

        new_params = {"url": "https://updated-example.com", "timeout": 5000}

        update_data = {"params": new_params}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/0",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        assert data["step"]["params"] == new_params

    def test_should_update_step_description(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试更新步骤的描述"""
        testcase = create_testcase_with_steps()

        update_data = {"description": "更新后的步骤描述"}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/0",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        assert data["step"]["description"] == "更新后的步骤描述"

    def test_should_update_step_required_flag(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试更新步骤的必需标志"""
        testcase = create_testcase_with_steps()

        update_data = {"required": False}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/0",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        assert data["step"]["required"] is False

    def test_should_update_multiple_fields(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试同时更新多个字段"""
        testcase = create_testcase_with_steps()

        update_data = {
            "action": "ai_assert",
            "params": {"prompt": "验证页面内容"},
            "description": "验证步骤",
            "required": True,
        }

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/0",
            json=update_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        step = data["step"]
        assert step["action"] == "ai_assert"
        assert step["params"] == {"prompt": "验证页面内容"}
        assert step["description"] == "验证步骤"
        assert step["required"] is True

    def test_should_return_400_for_invalid_step_index(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试无效步骤索引返回400"""
        testcase = create_testcase_with_steps(step_count=2)

        update_data = {"description": "更新不存在的步骤"}

        # 尝试更新索引为5的步骤（超出范围）
        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/5",
            json=update_data,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_return_404_for_negative_step_index(
        self, api_client, create_testcase_with_steps
    ):
        """测试负数步骤索引返回404（Flask路由不接受负数）"""
        testcase = create_testcase_with_steps()

        update_data = {"description": "负数索引测试"}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/-1",
            json=update_data,
            content_type="application/json",
        )

        # Flask路由不匹配负数，返回HTML格式的404
        assert response.status_code == 404

    def test_should_return_404_for_nonexistent_testcase(
        self, api_client, assert_api_response
    ):
        """测试不存在的测试用例返回404"""
        update_data = {"description": "更新不存在测试用例的步骤"}

        response = api_client.put(
            "/api/testcases/99999/steps/0",
            json=update_data,
            content_type="application/json",
        )

        assert_api_response(response, 404)

    def test_should_return_404_for_inactive_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试已删除的测试用例返回404"""
        testcase = create_test_testcase(name="已删除测试用例", is_active=False)

        update_data = {"description": "更新已删除测试用例的步骤"}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/0",
            json=update_data,
            content_type="application/json",
        )

        assert_api_response(response, 404)


class TestDeleteStepAPI:
    """删除步骤API测试 (DELETE /api/testcases/<testcase_id>/steps/<step_index>)"""

    def test_should_delete_step(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试删除步骤"""
        testcase = create_testcase_with_steps(step_count=3)

        response = api_client.delete(f"/api/testcases/{testcase.id}/steps/1")
        data = assert_api_response(response, 200)

        assert "deleted_step" in data
        assert data["remaining_steps"] == 2

    def test_should_delete_first_step(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试删除第一个步骤"""
        testcase = create_testcase_with_steps(step_count=2)

        response = api_client.delete(f"/api/testcases/{testcase.id}/steps/0")
        data = assert_api_response(response, 200)

        assert data["remaining_steps"] == 1

    def test_should_delete_last_step(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试删除最后一个步骤"""
        testcase = create_testcase_with_steps(step_count=3)

        response = api_client.delete(f"/api/testcases/{testcase.id}/steps/2")
        data = assert_api_response(response, 200)

        assert data["remaining_steps"] == 2

    def test_should_return_correct_deleted_step_data(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试返回正确的删除步骤数据"""
        testcase = create_testcase_with_steps()

        # 先获取原始步骤数据
        get_response = api_client.get(f"/api/testcases/{testcase.id}/steps")
        original_steps = get_response.get_json()["data"]["steps"]

        # 删除第一个步骤
        response = api_client.delete(f"/api/testcases/{testcase.id}/steps/0")
        data = assert_api_response(response, 200)

        # 验证删除的步骤数据
        deleted_step = data["deleted_step"]
        assert deleted_step == original_steps[0]

    def test_should_return_400_for_invalid_step_index(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试无效步骤索引返回400"""
        testcase = create_testcase_with_steps(step_count=2)

        # 尝试删除索引为5的步骤（超出范围）
        response = api_client.delete(f"/api/testcases/{testcase.id}/steps/5")
        assert_api_response(response, 400)

    def test_should_return_404_for_negative_step_index(
        self, api_client, create_testcase_with_steps
    ):
        """测试负数步骤索引返回404（Flask路由不接受负数）"""
        testcase = create_testcase_with_steps()

        response = api_client.delete(f"/api/testcases/{testcase.id}/steps/-1")

        # Flask路由不匹配负数，返回HTML格式的404
        assert response.status_code == 404

    def test_should_return_404_for_nonexistent_testcase(
        self, api_client, assert_api_response
    ):
        """测试不存在的测试用例返回404"""
        response = api_client.delete("/api/testcases/99999/steps/0")
        assert_api_response(response, 404)

    def test_should_return_404_for_inactive_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试已删除的测试用例返回404"""
        testcase = create_test_testcase(name="已删除测试用例", is_active=False)

        response = api_client.delete(f"/api/testcases/{testcase.id}/steps/0")
        assert_api_response(response, 404)


class TestReorderStepsAPI:
    """重排序步骤API测试 (PUT /api/testcases/<testcase_id>/steps/reorder)"""

    def test_should_reorder_steps(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试重排序步骤"""
        testcase = create_testcase_with_steps(step_count=3)

        # 重新排序：将第三个步骤移到第一位
        reorder_data = {"step_orders": [2, 0, 1]}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        data = assert_api_response(response, 200)

        # 验证重排序后的步骤数量不变
        get_response = api_client.get(f"/api/testcases/{testcase.id}/steps")
        steps_data = assert_api_response(get_response, 200)
        assert steps_data["total"] == 3

    def test_should_reverse_step_order(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试反转步骤顺序"""
        testcase = create_testcase_with_steps(step_count=4)

        # 反转顺序
        reorder_data = {"step_orders": [3, 2, 1, 0]}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 200)

    def test_should_handle_single_step_reorder(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试单个步骤的重排序"""
        testcase = create_testcase_with_steps(step_count=1)

        reorder_data = {"step_orders": [0]}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 200)

    def test_should_validate_step_orders_length(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试验证步骤排序数据长度"""
        testcase = create_testcase_with_steps(step_count=3)

        # 提供错误长度的排序数据
        reorder_data = {"step_orders": [0, 1]}  # 只有2个元素，但测试用例有3个步骤

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_validate_step_index_range(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试验证步骤索引范围"""
        testcase = create_testcase_with_steps(step_count=2)

        # 提供超出范围的索引
        reorder_data = {"step_orders": [0, 5]}  # 索引5超出范围

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_validate_negative_step_index(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试验证负数步骤索引"""
        testcase = create_testcase_with_steps(step_count=2)

        reorder_data = {"step_orders": [-1, 0]}  # 负数索引

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_require_step_orders_field(
        self, api_client, create_testcase_with_steps, assert_api_response
    ):
        """测试要求step_orders字段"""
        testcase = create_testcase_with_steps()

        # 缺少step_orders字段
        reorder_data = {}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 400)

    def test_should_handle_empty_steps_reorder(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试空步骤列表的重排序"""
        testcase = create_test_testcase(name="空步骤测试用例", steps="[]")

        reorder_data = {"step_orders": []}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 200)

    def test_should_return_404_for_nonexistent_testcase(
        self, api_client, assert_api_response
    ):
        """测试不存在的测试用例返回404"""
        reorder_data = {"step_orders": [0, 1]}

        response = api_client.put(
            "/api/testcases/99999/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 404)

    def test_should_return_404_for_inactive_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试已删除的测试用例返回404"""
        testcase = create_test_testcase(name="已删除测试用例", is_active=False)

        reorder_data = {"step_orders": []}

        response = api_client.put(
            f"/api/testcases/{testcase.id}/steps/reorder",
            json=reorder_data,
            content_type="application/json",
        )

        assert_api_response(response, 404)
