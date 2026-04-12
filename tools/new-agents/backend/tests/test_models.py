"""
Model Tests - LlmConfig 模型测试
"""

import pytest
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['FLASK_TESTING'] = '1'

from app import create_app
from models import db, LlmConfig


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


class TestLlmConfig:
    """测试 LlmConfig 模型"""

    def test_basic_creation_and_attributes(self, app):
        """LlmConfig 基本创建和属性"""
        with app.app_context():
            config = LlmConfig(
                config_key='test',
                api_key='sk-123',
                base_url='https://api.test.com',
                model='gpt-4',
                description='Test config'
            )
            db.session.add(config)
            db.session.commit()

            fetched = LlmConfig.query.filter_by(config_key='test').first()
            assert fetched is not None
            assert fetched.config_key == 'test'
            assert fetched.api_key == 'sk-123'
            assert fetched.base_url == 'https://api.test.com'
            assert fetched.model == 'gpt-4'
            assert fetched.description == 'Test config'
            assert fetched.is_active is True

    def test_to_dict_excludes_api_key(self, app):
        """to_dict() 不包含 api_key 字段"""
        with app.app_context():
            config = LlmConfig(
                config_key='test',
                api_key='sk-secret-key',
                base_url='https://api.test.com',
                model='gpt-4',
                description='Test config'
            )
            db.session.add(config)
            db.session.commit()

            d = config.to_dict()
            assert 'api_key' not in d
            assert d['config_key'] == 'test'
            assert d['base_url'] == 'https://api.test.com'
            assert d['model'] == 'gpt-4'
