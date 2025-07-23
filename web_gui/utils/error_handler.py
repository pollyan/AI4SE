"""
统一错误处理工具
"""
from flask import jsonify
from functools import wraps
import logging
import traceback
from typing import Dict, Any, Tuple, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """自定义API异常类"""
    def __init__(self, message: str, code: int = 500, details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(APIError):
    """数据验证错误"""
    def __init__(self, message: str, field: str = None):
        details = {'field': field} if field else {}
        super().__init__(message, 400, details)

class DatabaseError(APIError):
    """数据库操作错误"""
    def __init__(self, message: str, operation: str = None):
        details = {'operation': operation} if operation else {}
        super().__init__(message, 500, details)

class NotFoundError(APIError):
    """资源不存在错误"""
    def __init__(self, resource: str, resource_id: Any = None):
        message = f"{resource}不存在"
        if resource_id:
            message += f"：{resource_id}"
        super().__init__(message, 404, {'resource': resource, 'resource_id': resource_id})

def api_error_handler(f):
    """API错误处理装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except APIError as e:
            logger.warning(f"API错误: {e.message} (代码: {e.code})")
            return jsonify({
                'code': e.code,
                'message': e.message,
                'details': e.details
            }), e.code
        except Exception as e:
            # 记录完整的错误信息
            error_details = {
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }
            logger.error(f"未预期的错误: {str(e)}")
            logger.error(f"错误详情: {error_details}")
            
            return jsonify({
                'code': 500,
                'message': f'服务器内部错误: {str(e)}',
                'details': error_details if logger.level <= logging.DEBUG else {}
            }), 500
    return decorated_function

def db_transaction_handler(db):
    """数据库事务处理装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                db.session.commit()
                return result
            except Exception as e:
                db.session.rollback()
                logger.error(f"数据库事务回滚: {str(e)}")
                raise DatabaseError(f"数据库操作失败: {str(e)}")
        return decorated_function
    return decorator

def validate_json_data(required_fields: list = None, optional_fields: list = None):
    """JSON数据验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            
            # 检查是否有JSON数据
            if not request.is_json:
                raise ValidationError("请求必须包含JSON数据")
            
            data = request.get_json()
            if not data:
                raise ValidationError("JSON数据不能为空")
            
            # 验证必填字段
            if required_fields:
                for field in required_fields:
                    if field not in data or data[field] is None:
                        raise ValidationError(f"缺少必填字段: {field}", field)
                    
                    # 检查字符串字段是否为空
                    if isinstance(data[field], str) and not data[field].strip():
                        raise ValidationError(f"字段不能为空: {field}", field)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def format_success_response(data: Any = None, message: str = "操作成功") -> Dict:
    """格式化成功响应"""
    response = {
        'code': 200,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return response

def format_error_response(message: str, code: int = 500, details: Dict = None) -> Tuple[Dict, int]:
    """格式化错误响应"""
    response = {
        'code': code,
        'message': message
    }
    if details:
        response['details'] = details
    return response, code

def log_api_call(f):
    """API调用日志装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        start_time = time.time()
        
        logger.info(f"API调用开始: {request.method} {request.path}")
        
        try:
            result = f(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"API调用成功: {request.method} {request.path} ({duration:.3f}s)")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"API调用失败: {request.method} {request.path} ({duration:.3f}s) - {str(e)}")
            raise
    
    return decorated_function

# 导入time模块用于日志装饰器
import time