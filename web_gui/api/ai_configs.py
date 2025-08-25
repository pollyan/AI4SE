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

# AI配置常用模板（仅供参考）
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
        "name": "Google Gemini (OpenAI格式)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "models": ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-1.5-flash"]
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
        required_fields = ["config_name", "api_key", "base_url", "model_name"]
        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"缺少必要字段: {field}")
        
        # 创建配置
        config = RequirementsAIConfig(
            config_name=data["config_name"].strip(),
            api_key=data["api_key"].strip(),
            base_url=data["base_url"].strip(),
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
            # 允许删除最后一个配置，不抛出错误
        
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


@ai_configs_bp.route("/examples", methods=["GET"])
@log_api_call
def get_config_examples():
    """获取AI配置示例模板"""
    return standard_success_response(
        data=AI_CONFIG_EXAMPLES,
        message="获取配置示例成功"
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


@ai_configs_bp.route("/<int:config_id>/test", methods=["POST"])
@log_api_call
def test_config(config_id):
    """测试AI配置连接"""
    try:
        config = RequirementsAIConfig.query.get(config_id)
        if not config:
            raise NotFoundError("配置不存在")
        
        # 导入AI服务进行测试
        try:
            from ..services.requirements_ai_service import RequirementsAIService
            
            # 创建临时AI服务实例进行测试
            config_data = config.get_config_for_ai_service()
            temp_ai_service = RequirementsAIService(config=config_data)
            
            # 发送测试消息
            test_message = "你好，这是一个配置连接测试。请简单回复'测试成功'。"
            response = temp_ai_service.send_message(test_message)
            
            if response and len(response.strip()) > 0:
                return standard_success_response(
                    data={
                        "config_id": config_id,
                        "test_success": True,
                        "response_preview": response[:100] + "..." if len(response) > 100 else response,
                        "tested_at": datetime.utcnow().isoformat()
                    },
                    message="配置连接测试成功"
                )
            else:
                return standard_error_response("AI服务返回空响应", 422)
                
        except Exception as e:
            return standard_error_response(f"连接测试失败: {str(e)}", 422)
        
    except NotFoundError as e:
        return standard_error_response(e.message, 404)
    except Exception as e:
        return standard_error_response(f"测试配置失败: {str(e)}", 500)


@ai_configs_bp.route("/stats", methods=["GET"])
@log_api_call
def get_config_stats():
    """获取配置统计信息"""
    try:
        total_configs = RequirementsAIConfig.query.filter_by(is_active=True).count()
        current_config = RequirementsAIConfig.get_default_config()
        
        stats = {
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


@ai_configs_bp.route("/test-all", methods=["POST"])
@log_api_call
def test_all_configs():
    """批量测试所有配置连接"""
    try:
        configs = RequirementsAIConfig.get_all_active_configs()
        test_results = []
        
        for config in configs:
            try:
                # 导入AI服务进行测试
                from ..services.requirements_ai_service import RequirementsAIService
                
                config_data = config.get_config_for_ai_service()
                temp_ai_service = RequirementsAIService(config=config_data)
                
                # 发送简短测试消息
                test_message = "测试"
                response = temp_ai_service.send_message(test_message)
                
                test_results.append({
                    "config_id": config.id,
                    "config_name": config.config_name,
                    "test_success": True,
                    "message": "连接正常"
                })
                
            except Exception as e:
                test_results.append({
                    "config_id": config.id,
                    "config_name": config.config_name,
                    "test_success": False,
                    "message": f"连接失败: {str(e)}"
                })
        
        success_count = sum(1 for result in test_results if result["test_success"])
        total_count = len(test_results)
        
        return standard_success_response(
            data={
                "test_results": test_results,
                "summary": {
                    "total": total_count,
                    "success": success_count,
                    "failed": total_count - success_count
                }
            },
            message=f"批量测试完成: {success_count}/{total_count} 配置连接正常"
        )
        
    except Exception as e:
        return standard_error_response(f"批量测试失败: {str(e)}", 500)


def _clear_other_defaults(exclude_id=None):
    """清除其他默认配置"""
    query = RequirementsAIConfig.query.filter_by(is_default=True)
    if exclude_id:
        query = query.filter(RequirementsAIConfig.id != exclude_id)
    
    for config in query.all():
        config.is_default = False