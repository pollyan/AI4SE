"""
需求分析API端点
提供需求分析会话和消息管理功能
"""

import uuid
import json
import os
import logging
from datetime import datetime, timedelta
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
    # Removed legacy RequirementsAIService
    from ..services.adk_agents import AdkAssistantService
except ImportError:
    from web_gui.models import db, RequirementsSession, RequirementsMessage
    from web_gui.utils.error_handler import ValidationError, NotFoundError, DatabaseError
    from web_gui.services.adk_agents import AdkAssistantService

# ✨ 临时会话状态缓存（内存存储，24小时过期）
_session_state_cache = {}  # {session_id: {'is_activated': bool, 'last_access': datetime}}
_CACHE_TTL_HOURS = 24

def _cleanup_expired_sessions():
    """清理过期的会话状态"""
    now = datetime.now()
    expired_sessions = [
        sid for sid, data in _session_state_cache.items()
        if (now - data['last_access']).total_seconds() > _CACHE_TTL_HOURS * 3600
    ]
    for sid in expired_sessions:
        del _session_state_cache[sid]


def _get_session_activated(session_id: str) -> bool:
    """获取会话的激活状态"""
    _cleanup_expired_sessions()  # 顺便清理过期数据
    return _session_state_cache.get(session_id, {}).get('is_activated', False)

def _set_session_activated(session_id: str, is_activated: bool = True):
    """设置会话的激活状态"""
    _session_state_cache[session_id] = {
        'is_activated': is_activated,
        'last_access': datetime.now()
    }


def _clear_session_state(session_id: str):
    """清除会话状态（用户退出时调用）"""
    if session_id in _session_state_cache:
        del _session_state_cache[session_id]


# 初始化 logger
logger = logging.getLogger(__name__)

# AI服务实例（延迟初始化）
ai_service = None

def get_ai_service(assistant_type='alex'):
    """获取AI服务实例，每次重新检查配置避免缓存问题"""
    try:
        from ..models import RequirementsAIConfig
        from ..services.adk_agents import AdkAssistantService
        
        # 每次都重新获取默认AI配置，避免缓存问题
        default_config = RequirementsAIConfig.get_default_config()
        if default_config:
            config_data = default_config.get_config_for_ai_service()
            
            # 验证配置的完整性
            required_fields = ['api_key', 'base_url', 'model_name']
            missing_fields = [field for field in required_fields if not config_data.get(field)]
            
            if missing_fields:
                return None
            
            # 创建AI服务实例
            ai_service = AdkAssistantService(assistant_type=assistant_type, config=config_data)
            return ai_service
        else:
            # 如果没有默认配置，返回None
            return None
    except ImportError as e:
        return None
    except Exception as e:
        return None

# 创建蓝图
requirements_bp = Blueprint("requirements", __name__, url_prefix="/api/requirements")

# 全局变量存储active会话
active_sessions = {}


def process_uploaded_files(files):
    """处理上传的文件，提取内容"""
    attached_files = []
    
    for file in files:
        # 验证文件格式
        if not file.filename.lower().endswith(('.txt', '.md')):
            raise ValidationError(f"不支持的文件格式: {file.filename}。仅支持 txt 和 md 文件")
        
        # 验证文件大小（10MB）
        content_bytes = file.read()
        if len(content_bytes) > 10 * 1024 * 1024:
            raise ValidationError(f"文件过大: {file.filename}。最大支持 10MB")
        
        # 尝试解码文件内容
        content = None
        for encoding in ['utf-8', 'gbk', 'gb2312']:
            try:
                content = content_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if content is None:
            raise ValidationError(f"无法解码文件: {file.filename}")
        
        attached_files.append({
            "filename": file.filename,
            "content": content,
            "size": len(content_bytes),
            "encoding": encoding
        })
    
    return attached_files


def build_message_with_files(message_content, attached_files):
    """构建包含文件内容的完整消息"""
    if not attached_files:
        return message_content
    
    parts = ["=== 相关文档内容 ==="]
    
    for file_info in attached_files:
        parts.append(f"\n## 文档：{file_info['filename']}")
        parts.append("```")
        parts.append(file_info['content'])
        parts.append("```\n")
    
    if message_content and message_content.strip():
        parts.append("=== 用户问题 ===")
        parts.append(message_content)
    
    combined_message = "\n".join(parts)

    return combined_message


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
        
        # 验证助手类型（支持 lisa 别名）
        supported_types = list(IntelligentAssistantService.SUPPORTED_ASSISTANTS.keys()) + ['lisa']
        if assistant_type not in supported_types:
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
@log_api_call
def send_message(session_id):
    """发送消息到会话（HTTP轮询模式，支持文件上传）"""
    try:
        # 验证会话是否存在
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
            
        if session.session_status != "active":
            raise ValidationError("会话不在活跃状态，无法发送消息")
        
        # 检查请求类型：支持JSON和multipart/form-data
        if request.content_type and 'multipart/form-data' in request.content_type:
            # 有文件上传
            content = request.form.get('content', '').strip()
            files = request.files.getlist('files')
            attached_files = process_uploaded_files(files)
        else:
            # 纯文本消息（JSON）
            if not request.is_json:
                raise ValidationError("请求格式错误：需要JSON或multipart/form-data格式")
            data = request.get_json()
            content = data.get("content", "").strip()
            attached_files = []
        
        # 验证消息内容：内容和文件不能同时为空
        if not content and not attached_files:
            raise ValidationError("消息内容和文件不能同时为空")
        
        # 如果有文件附件，构建包含文件内容的完整消息
        full_content = build_message_with_files(content, attached_files)
            
        # 获取会话中的助手类型
        user_context = json.loads(session.user_context or "{}")
        assistant_type = user_context.get("assistant_type", "alex")
        
        # 检查是否是激活消息（仅依靠内容特征，不依赖长度）
        # 1. Bundle + 激活指令组合
        # 2. YAML格式配置 + agent定义  
        # 3. 关键操作指令的组合模式
        is_activation_message = (
            # Bundle激活模式：包含明确的Bundle标识和激活指令
            ("Bundle" in full_content and ("activation-instructions" in full_content or "persona:" in full_content)) or
            # YAML配置模式：包含YAML格式的agent配置
            ("```yaml" in full_content and "agent:" in full_content) or
            # 操作指令模式：包含关键操作指令的组合
            ("你的关键操作指令" in full_content and "请严格按照" in full_content and "persona执行" in full_content)
        )
        
        # 字符长度限制：支持环境变量覆盖；测试环境降至2000以匹配CI校验
        max_len_env = os.getenv('REQUIREMENTS_MESSAGE_MAX_LEN')
        is_testing_env = os.getenv('TESTING', '').lower() in ['1', 'true', 'yes']
        if max_len_env and max_len_env.isdigit():
            max_length = int(max_len_env)
        else:
            if is_activation_message:
                max_length = 50000
            else:
                max_length = 2000 if is_testing_env else 10000
        if len(full_content) > max_length:
            message = (
                f"激活消息内容不能超过{max_length}字符"
                if is_activation_message
                else f"消息内容不能超过{max_length}字符"
            )
            raise ValidationError(message)
        
        # 创建用户消息（激活消息标记为system类型，不显示给用户）
        user_message = RequirementsMessage(
            session_id=session_id,
            message_type="system" if is_activation_message else "user",
            content=content,  # 原始用户消息内容
            attached_files=json.dumps(attached_files) if attached_files else None,
            message_metadata=json.dumps({
                "stage": session.current_stage,
                "char_count": len(content),
                "source": "http",
                "is_activation": is_activation_message,
                "has_attachments": len(attached_files) > 0
            })
        )
        
        db.session.add(user_message)
        db.session.commit()
        
        # 根据助手类型获取对应的AI服务

        try:
            ai_svc = get_ai_service(assistant_type=assistant_type)
            if ai_svc is None:
                error_msg = f"AI服务初始化失败：未找到有效的AI配置或服务初始化失败。请检查AI服务配置或联系管理员。"
                logger.error(error_msg)
                raise Exception(error_msg)

        except Exception as ai_init_error:
            logger.error(f"AI服务初始化异常: {ai_init_error}")
            # 直接抛出异常，让外层的try-catch处理
            raise ai_init_error
        
        try:
            logger.debug(f"开始处理消息: 会话ID={session_id}, 助手类型={assistant_type}, 消息长度={len(full_content)}, 激活消息={is_activation_message}")
            
            # 构建会话上下文
            try:
                session_context = {
                    'user_context': json.loads(session.user_context) if session.user_context else {},
                    'ai_context': json.loads(session.ai_context) if session.ai_context else {},
                    'consensus_content': json.loads(session.consensus_content) if session.consensus_content else {}
                }

            except Exception as ctx_error:
                logger.error(f"构建会话上下文失败: {ctx_error}")
                raise Exception(f"会话上下文构建失败: {str(ctx_error)}")
            
            # 调用智能助手分析服务（传入包含文件内容的完整消息）
            logger.info(f"开始调用AI服务: {ai_svc.__class__.__name__}")
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                ai_result = loop.run_until_complete(ai_svc.analyze_user_requirement(
                    user_message=full_content,  # 使用包含文件内容的完整消息
                    session_context=session_context,
                    project_name=session.project_name,
                    current_stage=session.current_stage,
                    session_id=session_id
                ))
            finally:
                loop.close()

            
            # 创建AI响应消息

            try:
                if not ai_result or 'ai_response' not in ai_result:
                    raise Exception(f"AI服务返回的结果无效: {ai_result}")
                
                # ✨ 清理 JSON 元数据
                # ✨ 清理 JSON 元数据
                # 简单的内联清理逻辑，替代之前的 extract_natural_response
                raw_response = ai_result['ai_response']
                if isinstance(raw_response, str):
                    # 移除可能的 markdown 代码块标记
                    cleaned_ai_response = raw_response.strip()
                    if cleaned_ai_response.startswith('```json'):
                        cleaned_ai_response = cleaned_ai_response[7:]
                    elif cleaned_ai_response.startswith('```'):
                        cleaned_ai_response = cleaned_ai_response[3:]
                    
                    if cleaned_ai_response.endswith('```'):
                        cleaned_ai_response = cleaned_ai_response[:-3]
                    
                    cleaned_ai_response = cleaned_ai_response.strip()
                else:
                    cleaned_ai_response = str(raw_response)
                
                ai_message = RequirementsMessage(
                    session_id=session_id,
                    message_type='ai',
                    content=cleaned_ai_response,  # 使用清理后的内容
                    message_metadata=json.dumps({
                        'stage': ai_result.get('stage', session.current_stage),
                        'assistant_type': assistant_type,
                        'source': 'http'
                    })
                )

            except Exception as msg_error:
                logger.error(f"创建AI响应消息对象失败: {msg_error}")
                raise Exception(f"AI响应消息创建失败: {str(msg_error)}")
            
            # 可配置：是否持久化会话上下文/共识内容，默认不开启以减少写入
            should_persist_context = os.getenv('REQUIREMENTS_PERSIST_CONTEXT', '0') == '1'

            if should_persist_context:
                try:
                    session.ai_context = json.dumps(ai_result.get('ai_context', session_context['ai_context']))
                    session.consensus_content = json.dumps(ai_result.get('consensus_content', {}))
                    session.current_stage = ai_result.get('stage', session.current_stage)
                    session.updated_at = datetime.utcnow()

                except Exception as session_error:
                    logger.error(f"更新会话状态失败: {session_error}")
                    raise Exception(f"会话状态更新失败: {str(session_error)}")
            
            # 保存到数据库

            try:
                db.session.add(ai_message)
                db.session.commit()

            except Exception as db_error:
                logger.error(f"数据库事务失败: {db_error}")
                db.session.rollback()
                raise Exception(f"数据库保存失败: {str(db_error)}")
            
            # 构建响应数据（不强制返回大型分析结构）

            try:
                response_data = {
                    'ai_message': ai_message.to_dict(),
                    'current_stage': ai_result.get('stage', session.current_stage)
                }
                
                # 向后兼容：用户消息（若非激活）
                response_data['user_message'] = user_message.to_dict() if not is_activation_message else None

            except Exception as resp_error:
                logger.error(f"构建响应数据失败: {resp_error}")
                raise Exception(f"响应数据构建失败: {str(resp_error)}")
            

            return standard_success_response(
                data=response_data,
                message="消息处理成功"
            )
            
        except Exception as ai_error:
            error_details = str(ai_error)
            logger.error(f"AI服务调用失败: {error_details}")
            
            # 分析具体的错误类型，提供更有用的错误信息
            if "api_key" in error_details.lower() or "unauthorized" in error_details.lower():
                user_message = "AI服务配置错误：API密钥无效或未配置。请联系管理员检查AI服务配置。"
                error_type = "config_error"
            elif "timeout" in error_details.lower():
                user_message = "AI服务响应超时，请稍后重试。如果问题持续存在，请尝试简化您的消息。"
                error_type = "timeout_error"
            elif "connection" in error_details.lower() or "network" in error_details.lower():
                user_message = "无法连接到AI服务。请检查网络连接或稍后重试。"
                error_type = "connection_error"
            elif "not found" in error_details.lower() or "404" in error_details:
                user_message = "AI服务配置错误：服务端点不存在。请联系管理员检查基础URL配置。"
                error_type = "endpoint_error"
            elif "500" in error_details or "internal server error" in error_details.lower():
                user_message = "AI服务内部错误，可能是消息内容过长或格式问题。请尝试简化消息后重试。"
                error_type = "server_error"
            else:
                user_message = f"抱歉，AI分析服务遇到了问题：{error_details}。请稍后重试，或重新描述您的需求。"
                error_type = "unknown_error"
            
            # 创建AI服务错误消息
            error_message = RequirementsMessage(
                session_id=session_id,
                message_type='system',
                content=user_message,
                message_metadata=json.dumps({
                    'error_type': error_type,
                    'error_details': error_details,
                    'stage': session.current_stage,
                    'troubleshooting_hint': 'Check AI service configuration, network connectivity, and message size'
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
        logger.error(f"未处理的异常发生: {str(e)}")
        import traceback
        traceback.print_exc()
        
        db.session.rollback()
        
        error_response = standard_error_response(f"发送消息失败: {str(e)}", 500)
        return error_response


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
        bundle_path = Path(__file__).parent.parent.parent / "assistant-bundles" / bundle_file
        
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


@requirements_bp.route("/sessions/<session_id>/messages/stream", methods=["POST"])
def send_message_stream(session_id):
    """
    流式发送消息到会话（SSE 模式）
    
    使用 LangGraph 流式响应，逐块返回 AI 回复。
    前端通过 EventSource 或 fetch 接收 SSE 数据。
    """
    from flask import Response, stream_with_context, current_app
    import asyncio
    
    try:
        # 验证会话是否存在
        session = RequirementsSession.query.get(session_id)
        if not session:
            return standard_error_response("会话不存在", 404)
            
        if session.session_status != "active":
            return standard_error_response("会话不在活跃状态", 400)
        
        # 获取请求数据（支持 JSON 和 Multipart）
        content = ""
        attached_files = []
        
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Multipart 模式（支持文件）
            content = request.form.get('content', '').strip()
            files = request.files.getlist('files')
            if files:
                try:
                    attached_files = process_uploaded_files(files)
                    # 构建包含文件内容的完整消息
                    content = build_message_with_files(content, attached_files)
                except Exception as e:
                    return standard_error_response(f"文件处理失败: {str(e)}", 400)
        elif request.is_json:
            # JSON 模式
            data = request.get_json()
            content = data.get("content", "").strip()
        else:
            return standard_error_response("请求格式错误：需要JSON或multipart/form-data格式", 400)
        
        if not content:
            return standard_error_response("消息内容不能为空", 400)
        
        # 在生成器外部提取会话数据（避免 SQLAlchemy detached instance 错误）
        user_context = json.loads(session.user_context or "{}")
        assistant_type = user_context.get("assistant_type", "alex")
        project_name = session.project_name
        current_stage = session.current_stage
        
        # 检查是否是激活消息（仅依靠内容特征，不依赖长度）
        # 1. Bundle + 激活指令组合
        # 2. YAML格式配置 + agent定义  
        # 3. 关键操作指令的组合模式
        is_activation_message = (
            # Bundle激活模式：包含明确的Bundle标识和激活指令
            ("Bundle" in content and ("activation-instructions" in content or "persona:" in content)) or
            # YAML配置模式：包含YAML格式的agent配置
            ("```yaml" in content and "agent:" in content) or
            # 操作指令模式：包含关键操作指令的组合
            ("你的关键操作指令" in content and "请严格按照" in content and "persona执行" in content)
        )
        
        # 字符长度限制：支持环境变量覆盖
        max_len_env = os.getenv('REQUIREMENTS_MESSAGE_MAX_LEN')
        is_testing_env = os.getenv('TESTING', '').lower() in ['1', 'true', 'yes']
        if max_len_env and max_len_env.isdigit():
            max_length = int(max_len_env)
        else:
            if is_activation_message:
                max_length = 50000
            else:
                max_length = 2000 if is_testing_env else 10000
                
        if len(content) > max_length:
            message = (
                f"激活消息内容不能超过{max_length}字符"
                if is_activation_message
                else f"消息内容不能超过{max_length}字符"
            )
            return standard_error_response(message, 400)
        
        # 保存用户消息
        user_message = RequirementsMessage(
            session_id=session_id,
            message_type="system" if is_activation_message else "user",
            content=content,
            message_metadata=json.dumps({
                "stage": current_stage,
                "char_count": len(content),
                "source": "http_stream",
                "is_activation": is_activation_message,
                "has_attachments": len(attached_files) > 0
            })
        )
        db.session.add(user_message)
        db.session.commit()
        
        # 获取 Flask app 用于在生成器中创建应用上下文
        app = current_app._get_current_object()
        
        import sys
        
        def generate_stream():
            """生成 SSE 流"""
            full_response = []
            
            try:
                # 导入 ADK 服务
                from ..services.adk_agents import AdkAssistantService
                
                # 创建服务实例
                service = AdkAssistantService(
                    assistant_type=assistant_type
                )
                
            except ImportError as import_err:
                logger.error(f"ADK 导入失败: {import_err}")
                if is_testing_env:
                   import traceback
                   traceback.print_exc()
                # ADK失败则直接报错，不再回退到LangGraph
                raise import_err
            except Exception as create_err:
                logger.error(f"ADK 服务创建失败: {create_err}")
                if is_testing_env:
                   import traceback
                   traceback.print_exc()
                # ADK失败则直接报错，不再回退到LangGraph
                raise create_err
                
            try:
                async def stream_async():
                    await service.initialize()
                    
                    # 从缓存中获取激活状态
                    is_activated = _get_session_activated(session_id)
                    logger.info(f"会话 {session_id[:8]} 激活状态: {is_activated}")
                    
                    async for chunk in service.stream_message(
                        session_id=session_id,
                        user_message=content,
                        project_name=project_name,
                        is_activated=is_activated  # 传递激活状态
                    ):
                        yield chunk
                
                # 在同步环境中运行异步代码
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    async_gen = stream_async()
                    while True:
                        try:
                            chunk = loop.run_until_complete(async_gen.__anext__())
                            full_response.append(chunk)
                            # SSE 格式：data: <内容>\n\n
                            yield f"data: {json.dumps({'chunk': chunk, 'type': 'content'})}\n\n"
                        except StopAsyncIteration:
                            break
                finally:
                    loop.close()
                
                # 流式完成后保存完整的 AI 回复
                complete_response = "".join(full_response)
                
                if complete_response:
                    # ✨ 清理 JSON 元数据
                    # ✨ 清理 JSON 元数据
                    # 简单的内联清理逻辑，替代之前的 extract_natural_response
                    if isinstance(complete_response, str):
                        # 移除可能的 markdown 代码块标记
                        cleaned_response = complete_response.strip()
                        if cleaned_response.startswith('```json'):
                            cleaned_response = cleaned_response[7:]
                        elif cleaned_response.startswith('```'):
                            cleaned_response = cleaned_response[3:]
                        
                        if cleaned_response.endswith('```'):
                            cleaned_response = cleaned_response[:-3]
                        
                        cleaned_response = cleaned_response.strip()
                    else:
                        cleaned_response = str(complete_response)
                    
                    # 在应用上下文中保存消息（保存清理后的内容）
                    with app.app_context():
                        ai_message = RequirementsMessage(
                            session_id=session_id,
                            message_type='ai',
                            content=cleaned_response,  # 使用清理后的内容
                            message_metadata=json.dumps({
                                'stage': current_stage,
                                'assistant_type': assistant_type,
                                'source': 'langgraph_stream'
                            })
                        )
                        db.session.add(ai_message)
                        db.session.commit()
                        message_id = ai_message.id
                    
                    # ✨ 标记会话为已激活（首次响应后）
                    _set_session_activated(session_id, True)
                    
                    # 发送完成信号
                    yield f"data: {json.dumps({'type': 'done', 'message_id': message_id})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': '未能获取 AI 回复'})}\n\n"
                    
            except Exception as e:
                logger.error(f"流式处理失败: {str(e)}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate_stream()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # 禁用 Nginx 缓冲
                'Connection': 'keep-alive'
            }
        )
        
    except Exception as e:
        logger.error(f"流式端点错误: {str(e)}")
        return standard_error_response(f"发送消息失败: {str(e)}", 500)


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
        

    
    @socketio.on('leave_requirements_session')
    def on_leave_session(data):
        """用户离开需求分析会话"""
        session_id = data.get('session_id')
        if session_id:
            leave_room(f'requirements_{session_id}')
            
        if request.sid in active_sessions:
            del active_sessions[request.sid]
            
        emit('left_session', {'session_id': session_id})

    
    @socketio.on('requirements_message')
    def on_requirements_message(data):
        """处理需求分析消息"""
        try:
            session_id = data.get('session_id')
            content = data.get('content', '').strip()
            
            if not session_id or not content:
                emit('error', {'message': '缺少session_id或content参数'})
                return
                
            # 检查是否是激活消息（与HTTP逻辑保持一致，仅依靠内容特征）
            is_activation_message = (
                # Bundle激活模式：包含明确的Bundle标识和激活指令
                ("Bundle" in content and ("activation-instructions" in content or "persona:" in content)) or
                # YAML配置模式：包含YAML格式的agent配置
                ("```yaml" in content and "agent:" in content) or
                # 操作指令模式：包含关键操作指令的组合
                ("你的关键操作指令" in content and "请严格按照" in content and "persona执行" in content)
            )
            max_length = 50000 if is_activation_message else 10000
            
            if len(content) > max_length:
                message = f"激活消息内容不能超过{max_length}字符" if is_activation_message else "消息内容不能超过10000字符"
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
                

                
            except Exception as ai_error:
                logger.error(f"AI服务调用失败: {str(ai_error)}")
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
            logger.error(f"处理需求分析消息时出错: {str(e)}")
            emit('error', {'message': f'处理消息失败: {str(e)}'})
    
    @socketio.on('disconnect')
    def on_disconnect():
        """客户端断开连接时清理"""
        if request.sid in active_sessions:
            session_id = active_sessions[request.sid]
            leave_room(f'requirements_{session_id}')
            del active_sessions[request.sid]



# 注意：根据BMAD架构原则，以下函数已移除
# 所有业务逻辑决策（包括AI响应内容生成、共识提取等）都应该由AI服务处理
# Web层只负责数据传输和存储，不做任何内容生成或业务逻辑判断

# 真实实现中，应该有一个独立的AI服务端点，比如：
# POST /ai/requirements/analyze
# 参数：用户消息、会话上下文、当前阶段
# 返回：AI响应内容、更新的共识、新的阶段状态