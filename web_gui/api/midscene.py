"""
Midscene相关API模块
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

# 导入数据库模型
try:
    from ..models import db, ExecutionHistory, StepExecution
except ImportError:
    from web_gui.models import db, ExecutionHistory, StepExecution

logger = logging.getLogger(__name__)

# 从主蓝图导入
from . import api_bp
from .base import log_api_call

@api_bp.route('/midscene/execution-result', methods=['POST'])
@log_api_call
def midscene_execution_result():
    """接收MidScene服务器的执行结果并更新数据库记录"""
    try:
        data = request.get_json()
        print(f"🔄 接收到MidScene执行结果: {data}")
        
        # 验证必要字段
        required_fields = ['execution_id', 'testcase_id', 'status', 'mode']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必要字段: {field}'
                }), 400
        
        execution_id = data['execution_id']
        testcase_id = data['testcase_id']
        status = data['status']
        mode = data['mode']
        
        # 查找现有的执行记录
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if not execution:
            return jsonify({
                'code': 404,
                'message': f'执行记录不存在: {execution_id}'
            }), 404
        
        # 解析步骤数据
        steps_data = data.get('steps', [])
        steps_total = len(steps_data)
        steps_passed = sum(1 for step in steps_data if step.get('status') == 'success')
        steps_failed = sum(1 for step in steps_data if step.get('status') == 'failed')
        
        # 计算执行时间
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00')) if data.get('start_time') else execution.start_time
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00')) if data.get('end_time') else datetime.utcnow()
        duration = int((end_time - start_time).total_seconds())
        
        # 更新ExecutionHistory记录
        execution.status = status
        execution.end_time = end_time
        execution.duration = duration
        execution.steps_total = steps_total
        execution.steps_passed = steps_passed
        execution.steps_failed = steps_failed
        execution.error_message = data.get('error_message')
        
        db.session.flush()  # 获取ID
        
        # 创建StepExecution记录
        step_executions = []
        for i, step_data in enumerate(steps_data):
            step_execution = StepExecution(
                execution_id=execution_id,
                step_index=i,
                step_description=step_data.get('description', ''),
                status=step_data.get('status', 'pending'),
                start_time=datetime.fromisoformat(step_data['start_time'].replace('Z', '+00:00')) if step_data.get('start_time') else start_time,
                end_time=datetime.fromisoformat(step_data['end_time'].replace('Z', '+00:00')) if step_data.get('end_time') else end_time,
                duration=step_data.get('duration', 0),
                screenshot_path=step_data.get('screenshot_path'),
                error_message=step_data.get('error_message')
            )
            step_executions.append(step_execution)
            db.session.add(step_execution)
        
        db.session.commit()
        
        print(f"✅ 成功创建执行记录: {execution_id}, 包含 {len(step_executions)} 个步骤")
        
        return jsonify({
            'code': 200,
            'message': '执行结果记录成功',
            'data': {
                'execution_id': execution_id,
                'database_id': execution.id,
                'steps_count': len(step_executions)
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ 记录执行结果失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'记录执行结果失败: {str(e)}'
        }), 500

@api_bp.route('/midscene/execution-start', methods=['POST'])
@log_api_call
def midscene_execution_start():
    """接收MidScene服务器的执行开始通知并创建初始记录"""
    try:
        data = request.get_json()
        print(f"🚀 接收到MidScene执行开始通知: {data}")
        
        # 验证必要字段
        required_fields = ['execution_id', 'testcase_id', 'mode']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必要字段: {field}'
                }), 400
        
        execution_id = data['execution_id']
        testcase_id = data['testcase_id']
        mode = data['mode']
        
        # 创建初始ExecutionHistory记录
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=testcase_id,
            status='running',
            mode=mode,
            browser=data.get('browser', 'chrome'),
            start_time=datetime.utcnow(),
            steps_total=data.get('steps_total', 0),
            steps_passed=0,
            steps_failed=0,
            executed_by=data.get('executed_by', 'midscene-server'),
            created_at=datetime.utcnow()
        )
        
        db.session.add(execution)
        db.session.commit()
        
        print(f"✅ 成功创建初始执行记录: {execution_id}")
        
        return jsonify({
            'code': 200,
            'message': '执行开始记录成功',
            'data': {
                'execution_id': execution_id,
                'database_id': execution.id
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ 记录执行开始失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'记录执行开始失败: {str(e)}'
        }), 500