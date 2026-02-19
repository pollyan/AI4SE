"""
AI 智能体测试配置

提供测试所需的 fixtures 和配置。
参考 intent-tester/tests/conftest.py 的实现方式。
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock

# Ensure we can import from tools/ai-agents/backend/tests (for test helpers)
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)

# Ensure we can import from tools/ai-agents (for backend package)
# Note: backend/tests -> backend -> ai-agents, so we need '../..'
AI_AGENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if AI_AGENTS_DIR not in sys.path:
    sys.path.insert(0, AI_AGENTS_DIR)

# Ensure we can import from tools (for shared package)
TOOLS_DIR = os.path.abspath(os.path.join(AI_AGENTS_DIR, '..'))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

from shared.tests.api_client import APIClient

from backend.app import create_app


@pytest.fixture(scope='function')
def app():
    """Create application for the tests."""
    os.environ['FLASK_ENV'] = 'testing'
    
    _app = create_app()
    _app.config['TESTING'] = True
    _app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    # 在应用上下文中先导入再操作数据库
    with _app.app_context():
        # 从 web_gui.models 导入已注册的 db
        from backend.models import db
        db.create_all()
        yield _app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """Create a new database session for a test."""
    with app.app_context():
        from backend.models import db
        yield db.session


@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def api_client(client):
    """带有 JSON Content-Type 的 API 客户端"""
    return APIClient(client, prefix='/ai-agents')


@pytest.fixture
def assert_api_response():
    """API 响应断言助手"""
    
    def _assert_response(response, expected_status=200, expected_structure=None):
        """
        断言 API 响应格式和状态
        """
        assert (
            response.status_code == expected_status
        ), f"期望状态码 {expected_status}，实际 {response.status_code}, Response: {response.get_data(as_text=True)}"
        
        assert (
            response.content_type == "application/json"
        ), f"期望 JSON 响应，实际 {response.content_type}"
        
        data = response.get_json()
        assert data is not None, "响应体不是有效的 JSON"
        
        assert "code" in data, "响应缺少 code 字段"
        assert "message" in data, "响应缺少 message 字段"
        
        if expected_status < 400:
            return data.get("data", data)
        
        return data
    
    return _assert_response


# ==================== AI 配置相关 Fixtures ====================

@pytest.fixture
def sample_ai_config():
    """提供示例 AI 配置数据"""
    return {
        "name": "测试配置",
        "config_name": "测试配置",
        "base_url": "https://api.openai.com/v1",
        "api_key": "test-api-key-12345",
        "model_name": "gpt-4o-mini",
        "is_default": False,
        "is_active": True
    }


@pytest.fixture
def create_ai_config(app):
    """创建 AI 配置的工厂函数"""
    configs_created = []
    
    def _create_config(**kwargs):
        with app.app_context():
            from backend.models import db, RequirementsAIConfig
            
            defaults = {
                "config_name": "测试配置",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-api-key",
                "model_name": "gpt-4o-mini",
                "is_default": False,
                "is_active": True
            }
            defaults.update(kwargs)
            
            # 处理 name 到 config_name 的映射
            if 'name' in defaults and 'config_name' not in kwargs:
                defaults['config_name'] = defaults.pop('name')
            elif 'name' in defaults:
                defaults.pop('name')
            
            config = RequirementsAIConfig(**defaults)
            db.session.add(config)
            db.session.commit()
            db.session.refresh(config)
            configs_created.append(config.id)
            return config
    
    yield _create_config
    
    # 清理
    with app.app_context():
        from backend.models import db, RequirementsAIConfig
        for config_id in configs_created:
            try:
                config = RequirementsAIConfig.query.get(config_id)
                if config:
                    db.session.delete(config)
            except Exception:
                pass
        db.session.commit()


# ==================== 会话相关 Fixtures ====================

@pytest.fixture
def sample_session_data():
    """提供示例会话创建数据"""
    return {
        "assistant_type": "lisa",
        "project_name": "测试项目"
    }


@pytest.fixture
def mock_ai_service():
    """Mock AI 服务"""
    mock_service = MagicMock()
    mock_service.initialize = AsyncMock()
    mock_service.stream_message = AsyncMock(return_value=iter(["Hello", " World"]))
    mock_service.analyze_user_requirement = AsyncMock(return_value="测试回复")
    return mock_service


@pytest.fixture
def assistant_types():
    """支持的助手类型"""
    return ["lisa"]


def pytest_collection_modifyitems(items):
    """根据文件路径和名称自动添加标记"""
    for item in items:
        path = str(item.fspath)
        name = item.name

        # Agent Smoke 测试（真实 LLM，仅本地运行）
        if "agent_smoke" in path:
            item.add_marker(pytest.mark.slow)
        # API 测试
        elif "/api/" in path:
            item.add_marker(pytest.mark.api)
        # 集成测试
        elif "integration" in name or "integration" in path:
            item.add_marker(pytest.mark.integration)
        # E2E 测试
        elif "e2e" in name or "e2e" in path:
            item.add_marker(pytest.mark.e2e)
        # 默认为单元测试
        else:
            item.add_marker(pytest.mark.unit)
