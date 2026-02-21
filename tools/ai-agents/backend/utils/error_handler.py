"""
统一错误处理工具
增强版本，提供更完整的错误处理和日志记录功能
"""

from flask import jsonify, request
from functools import wraps
import logging
import traceback
import time
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

# 获取增强的日志器
logger = logging.getLogger(__name__)


class APIError(Exception):
    """自定义API异常类"""

    def __init__(
        self,
        message: str,
        code: int = 500,
        details: Optional[Dict] = None,
        error_id: Optional[str] = None,
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        self.error_id = error_id or str(uuid.uuid4())[:8]
        self.timestamp = datetime.utcnow().isoformat()
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "code": self.code,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ValidationError(APIError):
    """数据验证错误"""

    def __init__(self, message: str, field: str = None):
        details = {"field": field} if field else {}
        super().__init__(message, 400, details)


class DatabaseError(APIError):
    """数据库操作错误"""

    def __init__(self, message: str, operation: str = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message, 500, details)


class NotFoundError(APIError):
    """资源不存在错误"""

    def __init__(self, message: str, resource_id: Any = None):
        # 如果提供了resource_id，添加到消息中
        if resource_id:
            if not message.endswith(f"：{resource_id}"):
                message += f"：{resource_id}"
        super().__init__(message, 404, {"resource_id": resource_id})


def api_error_handler(f):
    """增强的API错误处理装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        error_logger = logging.getLogger("backend.api.error")
        start_time = time.time()

        # 生成请求ID用于追踪
        request_id = str(uuid.uuid4())[:8]
        if hasattr(request, "request_id"):
            request.request_id = request_id

        try:
            result = f(*args, **kwargs)
            duration = time.time() - start_time

            # 记录成功的API调用
            logger.info(
                f"[{request_id}] API成功: {request.method} {request.path} ({duration:.3f}s)"
            )
            return result

        except APIError as e:
            duration = time.time() - start_time

            # 记录API错误
            error_logger.warning(
                f"[{request_id}] API业务错误: {e.message} "
                f"(代码: {e.code}, 耗时: {duration:.3f}s)"
            )

            response_data = e.to_dict()
            response_data["request_id"] = request_id

            return jsonify(response_data), e.code

        except Exception as e:
            duration = time.time() - start_time
            error_id = str(uuid.uuid4())[:8]

            # 记录未预期的错误
            error_details = {
                "error_id": error_id,
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
                "request_method": (
                    request.method if hasattr(request, "method") else "unknown"
                ),
                "request_path": request.path if hasattr(request, "path") else "unknown",
                "request_data": _safe_get_request_data(),
                "duration": duration,
            }

            error_logger.error(
                f"[{request_id}] 系统错误 [{error_id}]: {str(e)} ({duration:.3f}s)"
            )
            error_logger.error(f"[{request_id}] 错误详情: {error_details}")

            # 生产环境下不暴露内部错误详情
            is_debug = logger.level <= logging.DEBUG

            return (
                jsonify(
                    {
                        "code": 500,
                        "message": "服务器内部错误，请联系系统管理员",
                        "error_id": error_id,
                        "request_id": request_id,
                        "details": (
                            error_details if is_debug else {"error_id": error_id}
                        ),
                    }
                ),
                500,
            )

    return decorated_function


def _safe_get_request_data() -> Dict[str, Any]:
    """安全地获取请求数据，避免敏感信息泄露"""
    try:
        if not hasattr(request, "is_json") or not request.is_json:
            return {}

        data = request.get_json()
        if not data:
            return {}

        # 过滤敏感字段
        sensitive_fields = ["password", "token", "secret", "key", "auth", "credential"]
        safe_data = {}

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                safe_data[key] = "***"
            elif isinstance(value, (str, int, float, bool)):
                safe_data[key] = value
            else:
                safe_data[key] = str(type(value).__name__)

        return safe_data

    except Exception:
        return {"error": "failed to parse request data"}


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
    response = {"code": 200, "message": message}
    if data is not None:
        response["data"] = data
    return response


def format_error_response(
    message: str, code: int = 500, details: Dict = None
) -> Tuple[Dict, int]:
    """格式化错误响应"""
    response = {"code": code, "message": message}
    if details:
        response["details"] = details
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
            logger.info(
                f"API调用成功: {request.method} {request.path} ({duration:.3f}s)"
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"API调用失败: {request.method} {request.path} ({duration:.3f}s) - {str(e)}"
            )
            raise

    return decorated_function
