"""
API测试配置文件
提供API测试所需的fixtures和配置
"""

import pytest
import json
from web_gui.app_enhanced import create_app
from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template
from tests.unit.factories import TestCaseFactory, ExecutionHistoryFactory, StepExecutionFactory


@pytest.fixture(scope="function")
def api_app():
    """创建API测试应用实例"""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False
    }
    
    app = create_app(test_config=test_config)
    
    # 确保应用上下文
    with app.app_context():
        # 启用SQLite外键约束
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        # 创建所有表
        db.create_all()
        
        yield app
        
        # 清理
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def api_client(api_app):
    """创建API测试客户端"""
    return api_app.test_client()


@pytest.fixture(scope="function") 
def db_session(api_app):
    """提供数据库会话"""
    with api_app.app_context():
        yield db.session


@pytest.fixture
def sample_testcase_data():
    """提供标准的测试用例数据"""
    return {
        'name': 'API测试用例',
        'description': '用于API测试的示例测试用例',
        'steps': [
            {
                'action': 'navigate',
                'params': {'url': 'https://example.com'},
                'description': '访问示例网站'
            },
            {
                'action': 'ai_input',
                'params': {
                    'text': '测试文本',
                    'locate': '输入框'
                },
                'description': '输入测试文本'
            }
        ],
        'category': 'API测试',
        'priority': 2,
        'tags': ['api', 'test']
    }


@pytest.fixture
def invalid_testcase_data():
    """提供无效的测试用例数据（用于错误测试）"""
    return {
        'name': '',  # 空名称
        'description': None,
        'steps': 'invalid_json',  # 无效的JSON
        'category': 'x' * 200,  # 超长类别
        'priority': 'invalid',  # 无效优先级
        'tags': None
    }


@pytest.fixture
def create_test_testcase(db_session):
    """创建测试用例的工厂函数"""
    def _create_testcase(**kwargs):
        # 设置默认值
        defaults = {
            'name': 'API测试用例',
            'description': '测试描述',
            'steps': json.dumps([
                {'action': 'navigate', 'params': {'url': 'https://example.com'}}
            ]),
            'category': 'API测试',
            'priority': 2,
            'tags': 'api,test',
            'created_by': 'test_user',
            'is_active': True
        }
        defaults.update(kwargs)
        
        testcase = TestCase(**defaults)
        db_session.add(testcase)
        db_session.commit()
        return testcase
    
    return _create_testcase


@pytest.fixture
def assert_json_structure():
    """验证JSON响应结构的辅助函数"""
    def _assert_structure(response_data, expected_fields):
        """验证响应数据包含期望的字段"""
        if isinstance(expected_fields, dict):
            for field, field_type in expected_fields.items():
                assert field in response_data, f"缺少字段: {field}"
                if field_type is not None:
                    assert isinstance(response_data[field], field_type), \
                        f"字段 {field} 类型错误，期望 {field_type}，实际 {type(response_data[field])}"
        elif isinstance(expected_fields, list):
            for field in expected_fields:
                assert field in response_data, f"缺少字段: {field}"
    
    return _assert_structure


@pytest.fixture
def assert_api_response():
    """验证API响应格式的辅助函数"""
    def _assert_response(response, expected_status=200, expected_fields=None):
        """验证API响应的基本格式"""
        assert response.status_code == expected_status, \
            f"状态码错误，期望 {expected_status}，实际 {response.status_code}"
        
        # 验证响应是JSON格式
        assert response.content_type == 'application/json', \
            f"Content-Type错误，期望 application/json，实际 {response.content_type}"
        
        data = response.get_json()
        assert data is not None, "响应体不是有效的JSON"
        
        # 验证基本结构
        assert 'code' in data, "响应缺少code字段"
        assert data['code'] == expected_status, \
            f"响应code字段错误，期望 {expected_status}，实际 {data['code']}"
        
        if expected_status == 200:
            assert 'data' in data or 'message' in data, "成功响应应该包含data或message字段"
        else:
            assert 'message' in data, "错误响应应该包含message字段"
        
        # 验证自定义字段
        if expected_fields:
            if 'data' in data and expected_fields:
                if isinstance(expected_fields, dict):
                    for field, field_type in expected_fields.items():
                        assert field in data['data'], f"响应数据缺少字段: {field}"
                        if field_type is not None:
                            assert isinstance(data['data'][field], field_type), \
                                f"字段 {field} 类型错误"
        
        return data
    
    return _assert_response