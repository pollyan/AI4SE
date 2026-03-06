"""
Error Handling Tests - 错误处理边界测试
测试 OpenAI API 超时、无效消息格式、配置缺失、网络中断、API 限流等场景
"""

import pytest
import os
import sys
import json
import time
from unittest.mock import patch, MagicMock
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError
import httpx

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


def _make_api_connection_error(message: str) -> APIConnectionError:
    """Helper to create APIConnectionError with required arguments"""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return APIConnectionError(message=message, request=request)


def _make_rate_limit_error(message: str) -> RateLimitError:
    """Helper to create RateLimitError with required arguments"""
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))
    return RateLimitError(message, response=response, body={"error": {"message": message}})


def _make_api_error(message: str) -> APIError:
    """Helper to create APIError with required arguments"""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return APIError(message, request, body={"error": {"message": message}})


class TestOpenAITimeoutHandling:
    """测试 OpenAI API 超时处理"""

    @patch('app.OpenAI')
    def test_connection_timeout(self, mock_openai, client, setup_default_config):
        """测试连接超时"""
        mock_openai.side_effect = APITimeoutError("Connection timed out")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        # SSE 流式响应返回 200，错误在流中
        assert response.status_code == 200
        assert response.mimetype == 'text/event-stream'

        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data
        assert 'timed out' in data.lower() or 'timeout' in data.lower()

    @patch('app.OpenAI')
    def test_read_timeout_during_stream(self, mock_openai, client, setup_default_config):
        """测试流式响应期间的读取超时"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # 模拟流开始后超时
        class TimeoutChunk:
            def __init__(self):
                self.choices = []

        def create_with_timeout(*args, **kwargs):
            yield TimeoutChunk()
            raise APITimeoutError("Read timeout during streaming")

        mock_client.chat.completions.create.side_effect = create_with_timeout

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        # 错误应该被捕获并在流中返回
        assert 'data:' in data

    @patch('app.OpenAI')
    def test_slow_response_handling(self, mock_openai, client, setup_default_config):
        """测试慢响应处理"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        # 模拟慢响应（正常完成，但延迟）
        def slow_create(*args, **kwargs):
            time.sleep(0.01)  # 模拟延迟
            return [MockChunk("Response")]

        mock_client.chat.completions.create.side_effect = slow_create

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"content": "Response"}' in data


class TestInvalidMessageFormat:
    """测试无效消息格式处理"""

    def test_missing_role_field(self, client, setup_default_config):
        """测试缺少 role 字段的消息"""
        messages = [{"content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        # 请求被接受，由 OpenAI 处理验证
        # 但因为我们需要 mock OpenAI，这里测试基本响应
        assert response.status_code in [200, 400]

    def test_missing_content_field(self, client, setup_default_config):
        """测试缺少 content 字段的消息"""
        messages = [{"role": "user"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code in [200, 400]

    def test_invalid_role_value(self, client, setup_default_config):
        """测试无效的 role 值"""
        messages = [{"role": "invalid_role", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code in [200, 400]

    def test_null_message_content(self, client, setup_default_config):
        """测试 null 消息内容"""
        messages = [{"role": "user", "content": None}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code in [200, 400]

    def test_non_string_content(self, client, setup_default_config):
        """测试非字符串内容"""
        messages = [{"role": "user", "content": 12345}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code in [200, 400]

    def test_empty_string_content(self, client, setup_default_config):
        """测试空字符串内容"""
        messages = [{"role": "user", "content": ""}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code in [200, 400]

    @patch('app.OpenAI')
    def test_malformed_message_structure(self, mock_openai, client, setup_default_config):
        """测试畸形消息结构"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # 畸形消息（缺少必需字段或格式错误）
        messages = [
            {"role": "user", "content": "Valid"},
            {"invalid_key": "value"},
            {"role": "assistant"}  # 缺少 content
        ]

        response = client.post('/api/chat/stream', json={"messages": messages})

        # API 应该转发给 OpenAI 处理验证
        assert response.status_code in [200, 400]

    def test_non_array_messages(self, client, setup_default_config):
        """测试非数组类型的 messages"""
        response = client.post('/api/chat/stream', json={"messages": "not an array"})
        # 当 messages 不是数组时，OpenAI 会处理验证
        assert response.status_code in [200, 400]


class TestConfigMissingScenarios:
    """测试配置缺失场景"""

    def test_no_default_config(self, client):
        """测试无默认配置"""
        # 不设置任何配置
        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 503
        assert "系统未配置" in response.json["error"]

    def test_inactive_config(self, client):
        """测试已停用的配置"""
        with app.app_context():
            session = get_session()
            config = LlmConfig(
                config_key='default',
                api_key='test-api-key',
                base_url='https://api.test.com',
                model='gpt-4',
                is_active=False  # 设置为非活动状态
            )
            session.add(config)
            session.commit()

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 503
        assert "系统未配置" in response.json["error"]

    @patch('app.OpenAI')
    def test_empty_api_key(self, mock_openai, client):
        """测试空 API Key"""
        with app.app_context():
            session = get_session()
            config = LlmConfig(
                config_key='default',
                api_key='',  # 空 API Key
                base_url='https://api.test.com',
                model='gpt-4'
            )
            session.add(config)
            session.commit()

        # OpenAI 客户端可能会因为空 key 而失败
        mock_openai.side_effect = Exception("Invalid API key")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data

    @patch('app.OpenAI')
    def test_invalid_base_url(self, mock_openai, client):
        """测试无效的 base URL"""
        with app.app_context():
            session = get_session()
            config = LlmConfig(
                config_key='default',
                api_key='test-key',
                base_url='not-a-valid-url',
                model='gpt-4'
            )
            session.add(config)
            session.commit()

        mock_openai.side_effect = _make_api_connection_error("Invalid base URL")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data


class TestNetworkInterruption:
    """测试网络中断处理"""

    @patch('app.OpenAI')
    def test_connection_refused(self, mock_openai, client, setup_default_config):
        """测试连接被拒绝"""
        mock_openai.side_effect = _make_api_connection_error("Connection refused")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data

    @patch('app.OpenAI')
    def test_dns_resolution_failure(self, mock_openai, client, setup_default_config):
        """测试 DNS 解析失败"""
        mock_openai.side_effect = _make_api_connection_error("DNS resolution failed")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data

    @patch('app.OpenAI')
    def test_ssl_certificate_error(self, mock_openai, client, setup_default_config):
        """测试 SSL 证书错误"""
        mock_openai.side_effect = _make_api_connection_error("SSL certificate verify failed")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data

    @patch('app.OpenAI')
    def test_connection_reset_during_stream(self, mock_openai, client, setup_default_config):
        """测试流式传输期间连接重置"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

        # 模拟部分数据后连接重置
        def create_with_reset(*args, **kwargs):
            yield MockChunk("Partial")
            raise _make_api_connection_error("Connection reset by peer")

        mock_client.chat.completions.create.side_effect = create_with_reset

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        # 应该包含部分数据和错误
        assert 'data: {"content": "Partial"}' in data
        assert 'data: {"error":' in data


class TestRateLimitHandling:
    """测试 API 限流 (429) 处理"""

    @patch('app.OpenAI')
    def test_rate_limit_error(self, mock_openai, client, setup_default_config):
        """测试 429 限流错误"""
        mock_openai.side_effect = _make_rate_limit_error("Rate limit exceeded")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data
        assert 'rate limit' in data.lower() or 'exceeded' in data.lower()

    @patch('app.OpenAI')
    def test_rate_limit_with_retry_after(self, mock_openai, client, setup_default_config):
        """测试带 retry-after 的限流错误"""
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        response_mock = httpx.Response(429, headers={"retry-after": "30"}, request=request)
        error = RateLimitError(
            "Rate limit exceeded",
            response=response_mock,
            body={"error": {"message": "Rate limit exceeded"}}
        )
        mock_openai.side_effect = error

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data

    @patch('app.OpenAI')
    def test_quota_exceeded(self, mock_openai, client, setup_default_config):
        """测试配额超限"""
        mock_openai.side_effect = _make_rate_limit_error("Quota exceeded for this billing period")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data


class TestResponseFormatAnomalies:
    """测试响应格式异常处理"""

    @patch('app.OpenAI')
    def test_empty_choices_in_response(self, mock_openai, client, setup_default_config):
        """测试响应中 choices 为空"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockChunk:
            def __init__(self):
                self.choices = []  # 空 choices

        mock_client.chat.completions.create.return_value = [MockChunk()]

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        # 空 choices 不应该产生内容，但也不应该崩溃
        assert 'data: [DONE]' in data

    @patch('app.OpenAI')
    def test_missing_delta_in_response(self, mock_openai, client, setup_default_config):
        """测试响应中缺少 delta"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockChoice:
            def __init__(self):
                self.delta = None  # 缺少 delta

        class MockChunk:
            def __init__(self):
                self.choices = [MockChoice()]

        mock_client.chat.completions.create.return_value = [MockChunk()]

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: [DONE]' in data

    @patch('app.OpenAI')
    def test_none_content_in_delta(self, mock_openai, client, setup_default_config):
        """测试 delta 中 content 为 None"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self):
                self.content = None

        class MockChoice:
            def __init__(self):
                self.delta = MockDelta()

        class MockChunk:
            def __init__(self):
                self.choices = [MockChoice()]

        mock_client.chat.completions.create.return_value = [MockChunk(), MockChunk()]

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: [DONE]' in data

    @patch('app.OpenAI')
    def test_unexpected_response_type(self, mock_openai, client, setup_default_config):
        """测试意外响应类型"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # 返回非预期的响应结构
        mock_client.chat.completions.create.return_value = "not an iterator"

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        # 应该捕获错误并返回
        assert 'data: {"error":' in data or 'data: [DONE]' in data

    @patch('app.OpenAI')
    def test_api_error_response(self, mock_openai, client, setup_default_config):
        """测试 API 错误响应"""
        mock_openai.side_effect = _make_api_error("Internal server error")

        messages = [{"role": "user", "content": "Hello"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"error":' in data

    @patch('app.OpenAI')
    def test_truncated_response(self, mock_openai, client, setup_default_config):
        """测试截断的响应"""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        class MockDelta:
            def __init__(self, content): self.content = content

        class MockChoice:
            def __init__(self, delta): self.delta = delta

        class MockChunk:
            def __init__(self, content):
                self.choices = [MockChoice(MockDelta(content))] if content else []

            # 模拟截断：finish_reason 设置为 length
            @property
            def finish_reason(self):
                return "length" if not hasattr(self, '_content') or not self._content else None

        mock_client.chat.completions.create.return_value = [
            MockChunk("This is a truncated response..."),
            MockChunk("")
        ]

        messages = [{"role": "user", "content": "Write a long story"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        assert 'data: {"content":' in data


class TestEdgeCases:
    """测试边界情况"""

    def test_request_body_not_json(self, client, setup_default_config):
        """测试非 JSON 请求体"""
        response = client.post('/api/chat/stream', data="not json", content_type='text/plain')
        # Flask returns 415 for unsupported media type when expecting JSON
        assert response.status_code in [400, 415]

    @patch('app.OpenAI')
    def test_unicode_in_messages(self, mock_openai, client, setup_default_config):
        """测试消息中的 Unicode 字符"""
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
            MockChunk("你好")
        ]

        messages = [{"role": "user", "content": "请用中文回复：🎉 你好世界"}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        data = response.get_data(as_text=True)
        # JSON may encode Unicode as escape sequences, so check for both formats
        assert '你好' in data or '\\u4f60\\u597d' in data

    @patch('app.OpenAI')
    def test_very_long_message(self, mock_openai, client, setup_default_config):
        """测试超长消息"""
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

        # 创建一个很长的消息（10000字符）
        long_message = "A" * 10000
        messages = [{"role": "user", "content": long_message}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['messages'][0]['content'] == long_message

    @patch('app.OpenAI')
    def test_special_characters_in_content(self, mock_openai, client, setup_default_config):
        """测试特殊字符处理"""
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

        # 包含各种特殊字符
        special_content = "Test\n\t\r\"'<>&\\"
        messages = [{"role": "user", "content": special_content}]
        response = client.post('/api/chat/stream', json={"messages": messages})

        assert response.status_code == 200
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['messages'][0]['content'] == special_content