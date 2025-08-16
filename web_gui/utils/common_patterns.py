"""
通用代码模式和重复代码提取
提供常用的代码模式，减少重复代码
"""
from functools import wraps
from typing import Dict, Any, Optional, Callable, Type, Tuple
from flask import request, jsonify
import logging

from .error_handler import APIError, ValidationError, NotFoundError, DatabaseError

logger = logging.getLogger(__name__)


def safe_api_operation(operation_name: str = "操作"):
    """
    安全API操作装饰器
    统一处理异常和响应格式
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # 如果函数返回的是Response对象，直接返回
                if hasattr(result, 'status_code'):
                    return result
                
                # 如果返回的是字典，包装成标准响应
                if isinstance(result, dict):
                    return jsonify({
                        'code': 200,
                        'message': f'{operation_name}成功',
                        'data': result
                    })
                
                return result
                
            except APIError as e:
                # API异常直接重抛，让上层错误处理器处理
                raise e
            except Exception as e:
                logger.error(f"{operation_name}失败: {str(e)}")
                raise APIError(f'{operation_name}失败: {str(e)}', 500)
        
        return wrapper
    return decorator


def paginated_query(query_builder: Callable, item_transformer: Optional[Callable] = None):
    """
    分页查询装饰器
    统一处理分页逻辑和响应格式
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取分页参数
            page = request.args.get('page', 1, type=int)
            size = request.args.get('size', 20, type=int)
            search = request.args.get('search', '')
            
            # 限制分页大小
            if size > 100:
                size = 100
            
            try:
                # 执行原函数获取查询对象
                query = func(*args, **kwargs)
                
                # 执行查询构建器
                if query_builder:
                    query = query_builder(query, {
                        'search': search,
                        'page': page,
                        'size': size
                    })
                
                # 分页
                pagination = query.paginate(
                    page=page, per_page=size, error_out=False
                )
                
                # 转换数据
                items = pagination.items
                if item_transformer:
                    items = [item_transformer(item) for item in items]
                else:
                    items = [item.to_dict() if hasattr(item, 'to_dict') else item 
                           for item in items]
                
                return jsonify({
                    'code': 200,
                    'message': '获取成功',
                    'data': {
                        'items': items,
                        'pagination': {
                            'page': page,
                            'per_page': size,
                            'total': pagination.total,
                            'pages': pagination.pages
                        }
                    }
                })
                
            except Exception as e:
                logger.error(f"分页查询失败: {str(e)}")
                raise APIError(f'查询失败: {str(e)}')
        
        return wrapper
    return decorator


def validate_resource_exists(model_class: Type, id_param: str = 'id', 
                           error_message: Optional[str] = None):
    """
    验证资源存在装饰器
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从kwargs获取ID参数
            resource_id = kwargs.get(id_param)
            
            if not resource_id:
                raise ValidationError(f'缺少参数: {id_param}')
            
            # 查询资源
            resource = model_class.query.get(resource_id)
            if not resource:
                message = error_message or f'{model_class.__name__}不存在'
                raise NotFoundError(message, resource_id)
            
            # 如果资源有is_active字段，检查是否活跃
            if hasattr(resource, 'is_active') and not resource.is_active:
                message = error_message or f'{model_class.__name__}已删除'
                raise NotFoundError(message, resource_id)
            
            # 将资源添加到kwargs中
            kwargs[f'{model_class.__name__.lower()}'] = resource
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def database_transaction(rollback_on_error: bool = True):
    """
    数据库事务装饰器
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from ..models import db
            
            try:
                result = func(*args, **kwargs)
                db.session.commit()
                return result
            except Exception as e:
                if rollback_on_error:
                    db.session.rollback()
                    logger.error(f"数据库事务回滚: {str(e)}")
                raise DatabaseError(f"数据库操作失败: {str(e)}")
        
        return wrapper
    return decorator


def require_json_data(required_fields: Optional[list] = None, 
                     optional_fields: Optional[list] = None):
    """
    要求JSON数据装饰器
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("请求必须包含JSON数据")
            
            data = request.get_json()
            if not data:
                raise ValidationError("JSON数据不能为空")
            
            # 验证必填字段
            if required_fields:
                for field in required_fields:
                    if field not in data or data[field] is None:
                        raise ValidationError(f"缺少必填字段: {field}")
                    
                    # 检查字符串字段是否为空
                    if isinstance(data[field], str) and not data[field].strip():
                        raise ValidationError(f"字段不能为空: {field}")
            
            # 将数据添加到kwargs中
            kwargs['data'] = data
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


class APIResponseHelper:
    """API响应辅助类"""
    
    @staticmethod
    def success(data: Any = None, message: str = "操作成功", code: int = 200) -> Dict[str, Any]:
        """成功响应"""
        response = {'code': code, 'message': message}
        if data is not None:
            response['data'] = data
        return response
    
    @staticmethod
    def error(message: str, code: int = 500, details: Dict = None) -> Tuple[Dict[str, Any], int]:
        """错误响应"""
        response = {'code': code, 'message': message}
        if details:
            response['details'] = details
        return response, code
    
    @staticmethod
    def paginated(items: list, page: int, size: int, total: int, 
                 message: str = "获取成功") -> Dict[str, Any]:
        """分页响应"""
        return {
            'code': 200,
            'message': message,
            'data': {
                'items': items,
                'pagination': {
                    'page': page,
                    'per_page': size,
                    'total': total,
                    'pages': (total + size - 1) // size
                }
            }
        }


class CommonQueries:
    """通用查询类"""
    
    @staticmethod
    def apply_search(query, search_term: str, search_fields: list):
        """应用搜索条件"""
        if search_term:
            from sqlalchemy import or_
            conditions = []
            for field in search_fields:
                if hasattr(field, 'ilike'):
                    conditions.append(field.ilike(f'%{search_term}%'))
            if conditions:
                query = query.filter(or_(*conditions))
        return query
    
    @staticmethod
    def apply_filters(query, filters: Dict[str, Any]):
        """应用过滤条件"""
        for field_name, value in filters.items():
            if value is not None:
                field = getattr(query.column_descriptions[0]['type'], field_name, None)
                if field:
                    query = query.filter(field == value)
        return query
    
    @staticmethod
    def apply_ordering(query, order_by: str = None, desc: bool = True):
        """应用排序"""
        if order_by:
            field = getattr(query.column_descriptions[0]['type'], order_by, None)
            if field:
                if desc:
                    query = query.order_by(field.desc())
                else:
                    query = query.order_by(field.asc())
        return query


# 通用的CRUD操作模式
class CRUDBase:
    """CRUD基础类"""
    
    def __init__(self, model_class: Type):
        self.model = model_class
    
    def get_by_id(self, item_id: int, raise_if_not_found: bool = True):
        """根据ID获取项目"""
        item = self.model.query.get(item_id)
        
        if not item and raise_if_not_found:
            raise NotFoundError(f'{self.model.__name__}不存在', item_id)
        
        # 检查是否软删除
        if item and hasattr(item, 'is_active') and not item.is_active:
            if raise_if_not_found:
                raise NotFoundError(f'{self.model.__name__}已删除', item_id)
            return None
        
        return item
    
    def create(self, data: Dict[str, Any]):
        """创建新项目"""
        try:
            if hasattr(self.model, 'from_dict'):
                item = self.model.from_dict(data)
            else:
                item = self.model(**data)
            
            from ..models import db
            db.session.add(item)
            db.session.flush()  # 获取ID但不提交
            
            return item
        except Exception as e:
            raise DatabaseError(f"创建{self.model.__name__}失败: {str(e)}")
    
    def update(self, item_id: int, data: Dict[str, Any]):
        """更新项目"""
        item = self.get_by_id(item_id)
        
        try:
            for key, value in data.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            
            if hasattr(item, 'updated_at'):
                from datetime import datetime
                item.updated_at = datetime.utcnow()
            
            return item
        except Exception as e:
            raise DatabaseError(f"更新{self.model.__name__}失败: {str(e)}")
    
    def delete(self, item_id: int, soft_delete: bool = True):
        """删除项目"""
        item = self.get_by_id(item_id)
        
        try:
            if soft_delete and hasattr(item, 'is_active'):
                item.is_active = False
                if hasattr(item, 'updated_at'):
                    from datetime import datetime
                    item.updated_at = datetime.utcnow()
            else:
                from ..models import db
                db.session.delete(item)
            
            return True
        except Exception as e:
            raise DatabaseError(f"删除{self.model.__name__}失败: {str(e)}")


def get_crud_helper(model_class: Type) -> CRUDBase:
    """获取CRUD辅助器"""
    return CRUDBase(model_class)