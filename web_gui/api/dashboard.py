"""
仪表板API模块
提供仪表板展示所需的各种数据接口
"""
import json
from datetime import datetime, timedelta
from flask import request, jsonify
from sqlalchemy import func, desc, and_

from . import api_bp
from .base import (
    standard_error_response, standard_success_response,
    log_api_call, db, TestCase, ExecutionHistory, StepExecution, Template
)

# 导入通用代码模式
try:
    from ..utils.common_patterns import safe_api_operation
except ImportError:
    from web_gui.utils.common_patterns import safe_api_operation

# 导入查询优化器
try:
    from ..services.query_optimizer import QueryOptimizer
except ImportError:
    from web_gui.services.query_optimizer import QueryOptimizer


# ==================== 仪表板数据 ====================

@api_bp.route('/dashboard/summary', methods=['GET'])
@log_api_call
@safe_api_operation("获取仪表板摘要数据")
def get_dashboard_summary():
    """获取仪表板摘要数据（优化版本）"""
    # 获取时间范围
    days = request.args.get('days', 30, type=int)
    
    # 使用优化的查询方法
    dashboard_data = QueryOptimizer.get_dashboard_stats(days=days)
    
    return dashboard_data


@api_bp.route('/dashboard/recent-activities', methods=['GET'])
@log_api_call
@safe_api_operation("获取最近活动")
def get_recent_activities():
    """获取最近活动"""
    limit = request.args.get('limit', 10, type=int)
    
    # 最近的执行记录
    recent_executions = db.session.query(
        ExecutionHistory,
        TestCase.name.label('testcase_name')
    ).join(TestCase).order_by(
        ExecutionHistory.start_time.desc()
    ).limit(limit).all()
    
    activities = []
    for execution, testcase_name in recent_executions:
        activities.append({
            'id': execution.id,
            'type': 'execution',
            'testcase_name': testcase_name,
            'status': execution.status,
            'start_time': execution.start_time.isoformat(),
            'executed_by': execution.executed_by,
            'execution_id': execution.execution_id
        })
    
    return {
        'activities': activities,
        'total': len(activities)
    }


@api_bp.route('/dashboard/execution-chart', methods=['GET'])
@log_api_call
@safe_api_operation("获取执行图表数据")
def get_execution_chart():
    """获取执行图表数据"""
    days = request.args.get('days', 7, type=int)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 按小时分组的执行统计（适用于短期）
    if days <= 1:
        # 按小时统计
        hourly_stats = db.session.query(
            func.date_trunc('hour', ExecutionHistory.start_time).label('hour'),
            func.count(ExecutionHistory.id).label('count')
        ).filter(
            ExecutionHistory.start_time >= start_date
        ).group_by(
            func.date_trunc('hour', ExecutionHistory.start_time)
        ).order_by('hour').all()
        
        chart_data = [
            {
                'time': hour.strftime('%H:00'),
                'count': count
            }
            for hour, count in hourly_stats
        ]
    else:
        # 按天统计
        daily_stats = db.session.query(
            func.date(ExecutionHistory.start_time).label('date'),
            func.count(ExecutionHistory.id).label('count')
        ).filter(
            ExecutionHistory.start_time >= start_date
        ).group_by(
            func.date(ExecutionHistory.start_time)
        ).order_by('date').all()
        
        chart_data = []
        for date, count in daily_stats:
            # SQLite返回字符串，需要解析为日期对象
            if isinstance(date, str):
                try:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    time_str = date_obj.strftime('%m-%d')
                except ValueError:
                    time_str = date  # 如果解析失败，使用原字符串
            else:
                time_str = date.strftime('%m-%d')
            
            chart_data.append({
                'time': time_str,
                'count': count
            })
    
    return {
        'chart_data': chart_data,
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': days
        }
    }


@api_bp.route('/dashboard/top-testcases', methods=['GET'])
@log_api_call
@safe_api_operation("获取热门测试用例")
def get_top_testcases():
    """获取热门测试用例"""
    limit = request.args.get('limit', 5, type=int)
    days = request.args.get('days', 7, type=int)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 按执行次数排序的测试用例
    top_testcases = db.session.query(
        TestCase.id,
        TestCase.name,
        TestCase.category,
        func.count(ExecutionHistory.id).label('execution_count'),
        func.sum(func.case([(ExecutionHistory.status == 'success', 1)], else_=0)).label('success_count')
    ).join(ExecutionHistory).filter(
        TestCase.is_active == True,
        ExecutionHistory.start_time >= start_date
    ).group_by(
        TestCase.id, TestCase.name, TestCase.category
    ).order_by(
        desc('execution_count')
    ).limit(limit).all()
    
    testcase_stats = []
    for tc_id, name, category, exec_count, success_count in top_testcases:
        success_rate = (success_count / exec_count * 100) if exec_count > 0 else 0
        testcase_stats.append({
            'id': tc_id,
            'name': name,
            'category': category,
            'execution_count': exec_count,
            'success_count': success_count,
            'success_rate': round(success_rate, 2)
        })
    
    return {
        'testcases': testcase_stats,
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': days
        }
    }


@api_bp.route('/dashboard/failure-analysis', methods=['GET'])
@log_api_call
@safe_api_operation("获取失败分析数据")
def get_failure_analysis():
    """获取失败分析数据"""
    days = request.args.get('days', 7, type=int)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # 最常见的失败原因
    failure_reasons = db.session.query(
        ExecutionHistory.error_message,
        func.count(ExecutionHistory.id).label('count')
    ).filter(
        and_(
            ExecutionHistory.start_time >= start_date,
            ExecutionHistory.status == 'failed',
            ExecutionHistory.error_message.isnot(None)
        )
    ).group_by(ExecutionHistory.error_message).order_by(
        desc('count')
    ).limit(10).all()
    
    # 失败步骤分析 - 使用step_description而不是action
    failed_steps = db.session.query(
        StepExecution.step_description,
        func.count(StepExecution.id).label('count')
    ).join(ExecutionHistory).filter(
        and_(
            ExecutionHistory.start_time >= start_date,
            StepExecution.status == 'failed'
        )
    ).group_by(StepExecution.step_description).order_by(
        desc('count')
    ).limit(10).all()
    
    # 失败率最高的测试用例
    failure_prone_testcases = db.session.query(
        TestCase.name,
        func.count(ExecutionHistory.id).label('total_count'),
        func.count(func.case([(ExecutionHistory.status == 'failed', 1)])).label('failure_count')
    ).join(ExecutionHistory).filter(
        and_(
            TestCase.is_active == True,
            ExecutionHistory.start_time >= start_date
        )
    ).group_by(TestCase.id, TestCase.name).having(
        func.count(ExecutionHistory.id) >= 5  # 至少5次执行
    ).all()
    
    # 计算失败率
    failure_rates = []
    for name, total_count, failure_count in failure_prone_testcases:
        failure_rate = (failure_count / total_count * 100) if total_count > 0 else 0
        if failure_rate > 0:  # 只显示有失败的测试用例
            failure_rates.append({
                'name': name,
                'total_executions': total_count,
                'failures': failure_count,
                'failure_rate': round(failure_rate, 2)
            })
        
    failure_rates.sort(key=lambda x: x['failure_rate'], reverse=True)
    
    return {
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': days
        },
        'failure_reasons': [
            {'reason': reason, 'count': count}
            for reason, count in failure_reasons
        ],
        'failed_steps': [
            {'description': description, 'count': count}
            for description, count in failed_steps
        ],
        'failure_prone_testcases': failure_rates[:10]  # 只取前10个
    }


@api_bp.route('/dashboard/health-check', methods=['GET'])
@log_api_call
@safe_api_operation("获取系统健康状态")
def get_system_health():
    """获取系统健康状态"""
    # 检查最近的执行情况
    recent_hours = 24
    start_time = datetime.utcnow() - timedelta(hours=recent_hours)
    
    # 最近24小时的执行统计
    recent_executions = ExecutionHistory.query.filter(
        ExecutionHistory.start_time >= start_time
    ).count()
    
    recent_success = ExecutionHistory.query.filter(
        and_(
            ExecutionHistory.start_time >= start_time,
            ExecutionHistory.status == 'success'
        )
    ).count()
    
    recent_failures = ExecutionHistory.query.filter(
        and_(
            ExecutionHistory.start_time >= start_time,
            ExecutionHistory.status == 'failed'
        )
    ).count()
    
    # 系统健康指标
    health_score = 100
    health_issues = []
    
    # 计算成功率
    success_rate = (recent_success / recent_executions * 100) if recent_executions > 0 else 100
    
    if success_rate < 80:
        health_score -= 20
        health_issues.append(f'执行成功率偏低: {success_rate:.1f}%')
    
    if recent_executions == 0:
        health_score -= 10
        health_issues.append('最近24小时无执行活动')
    
    # 检查是否有长时间运行的任务
    long_running = ExecutionHistory.query.filter(
        and_(
            ExecutionHistory.status == 'running',
            ExecutionHistory.start_time < datetime.utcnow() - timedelta(hours=1)
        )
    ).count()
    
    if long_running > 0:
        health_score -= 15
        health_issues.append(f'{long_running}个任务运行时间超过1小时')
    
    # 确定健康状态
    if health_score >= 90:
        health_status = 'excellent'
    elif health_score >= 70:
        health_status = 'good'
    elif health_score >= 50:
        health_status = 'warning'
    else:
        health_status = 'critical'
    
    return {
        'health_status': health_status,
        'health_score': health_score,
        'issues': health_issues,
        'metrics': {
            'recent_executions': recent_executions,
            'recent_success': recent_success,
            'recent_failures': recent_failures,
            'success_rate': round(success_rate, 2),
            'long_running_tasks': long_running
        },
        'check_time': datetime.utcnow().isoformat()
    }