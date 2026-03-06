"""
Chat History Tests - 对话历史管理测试
测试多轮对话消息注入和会话状态管理
"""

import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to easily import our app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ['FLASK_TESTING'] = '1'
try:
    from app import app, init_db, get_session
    from models import LlmConfig
except ImportError:
    app = None


@pytest.fixture
def client():
    if app is None:
        pytest.fail("Cannot import app from app.py, implementation missing.")

    import tempfile

    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE_URL'] = f'sqlite:///{db_path}'

    with app.app_context():
        from models import Base, get_engine
        engine = get_engine()
        Base.metadata.create_all(engine)

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def setup_default_config(client):
    """设置默认配置"""
    with app.app_context():
        session = get_session()
        config = LlmConfig(
            config_key='default',
            api_key='test-api-key',
            base_url='https://api.test.com',
            model='gpt-4',
            description='Test config'
        )
        session.add(config)
        session.commit()


class TestMultiTurnChatHistory:
    """测试多轮对话消息注入"""

    @patch('app.OpenAI')
    def test_single_turn_chat(self, mock_openai, client, setup_default_config):
        """测试单轮对话"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [
            MockChunk("Hello"),
            MockChunk(" there")
        ]

        messages = [{"role": "user", "content": "Hi"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'

        # Verify messages were passed correctly
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['messages'] == messages

    @patch('app.OpenAI')
    def test_multi_turn_chat_with_history(self, mock_openai, client, setup_default_config):
        """测试多轮对话历史注入"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [
            MockChunk("I understand")
        ]

        # 模拟多轮对话历史
        messages = [
            {"role": "user", "content": "Hello, who are you?"},
            {"role": "assistant", "content": "I am an AI assistant."},
            {"role": "user", "content": "What can you do?"},
            {"role": "assistant", "content": "I can help you with various tasks."},
            {"role": "user", "content": "Can you help me with coding?"}
        ]

        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200

        # Verify all messages were passed correctly
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['messages'] == messages
        assert len(call_args[1]['messages']) == 5

    @patch('app.OpenAI')
    def test_chat_with_system_message(self, mock_openai, client, setup_default_config):
        """测试包含系统消息的对话"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [
            MockChunk("Understood")
        ]

        messages = [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Help me write a function"}
        ]

        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200

        # Verify system message was included
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['messages'][0]['role'] == 'system'
        assert call_args[1]['messages'][0]['content'] == "You are a helpful coding assistant."

    @patch('app.OpenAI')
    def test_empty_assistant_message(self, mock_openai, client, setup_default_config):
        """测试空的助手消息处理"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [
            MockChunk("Response")
        ]

        # 助手消息为空字符串
        messages = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": ""},
            {"role": "user", "content": "Follow up"}
        ]

        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['messages'] == messages

    @patch('app.OpenAI')
    def test_long_conversation_history(self, mock_openai, client, setup_default_config):
        """测试长对话历史处理"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [
            MockChunk("OK")
        ]

        # 创建长对话历史（20轮）
        messages = []
        for i in range(20):
            messages.append({"role": "user", "content": f"User message {i}"})
            messages.append({"role": "assistant", "content": f"Assistant response {i}"})
        messages.append({"role": "user", "content": "Final question"})

        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert len(call_args[1]['messages']) == 41  # 20轮 * 2 + 1个最终问题


class TestMessageFormatValidation:
    """测试消息格式验证"""

    def test_missing_role_field(self, client, setup_default_config):
        """测试缺少 role 字段的消息"""
        messages = [{"content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        # API 应该接受但由 OpenAI 处理验证
        # 这里我们只验证请求被正确接收
        assert response.status_code in [200, 400]

    def test_missing_content_field(self, client, setup_default_config):
        """测试缺少 content 字段的消息"""
        messages = [{"role": "user"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        # API 应该接受但由 OpenAI 处理验证
        assert response.status_code in [200, 400]

    def test_invalid_role_value(self, client, setup_default_config):
        """测试无效的 role 值"""
        messages = [{"role": "invalid_role", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        # API 应该接受但由 OpenAI 处理验证
        assert response.status_code in [200, 400]

    def test_empty_messages_array(self, client, setup_default_config):
        """测试空消息数组"""
        messages = []
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 400
        assert "messages 不能为空" in response.json["error"]


class TestSessionStateManagement:
    """测试会话状态管理"""

    @patch('app.OpenAI')
    def test_temperature_parameter(self, mock_openai, client, setup_default_config):
        """测试温度参数传递"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [MockChunk("test")]

        messages = [{"role": "user", "content": "test"}]

        # 测试自定义温度
        response = client.post('/api/chat/stream', json={
            "messages": messages,
            "temperature": 0.3
        })

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.3

    @patch('app.OpenAI')
    def test_default_temperature(self, mock_openai, client, setup_default_config):
        """测试默认温度值"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [MockChunk("test")]

        messages = [{"role": "user", "content": "test"}]

        # 不指定温度
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['temperature'] == 0.7  # 默认值

    @patch('app.OpenAI')
    def test_model_override(self, mock_openai, client, setup_default_config):
        """测试模型覆盖"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [MockChunk("test")]

        messages = [{"role": "user", "content": "test"}]

        # 覆盖模型
        response = client.post('/api/chat/stream', json={
            "messages": messages,
            "model": "gpt-4-turbo"
        })

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == "gpt-4-turbo"

    @patch('app.OpenAI')
    def test_default_model_used(self, mock_openai, client, setup_default_config):
        """测试使用默认模型"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [MockChunk("test")]

        messages = [{"role": "user", "content": "test"}]

        # 不指定模型
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == "gpt-4"  # 来自 setup_default_config

    @patch('app.OpenAI')
    def test_sequential_requests_independence(self, mock_openai, client, setup_default_config):
        """测试连续请求的独立性"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        mock_client.chat.completions.create.return_value = [MockChunk("test")]

        # 第一个请求
        messages1 = [{"role": "user", "content": "First question"}]
        response1 = client.post('/api/chat/stream', json={"messages": messages1})

        # 第二个请求（不同的历史）
        messages2 = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"}
        ]
        response2 = client.post('/api/chat/stream', json={"messages": messages2})

        assert response1.status_code == 200
        assert response2.status_code == 200

        # 验证两个请求的消息是独立的
        calls = mock_client.chat.completions.create.call_args_list
        assert len(calls) == 2
        assert len(calls[0][1]['messages']) == 1
        assert len(calls[1][1]['messages']) == 3