"""
测试执行相关API模块
包含执行任务管理、变量管理和执行历史查询
"""
import json
import uuid
from datetime import datetime
from flask import request, jsonify

from . import api_bp
from .base import (
    api_error_handler, db_transaction_handler, validate_json_data,
    format_success_response, ValidationError, NotFoundError,
    get_pagination_params, format_paginated_response,
    standard_error_response, standard_success_response,
    require_json, log_api_call
)

# 直接从models导入，确保使用同一个db实例 - 强制使用绝对导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, TestCase, ExecutionHistory, StepExecution

# 导入通用代码模式
try:
    from ..utils.common_patterns import (
        safe_api_operation, validate_resource_exists,
        database_transaction, require_json_data, APIResponseHelper
    )
except ImportError:
    from web_gui.utils.common_patterns import (
        safe_api_operation, validate_resource_exists,
        database_transaction, require_json_data, APIResponseHelper
    )

# 导入变量管理服务
try:
    from ..services.variable_suggestion_service import VariableSuggestionService
    from ..services.variable_manager import VariableManagerFactory
except ImportError:
    from web_gui.services.variable_suggestion_service import VariableSuggestionService
    from web_gui.services.variable_manager import VariableManagerFactory


# ==================== 执行任务管理 ====================

@api_bp.route('/executions', methods=['POST'])
@log_api_call
def create_execution():
    """创建执行任务"""
    try:
        data = request.get_json()
        
        if not data or not data.get('testcase_id'):
            return jsonify({
                'code': 400,
                'message': 'testcase_id参数不能为空'
            }), 400
        
        # 验证测试用例存在
        testcase = TestCase.query.filter(
            TestCase.id == data['testcase_id'],
            TestCase.is_active == True
        ).first()
        
        if not testcase:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=data['testcase_id'],
            status='pending',
            mode=data.get('mode', 'headless'),
            browser=data.get('browser', 'chrome'),
            start_time=datetime.utcnow(),
            executed_by=data.get('executed_by', 'system')
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # TODO: 集成实际的执行引擎
        # 异步启动执行任务
        # _trigger_test_execution(execution_id, testcase, data)
        
        return jsonify({
            'code': 200,
            'message': '执行任务创建成功',
            'data': {
                'execution_id': execution_id,
                'status': 'pending',
                'testcase_name': testcase.name,
                'start_time': execution.start_time.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'创建执行任务失败: {str(e)}'
        })


@api_bp.route('/executions/<execution_id>', methods=['GET'])
@log_api_call
def get_execution_status(execution_id):
    """获取执行状态"""
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
            # 获取执行记录
            execution_sql = """
            SELECT id, execution_id, test_case_id, status, mode, browser, 
                   start_time, end_time, error_message, executed_by, result_summary
            FROM execution_history 
            WHERE execution_id = %s
            """
            cursor.execute(execution_sql, (execution_id,))
            execution_row = cursor.fetchone()
            
            if not execution_row:
                return jsonify({
                    'code': 404,
                    'message': '执行记录不存在'
                }), 404
            
            # 获取步骤执行详情
            steps_sql = """
            SELECT id, execution_id, step_index, step_description, status, start_time, end_time, 
                   error_message, ai_decision, screenshot_path
            FROM step_executions 
            WHERE execution_id = %s 
            ORDER BY step_index
            """
            cursor.execute(steps_sql, (execution_id,))
            step_rows = cursor.fetchall()
            
            # 构建响应数据
            execution_data = {
                'id': execution_row[0],
                'execution_id': execution_row[1],
                'test_case_id': execution_row[2],
                'status': execution_row[3],
                'mode': execution_row[4],
                'browser': execution_row[5],
                'start_time': execution_row[6].isoformat() if execution_row[6] else None,
                'end_time': execution_row[7].isoformat() if execution_row[7] else None,
                'error_message': execution_row[8],
                'executed_by': execution_row[9],
                'result_summary': json.loads(execution_row[10]) if execution_row[10] else {},
                'step_executions': []
            }
            
            # 添加步骤执行数据
            for step_row in step_rows:
                step_data = {
                    'id': step_row[0],
                    'execution_id': step_row[1],
                    'step_index': step_row[2],
                    'step_description': step_row[3],
                    'status': step_row[4],
                    'start_time': step_row[5].isoformat() if step_row[5] else None,
                    'end_time': step_row[6].isoformat() if step_row[6] else None,
                    'error_message': step_row[7],
                    'ai_decision': json.loads(step_row[8]) if step_row[8] else {},
                    'screenshot_path': step_row[9]
                }
                execution_data['step_executions'].append(step_data)
            
        finally:
            cursor.close()
            conn.close()
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': execution_data
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取执行状态失败: {str(e)}'
        })


@api_bp.route('/executions', methods=['GET'])
@log_api_call
def get_executions():
    """获取执行历史列表"""
    try:
        params = get_pagination_params()
        
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
            # 构建查询条件
            where_conditions = []
            sql_params = []
            
            # 按测试用例过滤
            if params.get('testcase_id'):
                where_conditions.append("test_case_id = %s")
                sql_params.append(params['testcase_id'])
            
            # 按状态过滤
            status = request.args.get('status')
            if status:
                where_conditions.append("status = %s")
                sql_params.append(status)
            
            # 按执行者过滤
            executed_by = request.args.get('executed_by')
            if executed_by:
                where_conditions.append("executed_by = %s")
                sql_params.append(executed_by)
            
            # 构建WHERE子句
            where_clause = ""
            if where_conditions:
                where_clause = " WHERE " + " AND ".join(where_conditions)
            
            # 计算分页参数
            page = params['page']
            size = params['size']
            offset = (page - 1) * size
            
            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM execution_history{where_clause}"
            cursor.execute(count_sql, sql_params)
            total_count = cursor.fetchone()[0]
            
            # 获取分页数据
            data_sql = f"""
            SELECT id, execution_id, test_case_id, status, mode, browser, 
                   start_time, end_time, duration, steps_total, steps_passed, 
                   steps_failed, result_summary, error_message, executed_by, created_at
            FROM execution_history
            {where_clause}
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
            """
            
            cursor.execute(data_sql, sql_params + [size, offset])
            rows = cursor.fetchall()
            
            # 构建响应数据
            executions_data = []
            for row in rows:
                execution = {
                    'id': row[0],
                    'execution_id': row[1],
                    'test_case_id': row[2],
                    'status': row[3],
                    'mode': row[4],
                    'browser': row[5],
                    'start_time': row[6].isoformat() if row[6] else None,
                    'end_time': row[7].isoformat() if row[7] else None,
                    'duration': row[8],
                    'steps_total': row[9],
                    'steps_passed': row[10],
                    'steps_failed': row[11],
                    'result_summary': json.loads(row[12]) if row[12] else {},
                    'error_message': row[13],
                    'executed_by': row[14],
                    'created_at': row[15].isoformat() if row[15] else None
                }
                executions_data.append(execution)
            
        finally:
            cursor.close()
            conn.close()
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'items': executions_data,
                'pagination': {
                    'page': page,
                    'per_page': size,
                    'total': total_count,
                    'pages': (total_count + size - 1) // size
                }
            }
        })
        
    except Exception as e:
        return standard_error_response(f'获取执行历史失败: {str(e)}')


@api_bp.route('/executions/<execution_id>/stop', methods=['POST'])
@log_api_call
def stop_execution(execution_id):
    """停止执行任务"""
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
            # 检查执行记录是否存在
            check_sql = "SELECT id, status FROM execution_history WHERE execution_id = %s"
            cursor.execute(check_sql, (execution_id,))
            execution_row = cursor.fetchone()
            
            if not execution_row:
                return jsonify({
                    'code': 404,
                    'message': '执行记录不存在'
                }), 404
            
            execution_status = execution_row[1]
            
            if execution_status not in ['pending', 'running']:
                return jsonify({
                    'code': 400,
                    'message': '执行已完成，无法停止'
                }), 400
            
            # TODO: 实现实际的停止执行逻辑
            # 需要向执行引擎发送停止信号
            _stop_test_execution(execution_id)
            
            # 更新执行状态
            now = datetime.now()
            update_sql = """
            UPDATE execution_history 
            SET status = %s, end_time = %s, error_message = %s
            WHERE execution_id = %s
            """
            
            cursor.execute(update_sql, ('cancelled', now, '用户手动取消执行', execution_id))
            conn.commit()
            
            return jsonify({
                'code': 200,
                'message': '执行已停止'
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
            'message': f'停止执行失败: {str(e)}'
        })


# ==================== 变量管理API ====================

@api_bp.route('/executions/<execution_id>/variables', methods=['GET'])
@log_api_call
def get_execution_variables(execution_id):
    """获取执行过程中的变量"""
    try:
        # 使用psycopg2直接连接数据库验证执行记录存在
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
            # 验证执行记录存在
            check_sql = "SELECT id FROM execution_history WHERE execution_id = %s"
            cursor.execute(check_sql, (execution_id,))
            if not cursor.fetchone():
                return jsonify({
                    'code': 404,
                    'message': '执行记录不存在'
                }), 404
        finally:
            cursor.close()
            conn.close()
        
        # 获取变量管理器
        manager = VariableManagerFactory.get_manager(execution_id)
        variables = manager.list_variables()
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'execution_id': execution_id,
                'variables': variables,
                'total_count': len(variables)
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取变量失败: {str(e)}'
        })


@api_bp.route('/executions/<execution_id>/variables/<variable_name>', methods=['GET'])
@log_api_call
@safe_api_operation("获取变量详细信息")
def get_variable_detail(execution_id, variable_name):
    """获取变量详细信息"""
    manager = VariableManagerFactory.get_manager(execution_id)
    metadata = manager.get_variable_metadata(variable_name)
    
    if not metadata:
        from ..utils.error_handler import NotFoundError
        raise NotFoundError('变量不存在')
    
    return metadata


@api_bp.route('/executions/<execution_id>/variable-references', methods=['GET'])
@log_api_call
def get_variable_references(execution_id):
    """获取变量引用历史"""
    try:
        # TODO: 实现从VariableReference表查询
        # 目前返回模拟数据
        references = [
            {
                'step_index': 2,
                'reference': '${user_info.name}',
                'resolved_value': 'John Doe',
                'status': 'success',
                'timestamp': datetime.utcnow().isoformat()
            },
            {
                'step_index': 3,
                'reference': '${product_price}',
                'resolved_value': 99.99,
                'status': 'success', 
                'timestamp': datetime.utcnow().isoformat()
            }
        ]
        
        return standard_success_response(data={
            'execution_id': execution_id,
            'references': references,
            'total_count': len(references)
        })
        
    except Exception as e:
        return standard_error_response(f'获取变量引用失败: {str(e)}')


# ==================== 变量建议API ====================

@api_bp.route('/v1/executions/<execution_id>/variable-suggestions', methods=['GET'])
@api_bp.route('/executions/<execution_id>/variable-suggestions', methods=['GET'])
@log_api_call
def get_variable_suggestions(execution_id):
    """获取变量建议列表"""
    try:
        step_index = request.args.get('step_index', type=int)
        include_properties = request.args.get('include_properties', 'true').lower() == 'true'
        limit = request.args.get('limit', type=int)
        
        service = VariableSuggestionService.get_service(execution_id)
        result = service.get_variable_suggestions(
            step_index=step_index,
            include_properties=include_properties,
            limit=limit
        )
        
        return jsonify(result)
        
    except Exception as e:
        return standard_error_response(f'获取变量建议失败: {str(e)}')


@api_bp.route('/v1/executions/<execution_id>/variables/<variable_name>/properties', methods=['GET'])
@api_bp.route('/executions/<execution_id>/variables/<variable_name>/properties', methods=['GET'])
@log_api_call
def get_variable_properties(execution_id, variable_name):
    """获取变量属性探索"""
    try:
        max_depth = request.args.get('max_depth', 3, type=int)
        
        service = VariableSuggestionService.get_service(execution_id)
        result = service.get_variable_properties(variable_name, max_depth)
        
        if result is None:
            return standard_error_response('变量不存在', 404)
        
        return jsonify(result)
        
    except Exception as e:
        return standard_error_response(f'获取变量属性失败: {str(e)}')


@api_bp.route('/v1/executions/<execution_id>/variable-suggestions/search', methods=['GET'])
@log_api_call
def search_variables(execution_id):
    """搜索变量"""
    try:
        query = request.args.get('query', '').strip()
        if not query:
            return standard_error_response('缺少查询参数', 400)
        
        limit = request.args.get('limit', 10, type=int)
        step_index = request.args.get('step_index', type=int)
        
        service = VariableSuggestionService.get_service(execution_id)
        result = service.search_variables(query, limit, step_index)
        
        return jsonify(result)
        
    except Exception as e:
        return standard_error_response(f'搜索变量失败: {str(e)}')


@api_bp.route('/v1/executions/<execution_id>/variables/validate', methods=['POST'])
@log_api_call
@safe_api_operation("验证变量引用")
@require_json_data(required_fields=['references'])
def validate_variable_references(execution_id, data):
    """验证变量引用"""
    references = data['references']
    
    if not isinstance(references, list):
        from ..utils.error_handler import ValidationError
        raise ValidationError('references必须是数组')
    
    step_index = data.get('step_index')
    
    service = VariableSuggestionService.get_service(execution_id)
    results = service.validate_references(references, step_index)
    
    return {
        'execution_id': execution_id,
        'validation_results': results
    }


# ==================== 辅助函数 ====================

def _trigger_test_execution(execution_id: str, testcase: TestCase, data: dict):
    """触发测试执行（待实现）"""
    # TODO: 实现实际的测试执行逻辑
    # 这里应该：
    # 1. 解析测试用例步骤
    # 2. 调用MidSceneJS执行引擎
    # 3. 更新执行状态
    # 4. 记录步骤执行结果
    pass


def _stop_test_execution(execution_id: str):
    """停止测试执行（待实现）"""
    # TODO: 实现停止执行逻辑
    # 这里应该：
    # 1. 向执行引擎发送停止信号
    # 2. 清理执行资源
    # 3. 更新执行状态
    pass