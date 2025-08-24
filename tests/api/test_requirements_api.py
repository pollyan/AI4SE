"""
需求分析API测试
测试需求分析相关的REST API端点
"""

import pytest
import json
import uuid
from datetime import datetime

from web_gui.models import db, RequirementsSession, RequirementsMessage


class TestRequirementsAPI:
    """需求分析API测试类 - 专注于数据传输和基础功能测试"""

    def test_create_session_success(self, api_client, assert_api_response):
        """测试创建需求分析会话 - 验证数据传输和存储功能"""
        data = {
            "project_name": "测试项目"
        }
        
        response = api_client.post('/api/requirements/sessions', json=data)
        result = assert_api_response(response, 200)
        
        # 验证基础数据结构和传输功能（assert_api_response已返回data字段内容）
        assert 'id' in result
        assert result['project_name'] == data['project_name']  # 输入传递正确
        assert result['session_status'] == 'active'  # 状态初始化正确
        assert result['current_stage'] == 'initial'  # 阶段初始化正确
        assert 'created_at' in result  # 时间戳正确记录
        
        # 验证数据库持久化功能
        session_id = result['id']
        session = RequirementsSession.query.get(session_id)
        assert session is not None
        assert session.project_name == data['project_name']  # 数据正确保存

    def test_create_session_invalid_data(self, api_client, assert_api_response):
        """测试创建会话时数据验证"""
        # 空项目名
        response = api_client.post('/api/requirements/sessions', json={
            "project_name": ""
        })
        assert_api_response(response, 400)
        
        # 缺少项目名
        response = api_client.post('/api/requirements/sessions', json={})
        assert_api_response(response, 400)
        
        # 只有空格的项目名
        response = api_client.post('/api/requirements/sessions', json={
            "project_name": "   "
        })
        assert_api_response(response, 400)

    def test_get_session_success(self, api_client, assert_api_response, create_test_requirements_session):
        """测试获取会话详情成功"""
        session = create_test_requirements_session()
        
        response = api_client.get(f'/api/requirements/sessions/{session.id}')
        result = assert_api_response(response, 200)
        
        # 验证返回的会话数据（专注数据传输验证）
        assert result['id'] == session.id
        assert result['project_name'] == session.project_name
        assert result['session_status'] == session.session_status
        assert result['current_stage'] == session.current_stage
        
        # 验证包含消息列表
        assert 'messages' in result
        assert 'message_count' in result
        assert isinstance(result['messages'], list)

    def test_get_session_not_found(self, api_client, assert_api_response):
        """测试获取不存在的会话"""
        fake_id = str(uuid.uuid4())
        response = api_client.get(f'/api/requirements/sessions/{fake_id}')
        assert_api_response(response, 404)

    def test_get_messages_success(self, api_client, assert_api_response, create_test_requirements_session):
        """测试获取会话消息列表"""
        session = create_test_requirements_session()
        
        # 添加测试消息
        msg1 = RequirementsMessage(
            session_id=session.id,
            message_type='user',
            content='用户测试消息1',
            message_metadata=json.dumps({'test': True})
        )
        msg2 = RequirementsMessage(
            session_id=session.id,
            message_type='assistant',
            content='AI回复消息1',
            message_metadata=json.dumps({'test': True})
        )
        
        db.session.add_all([msg1, msg2])
        db.session.commit()
        
        response = api_client.get(f'/api/requirements/sessions/{session.id}/messages')
        result = assert_api_response(response, 200)
        
        # 验证分页信息
        assert 'messages' in result
        assert 'pagination' in result
        assert result['pagination']['total'] == 2
        assert len(result['messages']) == 2
        
        # 验证消息顺序（按时间升序）
        messages = result['messages']
        assert messages[0]['message_type'] == 'user'
        assert messages[1]['message_type'] == 'assistant'

    def test_get_messages_pagination(self, api_client, assert_api_response, create_test_requirements_session):
        """测试消息分页功能"""
        session = create_test_requirements_session()
        
        # 创建多条消息
        for i in range(10):
            msg = RequirementsMessage(
                session_id=session.id,
                message_type='user' if i % 2 == 0 else 'assistant',
                content=f'测试消息{i}',
                message_metadata=json.dumps({'index': i})
            )
            db.session.add(msg)
        
        db.session.commit()
        
        # 测试第一页
        response = api_client.get(f'/api/requirements/sessions/{session.id}/messages?page=1&size=5')
        result = assert_api_response(response, 200)
        
        assert len(result['messages']) == 5
        assert result['pagination']['page'] == 1
        assert result['pagination']['size'] == 5
        assert result['pagination']['total'] == 10
        assert result['pagination']['pages'] == 2
        
        # 测试第二页
        response = api_client.get(f'/api/requirements/sessions/{session.id}/messages?page=2&size=5')
        result = assert_api_response(response, 200)
        
        assert len(result['messages']) == 5
        assert result['pagination']['page'] == 2

    def test_send_message_success(self, api_client, assert_api_response, create_test_requirements_session):
        """测试发送消息成功"""
        session = create_test_requirements_session()
        
        data = {
            "content": "我想开发一个在线购物平台"
        }
        
        response = api_client.post(f'/api/requirements/sessions/{session.id}/messages', json=data)
        result = assert_api_response(response, 200)
        
        # 验证返回的消息
        assert result['session_id'] == session.id
        assert result['message_type'] == 'user'
        assert result['content'] == data['content']
        assert 'created_at' in result
        
        # 验证数据库中的消息
        message = RequirementsMessage.query.filter_by(
            session_id=session.id,
            message_type='user'
        ).first()
        assert message is not None
        assert message.content == data['content']

    def test_send_message_validation(self, api_client, assert_api_response, create_test_requirements_session):
        """测试发送消息时的数据验证"""
        session = create_test_requirements_session()
        
        # 空消息内容
        response = api_client.post(f'/api/requirements/sessions/{session.id}/messages', json={
            "content": ""
        })
        assert_api_response(response, 400)
        
        # 缺少消息内容
        response = api_client.post(f'/api/requirements/sessions/{session.id}/messages', json={})
        assert_api_response(response, 400)
        
        # 消息内容过长
        long_content = "x" * 2001
        response = api_client.post(f'/api/requirements/sessions/{session.id}/messages', json={
            "content": long_content
        })
        assert_api_response(response, 400)

    def test_send_message_to_nonexistent_session(self, api_client, assert_api_response):
        """测试向不存在的会话发送消息"""
        fake_id = str(uuid.uuid4())
        
        response = api_client.post(f'/api/requirements/sessions/{fake_id}/messages', json={
            "content": "测试消息"
        })
        assert_api_response(response, 404)

    def test_send_message_to_inactive_session(self, api_client, assert_api_response, create_test_requirements_session):
        """测试向非活跃会话发送消息"""
        session = create_test_requirements_session()
        session.session_status = 'paused'
        db.session.commit()
        
        response = api_client.post(f'/api/requirements/sessions/{session.id}/messages', json={
            "content": "测试消息"
        })
        assert_api_response(response, 400)

    def test_update_session_status_success(self, api_client, assert_api_response, create_test_requirements_session):
        """测试更新会话状态成功"""
        session = create_test_requirements_session()
        
        # 更新状态
        data = {
            "status": "paused",
            "stage": "clarification"
        }
        
        response = api_client.put(f'/api/requirements/sessions/{session.id}/status', json=data)
        result = assert_api_response(response, 200)
        
        # 验证返回数据
        assert result['session_status'] == 'paused'
        assert result['current_stage'] == 'clarification'
        
        # 验证数据库更新
        updated_session = RequirementsSession.query.get(session.id)
        assert updated_session.session_status == 'paused'
        assert updated_session.current_stage == 'clarification'

    def test_update_session_status_validation(self, api_client, assert_api_response, create_test_requirements_session):
        """测试更新会话状态时的数据验证"""
        session = create_test_requirements_session()
        
        # 无效状态
        response = api_client.put(f'/api/requirements/sessions/{session.id}/status', json={
            "status": "invalid_status"
        })
        assert_api_response(response, 400)
        
        # 无效阶段
        response = api_client.put(f'/api/requirements/sessions/{session.id}/status', json={
            "stage": "invalid_stage"
        })
        assert_api_response(response, 400)

    def test_update_session_status_not_found(self, api_client, assert_api_response):
        """测试更新不存在会话的状态"""
        fake_id = str(uuid.uuid4())
        
        response = api_client.put(f'/api/requirements/sessions/{fake_id}/status', json={
            "status": "paused"
        })
        assert_api_response(response, 404)

    def test_get_welcome_message_ai_unavailable(self, api_client, assert_api_response, create_test_requirements_session):
        """测试AI服务不可用时的响应 - 验证错误传输功能"""
        session = create_test_requirements_session()
        
        # 在测试环境中，AI服务通常不可用（缺少API密钥）
        response = api_client.get(f'/api/requirements/sessions/{session.id}/welcome')
        # AI服务不可用应该返回500错误
        assert_api_response(response, 500)
    
    def test_get_welcome_message_not_found(self, api_client, assert_api_response):
        """测试获取不存在会话的欢迎消息"""
        response = api_client.get('/api/requirements/sessions/nonexistent-id/welcome')
        assert_api_response(response, 404)

    def test_session_model_methods(self, create_test_requirements_session):
        """测试RequirementsSession模型方法"""
        session = create_test_requirements_session()
        
        # 测试to_dict方法
        session_dict = session.to_dict()
        assert session_dict['id'] == session.id
        assert session_dict['project_name'] == session.project_name
        assert session_dict['session_status'] == session.session_status
        assert session_dict['current_stage'] == session.current_stage
        assert isinstance(session_dict['user_context'], dict)
        assert isinstance(session_dict['ai_context'], dict)
        assert isinstance(session_dict['consensus_content'], dict)
        
        # 测试update_context方法
        user_context = {'key1': 'value1'}
        ai_context = {'key2': 'value2'}
        consensus = {'requirements': ['需求1', '需求2']}
        
        session.update_context(
            user_context=user_context,
            ai_context=ai_context,
            consensus_content=consensus
        )
        
        updated_dict = session.to_dict()
        assert updated_dict['user_context'] == user_context
        assert updated_dict['ai_context'] == ai_context
        assert updated_dict['consensus_content'] == consensus

    def test_message_model_methods(self, create_test_requirements_session):
        """测试RequirementsMessage模型方法"""
        session = create_test_requirements_session()
        
        # 创建测试消息
        message_data = {
            'session_id': session.id,
            'message_type': 'user',
            'content': '测试消息内容',
            'metadata': {'key': 'value'}
        }
        
        message = RequirementsMessage.from_dict(message_data)
        db.session.add(message)
        db.session.commit()
        
        # 测试to_dict方法
        message_dict = message.to_dict()
        assert message_dict['session_id'] == session.id
        assert message_dict['message_type'] == 'user'
        assert message_dict['content'] == '测试消息内容'
        assert message_dict['metadata'] == {'key': 'value'}
        assert 'created_at' in message_dict
        
        # 测试get_by_session方法
        messages = RequirementsMessage.get_by_session(session.id, limit=10)
        assert len(messages) >= 1
        assert messages[0].session_id == session.id


@pytest.fixture
def create_test_requirements_session():
    """创建测试需求分析会话的固件"""
    def _create_session(project_name="测试项目", status="active", stage="initial"):
        session = RequirementsSession(
            id=str(uuid.uuid4()),
            project_name=project_name,
            session_status=status,
            current_stage=stage,
            user_context=json.dumps({}),
            ai_context=json.dumps({}),
            consensus_content=json.dumps({})
        )
        db.session.add(session)
        db.session.commit()
        return session
    
    created_sessions = []
    
    def create_wrapper(*args, **kwargs):
        session = _create_session(*args, **kwargs)
        created_sessions.append(session)
        return session
    
    yield create_wrapper
    
    # 清理测试数据
    for session in created_sessions:
        # 删除相关消息
        RequirementsMessage.query.filter_by(session_id=session.id).delete()
        # 删除会话
        db.session.delete(session)
    
    db.session.commit()