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

# 导入数据模型
try:
    from ..models import db, TestCase, ExecutionHistory, StepExecution
except ImportError:
    from web_gui.models import db, TestCase, ExecutionHistory, StepExecution

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
        # 使用SQLAlchemy查询
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        
        if not execution:
            return standard_error_response('执行记录不存在', 404)
        
        return format_success_response(
            message='获取成功',
            data=execution.to_dict()
        )
        
    except Exception as e:
        return standard_error_response(f'获取执行状态失败: {str(e)}')


@api_bp.route('/executions', methods=['GET'])
@log_api_call
def get_executions():
    """获取执行历史列表"""
    try:
        params = get_pagination_params()
        
        # 构建查询
        query = ExecutionHistory.query
        
        # 按测试用例过滤
        testcase_id = request.args.get('testcase_id', type=int)
        if testcase_id:
            query = query.filter(ExecutionHistory.test_case_id == testcase_id)
        
        # 按状态过滤
        status = request.args.get('status')
        if status:
            query = query.filter(ExecutionHistory.status == status)
        
        # 按执行者过滤
        executed_by = request.args.get('executed_by')
        if executed_by:
            query = query.filter(ExecutionHistory.executed_by == executed_by)
        
        # 排序
        query = query.order_by(ExecutionHistory.start_time.desc())
        
        # 分页
        page = params['page']
        size = params['size']
        
        # 获取总数
        total_count = query.count()
        
        # 获取分页数据
        executions = query.offset((page - 1) * size).limit(size).all()
        
        # 转换为字典
        executions_data = [execution.to_dict() for execution in executions]
        
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': {
                'items': executions_data,
                'total': total_count,
                'page': page,
                'size': size,
                'pages': (total_count + size - 1) // size
            }
        })
        
    except Exception as e:
        return standard_error_response(f'获取执行历史失败: {str(e)}')


@api_bp.route('/executions/<execution_id>/stop', methods=['POST'])
@log_api_call
def stop_execution(execution_id):
    """停止执行任务"""
    try:
        # 使用SQLAlchemy查询
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        
        if not execution:
            return standard_error_response('执行记录不存在', 404)
        
        if execution.status not in ['pending', 'running']:
            return standard_error_response('执行已完成，无法停止', 400)
        
        # TODO: 实现实际的停止执行逻辑
        # 需要向执行引擎发送停止信号
        # _stop_test_execution(execution_id)
        
        # 更新执行状态
        execution.status = 'stopped'
        execution.end_time = datetime.now()
        execution.error_message = '用户手动停止执行'
        
        db.session.commit()
        
        return format_success_response(
            message='执行已停止',
            data=execution.to_dict()
        )
        
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f'停止执行失败: {str(e)}')


@api_bp.route('/executions/<execution_id>', methods=['DELETE'])
@log_api_call
def delete_execution(execution_id):
    """删除执行记录"""
    try:
        # 使用SQLAlchemy查询
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        
        if not execution:
            return standard_error_response('执行记录不存在', 404)
        
        # 删除相关的步骤执行记录
        StepExecution.query.filter_by(execution_id=execution_id).delete()
        
        # 删除执行记录
        db.session.delete(execution)
        db.session.commit()
        
        return format_success_response(message='执行记录删除成功')
        
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f'删除执行记录失败: {str(e)}')


@api_bp.route('/executions/<execution_id>/export', methods=['GET'])
@log_api_call
def export_execution(execution_id):
    """导出单个执行报告"""
    try:
        # 使用SQLAlchemy查询执行记录
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        
        if not execution:
            return standard_error_response('执行记录不存在', 404)
        
        # 获取步骤执行详情
        step_executions = StepExecution.query.filter_by(execution_id=execution_id).order_by(StepExecution.step_index).all()
        
        # 构建导出数据，符合测试期望的格式
        execution_data = execution.to_dict()
        # 按照测试期望，直接返回导出数据（不用标准API响应格式）
        export_data = {
            'execution_id': execution.execution_id,
            'test_case_id': execution.test_case_id,
            'status': execution.status,
            'start_time': execution_data['start_time'],
            'end_time': execution_data['end_time'],
            'duration': execution.duration,
            'steps_total': execution.steps_total,
            'steps_passed': execution.steps_passed,
            'steps_failed': execution.steps_failed,
            'result_summary': execution_data['result_summary'],
            'step_executions': [step.to_dict() for step in step_executions],
            'exported_at': datetime.now().isoformat(),  # 使用测试期望的字段名
            'report_type': 'single_execution'
        }
        
        return jsonify(export_data)
        
    except Exception as e:
        return standard_error_response(f'导出执行报告失败: {str(e)}')


@api_bp.route('/executions/export-all', methods=['GET'])
@log_api_call
def export_all_executions():
    """导出所有执行报告"""
    try:
        params = get_pagination_params()
        
        # 构建查询
        query = ExecutionHistory.query
        
        # 排序
        query = query.order_by(ExecutionHistory.start_time.desc())
        
        # 分页
        page = params['page']
        size = params['size']
        
        # 获取分页数据
        executions = query.offset((page - 1) * size).limit(size).all()
        
        # 按照测试期望，构建导出数据
        export_data = {
            'reports': [execution.to_dict() for execution in executions],
            'exported_at': datetime.now().isoformat(),
            'report_type': 'batch_executions',
            'total_reports': len(executions),  # 当前页的报告数量
            'page': page,
            'size': size,
            'pagination': {
                'page': page,
                'size': size,
                'total': query.count()
            }
        }
        
        return jsonify(export_data)
        
    except Exception as e:
        return standard_error_response(f'导出执行报告失败: {str(e)}')


# ==================== MidScene集成API ====================

@api_bp.route('/midscene/execution-start', methods=['POST'])
@log_api_call
@require_json
def midscene_execution_start():
    """MidScene执行开始通知"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        if not data or not data.get('execution_id') or not data.get('testcase_id'):
            return standard_error_response('缺少必需字段: execution_id, testcase_id', 400)
        
        execution_id = data['execution_id']
        testcase_id = data['testcase_id']
        
        # 验证测试用例存在
        testcase = TestCase.query.filter_by(id=testcase_id, is_active=True).first()
        if not testcase:
            return standard_error_response('测试用例不存在', 404)
        
        # 创建或更新执行记录
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        
        if not execution:
            # 创建新执行记录
            execution = ExecutionHistory(
                execution_id=execution_id,
                test_case_id=testcase_id,
                status='running',
                mode=data.get('mode', 'headless'),
                browser=data.get('browser', 'chrome'),
                start_time=datetime.now(),
                executed_by=data.get('executed_by', 'midscene')
            )
            db.session.add(execution)
        else:
            # 更新现有记录
            execution.status = 'running'
            execution.start_time = datetime.now()
            execution.mode = data.get('mode', execution.mode)
            execution.browser = data.get('browser', execution.browser)
        
        db.session.commit()
        
        return format_success_response(
            message='执行开始记录成功',
            data=execution.to_dict()
        )
        
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f'记录执行开始失败: {str(e)}')


@api_bp.route('/midscene/execution-result', methods=['POST'])
@log_api_call
@require_json
def midscene_execution_result():
    """MidScene执行结果通知"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        if not data or not data.get('execution_id'):
            return standard_error_response('缺少必需字段: execution_id', 400)
        
        if 'status' not in data:
            return standard_error_response('缺少必需字段: status', 400)
        
        execution_id = data['execution_id']
        
        # 查找执行记录
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        
        if not execution:
            return standard_error_response('执行记录不存在', 404)
        
        # 更新执行记录
        execution.status = data.get('status', 'completed')
        execution.end_time = datetime.now()
        execution.duration = data.get('duration')
        execution.steps_total = data.get('steps_total')
        execution.steps_passed = data.get('steps_passed')
        execution.steps_failed = data.get('steps_failed')
        execution.result_summary = json.dumps(data.get('result_summary', {}))
        execution.error_message = data.get('error_message')
        
        # 处理步骤执行详情
        if 'steps' in data:
            # 清除现有步骤执行记录
            StepExecution.query.filter_by(execution_id=execution_id).delete()
            
            # 添加新的步骤执行记录
            for step_data in data['steps']:
                step_execution = StepExecution(
                    execution_id=execution_id,
                    step_index=step_data.get('index', 0),
                    step_description=step_data.get('description', ''),
                    status=step_data.get('status', 'unknown'),
                    start_time=datetime.fromisoformat(step_data['start_time']) if step_data.get('start_time') else None,
                    end_time=datetime.fromisoformat(step_data['end_time']) if step_data.get('end_time') else None,
                    duration=step_data.get('duration'),
                    screenshot_path=step_data.get('screenshot_path'),
                    ai_confidence=step_data.get('ai_confidence'),
                    ai_decision=json.dumps(step_data.get('ai_decision', {})),
                    error_message=step_data.get('error_message')
                )
                db.session.add(step_execution)
        
        db.session.commit()
        
        return format_success_response(
            message='执行结果记录成功',
            data=execution.to_dict()
        )
        
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f'记录执行结果失败: {str(e)}')


# ==================== 变量管理API ====================

@api_bp.route('/executions/<execution_id>/variables', methods=['GET'])
@log_api_call
def get_execution_variables(execution_id):
    """获取执行过程中的变量"""
    try:
        # 使用SQLAlchemy验证执行记录存在
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        
        if not execution:
            return standard_error_response('执行记录不存在', 404)
        
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