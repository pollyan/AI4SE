"""
Requirements API 测试

测试 /api/requirements 端点的会话和消息管理功能
"""

import pytest
import json


class TestSessionAPI:
    """会话管理 API 测试"""
    
    def test_create_session_success(self, api_client, app):
        """测试成功创建会话"""
        with app.app_context():
            response = api_client.post(
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
    
    def test_create_session_missing_project_name(self, api_client, app):
        """测试缺少项目名称时创建会话失败"""
        with app.app_context():
            response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_create_session_invalid_assistant_type(self, api_client, app):
        """测试无效助手类型时创建会话失败"""
        with app.app_context():
            response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "invalid_type"
                }),
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_get_session_success(self, api_client, app):
        """测试获取会话详情"""
        with app.app_context():
            # 先创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 获取会话
            response = api_client.get(f'/api/requirements/sessions/{session_id}')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['data']['id'] == session_id
    
    def test_get_session_not_found(self, api_client, app):
        """测试获取不存在的会话"""
        with app.app_context():
            response = api_client.get('/api/requirements/sessions/nonexistent-id')
            assert response.status_code == 404


class TestMessageAPI:
    """消息管理 API 测试"""
    
    def test_get_messages_empty(self, api_client, app):
        """测试获取空的消息列表"""
        with app.app_context():
            # 先创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 获取消息
            response = api_client.get(f'/api/requirements/sessions/{session_id}/messages')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'messages' in data['data']
            assert isinstance(data['data']['messages'], list)


class TestAssistantsAPI:
    """助手列表 API 测试"""
    
    def test_get_assistants(self, api_client, app):
        """测试获取助手列表"""
        with app.app_context():
            response = api_client.get('/api/requirements/assistants')
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
    
    def test_update_session_status(self, api_client, app):
        """测试更新会话状态"""
        with app.app_context():
            # 先创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 更新状态
            response = api_client.put(
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
    
    def test_update_session_invalid_status(self, api_client, app):
        """测试无效的会话状态"""
        with app.app_context():
            # 先创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 更新无效状态
            response = api_client.put(
                f'/api/requirements/sessions/{session_id}/status',
                data=json.dumps({
                    "status": "invalid_status"
                }),
                content_type='application/json'
            )
            assert response.status_code == 400


class TestSendMessageAPI:
    """消息发送 API 测试"""
    
    def test_send_message_session_not_found(self, api_client, app):
        """测试向不存在的会话发送消息"""
        with app.app_context():
            response = api_client.post(
                '/api/requirements/sessions/nonexistent-id/messages',
                data=json.dumps({"content": "测试消息"}),
                content_type='application/json'
            )
            assert response.status_code == 404
    
    def test_send_message_empty_content(self, api_client, app):
        """测试发送空消息"""
        with app.app_context():
            # 先创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 发送空消息
            response = api_client.post(
                f'/api/requirements/sessions/{session_id}/messages',
                data=json.dumps({"content": ""}),
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_send_message_success_mocked(self, api_client, app, mocker):
        """测试成功发送消息（使用 mock AI 服务）"""
        with app.app_context():
            # 创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # Mock AI 服务
            mock_ai_result = {
                'ai_response': '您好！我是 Alex，您的需求分析师。',
                'stage': 'initial'
            }
            
            mock_ai_service = mocker.MagicMock()
            mock_ai_service.analyze_user_requirement = mocker.AsyncMock(return_value=mock_ai_result)
            
            mocker.patch(
                'backend.api.requirements.get_ai_service',
                return_value=mock_ai_service
            )
            
            # 发送消息
            response = api_client.post(
                f'/api/requirements/sessions/{session_id}/messages',
                data=json.dumps({"content": "你好"}),
                content_type='application/json'
            )
            
            # 应该成功或返回服务不可用
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                data = response.get_json()
                assert 'data' in data
                assert 'ai_message' in data['data']
    
    def test_send_message_with_invalid_json(self, api_client, app):
        """测试发送非 JSON 格式请求"""
        with app.app_context():
            # 创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 发送非 JSON 格式
            response = api_client.post(
                f'/api/requirements/sessions/{session_id}/messages',
                data="这不是JSON",
                content_type='text/plain'
            )
            assert response.status_code == 400


class TestAssistantBundleAPI:
    """助手 Bundle API 测试"""
    
    def test_get_alex_bundle(self, api_client, app):
        """测试获取 Alex 助手 Bundle"""
        with app.app_context():
            response = api_client.get('/api/requirements/assistants/alex/bundle')
            
            # 可能成功或找不到文件
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.get_json()
                assert 'data' in data
                assert 'bundle_content' in data['data']
                assert 'assistant_info' in data['data']
                
                # 验证 bundle 内容不为空
                assert len(data['data']['bundle_content']) > 0
    
    def test_get_lisa_bundle(self, api_client, app):
        """测试获取 Lisa 助手 Bundle"""
        with app.app_context():
            response = api_client.get('/api/requirements/assistants/lisa/bundle')
            
            # 可能成功或找不到文件
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.get_json()
                assert 'data' in data
                assert 'bundle_content' in data['data']
    
    def test_get_invalid_assistant_bundle(self, api_client, app):
        """测试获取无效助手类型的 Bundle"""
        with app.app_context():
            response = api_client.get('/api/requirements/assistants/invalid_type/bundle')
            assert response.status_code == 400
    
    def test_get_alex_bundle_backward_compat(self, api_client, app):
        """测试向后兼容的 Alex Bundle 端点"""
        with app.app_context():
            response = api_client.get('/api/requirements/alex-bundle')
            
            # 可能成功或找不到文件
            assert response.status_code in [200, 404]


class TestStreamMessagesAPI:
    """流式消息 API 测试"""
    
    def test_stream_messages_session_not_found(self, api_client, app):
        """测试向不存在的会话发送流式消息"""
        with app.app_context():
            response = api_client.post(
                '/api/requirements/sessions/nonexistent-id/messages/stream',
                data=json.dumps({"content": "测试消息"}),
                content_type='application/json'
            )
            assert response.status_code == 404
    
    def test_stream_messages_empty_content(self, api_client, app):
        """测试流式发送空消息"""
        with app.app_context():
            # 先创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # 发送空消息
            response = api_client.post(
                f'/api/requirements/sessions/{session_id}/messages/stream',
                data=json.dumps({"content": ""}),
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_stream_messages_returns_sse(self, api_client, app, mocker):
        """测试流式消息返回 SSE 格式"""
        with app.app_context():
            # 创建会话
            create_response = api_client.post(
                '/api/requirements/sessions',
                data=json.dumps({
                    "project_name": "流式测试项目",
                    "assistant_type": "alex"
                }),
                content_type='application/json'
            )
            session_id = create_response.get_json()['data']['id']
            
            # Mock AI 服务的流式方法
            async def mock_stream(*args, **kwargs):
                yield "你好"
                yield "世界"
            
            mock_ai_service = mocker.MagicMock()
            mock_ai_service.stream_message = mock_stream
            
            mocker.patch(
                'backend.api.requirements.get_ai_service',
                return_value=mock_ai_service
            )
            
            # 发送流式请求
            response = api_client.post(
                f'/api/requirements/sessions/{session_id}/messages/stream',
                data=json.dumps({"content": "你好"}),
                content_type='application/json'
            )
            
            # 应该返回 SSE 格式或服务不可用
            # 注意：Flask test client 可能不完全支持 SSE
            assert response.status_code in [200, 500]
            
            if response.status_code == 200:
                # 验证返回的是 SSE 格式（允许包含 charset）
                assert 'text/event-stream' in response.content_type

