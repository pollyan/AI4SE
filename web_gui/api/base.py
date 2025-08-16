"""
API基础功能模块
提供通用的错误处理、验证和响应格式化功能
"""
from flask import jsonify, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# 导入统一错误处理工具
try:
    from ..utils.error_handler import (
        api_error_handler, db_transaction_handler, validate_json_data,
        format_success_response, ValidationError, NotFoundError, DatabaseError
    )
except ImportError:
    from web_gui.utils.error_handler import (
        api_error_handler, db_transaction_handler, validate_json_data,
        format_success_response, ValidationError, NotFoundError, DatabaseError
    )

# 导入数据模型 - 强制使用绝对导入确保使用同一个db实例
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, TestCase, ExecutionHistory, StepExecution, Template


def get_pagination_params():
    """获取分页参数"""
    return {
        'page': request.args.get('page', 1, type=int),
        'size': request.args.get('size', 20, type=int),
        'search': request.args.get('search', ''),
        'category': request.args.get('category', '')
    }


def format_paginated_response(pagination, items_key='items'):
    """格式化分页响应"""
    return {
        'code': 200,
        'data': {
            items_key: [item.to_dict() if hasattr(item, 'to_dict') else item for item in pagination.items],
            'total': pagination.total,
            'page': pagination.page,
            'size': pagination.per_page,
            'pages': pagination.pages
        },
        'message': '获取成功'
    }


def standard_error_response(message, code=500):
    """标准错误响应格式"""
    return jsonify({
        'code': code,
        'message': message
    }), code


def standard_success_response(data=None, message='操作成功', code=200):
    """标准成功响应格式"""
    response = {
        'code': code,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response)


def require_json(f):
    """要求请求包含JSON数据的装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return standard_error_response('请求必须包含JSON数据', 400)
        return f(*args, **kwargs)
    return wrapper


def log_api_call(f):
    """API调用日志装饰器"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        logger.info(f"API调用: {request.method} {request.path}")
        if request.is_json:
            logger.debug(f"请求数据: {request.get_json()}")
        try:
            result = f(*args, **kwargs)
            logger.info(f"API调用成功: {request.method} {request.path}")
            return result
        except Exception as e:
            logger.error(f"API调用失败: {request.method} {request.path}, 错误: {str(e)}")
            raise
    return wrapper