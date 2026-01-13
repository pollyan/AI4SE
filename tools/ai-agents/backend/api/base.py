"""
API 基础功能模块

提供通用的错误处理、验证和响应格式化功能。
从 web_gui/api/base.py 复制，用于 AI 智能体独立运行。
"""

from flask import jsonify, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# 导入统一错误处理工具
try:
    from ..utils.error_handler import (
        ValidationError,
        NotFoundError,
        DatabaseError,
    )
except ImportError:
    # 如果无法导入，定义简单的错误类
    class ValidationError(Exception):
        def __init__(self, message, code=400):
            self.message = message
            self.code = code
            super().__init__(message)
    
    class NotFoundError(Exception):
        def __init__(self, message, code=404):
            self.message = message
            self.code = code
            super().__init__(message)
    
    class DatabaseError(Exception):
        def __init__(self, message, code=500):
            self.message = message
            self.code = code
            super().__init__(message)


def standard_error_response(message, code=500):
    """标准错误响应格式"""
    return jsonify({"code": code, "message": message}), code


def standard_success_response(data=None, message="操作成功", code=200):
    """标准成功响应格式"""
    response = {"code": code, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), code if code != 200 else 200


def require_json(f):
    """要求请求包含 JSON 数据的装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return standard_error_response("请求必须包含 JSON 数据", 400)
        return f(*args, **kwargs)
    return wrapper


def log_api_call(f):
    """API 调用日志装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        logger.info(f"API 调用: {request.method} {request.path}")
        if request.is_json:
            logger.debug(f"请求数据: {request.get_json()}")
        try:
            result = f(*args, **kwargs)
            logger.info(f"API 调用成功: {request.method} {request.path}")
            return result
        except (ValidationError, NotFoundError, DatabaseError) as e:
            logger.error(f"API 调用失败: {request.method} {request.path}, 错误: {str(e)}")
            return jsonify({"code": e.code, "message": e.message}), e.code
        except Exception as e:
            logger.error(f"API 调用失败: {request.method} {request.path}, 错误: {str(e)}")
            raise
    return wrapper
