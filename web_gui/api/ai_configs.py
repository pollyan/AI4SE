"""
AI配置管理API端点 - 简化版
支持Story 1.4: AI配置管理功能
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from .base import (
    standard_success_response,
    standard_error_response,
    require_json,
    log_api_call,
)

# 导入数据模型和错误处理
try:
    from ..models import db, RequirementsAIConfig
    from ..utils.error_handler import ValidationError, NotFoundError, DatabaseError
except ImportError:
    from web_gui.models import db, RequirementsAIConfig
    from web_gui.utils.error_handler import ValidationError, NotFoundError, DatabaseError

# 创建蓝图
ai_configs_bp = Blueprint("ai_configs", __name__, url_prefix="/api/ai-configs")

# 支持的AI服务商配置
PROVIDER_CONFIGS = {
    "openai": {
        "name": "OpenAI",
        "default_base_url": "https://api.openai.com/v1",
        "default_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]
    },
    "dashscope": {
        "name": "阿里云DashScope",
        "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_models": ["qwen-vl-max-latest", "qwen-turbo", "qwen-plus"]
    },
    "claude": {
        "name": "Anthropic Claude",
        "default_base_url": "https://api.anthropic.com",
        "default_models": ["claude-3-5-sonnet-20241022", "claude-3-haiku-20240307"]
    }
}


@ai_configs_bp.route("", methods=["GET"])
@log_api_call
def list_configs():
    """获取所有AI配置列表"""
    try:
        configs = RequirementsAIConfig.get_all_active_configs()
        
        return standard_success_response(
            data={
                "configs": [config.to_dict() for config in configs],
                "total": len(configs)
            },
            message="获取AI配置列表成功"
        )
        
    except Exception as e:
        return standard_error_response(f"获取配置列表失败: {str(e)}", 500)


@ai_configs_bp.route("", methods=["POST"])
@require_json
@log_api_call
def create_config():
    """创建新的AI配置"""
    try:
        data = request.get_json()
        
        # 验证必要字段
        required_fields = ["config_name", "provider", "api_key", "model_name"]
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"缺少必要字段: {field}")
        
        # 验证服务商
        provider = data.get("provider").lower()
        if provider not in PROVIDER_CONFIGS:
            raise ValidationError(f"不支持的服务商: {provider}")
        
        # 设置默认base_url（如果未提供）
        base_url = data.get("base_url")
        if not base_url:
            base_url = PROVIDER_CONFIGS[provider]["default_base_url"]
        
        # 创建配置
        config = RequirementsAIConfig(
            config_name=data["config_name"].strip(),
            provider=provider,
            api_key=data["api_key"].strip(),
            base_url=base_url,
            model_name=data["model_name"].strip(),
            is_default=data.get("is_default", False),
            is_active=True
        )
        
        # 如果设置为默认配置，需要取消其他默认配置
        if config.is_default:
            _clear_other_defaults()
        
        db.session.add(config)
        db.session.commit()
        
        return standard_success_response(
            data=config.to_dict(),
            message="AI配置创建成功"
        )
        
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"创建配置失败: {str(e)}", 500)


@ai_configs_bp.route("/<int:config_id>", methods=["PUT"])
@require_json
@log_api_call
def update_config(config_id):
    """更新AI配置"""
    try:
        config = RequirementsAIConfig.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        data = request.get_json()
        
        # 更新基本字段
        if "config_name" in data:
            config.config_name = data["config_name"].strip()
        
        if "provider" in data:
            provider = data["provider"].lower()
            if provider not in PROVIDER_CONFIGS:
                raise ValidationError(f"不支持的服务商: {provider}")
            config.provider = provider
        
        if "api_key" in data:
            config.api_key = data["api_key"].strip()
        
        if "base_url" in data:
            config.base_url = data["base_url"].strip()
        
        if "model_name" in data:
            config.model_name = data["model_name"].strip()
        
        if "is_default" in data:
            config.is_default = bool(data["is_default"])
            # 如果设置为默认，清除其他默认配置
            if config.is_default:
                _clear_other_defaults(exclude_id=config.id)
        
        if "is_active" in data:
            config.is_active = bool(data["is_active"])
        
        config.updated_at = datetime.utcnow()
        db.session.commit()
        
        return standard_success_response(
            data=config.to_dict(),
            message="AI配置更新成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"更新配置失败: {str(e)}", 500)


@ai_configs_bp.route("/<int:config_id>", methods=["DELETE"])
@log_api_call
def delete_config(config_id):
    """删除AI配置"""
    try:
        config = RequirementsAIConfig.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        # 检查是否为默认配置
        if config.is_default:
            # 检查是否还有其他配置可以设为默认
            other_configs = RequirementsAIConfig.query.filter(
                RequirementsAIConfig.id != config_id,
                RequirementsAIConfig.is_active == True
            ).all()
            
            if other_configs:
                # 将第一个其他配置设为默认
                other_configs[0].is_default = True
            else:
                raise ValidationError("不能删除最后一个配置")
        
        db.session.delete(config)
        db.session.commit()
        
        return standard_success_response(
            data={"deleted_id": config_id},
            message="AI配置删除成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"删除配置失败: {str(e)}", 500)


@ai_configs_bp.route("/providers", methods=["GET"])
@log_api_call
def get_providers():
    """获取支持的AI服务商信息"""
    return standard_success_response(
        data=PROVIDER_CONFIGS,
        message="获取服务商信息成功"
    )


@ai_configs_bp.route("/default", methods=["GET"])
@log_api_call
def get_default_config():
    """获取默认AI配置"""
    try:
        config = RequirementsAIConfig.get_default_config()
        
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
        config = RequirementsAIConfig.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        if not config.is_active:
            raise ValidationError("不能将禁用的配置设为默认")
        
        # 清除其他默认配置
        _clear_other_defaults(exclude_id=config.id)
        
        # 设置为默认
        config.is_default = True
        config.updated_at = datetime.utcnow()
        db.session.commit()
        
        return standard_success_response(
            data=config.to_dict(),
            message="默认配置设置成功"
        )
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except ValidationError as e:
        return standard_error_response(e.message, 400)
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"设置默认配置失败: {str(e)}", 500)


def _clear_other_defaults(exclude_id=None):
    """清除其他默认配置"""
    query = RequirementsAIConfig.query.filter_by(is_default=True)
    if exclude_id:
        query = query.filter(RequirementsAIConfig.id != exclude_id)
    
    for config in query.all():
        config.is_default = False