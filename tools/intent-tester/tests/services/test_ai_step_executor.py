"""
AIStepExecutor 单元测试
测试 AI 步骤执行器的执行、变量解析和 Mock 模式功能
"""

import pytest
import json
import sys
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from collections import OrderedDict

# Mock the midscene_framework module before importing ai_step_executor
mock_midscene = MagicMock()
mock_midscene.MidSceneDataExtractor = MagicMock()
mock_midscene.DataExtractionMethod = MagicMock()
mock_midscene.DataExtractionMethod.AI_QUERY = "aiQuery"
mock_midscene.DataExtractionMethod.AI_STRING = "aiString"
mock_midscene.DataExtractionMethod.AI_NUMBER = "aiNumber"
mock_midscene.DataExtractionMethod.AI_BOOLEAN = "aiBoolean"
mock_midscene.DataExtractionMethod.AI_ASK = "aiAsk"
mock_midscene.DataExtractionMethod.AI_LOCATE = "aiLocate"
mock_midscene.ExtractionRequest = MagicMock()
sys.modules['midscene_framework'] = mock_midscene
sys.modules['midscene_framework.validators'] = MagicMock()

from backend.services.ai_step_executor import (
    AIStepExecutor,
    StepExecutionResult,
)
from backend.services.variable_resolver_service import VariableManager


class TestStepExecutionResult:
    """测试 StepExecutionResult 数据类"""

    def test_create_success_result(self):
        """测试创建成功的执行结果"""
        result = StepExecutionResult(
            success=True,
            step_index=0,
            action="goto",
            description="访问网站"
        )

        assert result.success is True
        assert result.step_index == 0
        assert result.action == "goto"
        assert result.description == "访问网站"
        assert result.return_value is None
        assert result.error_message is None

    def test_create_failure_result(self):
        """测试创建失败的执行结果"""
        result = StepExecutionResult(
            success=False,
            step_index=1,
            action="ai_input",
            description="输入文本",
            error_message="缺少参数"
        )

        assert result.success is False
        assert result.error_message == "缺少参数"

    def test_create_result_with_return_value(self):
        """测试创建带返回值的执行结果"""
        result = StepExecutionResult(
            success=True,
            step_index=0,
            action="aiQuery",
            description="查询数据",
            return_value={"title": "测试标题"}
        )

        assert result.return_value == {"title": "测试标题"}


class TestAIStepExecutorInit:
    """测试 AIStepExecutor 初始化"""

    def test_init_default(self):
        """测试默认初始化"""
        # When: 创建执行器（不传参数）
        executor = AIStepExecutor()

        # Then: 使用默认值
        assert executor.mock_mode is False
        assert executor.midscene_client is None
        assert executor.data_extractor is not None

    def test_init_mock_mode(self):
        """测试 Mock 模式初始化"""
        # When: 创建 Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)

        # Then: Mock 模式启用
        assert executor.mock_mode is True

    def test_init_with_client(self):
        """测试带 MidScene 客户端初始化"""
        # Given: Mock 客户端
        mock_client = MagicMock()

        # When: 创建带客户端的执行器
        executor = AIStepExecutor(midscene_client=mock_client)

        # Then: 客户端被正确设置
        assert executor.midscene_client is mock_client

    def test_ai_extraction_methods_initialized(self):
        """测试 AI 提取方法初始化"""
        # When: 创建执行器
        executor = AIStepExecutor()

        # Then: AI 提取方法被正确初始化
        assert "aiQuery" in executor.ai_extraction_methods
        assert "aiString" in executor.ai_extraction_methods
        assert "aiNumber" in executor.ai_extraction_methods
        assert "aiBoolean" in executor.ai_extraction_methods


class TestExecuteStep:
    """测试 execute_step 方法"""

    @pytest.mark.asyncio
    async def test_execute_set_variable_step(self, app, db_session):
        """测试执行 set_variable 步骤"""
        # Given: Mock 模式执行器和变量管理器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True  # 跳过数据库记录
        variable_manager = VariableManager("test-set-var-001")

        step_config = {
            "action": "set_variable",
            "params": {"name": "test_var", "value": "test_value"},
            "description": "设置变量"
        }

        # When: 执行步骤
        result = await executor.execute_step(
            step_config, 0, "test-exec-001", variable_manager
        )

        # Then: 步骤执行成功
        assert result.success is True
        assert result.variable_assigned == "test_var"
        assert variable_manager.get_variable("test_var") == "test_value"

    @pytest.mark.asyncio
    async def test_execute_get_variable_step(self, app, db_session):
        """测试执行 get_variable 步骤"""
        # Given: Mock 模式执行器和已设置的变量
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True
        variable_manager = VariableManager("test-get-var-001")
        variable_manager.store_variable(
            variable_name="existing_var",
            value="existing_value",
            source_step_index=0,
            source_api_method="test"
        )

        step_config = {
            "action": "get_variable",
            "params": {"name": "existing_var"},
            "description": "获取变量"
        }

        # When: 执行步骤
        result = await executor.execute_step(
            step_config, 0, "test-exec-002", variable_manager
        )

        # Then: 步骤执行成功并返回变量值
        assert result.success is True
        assert result.return_value == "existing_value"

    @pytest.mark.asyncio
    async def test_execute_get_variable_not_found(self, app, db_session):
        """测试获取不存在的变量"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True
        variable_manager = VariableManager("test-get-var-002")

        step_config = {
            "action": "get_variable",
            "params": {"name": "non_existent"},
            "description": "获取不存在的变量"
        }

        # When: 执行步骤
        result = await executor.execute_step(
            step_config, 0, "test-exec-003", variable_manager
        )

        # Then: 步骤执行失败
        assert result.success is False
        assert "变量不存在" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_evaluate_javascript_mock(self, app, db_session):
        """测试 Mock 模式下执行 JavaScript"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True
        variable_manager = VariableManager("test-js-001")

        step_config = {
            "action": "evaluateJavaScript",
            "params": {"script": "return {title: document.title}"},
            "description": "执行 JavaScript"
        }

        # When: 执行步骤
        result = await executor.execute_step(
            step_config, 0, "test-exec-004", variable_manager
        )

        # Then: 返回 Mock 结果
        assert result.success is True
        assert result.return_value is not None

    @pytest.mark.asyncio
    async def test_execute_step_with_output_variable(self, app, db_session):
        """测试带输出变量的步骤执行"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True
        variable_manager = VariableManager("test-output-001")

        step_config = {
            "action": "set_variable",
            "params": {"name": "source_var", "value": "output_value"},
            "description": "设置变量",
            "output_variable": "output_var"
        }

        # When: 执行步骤
        result = await executor.execute_step(
            step_config, 0, "test-exec-005", variable_manager
        )

        # Then: 输出变量被正确设置
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_step_missing_params(self, app, db_session):
        """测试缺少参数的步骤执行"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True
        variable_manager = VariableManager("test-missing-001")

        # set_variable 缺少 name 参数
        step_config = {
            "action": "set_variable",
            "params": {"value": "some_value"},
            "description": "缺少参数的步骤"
        }

        # When: 执行步骤
        result = await executor.execute_step(
            step_config, 0, "test-exec-006", variable_manager
        )

        # Then: 步骤执行失败
        assert result.success is False
        assert result.error_message is not None


class TestProcessVariableReferences:
    """测试 _process_variable_references 方法"""

    def test_process_simple_reference(self, app, db_session):
        """测试处理简单变量引用"""
        # Given: 执行器和已设置的变量
        executor = AIStepExecutor()
        variable_manager = VariableManager("test-process-001")
        variable_manager.store_variable(
            variable_name="url",
            value="https://resolved.com",
            source_step_index=0,
            source_api_method="test"
        )

        params = {"url": "${url}"}

        # When: 处理变量引用
        resolved = executor._process_variable_references(params, variable_manager)

        # Then: 变量被正确解析
        assert resolved["url"] == "https://resolved.com"

    def test_process_nested_reference(self, app, db_session):
        """测试处理嵌套变量引用"""
        # Given: 执行器和已设置的变量
        executor = AIStepExecutor()
        variable_manager = VariableManager("test-process-002")
        variable_manager.store_variable(
            variable_name="text",
            value="hello",
            source_step_index=0,
            source_api_method="test"
        )

        params = {
            "input": "${text} world",
            "locate": "搜索框"
        }

        # When: 处理变量引用
        resolved = executor._process_variable_references(params, variable_manager)

        # Then: 变量被正确解析
        assert resolved["input"] == "hello world"
        assert resolved["locate"] == "搜索框"

    def test_process_list_references(self, app, db_session):
        """测试处理列表中的变量引用"""
        # Given: 执行器和已设置的变量
        executor = AIStepExecutor()
        variable_manager = VariableManager("test-process-003")
        variable_manager.store_variable(
            variable_name="item1",
            value="resolved_item1",
            source_step_index=0,
            source_api_method="test"
        )

        params = {"items": ["${item1}", "static_item"]}

        # When: 处理变量引用
        resolved = executor._process_variable_references(params, variable_manager)

        # Then: 列表中的变量被正确解析
        assert resolved["items"][0] == "resolved_item1"
        assert resolved["items"][1] == "static_item"

    def test_process_nonexistent_reference(self, app, db_session):
        """测试处理不存在的变量引用"""
        # Given: 执行器
        executor = AIStepExecutor()
        variable_manager = VariableManager("test-process-004")

        params = {"url": "${nonexistent}"}

        # When: 处理变量引用
        resolved = executor._process_variable_references(params, variable_manager)

        # Then: 保留原始引用
        assert resolved["url"] == "${nonexistent}"

    def test_process_no_references(self, app, db_session):
        """测试处理无变量引用的参数"""
        # Given: 执行器
        executor = AIStepExecutor()
        variable_manager = VariableManager("test-process-005")

        params = {"url": "https://static.com", "timeout": 5000}

        # When: 处理变量引用
        resolved = executor._process_variable_references(params, variable_manager)

        # Then: 参数保持不变
        assert resolved == params


class TestMockEvaluateJavaScript:
    """测试 _mock_evaluate_javascript 方法"""

    @pytest.mark.asyncio
    async def test_mock_return_object(self):
        """测试 Mock 返回对象"""
        executor = AIStepExecutor()

        script = "return {title: document.title, url: window.location.href}"
        result = await executor._mock_evaluate_javascript(script)

        assert isinstance(result, dict)
        assert "title" in result

    @pytest.mark.asyncio
    async def test_mock_return_array(self):
        """测试 Mock 返回数组"""
        executor = AIStepExecutor()

        script = "return [1, 2, 3]"
        result = await executor._mock_evaluate_javascript(script)

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_mock_return_boolean(self):
        """测试 Mock 返回布尔值"""
        executor = AIStepExecutor()

        script_true = "return true"
        result = await executor._mock_evaluate_javascript(script_true)
        assert result is True

        script_false = "return false"
        result = await executor._mock_evaluate_javascript(script_false)
        assert result is False

    @pytest.mark.asyncio
    async def test_mock_return_number(self):
        """测试 Mock 返回数字"""
        executor = AIStepExecutor()

        script = "return 42"
        result = await executor._mock_evaluate_javascript(script)

        assert result == 42

    @pytest.mark.asyncio
    async def test_mock_return_null(self):
        """测试 Mock 返回 null"""
        executor = AIStepExecutor()

        script = "return null"
        result = await executor._mock_evaluate_javascript(script)

        assert result is None

    @pytest.mark.asyncio
    async def test_mock_no_return(self):
        """测试 Mock 无返回值"""
        executor = AIStepExecutor()

        script = "console.log('test')"
        result = await executor._mock_evaluate_javascript(script)

        assert result is None


class TestGetSupportedActions:
    """测试 get_supported_actions 方法"""

    def test_get_supported_actions(self):
        """测试获取支持的操作列表"""
        # Given: 执行器
        executor = AIStepExecutor()

        # When: 获取支持的操作
        actions = executor.get_supported_actions()

        # Then: 返回包含所有支持操作的列表
        assert "aiQuery" in actions
        assert "aiString" in actions
        assert "navigate" in actions
        assert "goto" in actions
        assert "ai_input" in actions
        assert "set_variable" in actions
        assert "get_variable" in actions


class TestGetStats:
    """测试 get_stats 方法"""

    def test_get_stats_mock_mode(self):
        """测试获取 Mock 模式统计信息"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)

        # When: 获取统计信息
        stats = executor.get_stats()

        # Then: 返回正确的统计信息
        assert stats["mock_mode"] is True
        assert stats["client_available"] is False
        assert "supported_ai_methods" in stats

    def test_get_stats_with_client(self):
        """测试获取带客户端的统计信息"""
        # Given: 带客户端的执行器
        mock_client = MagicMock()
        executor = AIStepExecutor(midscene_client=mock_client)

        # When: 获取统计信息
        stats = executor.get_stats()

        # Then: 返回正确的统计信息
        assert stats["mock_mode"] is False
        assert stats["client_available"] is True


class TestExecuteTestCase:
    """测试 execute_test_case 方法"""

    @pytest.mark.asyncio
    async def test_execute_test_case_multiple_steps(self, app, db_session):
        """测试执行包含多个步骤的测试用例"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True

        test_case = {
            "name": "多步骤测试",
            "steps": [
                {
                    "action": "set_variable",
                    "params": {"name": "var1", "value": "value1"},
                    "description": "设置变量1"
                },
                {
                    "action": "set_variable",
                    "params": {"name": "var2", "value": "value2"},
                    "description": "设置变量2"
                }
            ]
        }

        # When: 执行测试用例
        result = await executor.execute_test_case(test_case, "test-multi-001")

        # Then: 所有步骤执行成功
        assert result["success"] is True
        assert result["total_steps"] == 2
        assert result["successful_steps"] == 2
        assert result["failed_steps"] == 0

    @pytest.mark.asyncio
    async def test_execute_test_case_stop_on_failure(self, app, db_session):
        """测试遇错停止的测试用例执行"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True

        test_case = {
            "name": "遇错停止测试",
            "stop_on_failure": True,
            "steps": [
                {
                    "action": "set_variable",
                    "params": {"name": "var1", "value": "value1"},
                    "description": "成功步骤"
                },
                {
                    "action": "get_variable",
                    "params": {"name": "nonexistent"},
                    "description": "失败步骤"
                },
                {
                    "action": "set_variable",
                    "params": {"name": "var3", "value": "value3"},
                    "description": "不应执行的步骤"
                }
            ]
        }

        # When: 执行测试用例
        result = await executor.execute_test_case(test_case, "test-stop-001")

        # Then: 遇错停止
        assert result["success"] is False
        assert result["failed_steps"] >= 1

    @pytest.mark.asyncio
    async def test_execute_test_case_empty_steps(self, app, db_session):
        """测试执行空步骤的测试用例"""
        # Given: Mock 模式执行器
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True

        test_case = {
            "name": "空步骤测试",
            "steps": []
        }

        # When: 执行测试用例
        result = await executor.execute_test_case(test_case, "test-empty-001")

        # Then: 返回成功（0 步骤）
        assert result["total_steps"] == 0


class TestStepResultToDict:
    """测试 _step_result_to_dict 方法"""

    def test_step_result_to_dict(self):
        """测试将步骤结果转换为字典"""
        # Given: 执行器和步骤执行结果
        executor = AIStepExecutor()
        result = StepExecutionResult(
            success=True,
            step_index=0,
            action="goto",
            description="访问网站",
            return_value="https://example.com",
            execution_time=1.5
        )

        # When: 转换为字典
        result_dict = executor._step_result_to_dict(result)

        # Then: 返回正确的字典
        assert result_dict["success"] is True
        assert result_dict["step_index"] == 0
        assert result_dict["action"] == "goto"
        assert result_dict["description"] == "访问网站"
        assert result_dict["return_value"] == "https://example.com"
        assert result_dict["execution_time"] == 1.5

    def test_step_result_to_dict_with_error(self):
        """测试将失败的步骤结果转换为字典"""
        executor = AIStepExecutor()
        result = StepExecutionResult(
            success=False,
            step_index=1,
            action="ai_input",
            description="输入文本",
            error_message="参数缺失",
            execution_time=0.5
        )

        result_dict = executor._step_result_to_dict(result)

        assert result_dict["success"] is False
        assert result_dict["error_message"] == "参数缺失"


class TestExecuteNavigateStep:
    """测试 navigate/goto 步骤执行"""

    @pytest.mark.asyncio
    async def test_execute_navigate_with_midscene_client(self, app, db_session):
        """测试使用 MidScene 客户端执行导航"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True

        mock_client = MagicMock()
        mock_client.goto = MagicMock(return_value=None)
        mock_client.take_screenshot = MagicMock(return_value="screenshot.png")
        executor.midscene_client = mock_client
        executor.data_extractor.midscene_client = mock_client

        variable_manager = VariableManager("test-nav-001")

        step_config = {
            "action": "navigate",
            "params": {"url": "https://example.com"},
            "description": "导航到网站"
        }

        with patch.object(executor, '_record_step_execution', return_value=None):
            result = await executor.execute_step(
                step_config, 0, "test-exec-nav-001", variable_manager
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_goto_without_client(self, app, db_session):
        """测试没有 MidScene 客户端时执行 goto"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True
        executor.midscene_client = None

        variable_manager = VariableManager("test-goto-no-client-001")

        step_config = {
            "action": "goto",
            "params": {"url": "https://example.com"},
            "description": "导航"
        }

        with patch.object(executor, '_record_step_execution', return_value=None):
            result = await executor.execute_step(
                step_config, 0, "test-exec-goto-nc-001", variable_manager
            )

        assert result.success is False
        assert "客户端未初始化" in result.error_message


class TestExecuteAIActions:
    """测试 AI 操作步骤执行"""

    @pytest.mark.asyncio
    async def test_execute_ai_input_with_client(self, app, db_session):
        """测试使用客户端执行 ai_input"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True

        mock_client = MagicMock()
        mock_client.ai_input = MagicMock(return_value=None)
        mock_client.take_screenshot = MagicMock(return_value="screenshot.png")
        executor.midscene_client = mock_client
        executor.data_extractor.midscene_client = mock_client

        variable_manager = VariableManager("test-ai-input-001")

        step_config = {
            "action": "ai_input",
            "params": {"text": "hello", "locate": "input"},
            "description": "输入文本"
        }

        with patch.object(executor, '_record_step_execution', return_value=None):
            result = await executor.execute_step(
                step_config, 0, "test-exec-ai-input-001", variable_manager
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_ai_tap_with_client(self, app, db_session):
        """测试使用客户端执行 ai_tap"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True

        mock_client = MagicMock()
        mock_client.ai_tap = MagicMock(return_value=None)
        mock_client.take_screenshot = MagicMock(return_value="screenshot.png")
        executor.midscene_client = mock_client
        executor.data_extractor.midscene_client = mock_client

        variable_manager = VariableManager("test-ai-tap-001")

        step_config = {
            "action": "ai_tap",
            "params": {"prompt": "submit button"},
            "description": "点击按钮"
        }

        with patch.object(executor, '_record_step_execution', return_value=None):
            result = await executor.execute_step(
                step_config, 0, "test-exec-ai-tap-001", variable_manager
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_ai_assert_with_client(self, app, db_session):
        """测试使用客户端执行 ai_assert"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True

        mock_client = MagicMock()
        mock_client.ai_assert = MagicMock(return_value=None)
        mock_client.take_screenshot = MagicMock(return_value="screenshot.png")
        executor.midscene_client = mock_client
        executor.data_extractor.midscene_client = mock_client

        variable_manager = VariableManager("test-ai-assert-001")

        step_config = {
            "action": "ai_assert",
            "params": {"prompt": "page shows success"},
            "description": "断言"
        }

        with patch.object(executor, '_record_step_execution', return_value=None):
            result = await executor.execute_step(
                step_config, 0, "test-exec-ai-assert-001", variable_manager
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_ai_input_missing_params(self, app, db_session):
        """测试 ai_input 缺少参数"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True

        mock_client = MagicMock()
        executor.midscene_client = mock_client

        variable_manager = VariableManager("test-ai-input-missing-001")

        step_config = {
            "action": "ai_input",
            "params": {"text": "hello"},  # 缺少 locate
            "description": "输入文本"
        }

        with patch.object(executor, '_record_step_execution', return_value=None):
            result = await executor.execute_step(
                step_config, 0, "test-exec-missing-001", variable_manager
            )

        assert result.success is False


class TestRecordStepExecution:
    """测试 _record_step_execution 方法"""

    @pytest.mark.asyncio
    async def test_record_step_execution_skipped(self, app, db_session):
        """测试跳过数据库记录"""
        executor = AIStepExecutor(mock_mode=True)
        executor._skip_db_recording = True

        result = StepExecutionResult(
            success=True,
            step_index=0,
            action="goto",
            description="测试"
        )

        # Should not raise any error
        await executor._record_step_execution(result, "test-exec-001", {})


class TestBasicVariableResolution:
    """测试 _basic_variable_resolution 方法"""

    def test_resolve_nested_dict(self, app, db_session):
        """测试解析嵌套字典中的变量"""
        executor = AIStepExecutor()
        variable_manager = VariableManager("test-basic-001")
        variable_manager.store_variable(
            variable_name="key1",
            value="value1",
            source_step_index=0,
            source_api_method="test"
        )

        params = {
            "outer": {
                "inner": "${key1}"
            }
        }

        resolved = executor._basic_variable_resolution(params, variable_manager)

        assert resolved["outer"]["inner"] == "value1"

    def test_resolve_multiple_in_string(self, app, db_session):
        """测试解析字符串中的多个变量"""
        executor = AIStepExecutor()
        variable_manager = VariableManager("test-basic-002")
        variable_manager.store_variable(
            variable_name="first",
            value="Hello",
            source_step_index=0,
            source_api_method="test"
        )
        variable_manager.store_variable(
            variable_name="second",
            value="World",
            source_step_index=0,
            source_api_method="test"
        )

        params = {"text": "${first} ${second}!"}

        resolved = executor._basic_variable_resolution(params, variable_manager)

        assert resolved["text"] == "Hello World!"


class TestExecuteLegacyStepWithoutClient:
    """测试没有客户端时执行传统步骤"""

    @pytest.mark.asyncio
    async def test_navigate_without_client_fails(self, app, db_session):
        """测试没有客户端时导航失败"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True
        executor.midscene_client = None
        variable_manager = VariableManager("test-no-client-001")

        step_config = {
            "action": "navigate",
            "params": {"url": "https://example.com"},
            "description": "导航"
        }

        result = await executor.execute_step(
            step_config, 0, "test-exec-no-client-001", variable_manager
        )

        assert result.success is False
        assert "客户端未初始化" in result.error_message

    @pytest.mark.asyncio
    async def test_ai_tap_without_client_fails(self, app, db_session):
        """测试没有客户端时 ai_tap 失败"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True
        executor.midscene_client = None
        variable_manager = VariableManager("test-no-client-002")

        step_config = {
            "action": "ai_tap",
            "params": {"prompt": "button"},
            "description": "点击"
        }

        result = await executor.execute_step(
            step_config, 0, "test-exec-no-client-002", variable_manager
        )

        assert result.success is False

    @pytest.mark.asyncio
    async def test_ai_input_without_client_fails(self, app, db_session):
        """测试没有客户端时 ai_input 失败"""
        executor = AIStepExecutor(mock_mode=False)
        executor._skip_db_recording = True
        executor.midscene_client = None
        variable_manager = VariableManager("test-no-client-003")

        step_config = {
            "action": "ai_input",
            "params": {"text": "hello", "locate": "input"},
            "description": "输入"
        }

        result = await executor.execute_step(
            step_config, 0, "test-exec-no-client-003", variable_manager
        )

        assert result.success is False