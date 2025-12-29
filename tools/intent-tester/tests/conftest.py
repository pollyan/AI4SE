
import pytest
import sys
import os
import json
from unittest.mock import MagicMock

# Ensure we can import from tools/intent-tester/tests (for test_data_manager)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)

# Ensure we can import from tools/intent-tester/backend
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend'))
sys.path.insert(0, BACKEND_DIR)

# Ensure we can import shared modules
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, PROJECT_ROOT)

from app import create_app
# from shared.database import db as _db # shared db mismatches with web_gui.models.db used in app
from web_gui.models import db as _db

@pytest.fixture(scope='function')
def app():
    """Create application for the tests."""
    # Set testing config
    os.environ['FLASK_ENV'] = 'testing'
    
    _app = create_app()
    _app.config['TESTING'] = True
    _app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with _app.app_context():
        _db.create_all()
        yield _app
        _db.session.remove()
        _db.drop_all()

@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for a test."""
    yield _db.session

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def api_client(client):
    """A test client specifically for API requests (adds content-type header)."""
    class APIClient:
        def __init__(self, client):
            self.client = client
            
        def get(self, *args, **kwargs):
            return self.client.get(*args, **kwargs)
            
        def post(self, *args, **kwargs):
            if 'json' in kwargs:
                kwargs['content_type'] = 'application/json'
            return self.client.post(*args, **kwargs)
            
        def put(self, *args, **kwargs):
            if 'json' in kwargs:
                kwargs['content_type'] = 'application/json'
            return self.client.put(*args, **kwargs)
            
        def delete(self, *args, **kwargs):
            return self.client.delete(*args, **kwargs)
            
    return APIClient(client)


@pytest.fixture
def assert_api_response():
    """API响应断言助手"""

    def _assert_response(response, expected_status=200, expected_structure=None):
        """
        断言API响应格式和状态

        Args:
            response: Flask测试响应对象
            expected_status: 期望的HTTP状态码
            expected_structure: 期望的响应数据结构（字典）

        Returns:
            解析后的响应数据
        """
        assert (
            response.status_code == expected_status
        ), f"期望状态码{expected_status}，实际{response.status_code}, Response: {response.get_data(as_text=True)}"

        # 验证响应是JSON格式
        assert (
            response.content_type == "application/json"
        ), f"期望JSON响应，实际{response.content_type}"

        data = response.get_json()
        assert data is not None, "响应体不是有效的JSON"

        # 验证基本响应结构
        assert "code" in data, "响应缺少code字段"
        assert "message" in data, "响应缺少message字段"

        assert (
            data["code"] == expected_status
        ), f"响应code字段期望{expected_status}，实际{data['code']}"

        # 对于成功响应，默认返回data字段内容
        if expected_status < 400:
            if expected_structure:
                assert "data" in data, "成功响应缺少data字段"
                _validate_structure(data["data"], expected_structure)
            return data.get(
                "data", data
            )  # 成功响应返回data字段内容，如果没有data字段则返回完整响应

        return data  # 错误响应返回完整响应

    def _validate_structure(actual_data, expected_structure):
        """验证数据结构"""
        if isinstance(expected_structure, dict):
            for key, value_type in expected_structure.items():
                assert key in actual_data, f"响应数据缺少字段: {key}"

                if isinstance(value_type, type):
                    assert isinstance(
                        actual_data[key], value_type
                    ), f"字段{key}类型错误，期望{value_type}，实际{type(actual_data[key])}"
                elif isinstance(value_type, tuple):
                    # 支持多种类型
                    assert any(
                        isinstance(actual_data[key], t) for t in value_type
                    ), f"字段{key}类型错误，期望{value_type}之一，实际{type(actual_data[key])}"
                elif isinstance(value_type, dict):
                    # 嵌套结构验证
                    _validate_structure(actual_data[key], value_type)

    return _assert_response


@pytest.fixture
def sample_testcase_data():
    """提供标准的测试用例数据"""
    return {
        "name": "API测试用例",
        "description": "用于API测试的示例测试用例",
        "steps": [
            {
                "action": "navigate",
                "params": {"url": "https://example.com"},
                "description": "访问示例网站",
            },
            {
                "action": "ai_input",
                "params": {"text": "测试文本", "locate": "输入框"},
                "description": "输入测试文本",
            },
        ],
        "category": "API测试",
        "priority": 2,
        "tags": ["api", "test"],
    }


@pytest.fixture
def invalid_testcase_data():
    """提供无效的测试用例数据（用于错误测试）"""
    return {
        "name": "",  # 空名称
        "description": None,
        "steps": "invalid_json",  # 无效的JSON
        "category": "x" * 200,  # 超长类别
        "priority": "invalid",  # 无效优先级
        "tags": None,
    }


@pytest.fixture
def test_data_manager(db_session):
    """提供测试数据管理器"""
    from test_data_manager import APITestDataManager

    manager = APITestDataManager(db_session)
    yield manager
    # 自动清理
    manager.cleanup_all()


@pytest.fixture
def create_test_testcase(test_data_manager):
    """创建测试用例的便捷fixture"""

    def _create_testcase(data=None, **kwargs):
        # 如果传入了kwargs，合并到data中
        if kwargs:
            if data is None:
                data = kwargs
            else:
                data.update(kwargs)
        return test_data_manager.create_testcase(data)

    return _create_testcase


@pytest.fixture
def create_test_execution(test_data_manager):
    """创建执行记录的便捷fixture"""

    def _create_execution(data=None):
        return test_data_manager.create_execution(data)

    return _create_execution


@pytest.fixture
def create_test_template(test_data_manager):
    """创建模板的便捷fixture（占位符，等模板功能实现）"""

    def _create_template(data=None):
        # 目前返回模拟数据，等模板功能实现后再修改
        import uuid

        mock_template = {
            "id": abs(hash(str(uuid.uuid4()))) % 1000000,
            "name": data.get("name", "测试模板") if data else "测试模板",
            "description": (
                data.get("description", "测试模板描述") if data else "测试模板描述"
            ),
            "category": data.get("category", "API测试") if data else "API测试",
            "steps": data.get("steps", []) if data else [],
            "created_at": "2023-12-01T10:00:00Z",
        }
        return mock_template

    return _create_template


# ==================== Steps 测试相关 Fixtures ====================


@pytest.fixture
def sample_goto_step():
    """提供goto步骤数据"""
    return {
        "action": "goto",
        "params": {"url": "https://example.com"},
        "description": "访问示例网站",
        "required": True,
    }


@pytest.fixture
def sample_ai_input_step():
    """提供ai_input步骤数据"""
    return {
        "action": "ai_input",
        "params": {"locate": "搜索框", "text": "测试搜索内容"},
        "description": "在搜索框输入文本",
        "required": True,
    }


@pytest.fixture
def sample_ai_tap_step():
    """提供ai_tap步骤数据"""
    return {
        "action": "ai_tap",
        "params": {"locate": "提交按钮"},
        "description": "点击提交按钮",
        "required": True,
    }


@pytest.fixture
def sample_ai_assert_step():
    """提供ai_assert步骤数据"""
    return {
        "action": "ai_assert",
        "params": {"prompt": "页面显示成功消息"},
        "description": "验证操作成功",
        "required": True,
    }


@pytest.fixture
def sample_ai_wait_for_step():
    """提供ai_wait_for步骤数据"""
    return {
        "action": "ai_wait_for",
        "params": {"locate": "加载完成提示", "timeout": 5000},
        "description": "等待页面加载完成",
        "required": True,
    }


@pytest.fixture
def sample_sleep_step():
    """提供sleep步骤数据"""
    return {
        "action": "sleep",
        "params": {"duration": 2000},
        "description": "等待2秒",
        "required": False,
    }


@pytest.fixture
def sample_screenshot_step():
    """提供screenshot步骤数据"""
    return {
        "action": "screenshot",
        "params": {"name": "test_screenshot"},
        "description": "截取屏幕截图",
        "required": False,
    }


@pytest.fixture
def create_testcase_with_steps(db_session):
    """创建包含步骤的测试用例工厂函数"""
    from web_gui.models import TestCase

    def _create_testcase_with_steps(step_count=2, **kwargs):
        # 生成默认步骤
        default_steps = [
            {
                "action": "goto",
                "params": {"url": f"https://example{i}.com"},
                "description": f"访问网站{i+1}",
            }
            for i in range(step_count)
        ]

        # 设置默认值
        defaults = {
            "name": f"包含{step_count}个步骤的测试用例",
            "description": "用于步骤API测试的测试用例",
            "steps": json.dumps(default_steps),
            "category": "步骤测试",
            "priority": 2,
            "tags": "steps,api,test",
            "created_by": "test_user",
            "is_active": True,
        }
        defaults.update(kwargs)

        testcase = TestCase(**defaults)
        db_session.add(testcase)
        db_session.commit()
        return testcase

    return _create_testcase_with_steps


@pytest.fixture
def invalid_step_data():
    """提供无效的步骤数据（用于错误测试）"""
    return [
        # 缺少action字段
        {
            "params": {"url": "https://example.com"},
            "description": "缺少action字段的步骤",
        },
        # 无效的action类型
        {
            "action": "invalid_action_type",
            "params": {},
            "description": "无效的动作类型",
        },
        # goto缺少url参数
        {"action": "goto", "params": {}, "description": "goto动作缺少url参数"},
        # ai_input缺少必需参数
        {"action": "ai_input", "params": {}, "description": "ai_input动作缺少必需参数"},
        # ai_tap缺少locate参数
        {"action": "ai_tap", "params": {}, "description": "ai_tap动作缺少locate参数"},
    ]


@pytest.fixture
def all_supported_actions():
    """提供所有支持的动作类型列表"""
    return [
        "goto",
        "ai_input",
        "ai_tap",
        "ai_assert",
        "ai_wait_for",
        "ai_scroll",
        "ai_drag",
        "sleep",
        "screenshot",
        "refresh",
        "back",
        "ai_select",
        "ai_upload",
        "ai_check",
    ]


# ==================== Execution 测试相关 Fixtures ====================


@pytest.fixture
def sample_execution_data():
    """提供执行创建数据"""
    return {
        "testcase_id": None,  # 将在测试中设置
        "mode": "headless",
        "browser": "chrome",
        "executed_by": "test_user",
    }


@pytest.fixture
def sample_execution_start_data():
    """提供MidScene执行开始通知数据"""
    return {
        "execution_id": "test-exec-start-001",
        "testcase_id": 1,  # 将在测试中设置为实际的testcase_id
        "mode": "headless",
        "browser": "chrome",
        "executed_by": "midscene_user",
    }


@pytest.fixture
def sample_execution_result_data():
    """提供MidScene执行结果数据"""
    from datetime import datetime

    return {
        "execution_id": "test-exec-result-001",
        "status": "success",
        "end_time": datetime.utcnow().isoformat(),
        "duration": 1500,
        "steps_total": 3,
        "steps_passed": 3,
        "steps_failed": 0,
        "result_summary": {
            "total_steps": 3,
            "passed_steps": 3,
            "failed_steps": 0,
            "success_rate": 100.0,
        },
    }


@pytest.fixture
def sample_execution_result_with_steps():
    """提供包含步骤详情的MidScene执行结果数据"""
    from datetime import datetime

    return {
        "execution_id": "test-exec-with-steps-001",
        "status": "success",
        "end_time": datetime.utcnow().isoformat(),
        "duration": 2000,
        "steps_total": 2,
        "steps_passed": 2,
        "steps_failed": 0,
        "result_summary": {"total_steps": 2, "passed_steps": 2, "failed_steps": 0},
        "steps": [
            {
                "index": 0,
                "description": "访问测试网站",
                "status": "success",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration": 1000,
                "screenshot_path": "/screenshots/step1.png",
                "ai_confidence": 0.95,
            },
            {
                "index": 1,
                "description": "点击按钮",
                "status": "success",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": datetime.utcnow().isoformat(),
                "duration": 500,
                "screenshot_path": "/screenshots/step2.png",
                "ai_confidence": 0.88,
            },
        ],
    }


@pytest.fixture
def create_execution_history(db_session):
    """创建执行历史记录的工厂函数"""
    from web_gui.models import TestCase
    from web_gui.models import ExecutionHistory

    def _create_execution_history(**kwargs):
        from datetime import datetime
        import uuid

        # 创建测试用例（如果没有提供test_case_id）
        if "test_case_id" not in kwargs:
            testcase = TestCase(
                name="测试用例用于执行",
                description="用于执行测试的测试用例",
                steps=json.dumps(
                    [{"action": "goto", "params": {"url": "https://example.com"}}]
                ),
                created_by="test_user",
                is_active=True,
            )
            db_session.add(testcase)
            db_session.commit()
            kwargs["test_case_id"] = testcase.id

        # 设置默认值
        defaults = {
            "execution_id": f"test-exec-{uuid.uuid4().hex[:8]}",
            "status": "success",
            "mode": "headless",
            "browser": "chrome",
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow(),
            "duration": 1000,
            "steps_total": 1,
            "steps_passed": 1,
            "steps_failed": 0,
            "result_summary": json.dumps({"total": 1, "passed": 1, "failed": 0}),
            "executed_by": "test_user",
        }
        defaults.update(kwargs)

        execution = ExecutionHistory(**defaults)
        db_session.add(execution)
        db_session.commit()
        return execution

    return _create_execution_history


@pytest.fixture
def create_step_execution(db_session):
    """创建步骤执行记录的工厂函数"""
    from web_gui.models import StepExecution

    def _create_step_execution(**kwargs):
        from datetime import datetime

        # 设置默认值
        defaults = {
            "execution_id": "test-exec-001",
            "step_index": 0,
            "step_description": "测试步骤",
            "status": "success",
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow(),
            "duration": 500,
            "screenshot_path": "/screenshots/step.png",
            "ai_confidence": 0.9,
        }
        defaults.update(kwargs)

        step_execution = StepExecution(**defaults)
        db_session.add(step_execution)
        db_session.commit()
        return step_execution

    return _create_step_execution


@pytest.fixture
def execution_statuses():
    """提供所有支持的执行状态列表"""
    return ["running", "success", "failed", "stopped"]


@pytest.fixture
def browser_types():
    """提供所有支持的浏览器类型列表"""
    return ["chrome", "firefox", "safari", "edge"]


@pytest.fixture
def execution_modes():
    """提供所有支持的执行模式列表"""
    return ["headless", "browser"]

