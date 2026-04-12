"""
CORS Whitelist Tests - P0-1 CORS 白名单测试
"""

import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['FLASK_TESTING'] = '1'


class TestCORSDefault:
    """测试默认 CORS 配置"""

    def test_allowed_origin_gets_cors_headers(self):
        """允许的 Origin 获得 CORS 头"""
        from app import create_app
        db_fd, db_path = tempfile.mkstemp()
        os.environ.pop('CORS_ORIGINS', None)
        app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        })
        client = app.test_client()
        resp = client.get('/api/health', headers={"Origin": "http://localhost:5173"})
        assert resp.headers.get('Access-Control-Allow-Origin') == 'http://localhost:5173'
        os.close(db_fd)
        os.unlink(db_path)

    def test_disallowed_origin_no_cors_headers(self):
        """不允许的 Origin 不获得 CORS 头"""
        from app import create_app
        db_fd, db_path = tempfile.mkstemp()
        os.environ.pop('CORS_ORIGINS', None)
        app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        })
        client = app.test_client()
        resp = client.get('/api/health', headers={"Origin": "http://evil.com"})
        assert resp.headers.get('Access-Control-Allow-Origin') is None
        os.close(db_fd)
        os.unlink(db_path)

    def test_custom_cors_origins_env(self):
        """自定义 CORS_ORIGINS 环境变量生效"""
        from app import create_app
        db_fd, db_path = tempfile.mkstemp()
        os.environ['CORS_ORIGINS'] = 'http://myapp.com,http://other.com'
        app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        })
        client = app.test_client()

        # Allowed
        resp = client.get('/api/health', headers={"Origin": "http://myapp.com"})
        assert resp.headers.get('Access-Control-Allow-Origin') == 'http://myapp.com'

        # Not allowed
        resp2 = client.get('/api/health', headers={"Origin": "http://localhost:5173"})
        assert resp2.headers.get('Access-Control-Allow-Origin') is None

        os.environ.pop('CORS_ORIGINS', None)
        os.close(db_fd)
        os.unlink(db_path)
