"""
Requirements API 测试

测试 /api/requirements 端点的会话和消息管理功能
"""

import pytest
import json


class TestSessionAPI:
    """会话管理 API 测试"""
    
    def test_create_session_success(self, client, app):
        """测试成功创建会话"""
        with app.app_context():
            response = client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['code'] == 200
            assert 'data' in data
            assert 'id' in data['data']
            assert data['data']['project_name'] == "测试项目"
    
    def test_create_session_missing_project_name(self, client, app):
        """测试缺少项目名称时创建会话失败"""
        with app.app_context():
            response = client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_create_session_invalid_assistant_type(self, client, app):
        """测试无效助手类型时创建会话失败"""
        with app.app_context():
            response = client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "invalid_type"
                }),
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_get_session_success(self, client, app):
        """测试获取会话详情"""
        with app.app_context():
            # 先创建会话
            create_response = client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 获取会话
            response = client.get(f'/api/requirements/sessions/{session_id}')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['data']['id'] == session_id
    
    def test_get_session_not_found(self, client, app):
        """测试获取不存在的会话"""
        with app.app_context():
            response = client.get('/api/requirements/sessions/nonexistent-id')
            assert response.status_code == 404


class TestMessageAPI:
    """消息管理 API 测试"""
    
    def test_get_messages_empty(self, client, app):
        """测试获取空的消息列表"""
        with app.app_context():
            # 先创建会话
            create_response = client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 获取消息
            response = client.get(f'/api/requirements/sessions/{session_id}/messages')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'messages' in data['data']
            assert isinstance(data['data']['messages'], list)


class TestAssistantsAPI:
    """助手列表 API 测试"""
    
    def test_get_assistants(self, client, app):
        """测试获取助手列表"""
        with app.app_context():
            response = client.get('/api/requirements/assistants')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'assistants' in data['data']
            assert len(data['data']['assistants']) > 0
            
            # 验证助手数据结构
            assistant = data['data']['assistants'][0]
            assert 'id' in assistant
            assert 'name' in assistant


class TestSessionStatusAPI:
    """会话状态更新 API 测试"""
    
    def test_update_session_status(self, client, app):
        """测试更新会话状态"""
        with app.app_context():
            # 先创建会话
            create_response = client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 更新状态
            response = client.put(
                f'/api/requirements/sessions/{session_id}/status',
                data=json.dumps({
                    "status": "completed",
                    "stage": "documentation"
                }),
                content_type='application/json'
            )
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['data']['session_status'] == "completed"
    
    def test_update_session_invalid_status(self, client, app):
        """测试无效的会话状态"""
        with app.app_context():
            # 先创建会话
            create_response = client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 更新无效状态
            response = client.put(
                f'/api/requirements/sessions/{session_id}/status',
                data=json.dumps({
                    "status": "invalid_status"
                }),
                content_type='application/json'
            )
            assert response.status_code == 400
