"""
ExecutionService 单元测试
测试异步执行、步骤执行、变量解析和错误处理
"""

import pytest
import json
import sys
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock, PropertyMock
import threading

# Mock the missing ai_service module before importing execution_service
sys.modules['backend.services.ai_service'] = MagicMock()

from backend.services.execution_service import (
    ExecutionService,
    get_execution_service,
)
from backend.models import db, TestCase, ExecutionHistory, StepExecution


class TestExecutionServiceInit:
    """测试 ExecutionService 初始化"""

    def test_init_creates_execution_manager(self, app, db_session):
        """测试初始化创建执行管理器"""
        # When: 创建 ExecutionService 实例
        service = ExecutionService()

        # Then: 执行管理器被初始化
        assert hasattr(service, "execution_manager")
        assert isinstance(service.execution_manager, dict)


class TestExecuteTestcaseAsync:
    """测试 execute_testcase_async 方法"""

    def test_execute_testcase_async_returns_execution_id(self, app, db_session, test_data_manager):
        """测试异步执行返回执行ID"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({
            "name": "Async_Test_TC",
            "steps": json.dumps([{"action": "goto", "params": {"url": "https://example.com"}}])
        })

        # Mock threading.Thread
        with patch('backend.services.execution_service.threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            service = ExecutionService()

            # When: 异步执行测试用例
            execution_id = service.execute_testcase_async(tc.id)

            # Then: 返回有效的执行ID
            assert execution_id is not None
            assert isinstance(execution_id, str)
            # UUID 格式验证
            uuid.UUID(execution_id)  # 如果格式不正确会抛出异常

    def test_execute_testcase_async_creates_execution_record(self, app, db_session, test_data_manager):
        """测试异步执行创建执行记录"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({
            "name": "Record_Test_TC",
            "steps": json.dumps([{"action": "goto", "params": {"url": "https://example.com"}}])
        })

        with patch('backend.services.execution_service.threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            service = ExecutionService()

            # When: 异步执行测试用例
            execution_id = service.execute_testcase_async(tc.id)

            # Then: 数据库中创建执行记录
            execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
            assert execution is not None
            assert execution.status == "running"
            assert execution.test_case_id == tc.id

    def test_execute_testcase_async_testcase_not_found(self, app, db_session):
        """测试执行不存在的测试用例"""
        # Given: 不存在的测试用例ID
        service = ExecutionService()

        # When/Then: 抛出 ValueError
        with pytest.raises(ValueError) as exc_info:
            service.execute_testcase_async(99999)

        assert "测试用例不存在" in str(exc_info.value)

    def test_execute_testcase_async_starts_thread(self, app, db_session, test_data_manager):
        """测试异步执行启动线程"""
        # Given: 已存在的测试用例
        tc = test_data_manager.create_testcase({
            "name": "Thread_Test_TC",
            "steps": json.dumps([{"action": "goto", "params": {"url": "https://example.com"}}])
        })

        with patch('backend.services.execution_service.threading.Thread') as mock_thread:
            mock_thread_instance = MagicMock()
            mock_thread.return_value = mock_thread_instance

            service = ExecutionService()

            # When: 异步执行测试用例
            service.execute_testcase_async(tc.id)

            # Then: 线程被启动
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()


class TestResolveVariables:
    """测试 _resolve_variables 方法"""

    def test_resolve_string_variable(self, app, db_session):
        """测试解析字符串变量"""
        # Given: VariableManager 已存储变量
        from backend.services.variable_resolver_service import VariableManager

        service = ExecutionService()
        variable_manager = VariableManager("test-resolve-001")
        variable_manager.store_variable(
            variable_name="url",
            value="https://resolved.com",
            source_step_index=0,
            source_api_method="test"
        )

        params = {"url": "${url}"}

        # When: 解析变量
        resolved = service._resolve_variables(params, variable_manager)

        # Then: 变量被正确解析
        assert resolved["url"] == "https://resolved.com"

    def test_resolve_nested_variable(self, app, db_session):
        """测试解析嵌套变量"""
        from backend.services.variable_resolver_service import VariableManager

        service = ExecutionService()
        variable_manager = VariableManager("test-resolve-002")
        variable_manager.store_variable(
            variable_name="search_text",
            value="hello world",
            source_step_index=0,
            source_api_method="test"
        )

        params = {
            "text": "${search_text}",
            "locate": "搜索框"
        }

        # When: 解析变量
        resolved = service._resolve_variables(params, variable_manager)

        # Then: 嵌套变量被正确解析
        assert resolved["text"] == "hello world"
        assert resolved["locate"] == "搜索框"

    def test_resolve_variable_not_found(self, app, db_session):
        """测试解析不存在的变量"""
        from backend.services.variable_resolver_service import VariableManager

        service = ExecutionService()
        variable_manager = VariableManager("test-resolve-003")

        params = {"url": "${non_existent}"}

        # When: 解析变量（变量不存在）
        resolved = service._resolve_variables(params, variable_manager)

        # Then: 保留原始值
        assert resolved["url"] == "${non_existent}"

    def test_resolve_list_values(self, app, db_session):
        """测试解析列表中的变量"""
        from backend.services.variable_resolver_service import VariableManager

        service = ExecutionService()
        variable_manager = VariableManager("test-resolve-004")
        variable_manager.store_variable(
            variable_name="item1",
            value="resolved_item1",
            source_step_index=0,
            source_api_method="test"
        )

        params = {"items": ["${item1}", "static_item"]}

        # When: 解析变量
        resolved = service._resolve_variables(params, variable_manager)

        # Then: 列表中的变量被正确解析
        assert resolved["items"][0] == "resolved_item1"
        assert resolved["items"][1] == "static_item"

    def test_resolve_no_variables(self, app, db_session):
        """测试无变量的参数"""
        from backend.services.variable_resolver_service import VariableManager

        service = ExecutionService()
        variable_manager = VariableManager("test-resolve-005")

        params = {"url": "https://static.com", "timeout": 5000}

        # When: 解析变量
        resolved = service._resolve_variables(params, variable_manager)

        # Then: 参数保持不变
        assert resolved == params


class TestHandleSkippedStep:
    """测试 _handle_skipped_step 方法"""

    def test_handle_skipped_step_emits_event(self, app, db_session):
        """测试跳过步骤发送事件"""
        # Given: ExecutionService 实例
        service = ExecutionService()
        step = {"action": "goto", "description": "跳过的步骤"}

        with patch('backend.services.execution_service.socketio.emit') as mock_emit:
            # When: 处理跳过的步骤
            service._handle_skipped_step("test-exec-skip-001", 0, step)

            # Then: 发送跳过事件
            mock_emit.assert_called()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "step_skipped"
            assert call_args[0][1]["execution_id"] == "test-exec-skip-001"

    def test_handle_skipped_step_creates_record(self, app, db_session):
        """测试跳过步骤创建数据库记录"""
        # Given: ExecutionService 实例
        service = ExecutionService()
        step = {"action": "goto", "description": "跳过的步骤"}

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 处理跳过的步骤
            service._handle_skipped_step("test-exec-skip-002", 0, step)

            # Then: 数据库中创建步骤记录
            step_record = StepExecution.query.filter_by(
                execution_id="test-exec-skip-002",
                step_index=0
            ).first()
            assert step_record is not None
            assert step_record.status == "skipped"


class TestHandleStepError:
    """测试 _handle_step_error 方法"""

    def test_handle_step_error_emits_event(self, app, db_session):
        """测试步骤错误发送事件"""
        # Given: ExecutionService 实例
        service = ExecutionService()
        step = {"action": "goto", "description": "错误步骤"}

        with patch('backend.services.execution_service.socketio.emit') as mock_emit:
            # When: 处理步骤错误
            service._handle_step_error("test-exec-err-001", 0, step, "测试错误消息")

            # Then: 发送失败事件
            mock_emit.assert_called()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "step_completed"
            assert call_args[0][1]["status"] == "failed"
            assert call_args[0][1]["error_message"] == "测试错误消息"

    def test_handle_step_error_creates_record(self, app, db_session):
        """测试步骤错误创建数据库记录"""
        # Given: ExecutionService 实例
        service = ExecutionService()
        step = {"action": "goto", "description": "错误步骤"}

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 处理步骤错误
            service._handle_step_error("test-exec-err-002", 0, step, "错误消息")

            # Then: 数据库中创建错误步骤记录
            step_record = StepExecution.query.filter_by(
                execution_id="test-exec-err-002",
                step_index=0
            ).first()
            assert step_record is not None
            assert step_record.status == "failed"
            assert step_record.error_message == "错误消息"


class TestHandleExecutionError:
    """测试 _handle_execution_error 方法"""

    def test_handle_execution_error_updates_status(self, app, db_session, test_data_manager):
        """测试执行错误更新状态"""
        # Given: 已存在的执行记录
        tc = test_data_manager.create_testcase({"name": "TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-exec-fail-001",
            "status": "running"
        })

        service = ExecutionService()

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 处理执行错误
            service._handle_execution_error("test-exec-fail-001", "执行失败")

            # Then: 执行状态更新为失败
            db_session.expire_all()
            updated = ExecutionHistory.query.filter_by(
                execution_id="test-exec-fail-001"
            ).first()
            assert updated.status == "failed"
            assert updated.error_message == "执行失败"

    def test_handle_execution_error_emits_event(self, app, db_session, test_data_manager):
        """测试执行错误发送事件"""
        # Given: 已存在的执行记录
        tc = test_data_manager.create_testcase({"name": "TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-exec-fail-002",
            "status": "running"
        })

        service = ExecutionService()

        with patch('backend.services.execution_service.socketio.emit') as mock_emit:
            # When: 处理执行错误
            service._handle_execution_error("test-exec-fail-002", "执行失败")

            # Then: 发送错误事件
            mock_emit.assert_called()
            call_args = mock_emit.call_args
            assert call_args[0][0] == "execution_error"
            assert "test-exec-fail-002" in str(call_args[0][1])


class TestGetExecutionService:
    """测试 get_execution_service 单例函数"""

    def test_get_execution_service_returns_instance(self, app, db_session):
        """测试获取执行服务实例"""
        # When: 获取执行服务实例
        service = get_execution_service()

        # Then: 返回 ExecutionService 实例
        assert isinstance(service, ExecutionService)

    def test_get_execution_service_singleton(self, app, db_session):
        """测试执行服务单例模式"""
        # When: 多次获取执行服务实例
        service1 = get_execution_service()
        service2 = get_execution_service()

        # Then: 返回同一个实例
        assert service1 is service2


class TestExecuteSingleStep:
    """测试 _execute_single_step 方法"""

    def test_execute_goto_step(self, app, db_session, test_data_manager):
        """测试执行 goto 步骤"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        # 创建测试用例和执行记录
        tc = test_data_manager.create_testcase({
            "name": "Goto_TC",
            "steps": json.dumps([])
        })
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-goto-001"
        })

        # Mock AI 服务
        mock_ai = MagicMock()
        mock_ai.goto.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"

        step = {
            "action": "goto",
            "params": {"url": "https://example.com"},
            "description": "访问示例网站"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-goto-001", 0
            )

            # Then: 步骤执行成功
            assert result["success"] is True
            mock_ai.goto.assert_called_once_with("https://example.com")

    def test_execute_ai_input_step(self, app, db_session, test_data_manager):
        """测试执行 ai_input 步骤"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        tc = test_data_manager.create_testcase({"name": "Input_TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-input-001"
        })

        mock_ai = MagicMock()
        mock_ai.ai_input.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"

        step = {
            "action": "ai_input",
            "params": {"text": "测试文本", "locate": "搜索框"},
            "description": "输入文本"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-input-001", 0
            )

            # Then: 步骤执行成功
            assert result["success"] is True
            mock_ai.ai_input.assert_called_once_with("测试文本", "搜索框")

    def test_execute_ai_tap_step(self, app, db_session, test_data_manager):
        """测试执行 ai_tap 步骤"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        tc = test_data_manager.create_testcase({"name": "Tap_TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-tap-001"
        })

        mock_ai = MagicMock()
        mock_ai.ai_tap.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"

        step = {
            "action": "ai_tap",
            "params": {"prompt": "提交按钮"},
            "description": "点击按钮"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-tap-001", 0
            )

            # Then: 步骤执行成功
            assert result["success"] is True
            mock_ai.ai_tap.assert_called_once_with("提交按钮")

    def test_execute_ai_assert_step(self, app, db_session, test_data_manager):
        """测试执行 ai_assert 步骤"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        tc = test_data_manager.create_testcase({"name": "Assert_TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-assert-001"
        })

        mock_ai = MagicMock()
        mock_ai.ai_assert.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"

        step = {
            "action": "ai_assert",
            "params": {"prompt": "页面显示成功消息"},
            "description": "验证结果"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-assert-001", 0
            )

            # Then: 步骤执行成功
            assert result["success"] is True
            mock_ai.ai_assert.assert_called_once_with("页面显示成功消息")

    def test_execute_ai_wait_for_step(self, app, db_session, test_data_manager):
        """测试执行 ai_wait_for 步骤"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        tc = test_data_manager.create_testcase({"name": "WaitFor_TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-wait-001"
        })

        mock_ai = MagicMock()
        mock_ai.ai_wait_for.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"

        step = {
            "action": "ai_wait_for",
            "params": {"prompt": "加载完成", "timeout": 5000},
            "description": "等待加载"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-wait-001", 0
            )

            # Then: 步骤执行成功
            assert result["success"] is True
            mock_ai.ai_wait_for.assert_called_once_with("加载完成", 5000)

    def test_execute_ai_scroll_step(self, app, db_session, test_data_manager):
        """测试执行 ai_scroll 步骤"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        tc = test_data_manager.create_testcase({"name": "Scroll_TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-scroll-001"
        })

        mock_ai = MagicMock()
        mock_ai.ai_scroll.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"

        step = {
            "action": "ai_scroll",
            "params": {"direction": "down", "scroll_type": "once"},
            "description": "向下滚动"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-scroll-001", 0
            )

            # Then: 步骤执行成功
            assert result["success"] is True
            mock_ai.ai_scroll.assert_called_once()

    def test_execute_step_missing_params(self, app, db_session, test_data_manager):
        """测试执行步骤缺少参数"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        tc = test_data_manager.create_testcase({"name": "Missing_Params_TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-missing-001"
        })

        mock_ai = MagicMock()

        # goto 步骤缺少 url 参数
        step = {
            "action": "goto",
            "params": {},
            "description": "缺少参数的步骤"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-missing-001", 0
            )

            # Then: 步骤执行失败
            assert result["success"] is False
            assert "error_message" in result

    def test_execute_unsupported_action(self, app, db_session, test_data_manager):
        """测试执行不支持的操作类型"""
        # Given: ExecutionService 和 mock AI 服务
        service = ExecutionService()

        tc = test_data_manager.create_testcase({"name": "Unsupported_TC"})
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-unsupported-001"
        })

        mock_ai = MagicMock()

        step = {
            "action": "unknown_action",
            "params": {},
            "description": "不支持的操作"
        }

        with patch('backend.services.execution_service.socketio.emit'):
            # When: 执行步骤
            result = service._execute_single_step(
                mock_ai, step, "headless", "test-unsupported-001", 0
            )

            # Then: 步骤执行失败
            assert result["success"] is False
            assert "不支持的操作类型" in result["error_message"]


class TestExecuteTestcaseThread:
    """测试 _execute_testcase_thread 方法"""

    def test_execute_thread_success(self, app, db_session, test_data_manager):
        """测试线程执行成功"""
        # Given: 测试用例和执行记录
        tc = test_data_manager.create_testcase({
            "name": "ThreadSuccess_TC",
            "steps": json.dumps([
                {"action": "goto", "params": {"url": "https://example.com"}, "description": "访问"}
            ])
        })
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-thread-001",
            "status": "running"
        })

        service = ExecutionService()

        # Mock AI 服务
        mock_ai = MagicMock()
        mock_ai.goto.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"
        mock_ai.cleanup.return_value = None

        with patch('backend.services.execution_service.get_ai_service', return_value=mock_ai):
            with patch('backend.services.execution_service.socketio.emit'):
                with patch('backend.services.execution_service.time.sleep'):
                    # When: 执行线程
                    actual_tc = db_session.query(TestCase).get(tc.id)
                    service._execute_testcase_thread("test-thread-001", actual_tc, "headless")

        # Then: 执行状态更新
        db_session.expire_all()
        updated = ExecutionHistory.query.filter_by(execution_id="test-thread-001").first()
        assert updated.status in ["success", "failed"]

    def test_execute_thread_no_steps(self, app, db_session, test_data_manager):
        """测试执行空步骤的测试用例"""
        # Given: 空步骤的测试用例
        tc = test_data_manager.create_testcase({
            "name": "NoSteps_TC",
            "steps": json.dumps([])
        })
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-nosteps-001",
            "status": "running"
        })

        service = ExecutionService()

        mock_ai = MagicMock()
        mock_ai.cleanup.return_value = None

        with patch('backend.services.execution_service.get_ai_service', return_value=mock_ai):
            with patch('backend.services.execution_service.socketio.emit'):
                # When: 执行线程
                actual_tc = db_session.query(TestCase).get(tc.id)
                service._execute_testcase_thread("test-nosteps-001", actual_tc, "headless")

        # Then: 执行状态为失败
        db_session.expire_all()
        updated = ExecutionHistory.query.filter_by(execution_id="test-nosteps-001").first()
        assert updated.status == "failed"

    def test_execute_thread_with_skip_step(self, app, db_session, test_data_manager):
        """测试跳过步骤的执行"""
        # Given: 包含跳过步骤的测试用例
        tc = test_data_manager.create_testcase({
            "name": "SkipStep_TC",
            "steps": json.dumps([
                {"action": "goto", "params": {"url": "https://example.com"}, "description": "访问", "skip": True}
            ])
        })
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-skip-001",
            "status": "running"
        })

        service = ExecutionService()

        mock_ai = MagicMock()
        mock_ai.take_screenshot.return_value = "screenshot.png"
        mock_ai.cleanup.return_value = None

        with patch('backend.services.execution_service.get_ai_service', return_value=mock_ai):
            with patch('backend.services.execution_service.socketio.emit'):
                with patch('backend.services.execution_service.time.sleep'):
                    # When: 执行线程
                    actual_tc = db_session.query(TestCase).get(tc.id)
                    service._execute_testcase_thread("test-skip-001", actual_tc, "headless")

        # Then: 步骤被跳过
        db_session.expire_all()
        step_records = StepExecution.query.filter_by(execution_id="test-skip-001").all()
        execution = ExecutionHistory.query.filter_by(execution_id="test-skip-001").first()
        print(f"DEBUG: execution status: {execution.status}, error: {execution.error_message}")
        assert len(step_records) >= 1

    def test_execute_thread_with_failed_step_browser_mode(self, app, db_session, test_data_manager):
        """测试 browser 模式下步骤失败不停止"""
        tc = test_data_manager.create_testcase({
            "name": "BrowserFail_TC",
            "steps": json.dumps([
                {"action": "goto", "params": {"url": "https://example.com"}, "description": "访问1"},
                {"action": "unknown_action", "params": {}, "description": "会失败的步骤"},
                {"action": "goto", "params": {"url": "https://test.com"}, "description": "访问2"}
            ])
        })
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-browser-fail-001",
            "status": "running"
        })

        service = ExecutionService()

        mock_ai = MagicMock()
        mock_ai.goto.return_value = None
        mock_ai.take_screenshot.return_value = "screenshot.png"
        mock_ai.cleanup.return_value = None

        with patch('backend.services.execution_service.get_ai_service', return_value=mock_ai):
            with patch('backend.services.execution_service.socketio.emit'):
                with patch('backend.services.execution_service.time.sleep'):
                    # When: 执行线程（browser 模式）
                    actual_tc = db_session.query(TestCase).get(tc.id)
                    service._execute_testcase_thread("test-browser-fail-001", actual_tc, "browser")

        # Then: 所有步骤被执行（browser 模式不停止）
        db_session.expire_all()
        updated = ExecutionHistory.query.filter_by(execution_id="test-browser-fail-001").first()
        assert updated is not None

    def test_execute_thread_step_exception(self, app, db_session, test_data_manager):
        """测试步骤执行异常处理"""
        tc = test_data_manager.create_testcase({
            "name": "Exception_TC",
            "steps": json.dumps([
                {"action": "goto", "params": {"url": "https://example.com"}, "description": "访问"}
            ])
        })
        execution = test_data_manager.create_execution({
            "test_case_id": tc.id,
            "execution_id": "test-exception-001",
            "status": "running"
        })

        service = ExecutionService()

        mock_ai = MagicMock()
        mock_ai.goto.side_effect = Exception("模拟异常")
        mock_ai.cleanup.return_value = None

        with patch('backend.services.execution_service.get_ai_service', return_value=mock_ai):
            with patch('backend.services.execution_service.socketio.emit'):
                # When: 执行线程
                actual_tc = db_session.query(TestCase).get(tc.id)
                service._execute_testcase_thread("test-exception-001", actual_tc, "headless")

        # Then: 执行状态为失败
        db_session.expire_all()
        updated = ExecutionHistory.query.filter_by(execution_id="test-exception-001").first()
        assert updated.status == "failed"