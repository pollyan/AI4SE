"""
需求分析API端点
提供需求分析会话和消息管理功能
"""

import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from .base import (
    standard_success_response,
    standard_error_response,
    require_json,
    log_api_call,
)

# 导入数据模型和服务
try:
    from ..models import db, RequirementsSession, RequirementsMessage
    from ..utils.error_handler import ValidationError, NotFoundError, DatabaseError
    from ..services.requirements_ai_service import RequirementsAIService
except ImportError:
    from web_gui.models import db, RequirementsSession, RequirementsMessage
    from web_gui.utils.error_handler import ValidationError, NotFoundError, DatabaseError
    from web_gui.services.requirements_ai_service import RequirementsAIService

# 初始化AI服务
try:
    ai_service = RequirementsAIService()
    print("✅ 需求分析AI服务初始化成功")
except Exception as e:
    print(f"⚠️ 需求分析AI服务初始化失败: {e}")
    ai_service = None

# 创建蓝图
requirements_bp = Blueprint("requirements", __name__, url_prefix="/api/requirements")

# 全局变量存储active会话
active_sessions = {}


@requirements_bp.route("/sessions", methods=["POST"])
@require_json
@log_api_call
def create_session():
    """创建新的需求分析会话"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        project_name = data.get("project_name", "")
        if not project_name or len(project_name.strip()) == 0:
            raise ValidationError("项目名称不能为空")
        
        # 生成UUID作为会话ID
        session_id = str(uuid.uuid4())
        
        # 创建会话记录
        session = RequirementsSession(
            id=session_id,
            project_name=project_name.strip(),
            session_status="active",
            current_stage="initial",
            user_context=json.dumps({}),
            ai_context=json.dumps({}),
            consensus_content=json.dumps({})
        )
        
        db.session.add(session)
        db.session.commit()
        
        # 注意：不在这里创建欢迎消息
        # 根据BMAD架构，所有消息内容都应该由AI生成
        # 用户进入会话后，前端会发送初始化请求给AI来获取欢迎消息
        
        return standard_success_response(
            data=session.to_dict(),
            message="需求分析会话创建成功"
        )
        
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"创建会话失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>", methods=["GET"])
@log_api_call
def get_session(session_id):
    """获取会话详情"""
    try:
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
        
        # 获取最近20条消息
        messages = RequirementsMessage.get_by_session(session_id, limit=20)
        
        session_data = session.to_dict()
        session_data["messages"] = [msg.to_dict() for msg in messages]
        session_data["message_count"] = RequirementsMessage.query.filter_by(session_id=session_id).count()
        
        return standard_success_response(
            data=session_data,
            message="获取会话详情成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except Exception as e:
        return standard_error_response(f"获取会话失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/messages", methods=["GET"])
@log_api_call
def get_messages(session_id):
    """获取会话消息列表"""
    try:
        # 验证会话是否存在
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
        
        # 获取分页参数
        page = request.args.get("page", 1, type=int)
        size = min(request.args.get("size", 50, type=int), 100)  # 最大100条
        offset = (page - 1) * size
        
        # 获取消息
        messages = RequirementsMessage.get_by_session(session_id, limit=size, offset=offset)
        total_count = RequirementsMessage.query.filter_by(session_id=session_id).count()
        
        return standard_success_response(
            data={
                "messages": [msg.to_dict() for msg in messages],
                "pagination": {
                    "page": page,
                    "size": size,
                    "total": total_count,
                    "pages": (total_count + size - 1) // size
                }
            },
            message="获取消息列表成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except Exception as e:
        return standard_error_response(f"获取消息失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/messages", methods=["POST"])
@require_json
@log_api_call
def send_message(session_id):
    """发送消息到会话"""
    try:
        # 验证会话是否存在
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
            
        if session.session_status != "active":
            raise ValidationError("会话不在活跃状态，无法发送消息")
        
        data = request.get_json()
        content = data.get("content", "").strip()
        
        if not content:
            raise ValidationError("消息内容不能为空")
            
        if len(content) > 2000:
            raise ValidationError("消息内容不能超过2000字符")
        
        # 创建用户消息
        user_message = RequirementsMessage(
            session_id=session_id,
            message_type="user",
            content=content,
            message_metadata=json.dumps({
                "stage": session.current_stage,
                "char_count": len(content)
            })
        )
        
        db.session.add(user_message)
        db.session.commit()
        
        # 触发AI处理（通过WebSocket异步处理）
        # 这里返回用户消息，AI响应会通过WebSocket推送
        
        return standard_success_response(
            data=user_message.to_dict(),
            message="消息发送成功"
        )
        
    except (ValidationError, NotFoundError) as e:
        return standard_error_response(e.message, e.code if hasattr(e, 'code') else 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"发送消息失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/status", methods=["PUT"])
@require_json
@log_api_call
def update_session_status(session_id):
    """更新会话状态"""
    try:
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
        
        data = request.get_json()
        new_status = data.get("status")
        new_stage = data.get("stage")
        
        # 验证状态值
        valid_statuses = ["active", "paused", "completed", "archived"]
        valid_stages = ["initial", "clarification", "consensus", "documentation"]
        
        if new_status and new_status not in valid_statuses:
            raise ValidationError(f"无效的状态值: {new_status}")
            
        if new_stage and new_stage not in valid_stages:
            raise ValidationError(f"无效的阶段值: {new_stage}")
        
        # 更新会话
        if new_status:
            session.session_status = new_status
        if new_stage:
            session.current_stage = new_stage
            
        session.updated_at = datetime.utcnow()
        db.session.commit()
        
        return standard_success_response(
            data=session.to_dict(),
            message="会话状态更新成功"
        )
        
    except (ValidationError, NotFoundError) as e:
        return standard_error_response(e.message, e.code if hasattr(e, 'code') else 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"更新会话状态失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/welcome", methods=["GET"])
@log_api_call
def get_welcome_message(session_id):
    """获取Alex的欢迎消息"""
    try:
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
            
        if ai_service is None:
            raise Exception("AI服务暂不可用")
        
        # 调用Alex生成欢迎消息
        welcome_result = ai_service.generate_welcome_message(session.project_name)
        
        # 创建欢迎消息记录
        welcome_message = RequirementsMessage(
            session_id=session_id,
            message_type='ai',
            content=welcome_result['ai_response'],
            message_metadata=json.dumps({
                'message_type': 'welcome',
                'alex_persona': welcome_result.get('alex_persona', True),
                'analysis_summary': welcome_result.get('analysis_summary', ''),
                'stage': 'initial'
            })
        )
        
        # 初始化会话的共识内容
        session.consensus_content = json.dumps(welcome_result.get('consensus_content', {}))
        session.current_stage = 'initial'
        
        db.session.add(welcome_message)
        db.session.commit()
        
        return standard_success_response(
            data={
                'message': welcome_message.to_dict(),
                'consensus_content': welcome_result.get('consensus_content', {}),
                'information_gaps': welcome_result.get('information_gaps', []),
                'clarification_questions': welcome_result.get('clarification_questions', [])
            },
            message="Alex欢迎消息生成成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"获取欢迎消息失败: {str(e)}", 500)


def register_requirements_socketio(socketio: SocketIO):
    """注册需求分析相关的WebSocket事件处理器"""
    
    @socketio.on('join_requirements_session')
    def on_join_session(data):
        """用户加入需求分析会话"""
        session_id = data.get('session_id')
        if not session_id:
            emit('error', {'message': '缺少session_id参数'})
            return
            
        # 验证会话存在
        session = RequirementsSession.query.get(session_id)
        if not session:
            emit('error', {'message': '会话不存在'})
            return
            
        # 加入房间
        join_room(f'requirements_{session_id}')
        active_sessions[request.sid] = session_id
        
        emit('joined_session', {
            'session_id': session_id,
            'session_info': session.to_dict()
        })
        
        print(f"用户 {request.sid} 加入需求分析会话: {session_id}")
    
    @socketio.on('leave_requirements_session')
    def on_leave_session(data):
        """用户离开需求分析会话"""
        session_id = data.get('session_id')
        if session_id:
            leave_room(f'requirements_{session_id}')
            
        if request.sid in active_sessions:
            del active_sessions[request.sid]
            
        emit('left_session', {'session_id': session_id})
        print(f"用户 {request.sid} 离开需求分析会话: {session_id}")
    
    @socketio.on('requirements_message')
    def on_requirements_message(data):
        """处理需求分析消息"""
        try:
            session_id = data.get('session_id')
            content = data.get('content', '').strip()
            
            if not session_id or not content:
                emit('error', {'message': '缺少session_id或content参数'})
                return
                
            if len(content) > 2000:
                emit('error', {'message': '消息内容不能超过2000字符'})
                return
            
            # 验证会话
            session = RequirementsSession.query.get(session_id)
            if not session or session.session_status != 'active':
                emit('error', {'message': '会话不存在或不在活跃状态'})
                return
            
            # 保存用户消息
            user_message = RequirementsMessage(
                session_id=session_id,
                message_type='user',
                content=content,
                message_metadata=json.dumps({
                    'stage': session.current_stage,
                    'char_count': len(content),
                    'source': 'websocket'
                })
            )
            
            db.session.add(user_message)
            db.session.commit()
            
            # 广播用户消息到房间内所有客户端
            socketio.emit('new_message', {
                'message': user_message.to_dict(),
                'session_id': session_id
            }, room=f'requirements_{session_id}')
            
            # 调用真实的Alex AI服务处理用户消息
            if ai_service is None:
                emit('error', {'message': 'AI服务暂不可用，请稍后重试'})
                return
            
            try:
                # 构建会话上下文
                session_context = {
                    'user_context': json.loads(session.user_context) if session.user_context else {},
                    'ai_context': json.loads(session.ai_context) if session.ai_context else {},
                    'consensus_content': json.loads(session.consensus_content) if session.consensus_content else {}
                }
                
                # 调用Alex智能需求分析服务
                print(f"🤖 调用Alex分析用户消息: {content[:50]}...")
                ai_result = ai_service.analyze_user_requirement(
                    user_message=content,
                    session_context=session_context,
                    project_name=session.project_name,
                    current_stage=session.current_stage
                )
                
                # 创建AI响应消息
                ai_message = RequirementsMessage(
                    session_id=session_id,
                    message_type='ai',
                    content=ai_result['ai_response'],
                    message_metadata=json.dumps({
                        'stage': ai_result.get('stage', session.current_stage),
                        'identified_requirements': ai_result.get('identified_requirements', []),
                        'information_gaps': ai_result.get('information_gaps', []),
                        'clarification_questions': ai_result.get('clarification_questions', []),
                        'analysis_summary': ai_result.get('analysis_summary', ''),
                        'alex_persona': ai_result.get('alex_persona', True)
                    })
                )
                
                # 更新会话上下文和共识内容
                session.ai_context = json.dumps(ai_result.get('ai_context', session_context['ai_context']))
                session.consensus_content = json.dumps(ai_result.get('consensus_content', {}))
                session.current_stage = ai_result.get('stage', session.current_stage)
                session.updated_at = datetime.utcnow()
                
                db.session.add(ai_message)
                db.session.commit()
                
                # 广播AI回应到房间内所有客户端
                socketio.emit('new_message', {
                    'message': ai_message.to_dict(),
                    'session_id': session_id
                }, room=f'requirements_{session_id}')
                
                # 发送共识内容更新
                socketio.emit('consensus_updated', {
                    'session_id': session_id,
                    'consensus_content': ai_result.get('consensus_content', {}),
                    'identified_requirements': ai_result.get('identified_requirements', []),
                    'information_gaps': ai_result.get('information_gaps', []),
                    'clarification_questions': ai_result.get('clarification_questions', []),
                    'current_stage': session.current_stage
                }, room=f'requirements_{session_id}')
                
                print(f"✅ Alex处理完成，生成了{len(ai_result.get('clarification_questions', []))}个澄清问题")
                
            except Exception as ai_error:
                print(f"❌ Alex AI服务调用失败: {str(ai_error)}")
                # 发送AI服务错误消息
                error_message = RequirementsMessage(
                    session_id=session_id,
                    message_type='system',
                    content=f"抱歉，AI分析服务遇到了问题：{str(ai_error)}。请稍后重试，或重新描述您的需求。",
                    message_metadata=json.dumps({
                        'error_type': 'ai_service_error',
                        'error_details': str(ai_error),
                        'stage': session.current_stage
                    })
                )
                
                db.session.add(error_message)
                db.session.commit()
                
                socketio.emit('new_message', {
                    'message': error_message.to_dict(),
                    'session_id': session_id
                }, room=f'requirements_{session_id}')
            
        except Exception as e:
            print(f"处理需求分析消息时出错: {str(e)}")
            emit('error', {'message': f'处理消息失败: {str(e)}'})
    
    @socketio.on('disconnect')
    def on_disconnect():
        """客户端断开连接时清理"""
        if request.sid in active_sessions:
            session_id = active_sessions[request.sid]
            leave_room(f'requirements_{session_id}')
            del active_sessions[request.sid]
            print(f"客户端 {request.sid} 断开连接，清理会话: {session_id}")


# 注意：根据BMAD架构原则，以下函数已移除
# 所有业务逻辑决策（包括AI响应内容生成、共识提取等）都应该由AI服务处理
# Web层只负责数据传输和存储，不做任何内容生成或业务逻辑判断

# 真实实现中，应该有一个独立的AI服务端点，比如：
# POST /ai/requirements/analyze
# 参数：用户消息、会话上下文、当前阶段
# 返回：AI响应内容、更新的共识、新的阶段状态