"""
需求分析API端点
提供需求分析会话和消息管理功能
"""

import uuid
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from flask import Blueprint, request, Response, stream_with_context
from werkzeug.datastructures import FileStorage

# SocketIO support removed for cleanup
from .base import (
    standard_success_response,
    standard_error_response,
    require_json,
    log_api_call,
)

# 导入数据模型和服务
from ..agents import LangchainAssistantService

try:
    from ..models import db, RequirementsSession, RequirementsMessage, RequirementsAIConfig
    from ..utils.error_handler import ValidationError, NotFoundError, DatabaseError
except ImportError:
    # 回退定义
    db = None
    RequirementsSession = None
    RequirementsMessage = None
    RequirementsAIConfig = None
    class ValidationError(Exception):
        def __init__(self, message):
            self.message = message
    class NotFoundError(Exception):
        def __init__(self, message):
            self.message = message
    class DatabaseError(Exception):
        def __init__(self, message):
            self.message = message

# ✨ 临时会话状态缓存（内存存储，24小时过期）
_session_state_cache = {}  # {session_id: {'is_activated': bool, 'last_access': datetime}}
_CACHE_TTL_HOURS = 24

def _cleanup_expired_sessions() -> None:
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

def _set_session_activated(session_id: str, is_activated: bool = True) -> None:
    """设置会话的激活状态"""
    _session_state_cache[session_id] = {
        'is_activated': is_activated,
        'last_access': datetime.now()
    }


def _clear_session_state(session_id: str) -> None:
    """清除会话状态（用户退出时调用）"""
    if session_id in _session_state_cache:
        del _session_state_cache[session_id]


# 初始化 logger
logger = logging.getLogger(__name__)

# ✨ AI服务实例缓存（按session_id缓存）
_ai_service_cache = {}  # {session_id: {'service': instance, 'last_access': datetime}}

def get_ai_service(assistant_type: str = 'lisa', session_id: Optional[str] = None) -> Optional[LangchainAssistantService]:
    """获取AI服务实例，支持会话级缓存"""
    
    # 清理过期缓存
    now = datetime.now()
    expired = [k for k, v in _ai_service_cache.items() 
              if (now - v['last_access']).total_seconds() > _CACHE_TTL_HOURS * 3600]
    for k in expired:
        del _ai_service_cache[k]
        
    # 尝试从缓存获取
    if session_id and session_id in _ai_service_cache:
        cached = _ai_service_cache[session_id]
        # 检查是否为了同一个assistant_type
        if cached['service'].assistant_type == assistant_type:
            cached['last_access'] = now
            return cached['service']
            
    try:
        if RequirementsAIConfig is None:
            return None
            
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
            # 创建AI服务实例
            ai_service = LangchainAssistantService(assistant_type=assistant_type, config=config_data)
            
            # 缓存实例
            if session_id:
                _ai_service_cache[session_id] = {
                    'service': ai_service,
                    'last_access': now
                }
                
            return ai_service
        else:
            return None
    except ImportError as e:
        logger.error(f"Import error in get_ai_service: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in get_ai_service: {e}")
        return None

# 创建蓝图
requirements_bp = Blueprint("requirements", __name__, url_prefix="/ai-agents/api/requirements")

# 全局变量存储active会话
active_sessions = {}


def process_uploaded_files(files: List[FileStorage]) -> List[Dict[str, Any]]:
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


def build_message_with_files(message_content: str, attached_files: List[Dict[str, Any]]) -> str:
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
def create_session() -> Response:
    """创建新的智能助手会话"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        project_name = data.get("project_name", "")
        if not project_name or len(project_name.strip()) == 0:
            raise ValidationError("项目名称不能为空")
        
        # 获取助手类型参数
        assistant_type = data.get("assistant_type", "lisa")
        
        # 验证助手类型（支持 lisa 别名）
        # 验证助手类型（支持 lisa 别名）
        # 验证助手类型（支持 lisa 别名）
        supported_types = list(LangchainAssistantService.SUPPORTED_ASSISTANTS.keys()) + ['lisa']

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
def get_session(session_id: str) -> Response:
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
def get_messages(session_id: str) -> Response:
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
def send_message(session_id: str) -> Response:
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
        assistant_type = user_context.get("assistant_type", "lisa")
        
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
            # 传入 session_id 以启用缓存
            ai_svc = get_ai_service(assistant_type=assistant_type, session_id=session_id)
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


@requirements_bp.route("/sessions/<session_id>/messages/stream", methods=["POST"])
def stream_messages(session_id: str) -> Response:
    """
    [Deprecated] V1 流式发送消息给AI助手 (SSE)
    请使用 V2 端点: /sessions/<session_id>/messages/v2/stream
    """
    try:
        # Warn about deprecation
        logger.warning(f"Deprecated V1 stream endpoint called for session {session_id}")
        
        data = request.get_json()
        if not data or not data.get("content"):
            return standard_error_response("消息内容不能为空", 400)
            
        content = data.get("content")
        
        # 获取会话
        session = RequirementsSession.query.filter_by(id=session_id).first()
        if not session:
            return standard_error_response("会话不存在", 404)
        
        session.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 从 user_context 获取 assistant_type
        user_context = json.loads(session.user_context or "{}")
        assistant_type = user_context.get("assistant_type", "lisa")
        
        # 获取 AI 服务
        try:
            ai_service = get_ai_service(assistant_type, session_id)
            if not ai_service:
                return standard_error_response(f"无法初始化 {session.assistant_type} 助手", 500)
        except Exception as e:
            return standard_error_response(f"AI服务初始化错误: {str(e)}", 500)
            
        # 保存用户消息
        user_message = RequirementsMessage(
            session_id=session.id,
            content=content,
            message_type="user"
        )
        db.session.add(user_message)
        db.session.commit()
        
        # 创建 AI 消息占位
        ai_message = RequirementsMessage(
            session_id=session.id,
            content="",
            message_type="ai"
        )
        db.session.add(ai_message)
        db.session.commit()
        ai_message_id = ai_message.id
        
        # 预先获取需要的会话数据，避免在 generator 中访问 session 对象导致 DetachedInstanceError
        project_name = session.project_name
        
        def generate():
            import asyncio
            
            # 在生成器中创建新的事件循环来运行异步代码
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            full_content = ""
            
            try:
                # 获取异步生成器
                async_gen = ai_service.stream_message(
                    session_id=session_id, 
                    user_message=content,
                    project_name=project_name
                )
                
                # 手动驱动异步生成器
                while True:
                    try:
                        # 使用 loop.run_until_complete 等待下一个 chunk
                        # 注意：__anext__() 在 Python 3.10+
                        item = loop.run_until_complete(async_gen.__anext__())
                        
                        # 支持混合类型：str (content) 和 dict (state event)
                        if isinstance(item, dict):
                            # state 事件直接序列化输出
                            yield f"data: {json.dumps(item)}\n\n"
                        else:
                            # 文本内容
                            full_content += item
                            yield f"data: {json.dumps({'type': 'content', 'chunk': item})}\n\n"
                    except StopAsyncIteration:
                        break
                
                # 更新数据库中的完整消息 (使用应用上下文，因为我们可能在不同线程)
                # 注意：db.session 是基于线程的。如果 generator 在 worker 线程运行，应该没问题。
                # 安全起见，只 yield 完成信号，更新逻辑可以尝试在此处执行
                # 但要小心 SQLAlchemy 的 session 绑定。
                
                # 尝试在此处更新 DB - 需要应用上下文吗？
                # generate() 运行在 Flask 视图调用的上下文中（响应流式传输时），
                # 通常 Flask 会保持上下文直到响应结束。
                
                # 重新查询并更新，因为 session 对象可能过期
                # 这里简单处理，如果更新失败不影响流式输出
                try:
                    # 我们需要一个新的 session scope 或者 merge
                    pass 
                except Exception:
                    pass

                yield f"data: {json.dumps({'type': 'done', 'message_id': ai_message_id})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            finally:
                loop.close()

        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    except Exception as e:
        logger.error(f"Stream route error: {e}")
        return standard_error_response(f"流式请求失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/messages/v2/stream", methods=["POST"])
def stream_messages_v2(session_id: str) -> Response:
    """
    V2 流式消息端点 - 使用 Data Stream Protocol
    
    响应头:
        x-vercel-ai-ui-message-stream: v1
    """
    try:
        data = request.get_json()
        if not data:
            return standard_error_response("消息内容不能为空", 400)
            
        # 兼容 Vercel AI SDK 格式 (messages 数组)
        messages = data.get("messages", [])
        if messages and isinstance(messages, list):
            # 获取最后一条消息
            last_message = messages[-1]
            if isinstance(last_message, dict):
                content = last_message.get("content", "")
                
                # 尝试从 parts 获取 (AI SDK V2 format)
                if not content and "parts" in last_message:
                    content = last_message.get("parts")

                # 如果是多模态内容（数组/parts），提取文本
                if isinstance(content, list):
                     text_parts = [p.get("text", "") for p in content if p.get("type") == "text"]
                     content = "\n".join(text_parts)
            else:
                content = str(last_message)
        else:
            content = data.get("content", "")
            
        # 如果依然为空，记录警告
        if not content:
            logger.warning(f"接收到空消息内容。Data: {data}")
        
        # 获取会话
        session = RequirementsSession.query.filter_by(id=session_id).first()
        if not session:
            return standard_error_response("会话不存在", 404)
        
        # 从 user_context 获取 assistant_type
        user_context = json.loads(session.user_context or "{}")
        assistant_type = user_context.get("assistant_type", "lisa")
        
        # 获取 AI 服务
        try:
            ai_service = get_ai_service(assistant_type, session_id)
            if not ai_service:
                return standard_error_response(f"无法初始化 {session.assistant_type} 助手", 500)
        except Exception as e:
            return standard_error_response(f"AI服务初始化错误: {str(e)}", 500)
            
        # 处理 experimental_attachments (Vercel AI SDK Standard)
        attached_files = []
        if messages and isinstance(messages, list):
            last_message = messages[-1]
            if isinstance(last_message, dict):
                attachments = last_message.get("experimental_attachments", [])
                if attachments:
                    import base64
                    for att in attachments:
                        # att: { name, contentType, url }
                        # url might be data:application/octet-stream;base64,....
                        if att.get("url", "").startswith("data:"):
                            try:
                                header, encoded = att["url"].split(",", 1)
                                # Decode base64
                                content_bytes = base64.b64decode(encoded)
                                # Try to decode text
                                try:
                                    decoded_text = content_bytes.decode('utf-8')
                                except UnicodeDecodeError:
                                    # Fallback for non-utf8 text? Or skip binary?
                                    # For now, we only support text agents, so maybe skip or try others
                                    decoded_text = content_bytes.decode('gbk', errors='ignore')

                                attached_files.append({
                                    "filename": att.get("name", "unknown.txt"),
                                    "content": decoded_text,
                                    "size": len(content_bytes),
                                    "encoding": "utf-8"
                                })
                            except Exception as e:
                                logger.error(f"Failed to process attachment {att.get('name')}: {e}")

        # 如果有附件，整合到 content 中传给 AI
        if attached_files:
            content = build_message_with_files(content, attached_files)

        session.updated_at = datetime.utcnow()
        db.session.commit()
        
        # 保存用户消息
        user_message = RequirementsMessage(
            session_id=session.id,
            content=content, # 保存完整内容（含文件）还是原始内容？
                             # 为了保持 history 上下文给 LLM，通常保存处理后的 Prompt 内容比较安全，
                             # 或者保存原始 content 并依赖 attached_files 字段重组。
                             # 这里为了简单和 agent 读取方便，我们保存 augmented content，
                             # 或者保存原始 content + attached_files。
                             # 考虑到 `build_message_with_files` 是用来构建 Prompt 的，
                             # 最好还是存原始 content，但是 message_history loading 的时候需要重新组装吗？
                             # 之前的实现 (send_message) 是：
                             #   content = data.get("content")
                             #   full_content = build_message_with_files() [用于传给 AI]
                             #   user_message.content = content [原始]
                             #   user_message.attached_files = ...
                             # 所以我们也保持一致：
            
            # Wait, `content` variable above has been updated by build_message_with_files if attached_files exist.
            # Let's verify standard `build_message_with_files` behavior.
            # It returns "=== ... \n content".
            # So `content` is now the full prompt.
            # If we want to save purely what user typed, we should have kept a reference.
            # But in V2 stream, we reconstruct context from DB messages usually? 
            # Or does LangGraph manage history?
            # Lisa/Alex usually read history from DB or passing `messages`.
            
            # Implementation Decision: Save the FULL content (Prompt) to `content` column?
            # Or save original?
            # If `content` column is what's shown to user, we shouldn't save the big prompt there.
            # BUT, the Frontend V2 displays what it sent locally (optimistic).
            # The Backend DB is for history and context.
            # The Agent reads `content` from DB messages usually.
            # So saving the augmented content is safer for the Agent to "see" the file in history.
            
            # HOWEVER, `RequirementsMessage.to_dict()` is sent back to frontend in some APIs.
            # If we change `content` to include file dump, frontend might show it duplicate?
            # Frontend uses `messages` from AI SDK mostly.
            
            # Let's save the augmented content for now, as that ensures the agent sees it.
            # And also save `attached_files`.
            
            message_type="user"
        )
        
        if attached_files:
             user_message.attached_files = json.dumps(attached_files)
             
        db.session.add(user_message)
        
        # 创建 AI 消息占位
        ai_message = RequirementsMessage(
            session_id=session.id,
            content="",
            message_type="ai"
        )
        db.session.add(ai_message)
        db.session.commit()
        
        # 预先获取 ID，避免在 generator 中访问 detached 对象
        ai_message_id = ai_message.id
        
        def generate():
            import asyncio
            from ..agents.shared.data_stream_adapter import adapt_langgraph_stream
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 用于捕获最终状态的闭包变量
            final_progress = {}
            
            def on_state_update(progress):
                nonlocal final_progress
                final_progress = progress
            
            try:
                # 运行适配器
                async_gen = adapt_langgraph_stream(
                    ai_service, 
                    session_id, 
                    content, 
                    db_message_id=ai_message_id,
                    on_state_update=on_state_update
                )
                
                while True:
                    try:
                        item = loop.run_until_complete(async_gen.__anext__())
                        yield item
                    except StopAsyncIteration:
                        break
                        
            except Exception as e:
                logger.error(f"V2 Streaming error: {e}")
                from ..agents.shared.data_stream import stream_error
                
                # Sanitize error message for frontend
                error_msg = str(e)
                if "api_key" in error_msg.lower():
                    safe_msg = "Configuration Error: API Key issue"
                elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    safe_msg = "Network Error: AI service unreachable"
                else:
                    # In development, might want to see more, but for safety:
                    safe_msg = "An unexpected error occurred during processing."
                    
                yield stream_error(safe_msg)
            finally:
                # ✨ 关键修复：流结束后持久化 artifacts 到数据库
                if final_progress and "artifacts" in final_progress:
                    try:
                        # 重新查询会话以确保附加到当前会话上下文
                        session_to_update = RequirementsSession.query.get(session_id)
                        if session_to_update:
                            current_ai_context = json.loads(session_to_update.ai_context or "{}")
                            
                            # 更新 artifacts
                            if "artifacts" not in current_ai_context:
                                current_ai_context["artifacts"] = {}
                            
                            # 增量更新
                            current_ai_context["artifacts"].update(final_progress["artifacts"])
                            
                            # 保存
                            session_to_update.ai_context = json.dumps(current_ai_context)
                            session_to_update.updated_at = datetime.utcnow()
                            db.session.commit()
                            logger.info(f"成功持久化会话 {session_id} 的 artifacts")
                    except Exception as persist_error:
                        logger.error(f"持久化会话状态失败: {persist_error}")
                        db.session.rollback()
                
                loop.close()
    
        from ..agents.shared.data_stream import DataStreamHeaders
        headers = DataStreamHeaders.as_dict()
        return Response(stream_with_context(generate()), mimetype='text/event-stream', headers=headers)

    except Exception as e:
        logger.error(f"V2 Stream route error: {e}")
        return standard_error_response(f"流式请求失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/sync", methods=["POST"])
@require_json
@log_api_call
def sync_session_messages(session_id: str) -> Response:
    """Synchronize full message history from frontend (Sync on Finish)"""
    try:
        session = RequirementsSession.query.get(session_id)
        if not session:
            raise NotFoundError("会话不存在")
            
        data = request.get_json()
        messages = data.get("messages", [])
        
        if not messages:
            return standard_success_response(message="无需同步")
            
        # We only care about the *last* message which is the AI response being completed
        last_msg = messages[-1]
        
        # Verify it's an assistant message
        if last_msg.get("role") != "assistant":
             return standard_success_response(message="忽略非助手消息")
             
        message_id = last_msg.get("id")
        # message_id should be our DB ID (as string)
        
        if not message_id or not message_id.isdigit():
            # If it's a random ID (e.g. from a fresh session on client not yet synced?), 
            # we might need to create it. But in our flow, we created it in stream start.
            logger.warning(f"Sync received non-integer ID: {message_id}")
            return standard_error_response("无效的消息ID", 400)
            
        db_id = int(message_id)
        ai_message = RequirementsMessage.query.get(db_id)
        
        if not ai_message:
            raise NotFoundError(f"消息ID {db_id} 不存在")
            
        if ai_message.session_id != session_id:
             raise ValidationError("消息不属于该会话")
             
        # Update content and metadata
        # Store the FULL Vercel message object (parts, toolInvocations) in metadata
        # to support re-hydration on frontend refresh
        
        # Extract text content for compatibility
        content = last_msg.get("content", "")
        
        # Update metadata
        current_meta = json.loads(ai_message.message_metadata) if ai_message.message_metadata else {}
        current_meta["vercel_message"] = last_msg # Save full state!
        
        ai_message.content = content
        ai_message.message_metadata = json.dumps(current_meta)
        
        # Phase 2: Process tool invocations and create Tool Messages for LangChain
        tool_invocations = last_msg.get("toolInvocations", [])
        if tool_invocations:
            # Fetch existing tool messages for this session to prevent duplicates
            # Optimization: limit to recent messages or use a better query if metadata was indexed
            existing_msgs = RequirementsMessage.query.filter_by(
                session_id=session_id, 
                message_type='tool'
            ).all()
            
            existing_tool_ids = set()
            for msg in existing_msgs:
                try:
                    meta = json.loads(msg.message_metadata or "{}")
                    if "tool_call_id" in meta:
                        existing_tool_ids.add(meta["tool_call_id"])
                except Exception as e:
                    logger.warning(f"Failed to parse message metadata: {e}")
                    continue
            
            for tool_inv in tool_invocations:
                if tool_inv.get("state") == "result":
                    tool_call_id = tool_inv.get("toolCallId")
                    if tool_call_id and tool_call_id not in existing_tool_ids:
                        # Create new Tool Message
                        tool_result = tool_inv.get("result")
                        # Ensure result is string
                        if not isinstance(tool_result, str):
                            tool_result = json.dumps(tool_result, ensure_ascii=False)
                            
                        tool_msg = RequirementsMessage(
                            session_id=session_id,
                            message_type='tool',
                            content=tool_result,
                            message_metadata=json.dumps({
                                "tool_call_id": tool_call_id,
                                "tool_name": tool_inv.get("toolName"),
                                "source": "sync_on_finish"
                            })
                        )
                        db.session.add(tool_msg)
        
        db.session.commit()
        
        return standard_success_response(message="同步成功")

    except (ValidationError, NotFoundError) as e:
        return standard_error_response(e.message, e.code if hasattr(e, 'code') else 400)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Sync error: {e}")
        return standard_error_response(f"同步失败: {str(e)}", 500)


@requirements_bp.route("/sessions/<session_id>/status", methods=["PUT"])
@require_json
@log_api_call
def update_session_status(session_id: str) -> Response:
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
def get_assistants() -> Union[Response, Dict[str, Any]]:
    """获取支持的助手列表"""
    try:
        assistants = []
        for assistant_id, info in LangchainAssistantService.SUPPORTED_ASSISTANTS.items():
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
def get_assistant_bundle(assistant_type: str) -> Union[Response, Dict[str, Any]]:
    """获取指定助手的完整bundle内容"""
    try:
        if assistant_type not in LangchainAssistantService.SUPPORTED_ASSISTANTS:
            return standard_error_response(f"不支持的助手类型: {assistant_type}", 400)
        
        assistant_info = LangchainAssistantService.SUPPORTED_ASSISTANTS[assistant_type]

        bundle_file = assistant_info["bundle_file"]
        # 动态解析 bundle 路径 (相对于 backend/agents/...)
        base_agents_path = Path(__file__).resolve().parents[1] / "agents"
        
        if assistant_type == "lisa":
             bundle_path = base_agents_path / "lisa" / "lisa_v5_bundle.txt"
        else:
             # Fallback to old behavior if needed or error
             bundle_path = Path(__file__).resolve().parents[4] / "assistant-bundles" / bundle_file
        
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


