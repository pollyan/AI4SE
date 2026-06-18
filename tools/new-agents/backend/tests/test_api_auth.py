"""
API Key Authentication Tests - P0-2 认证中间件测试
"""

import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['FLASK_TESTING'] = '1'

from app import create_app
from models import db


VALID_AGENT_RUN_PAYLOAD = {
    "prompt": "hi",
    "systemPrompt": "system",
    "workflowId": "TEST_DESIGN",
    "stageId": "CLARIFY",
}


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with app.app_context():
        db.create_all()
        yield app
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


class TestAPIKeyAuth:
    """测试 API Key 认证中间件"""

    def test_no_key_returns_401(self, client, monkeypatch):
        """设置 PROXY_API_KEY 后，无 X-API-Key 返回 401"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post(
            '/api/agent/runs/stream',
            json=VALID_AGENT_RUN_PAYLOAD,
        )
        assert resp.status_code == 401

    def test_mermaid_repair_no_key_returns_401(self, client, monkeypatch):
        """设置 PROXY_API_KEY 后，Mermaid 修复端点无 X-API-Key 返回 401"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post('/api/utils/mermaid/repair', json={
            "brokenCode": "graph TD\n  A-->",
            "errorMessage": "Syntax Error",
        })
        assert resp.status_code == 401

    def test_wrong_key_returns_401(self, client, monkeypatch):
        """设置 PROXY_API_KEY 后，错误 Key 返回 401"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post(
            '/api/agent/runs/stream',
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_correct_key_passes(self, client, app, monkeypatch):
        """设置 PROXY_API_KEY 后，正确 Key 放行（可能因无配置返回 503，但不是 401）"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post(
            '/api/agent/runs/stream',
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-API-Key": "secret-key"},
        )
        assert resp.status_code != 401

    def test_gateway_forwarded_agent_request_passes_without_browser_key(
        self,
        client,
        monkeypatch,
    ):
        """浏览器经 Nginx 网关注入内部头后，不需要把 PROXY_API_KEY 暴露给前端"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post(
            '/api/agent/runs/stream',
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-AI4SE-Gateway": "new-agents"},
        )
        assert resp.status_code != 401

    def test_gateway_forwarded_mermaid_repair_request_passes_without_browser_key(
        self,
        client,
        monkeypatch,
    ):
        """Mermaid 修复同样应允许可信网关转发，不要求浏览器持有后端密钥"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post(
            '/api/utils/mermaid/repair',
            json={
                "brokenCode": "graph TD\n  A-->",
                "errorMessage": "Syntax Error",
            },
            headers={"X-AI4SE-Gateway": "new-agents"},
        )
        assert resp.status_code != 401

    def test_wrong_gateway_marker_does_not_bypass_proxy_key(
        self,
        client,
        monkeypatch,
    ):
        """内部网关标记必须精确匹配，避免任意头值绕过认证"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post(
            '/api/agent/runs/stream',
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-AI4SE-Gateway": "wrong"},
        )
        assert resp.status_code == 401

    def test_no_proxy_key_allows_all(self, client, monkeypatch):
        """未设置 PROXY_API_KEY 时，请求正常放行"""
        monkeypatch.delenv('PROXY_API_KEY', raising=False)
        resp = client.post(
            '/api/agent/runs/stream',
            json=VALID_AGENT_RUN_PAYLOAD,
        )
        assert resp.status_code != 401

    def test_non_stream_endpoint_no_auth(self, client, monkeypatch):
        """非敏感端点不需要认证"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_get_method_on_agent_stream_no_auth(self, client, monkeypatch):
        """GET /api/agent/runs/stream 不需要认证（只对 POST 限制）"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.get('/api/agent/runs/stream')
        assert resp.status_code != 401
