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
        resp = client.post('/api/chat/stream', json={"messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code == 401

    def test_wrong_key_returns_401(self, client, monkeypatch):
        """设置 PROXY_API_KEY 后，错误 Key 返回 401"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post('/api/chat/stream',
                           json={"messages": [{"role": "user", "content": "hi"}]},
                           headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401

    def test_correct_key_passes(self, client, app, monkeypatch):
        """设置 PROXY_API_KEY 后，正确 Key 放行（可能因无配置返回 503，但不是 401）"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.post('/api/chat/stream',
                           json={"messages": [{"role": "user", "content": "hi"}]},
                           headers={"X-API-Key": "secret-key"})
        assert resp.status_code != 401

    def test_no_proxy_key_allows_all(self, client, monkeypatch):
        """未设置 PROXY_API_KEY 时，请求正常放行"""
        monkeypatch.delenv('PROXY_API_KEY', raising=False)
        resp = client.post('/api/chat/stream',
                           json={"messages": [{"role": "user", "content": "hi"}]})
        assert resp.status_code != 401

    def test_non_stream_endpoint_no_auth(self, client, monkeypatch):
        """非 /api/chat/stream 端点不需要认证"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.get('/api/health')
        assert resp.status_code == 200

    def test_get_method_on_stream_no_auth(self, client, monkeypatch):
        """GET /api/chat/stream 不需要认证（只对 POST 限制）"""
        monkeypatch.setenv('PROXY_API_KEY', 'secret-key')
        resp = client.get('/api/chat/stream')
        # GET on /api/chat/stream returns 405 Method Not Allowed, not 401
        assert resp.status_code != 401
