"""
测试用例管理API模块
包含测试用例的CRUD操作和步骤管理
"""
import json
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional
from flask import request, jsonify, Response

from . import api_bp
from .base import (
    api_error_handler, db_transaction_handler, validate_json_data,
    format_success_response, ValidationError, NotFoundError,
    get_pagination_params, format_paginated_response,
    standard_error_response, standard_success_response,
    require_json, log_api_call, db, TestCase
)

# 导入通用代码模式
try:
    from ..utils.common_patterns import (
        safe_api_operation, validate_resource_exists, 
        database_transaction, require_json_data, get_crud_helper
    )
except ImportError:
    from web_gui.utils.common_patterns import (
        safe_api_operation, validate_resource_exists, 
        database_transaction, require_json_data, get_crud_helper
    )

# 导入查询优化器
try:
    from ..services.query_optimizer import QueryOptimizer
except ImportError:
    from web_gui.services.query_optimizer import QueryOptimizer


# ==================== 测试用例CRUD操作 ====================

@api_bp.route('/testcases', methods=['GET'])
@log_api_call
def get_testcases() -> Response:
    """获取测试用例列表（优化版本，避免N+1查询）"""
    try:
        params = get_pagination_params()
        
        # 使用原生SQL查询避免SQLAlchemy实例问题
        from flask import current_app
        import json
        
        page = params['page']
        size = params['size']
        category = params.get('category')
        search = params.get('search')
        
        # 使用原生SQL查询获取真实数据
        sql = """
        SELECT id, name, description, steps, tags, category, priority, 
               created_at, updated_at, created_by, is_active
        FROM test_cases 
        WHERE is_active = true
        """
        sql_params = []
        
        if category:
            sql += " AND category = %s"
            sql_params.append(category)
            
        if search:
            sql += " AND (name ILIKE %s OR description ILIKE %s OR tags ILIKE %s)"
            search_pattern = f'%{search}%'
            sql_params.extend([search_pattern, search_pattern, search_pattern])
        
        sql += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
        sql_params.extend([size, (page - 1) * size])
        
        # 获取总数的SQL
        count_sql = """
        SELECT COUNT(*) 
        FROM test_cases 
        WHERE is_active = true
        """
        count_params = []
        
        if category:
            count_sql += " AND category = %s"
            count_params.append(category)
            
        if search:
            count_sql += " AND (name ILIKE %s OR description ILIKE %s OR tags ILIKE %s)"
            search_pattern = f'%{search}%'
            count_params.extend([search_pattern, search_pattern, search_pattern])
        
        try:
            # 使用psycopg2直接连接数据库
            import psycopg2
            import os
            
            # 获取数据库连接信息
            try:
                from database_config import DatabaseConfig
                db_config = DatabaseConfig()
                database_url = db_config.database_url
            except ImportError:
                try:
                    from web_gui.database_config import DatabaseConfig
                    db_config = DatabaseConfig()
                    database_url = db_config.database_url
                except:
                    database_url = os.getenv('DATABASE_URL')
            
            if not database_url:
                raise Exception("未找到数据库连接配置")
            
            # 连接数据库
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            try:
                # 获取总数
                cursor.execute(count_sql, count_params)
                total_count = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
                
                # 获取数据
                cursor.execute(sql, sql_params)
                rows = cursor.fetchall()
                
                testcases_data = []
                for row in rows:
                    data = {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'steps': json.loads(row[3]) if row[3] else [],
                        'tags': row[4] or '',
                        'category': row[5] or '',
                        'priority': row[6] or 2,
                        'created_at': row[7].isoformat() if row[7] else None,
                        'updated_at': row[8].isoformat() if row[8] else None,
                        'created_by': row[9] or '',
                        'is_active': row[10],
                        'execution_count': 0,  # 后续可以添加真实查询
                        'success_rate': 0.0,
                        'last_execution_time': None
                    }
                    testcases_data.append(data)
                    
            finally:
                cursor.close()
                conn.close()
                    
        except Exception as e:
            raise Exception(f"数据库查询失败: {str(e)}")
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'items': testcases_data,
                'pagination': {
                    'page': params['page'],
                    'per_page': params['size'],
                    'total': total_count,
                    'pages': (total_count + params['size'] - 1) // params['size']
                }
            }
        })
        
    except Exception as e:
        return standard_error_response(f'获取失败: {str(e)}')


@api_bp.route('/testcases', methods=['POST'])
@log_api_call
def create_testcase():
    """创建测试用例"""
    try:
        data = request.get_json()
        
        # 基本验证
        if not data or not data.get('name'):
            return jsonify({
                'code': 400,
                'message': '测试用例名称不能为空'
            })
        
        # 使用psycopg2直接连接数据库
        import psycopg2
        import os
        
        # 获取数据库连接信息
        try:
            from database_config import DatabaseConfig
            db_config = DatabaseConfig()
            database_url = db_config.database_url
        except ImportError:
            try:
                from web_gui.database_config import DatabaseConfig
                db_config = DatabaseConfig()
                database_url = db_config.database_url
            except:
                database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            raise Exception("未找到数据库连接配置")
        
        # 准备插入数据
        name = data.get('name', '')
        description = data.get('description', '')
        steps = json.dumps(data.get('steps', []))
        tags = data.get('tags', '')
        category = data.get('category', '')
        priority = data.get('priority', 2)
        created_by = data.get('created_by', 'user')
        now = datetime.now()
        
        # 连接数据库并插入数据
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        try:
            # 插入测试用例
            insert_sql = """
            INSERT INTO test_cases (name, description, steps, tags, category, priority, 
                                  created_by, created_at, updated_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, description, steps, tags, category, priority, 
                     created_at, updated_at, created_by, is_active
            """
            
            cursor.execute(insert_sql, (
                name, description, steps, tags, category, priority,
                created_by, now, now, True
            ))
            
            # 获取插入的记录
            row = cursor.fetchone()
            
            if row:
                testcase_data = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'steps': json.loads(row[3]) if row[3] else [],
                    'tags': row[4] or '',
                    'category': row[5] or '',
                    'priority': row[6] or 2,
                    'created_at': row[7].isoformat() if row[7] else None,
                    'updated_at': row[8].isoformat() if row[8] else None,
                    'created_by': row[9] or '',
                    'is_active': row[10],
                    'execution_count': 0,
                    'success_rate': 0.0,
                    'last_execution_time': None
                }
                
                # 提交事务
                conn.commit()
                
                return jsonify({
                    'code': 200,
                    'message': '测试用例创建成功',
                    'data': testcase_data
                })
            else:
                raise Exception("创建测试用例失败，未返回数据")
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'创建失败: {str(e)}'
        })


@api_bp.route('/testcases/<int:testcase_id>', methods=['GET'])
@log_api_call
def get_testcase(testcase_id):
    """获取测试用例详情"""
    try:
        # 使用psycopg2直接连接数据库
        import psycopg2
        import os
        
        # 获取数据库连接信息
        try:
            from database_config import DatabaseConfig
            db_config = DatabaseConfig()
            database_url = db_config.database_url
        except ImportError:
            try:
                from web_gui.database_config import DatabaseConfig
                db_config = DatabaseConfig()
                database_url = db_config.database_url
            except:
                database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            raise Exception("未找到数据库连接配置")
        
        # 连接数据库
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        try:
            # 查询单个测试用例
            sql = """
            SELECT id, name, description, steps, tags, category, priority, 
                   created_at, updated_at, created_by, is_active
            FROM test_cases 
            WHERE id = %s AND is_active = true
            """
            
            cursor.execute(sql, (testcase_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({
                    'code': 404,
                    'message': '测试用例不存在'
                }), 404
            
            testcase_data = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'steps': json.loads(row[3]) if row[3] else [],
                'tags': row[4] or '',
                'category': row[5] or '',
                'priority': row[6] or 2,
                'created_at': row[7].isoformat() if row[7] else None,
                'updated_at': row[8].isoformat() if row[8] else None,
                'created_by': row[9] or '',
                'is_active': row[10],
                'execution_count': 0,
                'success_rate': 0.0,
                'last_execution_time': None
            }
            
        finally:
            cursor.close()
            conn.close()
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': testcase_data
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        })


@api_bp.route('/testcases/<int:testcase_id>', methods=['PUT'])
@log_api_call
def update_testcase(testcase_id):
    """更新测试用例"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'code': 400,
                'message': '请求数据不能为空'
            }), 400
        
        # 使用psycopg2直接连接数据库
        import psycopg2
        import os
        
        # 获取数据库连接信息
        try:
            from database_config import DatabaseConfig
            db_config = DatabaseConfig()
            database_url = db_config.database_url
        except ImportError:
            try:
                from web_gui.database_config import DatabaseConfig
                db_config = DatabaseConfig()
                database_url = db_config.database_url
            except:
                database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            raise Exception("未找到数据库连接配置")
        
        # 连接数据库
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        try:
            # 首先检查测试用例是否存在
            check_sql = "SELECT id FROM test_cases WHERE id = %s AND is_active = true"
            cursor.execute(check_sql, (testcase_id,))
            if not cursor.fetchone():
                return jsonify({
                    'code': 404,
                    'message': '测试用例不存在'
                }), 404
            
            # 构建更新语句
            update_fields = []
            update_values = []
            
            if 'name' in data:
                update_fields.append("name = %s")
                update_values.append(data['name'])
            if 'description' in data:
                update_fields.append("description = %s")
                update_values.append(data['description'])
            if 'steps' in data:
                update_fields.append("steps = %s")
                update_values.append(json.dumps(data['steps']))
            if 'tags' in data:
                update_fields.append("tags = %s")
                update_values.append(data['tags'] if isinstance(data['tags'], str) else ','.join(data['tags']))
            if 'category' in data:
                update_fields.append("category = %s")
                update_values.append(data['category'])
            if 'priority' in data:
                update_fields.append("priority = %s")
                update_values.append(data['priority'])
            
            if not update_fields:
                return jsonify({
                    'code': 400,
                    'message': '没有要更新的字段'
                }), 400
            
            # 添加更新时间
            update_fields.append("updated_at = %s")
            update_values.append(datetime.now())
            update_values.append(testcase_id)
            
            # 执行更新
            update_sql = f"""
            UPDATE test_cases 
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING id, name, description, steps, tags, category, priority, 
                     created_at, updated_at, created_by, is_active
            """
            
            cursor.execute(update_sql, update_values)
            row = cursor.fetchone()
            
            if row:
                testcase_data = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'steps': json.loads(row[3]) if row[3] else [],
                    'tags': row[4] or '',
                    'category': row[5] or '',
                    'priority': row[6] or 2,
                    'created_at': row[7].isoformat() if row[7] else None,
                    'updated_at': row[8].isoformat() if row[8] else None,
                    'created_by': row[9] or '',
                    'is_active': row[10],
                    'execution_count': 0,
                    'success_rate': 0.0,
                    'last_execution_time': None
                }
                
                # 提交事务
                conn.commit()
                
                return jsonify({
                    'code': 200,
                    'message': '测试用例更新成功',
                    'data': testcase_data
                })
            else:
                raise Exception("更新测试用例失败")
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'更新失败: {str(e)}'
        })


@api_bp.route('/testcases/<int:testcase_id>', methods=['DELETE'])
@log_api_call
def delete_testcase(testcase_id):
    """删除测试用例（软删除）"""
    try:
        # 使用psycopg2直接连接数据库
        import psycopg2
        import os
        
        # 获取数据库连接信息
        try:
            from database_config import DatabaseConfig
            db_config = DatabaseConfig()
            database_url = db_config.database_url
        except ImportError:
            try:
                from web_gui.database_config import DatabaseConfig
                db_config = DatabaseConfig()
                database_url = db_config.database_url
            except:
                database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            raise Exception("未找到数据库连接配置")
        
        # 连接数据库
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        try:
            # 首先检查测试用例是否存在
            check_sql = "SELECT id FROM test_cases WHERE id = %s AND is_active = true"
            cursor.execute(check_sql, (testcase_id,))
            if not cursor.fetchone():
                return jsonify({
                    'code': 404,
                    'message': '测试用例不存在'
                }), 404
            
            # 软删除测试用例
            delete_sql = """
            UPDATE test_cases 
            SET is_active = false, updated_at = %s
            WHERE id = %s
            """
            
            cursor.execute(delete_sql, (datetime.now(), testcase_id))
            
            # 提交事务
            conn.commit()
            
            return jsonify({
                'code': 200,
                'message': '测试用例删除成功'
            })
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'删除失败: {str(e)}'
        })


# ==================== 测试用例步骤管理 ====================

@api_bp.route('/testcases/<int:testcase_id>/steps', methods=['GET'])
@log_api_call
@safe_api_operation("获取测试用例步骤")
@validate_resource_exists(TestCase, 'testcase_id', '测试用例不存在')
def get_testcase_steps(testcase_id, testcase):
    """获取测试用例步骤"""
    steps = json.loads(testcase.steps) if testcase.steps else []
    
    return {
        'testcase_id': testcase_id,
        'steps': steps,
        'total_steps': len(steps)
    }


@api_bp.route('/testcases/<int:testcase_id>/steps', methods=['POST'])
@log_api_call
@safe_api_operation("添加测试用例步骤")
@validate_resource_exists(TestCase, 'testcase_id', '测试用例不存在')
@require_json_data(required_fields=['action'])
@database_transaction()
def add_testcase_step(testcase_id, testcase, data):
    """添加测试用例步骤"""
    # 获取现有步骤
    steps = json.loads(testcase.steps) if testcase.steps else []
    
    # 添加新步骤
    new_step = {
        'action': data['action'],
        'params': data.get('params', {}),
        'description': data.get('description', ''),
        'wait_time': data.get('wait_time', 0),
        'retry_count': data.get('retry_count', 0),
        'output_variable': data.get('output_variable', '')
    }
    
    # 支持指定位置插入
    position = data.get('position', len(steps))
    if position < 0 or position > len(steps):
        position = len(steps)
    
    steps.insert(position, new_step)
    
    # 更新数据库
    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()
    
    return {
        'step_index': position,
        'step': new_step,
        'total_steps': len(steps)
    }


@api_bp.route('/testcases/<int:testcase_id>/steps/<int:step_index>', methods=['PUT'])
@log_api_call
@safe_api_operation("更新测试用例步骤")
@validate_resource_exists(TestCase, 'testcase_id', '测试用例不存在')
@require_json_data(required_fields=['action'])
@database_transaction()
def update_testcase_step(testcase_id, step_index, testcase, data):
    """更新测试用例步骤"""
    steps = json.loads(testcase.steps) if testcase.steps else []
    
    if step_index < 0 or step_index >= len(steps):
        from ..utils.error_handler import ValidationError
        raise ValidationError('步骤索引超出范围')
    
    # 更新步骤
    steps[step_index].update({
        'action': data['action'],
        'params': data.get('params', {}),
        'description': data.get('description', ''),
        'wait_time': data.get('wait_time', 0),
        'retry_count': data.get('retry_count', 0),
        'output_variable': data.get('output_variable', '')
    })
    
    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()
    
    return {'step_index': step_index, 'step': steps[step_index]}


@api_bp.route('/testcases/<int:testcase_id>/steps/<int:step_index>', methods=['DELETE'])
@log_api_call
@safe_api_operation("删除测试用例步骤")
@validate_resource_exists(TestCase, 'testcase_id', '测试用例不存在')
@database_transaction()
def delete_testcase_step(testcase_id, step_index, testcase):
    """删除测试用例步骤"""
    steps = json.loads(testcase.steps) if testcase.steps else []
    
    if step_index < 0 or step_index >= len(steps):
        from ..utils.error_handler import ValidationError
        raise ValidationError('步骤索引超出范围')
    
    # 删除步骤
    deleted_step = steps.pop(step_index)
    
    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()
    
    return {
        'deleted_step': deleted_step,
        'remaining_steps': len(steps)
    }


@api_bp.route('/testcases/<int:testcase_id>/steps/reorder', methods=['PUT'])
@log_api_call
@safe_api_operation("重新排序测试用例步骤")
@validate_resource_exists(TestCase, 'testcase_id', '测试用例不存在')
@require_json_data(required_fields=['step_orders'])
@database_transaction()
def reorder_testcase_steps(testcase_id, testcase, data):
    """重新排序测试用例步骤"""
    step_orders = data['step_orders']
    
    steps = json.loads(testcase.steps) if testcase.steps else []
    
    if len(step_orders) != len(steps):
        from ..utils.error_handler import ValidationError
        raise ValidationError('步骤索引数量不匹配')
    
    # 验证索引有效性
    if not all(isinstance(idx, int) and 0 <= idx < len(steps) for idx in step_orders):
        from ..utils.error_handler import ValidationError
        raise ValidationError('无效的步骤索引')
    
    # 重新排序
    reordered_steps = [steps[i] for i in step_orders]
    
    testcase.steps = json.dumps(reordered_steps)
    testcase.updated_at = datetime.utcnow()
    
    return {'steps': reordered_steps}


@api_bp.route('/testcases/<int:testcase_id>/steps/<int:step_index>/duplicate', methods=['POST'])
@log_api_call
@safe_api_operation("复制测试用例步骤")
@validate_resource_exists(TestCase, 'testcase_id', '测试用例不存在')
@database_transaction()
def duplicate_testcase_step(testcase_id, step_index, testcase):
    """复制测试用例步骤"""
    steps = json.loads(testcase.steps) if testcase.steps else []
    
    if step_index < 0 or step_index >= len(steps):
        from ..utils.error_handler import ValidationError
        raise ValidationError('步骤索引超出范围')
    
    # 复制步骤
    original_step = steps[step_index].copy()
    
    # 修改描述以标识为复制
    if original_step.get('description'):
        original_step['description'] += ' (副本)'
    else:
        original_step['description'] = '复制的步骤'
    
    # 插入到原步骤后面
    steps.insert(step_index + 1, original_step)
    
    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()
    
    return {
        'original_index': step_index,
        'duplicate_index': step_index + 1,
        'duplicate_step': original_step,
        'total_steps': len(steps)
    }