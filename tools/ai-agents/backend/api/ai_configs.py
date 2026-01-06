"""
AI 配置管理 API 端点

支持 AI 配置的 CRUD 操作、默认配置管理和连接测试。
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from .base import (
    standard_success_response,
    standard_error_response,
    require_json,
    log_api_call,
    ValidationError,
    NotFoundError,
)

# 导入数据模型
try:
    from ..models import db, RequirementsAIConfig
except ImportError:
    # 如果无法导入，延迟导入
    db = None
    RequirementsAIConfig = None

# 创建蓝图
ai_configs_bp = Blueprint("ai_configs", __name__, url_prefix="/ai-agents/api/ai-configs")

# AI 配置常用模板（仅供参考）
AI_CONFIG_EXAMPLES = {
    "openai_gpt4": {
        "name": "OpenAI GPT-4",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
    },
    "dashscope_qwen": {
        "name": "阿里云通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-vl-max-latest", "qwen-turbo", "qwen-plus"]
    },
    "claude_api": {
        "name": "Claude API",
        "base_url": "https://api.anthropic.com",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
    },
    "gemini_openai_format": {
        "name": "Google Gemini (OpenAI 格式)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-1.5-flash"]
    }
}


def _get_model():
    """获取数据模型（延迟导入）"""
    global db, RequirementsAIConfig
    if RequirementsAIConfig is None:
        from ..models import db as _db, RequirementsAIConfig as _config
        db = _db
        RequirementsAIConfig = _config
    return db, RequirementsAIConfig


def _clear_other_defaults(exclude_id=None):
    """清除其他默认配置"""
    _db, Config = _get_model()
    query = Config.query.filter_by(is_default=True)
    if exclude_id:
        query = query.filter(Config.id != exclude_id)
    
    for config in query.all():
        config.is_default = False


@ai_configs_bp.route("/", methods=["GET"])
@ai_configs_bp.route("", methods=["GET"])
@log_api_call
def list_configs():
    """获取所有 AI 配置列表"""
    try:
        _db, Config = _get_model()
        configs = Config.get_all_active_configs()
        
        return standard_success_response(
            data=[config.to_dict() for config in configs],
            message="获取 AI 配置列表成功"
        )
        
    except Exception as e:
        return standard_error_response(f"获取配置列表失败: {str(e)}", 500)


@ai_configs_bp.route("/", methods=["POST"])
@ai_configs_bp.route("", methods=["POST"])
@require_json
@log_api_call
def create_config():
    """创建新的 AI 配置"""
    try:
        _db, Config = _get_model()
        data = request.get_json()
        
        # 验证必要字段（支持两种命名方式）
        config_name = data.get("config_name") or data.get("name")
        api_key = data.get("api_key")
        base_url = data.get("base_url")
        model_name = data.get("model_name")
        
        if not config_name:
            raise ValidationError("缺少必要字段: name/config_name")
        if not api_key:
            raise ValidationError("缺少必要字段: api_key")
        if not base_url:
            raise ValidationError("缺少必要字段: base_url")
        if not model_name:
            raise ValidationError("缺少必要字段: model_name")
        
        # 检查是否存在同名配置
        existing = Config.query.filter_by(config_name=config_name.strip()).first()
        if existing:
            raise ValidationError(f"配置名称 '{config_name}' 已存在")
        
        # 创建配置
        config = Config(
            config_name=config_name.strip(),
            api_key=api_key.strip(),
            base_url=base_url.strip(),
            model_name=model_name.strip(),
            is_default=data.get("is_default", False),
            is_active=data.get("is_active", True)
        )
        
        # 如果设置为默认配置，需要取消其他默认配置
        if config.is_default:
            _clear_other_defaults()
        
        _db.session.add(config)
        _db.session.commit()
        
        return standard_success_response(
            data=config.to_dict(),
            message="AI 配置创建成功",
            code=201
        )
        
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        _db.session.rollback()
        return standard_error_response(f"创建配置失败: {str(e)}", 500)


@ai_configs_bp.route("/<int:config_id>", methods=["PUT"])
@require_json
@log_api_call
def update_config(config_id):
    """更新 AI 配置"""
    try:
        _db, Config = _get_model()
        config = Config.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        data = request.get_json()
        
        # 更新字段（支持两种命名方式）
        if "config_name" in data or "name" in data:
            new_name = data.get("config_name") or data.get("name")
            config.config_name = new_name.strip()
        
        if "api_key" in data:
            config.api_key = data["api_key"].strip()
        
        if "base_url" in data:
            config.base_url = data["base_url"].strip()
        
        if "model_name" in data:
            config.model_name = data["model_name"].strip()
        
        if "is_default" in data:
            config.is_default = bool(data["is_default"])
            if config.is_default:
                _clear_other_defaults(exclude_id=config.id)
        
        if "is_active" in data:
            config.is_active = bool(data["is_active"])
        
        config.updated_at = datetime.utcnow()
        _db.session.commit()
        
        return standard_success_response(
            data=config.to_dict(),
            message="AI 配置更新成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        _db.session.rollback()
        return standard_error_response(f"更新配置失败: {str(e)}", 500)


@ai_configs_bp.route("/<int:config_id>", methods=["DELETE"])
@log_api_call
def delete_config(config_id):
    """删除 AI 配置"""
    try:
        _db, Config = _get_model()
        config = Config.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        # 如果是默认配置，尝试设置其他配置为默认
        if config.is_default:
            other_configs = Config.query.filter(
                Config.id != config_id,
                Config.is_active == True
            ).all()
            
            if other_configs:
                other_configs[0].is_default = True
        
        _db.session.delete(config)
        _db.session.commit()
        
        return standard_success_response(
            data={"deleted_id": config_id},
            message="AI 配置删除成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except Exception as e:
        _db.session.rollback()
        return standard_error_response(f"删除配置失败: {str(e)}", 500)


@ai_configs_bp.route("/examples", methods=["GET"])
@log_api_call
def get_config_examples():
    """获取 AI 配置示例模板"""
    return standard_success_response(
        data=AI_CONFIG_EXAMPLES,
        message="获取配置示例成功"
    )


@ai_configs_bp.route("/default", methods=["GET"])
@log_api_call
def get_default_config():
    """获取默认 AI 配置"""
    try:
        _db, Config = _get_model()
        config = Config.get_default_config()
        
        if not config:
            return standard_error_response("未找到默认配置", 404)
        
        return standard_success_response(
            data=config.to_dict(),
            message="获取默认配置成功"
        )
        
    except Exception as e:
        return standard_error_response(f"获取默认配置失败: {str(e)}", 500)


@ai_configs_bp.route("/<int:config_id>/set-default", methods=["POST"])
@log_api_call
def set_default_config(config_id):
    """设置指定配置为默认配置"""
    try:
        _db, Config = _get_model()
        config = Config.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        if not config.is_active:
            raise ValidationError("不能将禁用的配置设为默认")
        
        # 清除其他默认配置
        _clear_other_defaults(exclude_id=config.id)
        
        # 设置为默认
        config.is_default = True
        config.updated_at = datetime.utcnow()
        _db.session.commit()
        
        return standard_success_response(
            data=config.to_dict(),
            message="默认配置设置成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        _db.session.rollback()
        return standard_error_response(f"设置默认配置失败: {str(e)}", 500)


@ai_configs_bp.route("/stats", methods=["GET"])
@log_api_call
def get_config_stats():
    """获取配置统计信息"""
    try:
        _db, Config = _get_model()
        total_configs = Config.query.filter_by(is_active=True).count()
        current_config = Config.get_default_config()
        
        stats = {
            "total": total_configs,
            "total_configs": total_configs,
            "selected_configs": 1 if current_config else 0,
            "current_config_name": current_config.config_name if current_config else "无"
        }
        
        return standard_success_response(
            data=stats,
            message="获取配置统计成功"
        )
        
    except Exception as e:
        return standard_error_response(f"获取配置统计失败: {str(e)}", 500)


@ai_configs_bp.route("/<int:config_id>/test", methods=["POST"])
@log_api_call
def test_config(config_id):
    """测试 AI 配置连接"""
    try:
        _db, Config = _get_model()
        config = Config.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        # 使用本地 agents 模块
        from ..agents import LangchainAssistantService
        
        import time
        import asyncio
        
        config_data = config.get_config_for_ai_service()
        temp_ai_service = LangchainAssistantService(assistant_type="alex", config=config_data)
        
        start_time = time.time()
        messages = [{"role": "user", "content": "你好"}]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(temp_ai_service.test_connection(messages))
        finally:
            loop.close()
        
        duration = time.time() - start_time
        
        if response and len(response.strip()) > 0:
            return standard_success_response(
                data={
                    "config_id": config_id,
                    "config_name": config.config_name,
                    "model_name": config.model_name,
                    "test_success": True,
                    "duration_ms": round(duration * 1000, 2),
                    "ai_response": response.strip(),
                    "tested_at": datetime.utcnow().isoformat()
                },
                message="配置测试成功"
            )
        else:
            return standard_error_response(
                f"AI 未返回有效响应", 422
            )
            
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except Exception as e:
        return standard_error_response(f"测试配置失败: {str(e)}", 500)
