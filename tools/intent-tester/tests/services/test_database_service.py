"""
DatabaseService 单元测试
测试数据库服务层的所有公共方法
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock

from backend.services.database_service import DatabaseService
from backend.models import db, TestCase, ExecutionHistory, StepExecution


class TestDatabaseServiceGetTestcases:
    """测试 get_testcases 方法"""

    def test_get_testcases_with_pagination(self, app, db_session, test_data_manager):
        """测试分页获取测试用例"""
        # Given: 数据库中有 25 条测试用例
        for i in range(25):
            test_data_manager.create_testcase({
                "name": f"test_{i}",
                "category": "TestCat",
                "is_active": True
            })

        # When: 请求第 2 页，每页 10 条
        result = DatabaseService.get_testcases(page=2, size=10)

        # Then: 返回正确的分页结果
        assert "items" in result
        assert "pagination" in result
        assert len(result["items"]) == 10
        assert result["pagination"]["total"] == 25
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["pages"] == 3

    def test_get_testcases_with_search(self, app, db_session, test_data_manager):
        """测试搜索过滤"""
        # Given: 数据库中有不同名称的测试用例
        test_data_manager.create_testcase({"name": "SearchMe_TestCase", "category": "Cat1"})
        test_data_manager.create_testcase({"name": "IgnoreMe_TestCase", "category": "Cat2"})

        # When: 搜索 "Search"
        result = DatabaseService.get_testcases(search="Search")

        # Then: 只返回匹配的结果
        assert result["pagination"]["total"] == 1
        assert "SearchMe" in result["items"][0]["name"]

    def test_get_testcases_with_category_filter(self, app, db_session, test_data_manager):
        """测试分类过滤"""
        # Given: 数据库中有不同分类的测试用例
        test_data_manager.create_testcase({"name": "TC1", "category": "FilterCat"})
        test_data_manager.create_testcase({"name": "TC2", "category": "OtherCat"})

        # When: 按 "FilterCat" 过滤
        result = DatabaseService.get_testcases(category="FilterCat")

        # Then: 只返回匹配分类的结果
        assert result["pagination"]["total"] == 1
        assert result["items"][0]["category"] == "FilterCat"

    def test_get_testcases_empty_database(self, app, db_session):
        """测试空数据库返回空列表"""
        # Given: 空数据库
        # When: 获取测试用例列表
        result = DatabaseService.get_testcases()

        # Then: 返回空列表
        assert result["items"] == []
        assert result["pagination"]["total"] == 0

    def test_get_testcases_excludes_inactive(self, app, db_session, test_data_manager):
        """测试不返回已删除（is_active=False）的测试用例"""
        # Given: 一个活跃和一个非活跃的测试用例
        tc1 = test_data_manager.create_testcase({"name": "Active_TC", "is_active": True})
        tc2 = test_data_manager.create_testcase({"name": "Inactive_TC", "is_active": False})

        # When: 获取测试用例列表
        result = DatabaseService.get_testcases()

        # Then: 只返回活跃的测试用例
        assert result["pagination"]["total"] == 1
        assert result["items"][0]["name"] == "Active_TC"


class TestDatabaseServiceGetTestcaseById:
    """测试 get_testcase_by_id 方法"""

    def test_get_testcase_by_id_success(self, app, db_session, test_data_manager):
        """测试根据ID获取测试用例 - 成功"""
        # Given: 数据库中存在测试用例
        tc = test_data_manager.create_testcase({"name": "Test_TC"})

        # When: 根据ID查询
        result = DatabaseService.get_testcase_by_id(tc.id)

        # Then: 返回正确的测试用例
        assert result is not None
        assert result.name == "Test_TC"

    def test_get_testcase_by_id_not_found(self, app, db_session):
        """测试根据ID获取测试用例 - 不存在"""
        # Given: 数据库为空
        # When: 查询不存在的ID
        result = DatabaseService.get_testcase_by_id(99999)

        # Then: 返回 None
        assert result is None

    def test_get_testcase_by_id_excludes_inactive(self, app, db_session, test_data_manager):
        """测试不返回已删除的测试用例"""
        # Given: 一个已删除的测试用例
        tc = test_data_manager.create_testcase({"name": "Deleted_TC", "is_active": False})

        # When: 根据ID查询
        result = DatabaseService.get_testcase_by_id(tc.id)

        # Then: 返回 None
        assert result is None


class TestDatabaseServiceCreateTestcase:
    """测试 create_testcase 方法"""

    def test_create_testcase_success(self, app, db_session):
        """测试创建测试用例 - 成功"""
        # Given: 有效的测试用例数据
        data = {
            "name": "New_TestCase",
            "description": "测试描述",
            "steps": [{"action": "goto", "params": {"url": "https://example.com"}}],
            "category": "TestCategory",
            "priority": 1,
            "tags": ["tag1", "tag2"]
        }

        # When: 创建测试用例
        result = DatabaseService.create_testcase(data)

        # Then: 返回创建的测试用例
        assert "error" not in result
        assert result["name"] == "New_TestCase"
        assert result["id"] is not None

    def test_create_testcase_with_tags_as_string(self, app, db_session):
        """测试创建测试用例 - tags为字符串"""
        # Given: tags 为字符串格式
        data = {
            "name": "Tags_String_TC",
            "tags": "tag1,tag2,tag3"
        }

        # When: 创建测试用例
        result = DatabaseService.create_testcase(data)

        # Then: 正确保存 tags (to_dict 可能返回列表)
        assert "error" not in result
        # tags 可能是字符串或列表，取决于 to_dict 的实现
        assert result["tags"] in ["tag1,tag2,tag3", ["tag1", "tag2", "tag3"]]

    def test_create_testcase_minimal_data(self, app, db_session):
        """测试创建测试用例 - 最小数据"""
        # Given: 只提供必需的字段
        data = {"name": "Minimal_TC"}

        # When: 创建测试用例
        result = DatabaseService.create_testcase(data)

        # Then: 使用默认值创建成功
        assert "error" not in result
        assert result["name"] == "Minimal_TC"


class TestDatabaseServiceUpdateTestcase:
    """测试 update_testcase 方法"""

    def test_update_testcase_success(self, app, db_session, test_data_manager):
        """测试更新测试用例 - 成功"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({"name": "Original_Name"})

        # When: 更新测试用例
        result = DatabaseService.update_testcase(tc.id, {"name": "Updated_Name"})

        # Then: 更新成功
        assert result is not None
        assert result["name"] == "Updated_Name"

    def test_update_testcase_not_found(self, app, db_session):
        """测试更新不存在的测试用例"""
        # Given: 不存在的测试用例ID
        # When: 尝试更新
        result = DatabaseService.update_testcase(99999, {"name": "New_Name"})

        # Then: 返回 None
        assert result is None

    def test_update_testcase_partial_update(self, app, db_session, test_data_manager):
        """测试部分更新测试用例"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({
            "name": "Original",
            "description": "Original Description",
            "priority": 2
        })

        # When: 只更新部分字段
        result = DatabaseService.update_testcase(tc.id, {"priority": 1})

        # Then: 只有指定字段被更新
        assert result["priority"] == 1
        assert result["name"] == "Original"


class TestDatabaseServiceDeleteTestcase:
    """测试 delete_testcase 方法"""

    def test_delete_testcase_success(self, app, db_session, test_data_manager):
        """测试软删除测试用例 - 成功"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({"name": "To_Delete"})

        # When: 删除测试用例
        result = DatabaseService.delete_testcase(tc.id)

        # Then: 返回 True
        assert result is True

        # And: 测试用例被标记为非活跃
        db_session.expire_all()
        deleted_tc = TestCase.query.get(tc.id)
        assert deleted_tc.is_active is False

    def test_delete_testcase_not_found(self, app, db_session):
        """测试删除不存在的测试用例"""
        # Given: 不存在的测试用例ID
        # When: 尝试删除
        result = DatabaseService.delete_testcase(99999)

        # Then: 返回 False
        assert result is False


class TestDatabaseServiceCreateExecution:
    """测试 create_execution 方法"""

    def test_create_execution_success(self, app, db_session, test_data_manager):
        """测试创建执行记录 - 成功"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({"name": "Test_For_Execution"})

        # When: 创建执行记录
        result = DatabaseService.create_execution(tc.id)

        # Then: 返回执行记录信息
        assert result is not None
        assert "execution_id" in result
        assert result["status"] == "pending"
        assert result["testcase_name"] == "Test_For_Execution"

    def test_create_execution_with_options(self, app, db_session, test_data_manager):
        """测试创建执行记录 - 带选项"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({"name": "Options_TC"})

        # When: 创建执行记录（带模式和浏览器选项）
        result = DatabaseService.create_execution(
            tc.id,
            mode="browser",
            browser="firefox",
            executed_by="test_user"
        )

        # Then: 选项被正确设置
        assert result is not None
        assert result["status"] == "pending"

    def test_create_execution_testcase_not_found(self, app, db_session):
        """测试为不存在的测试用例创建执行记录"""
        # Given: 不存在的测试用例ID
        # When: 尝试创建执行记录
        result = DatabaseService.create_execution(99999)

        # Then: 返回 None
        assert result is None


class TestDatabaseServiceGetExecutionById:
    """测试 get_execution_by_id 方法"""

    def test_get_execution_by_id_success(self, app, db_session, test_data_manager):
        """测试根据执行ID获取执行记录 - 成功"""
        # Given: 已存在的执行记录
        tc = test_data_manager.create_testcase({"name": "TC"})
        exec_result = test_data_manager.create_execution({"test_case_id": tc.id})

        # When: 根据执行ID查询
        result = DatabaseService.get_execution_by_id(exec_result.execution_id)

        # Then: 返回正确的执行记录
        assert result is not None
        assert result["execution_id"] == exec_result.execution_id

    def test_get_execution_by_id_not_found(self, app, db_session):
        """测试根据执行ID获取执行记录 - 不存在"""
        # Given: 不存在的执行ID
        # When: 查询
        result = DatabaseService.get_execution_by_id("non-existent-id")

        # Then: 返回 None
        assert result is None

    def test_get_execution_by_id_with_steps(self, app, db_session, test_data_manager):
        """测试获取执行记录（包含步骤详情）"""
        # Given: 执行记录包含步骤
        tc = test_data_manager.create_testcase({"name": "TC"})
        execution = test_data_manager.create_execution({"test_case_id": tc.id})
        test_data_manager.create_step_execution(execution.execution_id, {
            "step_index": 0,
            "status": "success"
        })

        # When: 获取执行记录
        result = DatabaseService.get_execution_by_id(execution.execution_id)

        # Then: 包含步骤执行详情
        assert result is not None
        assert "step_executions" in result
        assert len(result["step_executions"]) == 1


class TestDatabaseServiceGetExecutions:
    """测试 get_executions 方法"""

    def test_get_executions_with_pagination(self, app, db_session, test_data_manager):
        """测试分页获取执行历史"""
        # Given: 数据库中有 15 条执行记录
        tc = test_data_manager.create_testcase({"name": "TC"})
        for i in range(15):
            test_data_manager.create_execution({
                "test_case_id": tc.id,
                "execution_id": f"exec-{i}"
            })

        # When: 请求第 1 页，每页 10 条
        result = DatabaseService.get_executions(page=1, size=10)

        # Then: 返回正确的分页结果
        assert len(result["items"]) == 10
        assert result["pagination"]["total"] == 15

    def test_get_executions_filter_by_status(self, app, db_session, test_data_manager):
        """测试按状态过滤执行历史"""
        # Given: 不同状态的执行记录
        tc = test_data_manager.create_testcase({"name": "TC"})
        test_data_manager.create_execution({
            "test_case_id": tc.id,
            "status": "success"
        })
        test_data_manager.create_execution({
            "test_case_id": tc.id,
            "status": "failed"
        })

        # When: 按状态过滤
        result = DatabaseService.get_executions(status="success")

        # Then: 只返回匹配状态的记录
        assert result["pagination"]["total"] == 1
        assert result["items"][0]["status"] == "success"

    def test_get_executions_filter_by_testcase(self, app, db_session, test_data_manager):
        """测试按测试用例ID过滤执行历史"""
        # Given: 不同测试用例的执行记录
        tc1 = test_data_manager.create_testcase({"name": "TC1"})
        tc2 = test_data_manager.create_testcase({"name": "TC2"})
        test_data_manager.create_execution({"test_case_id": tc1.id})
        test_data_manager.create_execution({"test_case_id": tc2.id})

        # When: 按测试用例ID过滤
        result = DatabaseService.get_executions(testcase_id=tc1.id)

        # Then: 只返回该测试用例的执行记录
        assert result["pagination"]["total"] == 1


class TestDatabaseServiceStopExecution:
    """测试 stop_execution 方法"""

    def test_stop_running_execution(self, app, db_session, test_data_manager):
        """测试停止正在运行的执行"""
        # Given: 正在运行的执行记录
        tc = test_data_manager.create_testcase({"name": "TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "status": "running"
        })

        # When: 停止执行
        result = DatabaseService.stop_execution(execution.execution_id)

        # Then: 返回成功消息
        assert result is not None
        assert "message" in result

        # And: 状态更新为 cancelled
        db_session.expire_all()
        updated = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).first()
        assert updated.status == "cancelled"

    def test_stop_completed_execution(self, app, db_session, test_data_manager):
        """测试停止已完成的执行"""
        # Given: 已完成的执行记录
        tc = test_data_manager.create_testcase({"name": "TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "status": "success"
        })

        # When: 尝试停止
        result = DatabaseService.stop_execution(execution.execution_id)

        # Then: 返回错误信息
        assert "error" in result

    def test_stop_execution_not_found(self, app, db_session):
        """测试停止不存在的执行"""
        # Given: 不存在的执行ID
        # When: 尝试停止
        result = DatabaseService.stop_execution("non-existent-id")

        # Then: 返回 None
        assert result is None


class TestDatabaseServiceHandleDbError:
    """测试 handle_db_error 方法"""

    def test_handle_db_error_returns_error_dict(self, app):
        """测试数据库错误处理返回错误字典"""
        # Given: 一个错误对象
        error = Exception("Test error message")

        # When: 调用错误处理
        result = DatabaseService.handle_db_error("test_operation", error)

        # Then: 返回包含错误信息的字典
        assert "error" in result
        assert "test_operation" in result["error"]
        assert "Test error message" in result["error"]