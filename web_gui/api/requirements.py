"""
需求分析API端点
提供需求分析会话和消息管理功能
"""

import uuid
import json
from datetime import datetime
from pathlib import Path
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
    from ..services.requirements_ai_service import RequirementsAIService, IntelligentAssistantService
except ImportError:
    from web_gui.models import db, RequirementsSession, RequirementsMessage
    from web_gui.utils.error_handler import ValidationError, NotFoundError, DatabaseError
    from web_gui.services.requirements_ai_service import RequirementsAIService, IntelligentAssistantService

# AI服务实例（延迟初始化）
ai_service = None

def get_ai_service(assistant_type='alex'):
    """获取AI服务实例，每次重新检查配置避免缓存问题"""
    try:
        from ..models import RequirementsAIConfig
        
        # 每次都重新获取默认AI配置，避免缓存问题
        default_config = RequirementsAIConfig.get_default_config()
        if default_config:
            config_data = default_config.get_config_for_ai_service()
            # 创建智能助手服务实例
            ai_service = IntelligentAssistantService(config=config_data, assistant_type=assistant_type)
            assistant_info = IntelligentAssistantService.SUPPORTED_ASSISTANTS.get(assistant_type, {})
            print(f"✅ 智能助手AI服务初始化成功，使用{assistant_info.get('title', '')} {assistant_info.get('name', '')}，配置: {default_config.config_name}")
            return ai_service
        else:
            # 如果没有默认配置，返回None而不是使用环境变量
            print("⚠️ 未找到默认AI配置")
            return None
    except Exception as e:
        print(f"⚠️ 智能助手AI服务初始化失败: {e}")
        return None

# 创建蓝图
requirements_bp = Blueprint("requirements", __name__, url_prefix="/api/requirements")

# 全局变量存储active会话
active_sessions = {}


@requirements_bp.route("/sessions", methods=["POST"])
@require_json
@log_api_call
def create_session():
    """创建新的智能助手会话"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        project_name = data.get("project_name", "")
        if not project_name or len(project_name.strip()) == 0:
            raise ValidationError("项目名称不能为空")
        
        # 获取助手类型参数
        assistant_type = data.get("assistant_type", "alex")
        
        # 验证助手类型
        if assistant_type not in IntelligentAssistantService.SUPPORTED_ASSISTANTS:
            raise ValidationError(f"不支持的助手类型: {assistant_type}")
        
        # 生成UUID作为会话ID
        session_id = str(uuid.uuid4())
        
        # 创建会话记录，在user_context中记录助手类型
        session = RequirementsSession(
            id=session_id,
            project_name=project_name.strip(),
            session_status="active",
            current_stage="initial",
            user_context=json.dumps({"assistant_type": assistant_type}),
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
    """发送消息到会话（HTTP轮询模式）"""
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
            
        # 获取会话中的助手类型
        user_context = json.loads(session.user_context or "{}")
        assistant_type = user_context.get("assistant_type", "alex")
        
        # 检查是否是激活消息（包含bundle关键标识）
        # 1. 包含明确的bundle激活标识
        # 2. 长度超过5000字符（bundle通常很长）
        # 3. 包含YAML格式的配置内容
        is_activation_message = (
            ("Bundle" in content and ("activation-instructions" in content or "persona:" in content)) or
            len(content) > 5000 or
            ("```yaml" in content and "agent:" in content)
        )
        
        # 字符长度限制：激活消息允许更长，常规消息限制2000字符
        max_length = 50000 if is_activation_message else 2000
        if len(content) > max_length:
            message = f"激活消息内容不能超过{max_length}字符" if is_activation_message else "消息内容不能超过2000字符"
            raise ValidationError(message)
        
        # 创建用户消息（激活消息标记为system类型，不显示给用户）
        user_message = RequirementsMessage(
            session_id=session_id,
            message_type="system" if is_activation_message else "user",
            content=content,
            message_metadata=json.dumps({
                "stage": session.current_stage,
                "char_count": len(content),
                "source": "http",
                "is_activation": is_activation_message
            })
        )
        
        db.session.add(user_message)
        db.session.commit()
        
        # 根据助手类型获取对应的AI服务
        ai_svc = get_ai_service(assistant_type=assistant_type)
        if ai_svc is None:
            raise Exception("AI服务暂不可用，请稍后重试")
        
        try:
            # 构建会话上下文
            session_context = {
                'user_context': json.loads(session.user_context) if session.user_context else {},
                'ai_context': json.loads(session.ai_context) if session.ai_context else {},
                'consensus_content': json.loads(session.consensus_content) if session.consensus_content else {}
            }
            
            # 调用智能助手分析服务
            ai_result = ai_svc.analyze_user_requirement(
                user_message=content,
                session_context=session_context,
                project_name=session.project_name,
                current_stage=session.current_stage,
                session_id=session_id
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
                    'assistant_type': assistant_type,
                    'source': 'http'
                })
            )
            
            # 更新会话上下文和共识内容
            session.ai_context = json.dumps(ai_result.get('ai_context', session_context['ai_context']))
            session.consensus_content = json.dumps(ai_result.get('consensus_content', {}))
            session.current_stage = ai_result.get('stage', session.current_stage)
            session.updated_at = datetime.utcnow()
            
            db.session.add(ai_message)
            db.session.commit()
            
            # 返回结果，仅当不是激活消息时才返回用户消息
            response_data = {
                'ai_message': ai_message.to_dict(),
                'consensus_content': ai_result.get('consensus_content', {}),
                'identified_requirements': ai_result.get('identified_requirements', []),
                'information_gaps': ai_result.get('information_gaps', []),
                'clarification_questions': ai_result.get('clarification_questions', []),
                'current_stage': session.current_stage
            }
            
            # 统一返回格式，包含AI响应和用户消息（如果非激活消息）
            response_data['user_message'] = user_message.to_dict() if not is_activation_message else None
            
            return standard_success_response(
                data=response_data,
                message="消息处理成功"
            )
            
        except Exception as ai_error:
            print(f"❌ AI服务调用失败: {str(ai_error)}")
            # 创建AI服务错误消息
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
            
            # 为了向后兼容，即使AI出错也返回用户消息格式
            if not is_activation_message:
                return standard_success_response(
                    data=user_message.to_dict(),
                    message="消息处理完成（AI服务异常）"
                )
            else:
                return standard_success_response(
                    data={
                        'ai_message': error_message.to_dict(),
                        'error': 'AI服务异常'
                    },
                    message="消息处理完成（AI服务异常）"
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





@requirements_bp.route("/assistants", methods=["GET"])
@log_api_call
def get_assistants():
    """获取支持的助手列表"""
    try:
        assistants = []
        for assistant_id, info in IntelligentAssistantService.SUPPORTED_ASSISTANTS.items():
            assistants.append({
                "id": assistant_id,
                "name": info["name"],
                "title": info["title"],
                "bundle_file": info["bundle_file"]
            })
        
        return {
            "code": 200,
            "data": {"assistants": assistants},
            "message": "获取助手列表成功"
        }
        
    except Exception as e:
        return standard_error_response(f"获取助手列表失败: {str(e)}", 500)


@requirements_bp.route("/assistants/<assistant_type>/bundle", methods=["GET"])
@log_api_call
def get_assistant_bundle(assistant_type):
    """获取指定助手的完整bundle内容"""
    try:
        if assistant_type not in IntelligentAssistantService.SUPPORTED_ASSISTANTS:
            return standard_error_response(f"不支持的助手类型: {assistant_type}", 400)
        
        assistant_info = IntelligentAssistantService.SUPPORTED_ASSISTANTS[assistant_type]
        bundle_file = assistant_info["bundle_file"]
        bundle_path = Path(__file__).parent.parent.parent / "intelligent-requirements-analyzer" / "dist" / bundle_file
        
        if bundle_path.exists():
            with open(bundle_path, 'r', encoding='utf-8') as f:
                bundle_content = f.read()
            
            # 添加系统指令前缀
            full_bundle = f"""你的关键操作指令已附在下方，请严格按照指令中的persona执行，不要打破角色设定。

{bundle_content}"""
                
            return {
                "code": 200,
                "data": {
                    "bundle_content": full_bundle,
                    "assistant_info": assistant_info
                },
                "message": f"获取{assistant_info['title']} {assistant_info['name']} bundle成功"
            }
        else:
            return standard_error_response(f"{assistant_info['title']} bundle文件不存在", 404)
            
    except Exception as e:
        return standard_error_response(f"获取助手bundle失败: {str(e)}", 500)


@requirements_bp.route("/alex-bundle", methods=["GET"])
@log_api_call
def get_alex_bundle():
    """获取完整的Alex需求分析师Bundle内容 - 向后兼容端点"""
    # 直接调用新的助手bundle端点
    return get_assistant_bundle('alex')


@requirements_bp.route("/sessions/<session_id>/poll-messages", methods=["GET"])
@log_api_call
def poll_messages(session_id):
    """轮询获取新消息（用于Vercel环境）"""
    try:
        # 验证会话是否存在
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
        
        # 获取查询参数
        since = request.args.get("since")  # ISO时间戳
        limit = min(int(request.args.get("limit", 10)), 50)  # 最大50条
        
        # 构建查询
        query = RequirementsMessage.query.filter_by(session_id=session_id)
        
        # 过滤掉系统激活消息
        query = query.filter(RequirementsMessage.message_type != 'system')
        
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                query = query.filter(RequirementsMessage.created_at > since_dt)
            except ValueError:
                pass  # 忽略无效的时间格式
        
        # 获取消息，按时间排序
        messages = query.order_by(RequirementsMessage.created_at.asc()).limit(limit).all()
        
        return standard_success_response(
            data={
                "messages": [msg.to_dict() for msg in messages],
                "count": len(messages),
                "session_info": {
                    "current_stage": session.current_stage,
                    "session_status": session.session_status
                }
            },
            message="轮询消息成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except Exception as e:
        return standard_error_response(f"轮询消息失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/messages/<message_id>/refresh", methods=["POST"])
@log_api_call
def refresh_message(session_id, message_id):
    """刷新AI消息内容，重新生成完整回复"""
    try:
        # 验证会话是否存在
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
        
        # 验证消息是否存在且为AI消息
        message = RequirementsMessage.query.filter_by(
            id=message_id, 
            session_id=session_id,
            message_type='ai'
        ).first()
        
        if not message:
            raise NotFoundError("AI消息不存在")
        
        # 获取AI服务实例
        ai_service_instance = get_ai_service()
        if not ai_service_instance:
            return standard_error_response("AI服务未初始化", 500)
        
        # 获取该消息之前的所有历史消息（用于重新生成上下文）
        previous_messages = RequirementsMessage.query.filter(
            RequirementsMessage.session_id == session_id,
            RequirementsMessage.created_at <= message.created_at,
            RequirementsMessage.id != message_id  # 排除当前要刷新的消息
        ).order_by(RequirementsMessage.created_at.asc()).all()
        
        # 找到触发该AI消息的用户消息
        user_message = None
        for prev_msg in reversed(previous_messages):
            if prev_msg.message_type == 'user':
                user_message = prev_msg
                break
        
        if not user_message:
            raise ValidationError("找不到对应的用户消息")
        
        # 重新调用AI服务生成回复
        try:
            ai_result = ai_service_instance.analyze_user_requirement(
                user_message.content,
                session_context={},  # 空上下文，使用全历史模式
                project_name=session.project_name or "刷新项目",
                current_stage="refresh",
                session_id=session_id
            )
            
            if ai_result and 'ai_response' in ai_result:
                # 更新消息内容
                message.content = ai_result['ai_response']
                
                # 在metadata中记录刷新时间
                refresh_time = datetime.utcnow()
                metadata = json.loads(message.message_metadata or '{}')
                metadata['refreshed_at'] = refresh_time.isoformat()
                metadata['refresh_count'] = metadata.get('refresh_count', 0) + 1
                message.message_metadata = json.dumps(metadata)
                
                # 提交数据库更改
                db.session.commit()
                
                # 构造返回的消息数据
                message_dict = message.to_dict()
                message_dict['updated_at'] = refresh_time.isoformat()  # 前端需要的时间戳
                
                return standard_success_response(
                    data={
                        "message": message_dict,
                        "refresh_time": refresh_time.isoformat()
                    },
                    message="AI消息刷新成功"
                )
            else:
                raise Exception("AI服务返回无效响应")
                
        except Exception as ai_error:
            raise Exception(f"AI服务调用失败: {str(ai_error)}")
            
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"刷新消息失败: {str(e)}", 500)


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
                
            # 检查是否是激活消息
            is_activation_message = ("智能需求分析师" in content and "Bundle" in content) or len(content) > 10000
            max_length = 50000 if is_activation_message else 2000
            
            if len(content) > max_length:
                message = f"激活消息内容不能超过{max_length}字符" if is_activation_message else "消息内容不能超过2000字符"
                emit('error', {'message': message})
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
            
            # 调用AI助手服务处理用户消息
            ai_svc = get_ai_service()
            if ai_svc is None:
                emit('error', {'message': 'AI服务暂不可用，请稍后重试'})
                return
            
            try:
                # 构建会话上下文
                session_context = {
                    'user_context': json.loads(session.user_context) if session.user_context else {},
                    'ai_context': json.loads(session.ai_context) if session.ai_context else {},
                    'consensus_content': json.loads(session.consensus_content) if session.consensus_content else {}
                }
                
                # 调用智能助手分析服务
                print(f"🤖 调用AI助手分析用户消息: {content[:50]}...")
                ai_result = ai_svc.analyze_user_requirement(
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
                        'assistant_type': assistant_type
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
                
                print(f"✅ AI助手处理完成，生成了{len(ai_result.get('clarification_questions', []))}个澄清问题")
                
            except Exception as ai_error:
                print(f"❌ AI服务调用失败: {str(ai_error)}")
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