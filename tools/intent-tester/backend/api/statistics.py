"""
统计分析API模块
包含测试报告、统计数据和分析功能
"""

import json
from datetime import datetime, timedelta
from flask import request, jsonify
from sqlalchemy import func, desc

from . import api_bp
from .base import standard_error_response, standard_success_response, log_api_call

# 使用相对导入确保使用同一个db实例
from ..models import db, TestCase, ExecutionHistory, StepExecution


# ==================== 报告API ====================


@api_bp.route("/reports/failure-analysis", methods=["GET"])
@log_api_call
def get_reports_failure_analysis():
    """获取失败分析报告"""
    try:
        # 获取时间范围参数
        days = request.args.get("days", 30, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 查询失败的执行记录
        failed_executions = (
            ExecutionHistory.query.filter(
                ExecutionHistory.status.in_(["failed", "error"]),
                ExecutionHistory.start_time >= start_date,
            )
            .order_by(desc(ExecutionHistory.start_time))
            .limit(100)
            .all()
        )

        # 分析失败原因
        failure_patterns = {}
        failure_by_testcase = {}

        for execution in failed_executions:
            error_msg = execution.error_message or "未知错误"

            # 简化错误信息作为分类
            error_category = _categorize_error(error_msg)

            if error_category not in failure_patterns:
                failure_patterns[error_category] = {"count": 0, "examples": []}

            failure_patterns[error_category]["count"] += 1
            if len(failure_patterns[error_category]["examples"]) < 3:
                failure_patterns[error_category]["examples"].append(
                    {
                        "execution_id": execution.execution_id,
                        "test_case_name": (
                            execution.test_case.name if execution.test_case else "未知"
                        ),
                        "error_message": (
                            error_msg[:200] + "..."
                            if len(error_msg) > 200
                            else error_msg
                        ),
                        "start_time": execution.start_time.isoformat(),
                    }
                )

            # 按测试用例统计
            testcase_name = (
                execution.test_case.name if execution.test_case else "未知测试用例"
            )
            if testcase_name not in failure_by_testcase:
                failure_by_testcase[testcase_name] = 0
            failure_by_testcase[testcase_name] += 1

        # 转换为列表格式
        failure_analysis = [
            {
                "category": category,
                "count": data["count"],
                "percentage": round(
                    data["count"] / max(len(failed_executions), 1) * 100, 1
                ),
                "examples": data["examples"],
            }
            for category, data in sorted(
                failure_patterns.items(), key=lambda x: x[1]["count"], reverse=True
            )
        ]

        testcase_failures = [
            {"testcase_name": name, "failure_count": count}
            for name, count in sorted(
                failure_by_testcase.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # 计算失败率（需要总执行数来计算）
        total_executions = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= start_date
        ).count()
        failure_rate = (
            round(len(failed_executions) / max(total_executions, 1) * 100, 1)
            if total_executions > 0
            else 0
        )

        return standard_success_response(
            {
                "analysis_period": f"{days} 天",
                "total_failures": len(failed_executions),
                "failure_rate": failure_rate,
                "common_failures": failure_analysis,  # 重命名以匹配测试期望
                "failure_trends": [],  # 暂时返回空列表，完整实现可以按时间分组
                "top_failing_testcases": testcase_failures,
                "generated_at": datetime.utcnow().isoformat(),
            }
        )

    except Exception as e:
        return standard_error_response(f"获取失败分析失败: {str(e)}")


def _categorize_error(error_message):
    """将错误信息分类"""
    error_msg_lower = error_message.lower()

    if "timeout" in error_msg_lower or "超时" in error_msg_lower:
        return "超时错误"
    elif (
        "network" in error_msg_lower
        or "网络" in error_msg_lower
        or "connection" in error_msg_lower
    ):
        return "网络连接错误"
    elif "element" in error_msg_lower and (
        "not found" in error_msg_lower or "找不到" in error_msg_lower
    ):
        return "元素定位失败"
    elif (
        "database" in error_msg_lower
        or "sql" in error_msg_lower
        or "数据库" in error_msg_lower
    ):
        return "数据库错误"
    elif (
        "assertion" in error_msg_lower
        or "assert" in error_msg_lower
        or "断言" in error_msg_lower
    ):
        return "断言失败"
    elif "permission" in error_msg_lower or "权限" in error_msg_lower:
        return "权限错误"
    elif (
        "memory" in error_msg_lower
        or "out of memory" in error_msg_lower
        or "内存" in error_msg_lower
    ):
        return "内存错误"
    else:
        return "其他错误"


@api_bp.route("/reports/stats", methods=["GET"])
@log_api_call
def get_reports_stats():
    """获取报告统计数据"""
    try:
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")

        if start_date_str and end_date_str:
            start_date = datetime.fromisoformat(start_date_str)
            end_date = datetime.fromisoformat(end_date_str)
        else:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

        # 基础统计
        total_testcases = TestCase.query.filter(TestCase.is_active == True).count()

        total_executions = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= start_date,
            ExecutionHistory.start_time <= end_date,
        ).count()

        successful_executions = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= start_date,
            ExecutionHistory.start_time <= end_date,
            ExecutionHistory.status == "success",
        ).count()

        failed_executions = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= start_date,
            ExecutionHistory.start_time <= end_date,
            ExecutionHistory.status.in_(["failed", "error"]),
        ).count()

        success_rate = (successful_executions / max(total_executions, 1)) * 100

        return standard_success_response(
            {
                "total_testcases": total_testcases,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": round(success_rate, 1),
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            }
        )

    except Exception as e:
        return standard_error_response(f"获取报告统计失败: {str(e)}")


@api_bp.route("/stats/trend", methods=["GET"])
@log_api_call
def get_stats_trend():
    """获取趋势数据"""
    try:
        days = request.args.get("days", 7, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 按天统计执行数据
        daily_stats = []
        current_date = start_date

        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)

            day_executions = ExecutionHistory.query.filter(
                ExecutionHistory.start_time >= current_date,
                ExecutionHistory.start_time < next_date,
            ).count()

            day_success = ExecutionHistory.query.filter(
                ExecutionHistory.start_time >= current_date,
                ExecutionHistory.start_time < next_date,
                ExecutionHistory.status == "success",
            ).count()

            day_failed = ExecutionHistory.query.filter(
                ExecutionHistory.start_time >= current_date,
                ExecutionHistory.start_time < next_date,
                ExecutionHistory.status.in_(["failed", "error"]),
            ).count()

            daily_stats.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "total_executions": day_executions,
                    "successful_executions": day_success,
                    "failed_executions": day_failed,
                    "success_rate": round(
                        (day_success / max(day_executions, 1)) * 100, 1
                    ),
                }
            )

            current_date = next_date

        return standard_success_response(
            {"period_days": days, "daily_stats": daily_stats}
        )

    except Exception as e:
        return standard_error_response(f"获取趋势数据失败: {str(e)}")


@api_bp.route("/reports/success-rate", methods=["GET"])
@log_api_call
def get_reports_success_rate():
    """获取成功率数据"""
    try:
        days = request.args.get("days", 30, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 按测试用例统计成功率
        from sqlalchemy import case

        testcase_stats = (
            db.session.query(
                TestCase.name,
                func.count(ExecutionHistory.id).label("total"),
                func.sum(
                    case((ExecutionHistory.status == "success", 1), else_=0)
                ).label("success_count"),
            )
            .join(ExecutionHistory, TestCase.id == ExecutionHistory.test_case_id)
            .filter(
                TestCase.is_active == True, ExecutionHistory.start_time >= start_date
            )
            .group_by(TestCase.name)
            .all()
        )

        success_rate_data = []
        for testcase_name, total, success_count in testcase_stats:
            success_rate = (success_count / max(total, 1)) * 100
            success_rate_data.append(
                {
                    "testcase_name": testcase_name,
                    "total_executions": total,
                    "successful_executions": success_count or 0,
                    "success_rate": round(success_rate, 1),
                }
            )

        # 按成功率排序
        success_rate_data.sort(key=lambda x: x["success_rate"], reverse=True)

        return standard_success_response(
            {
                "analysis_period": f"{days} 天",
                "testcase_success_rates": success_rate_data,
            }
        )

    except Exception as e:
        return standard_error_response(f"获取成功率数据失败: {str(e)}")


@api_bp.route("/stats/today", methods=["GET"])
@log_api_call
def get_stats_today():
    """获取今日统计数据"""
    try:
        # 获取今日开始时间
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        # 今日统计
        today_executions = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= today, ExecutionHistory.start_time < tomorrow
        ).count()

        today_success = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= today,
            ExecutionHistory.start_time < tomorrow,
            ExecutionHistory.status == "success",
        ).count()

        today_failed = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= today,
            ExecutionHistory.start_time < tomorrow,
            ExecutionHistory.status.in_(["failed", "error"]),
        ).count()

        today_running = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= today,
            ExecutionHistory.start_time < tomorrow,
            ExecutionHistory.status.in_(["running", "pending"]),
        ).count()

        # 计算成功率
        today_success_rate = (today_success / max(today_executions, 1)) * 100

        # 活跃测试用例数（今日有执行的）
        active_testcases = (
            db.session.query(ExecutionHistory.test_case_id)
            .filter(
                ExecutionHistory.start_time >= today,
                ExecutionHistory.start_time < tomorrow,
            )
            .distinct()
            .count()
        )

        # 总测试用例数
        total_testcases = TestCase.query.filter(TestCase.is_active == True).count()

        return standard_success_response(
            {
                "date": today.strftime("%Y-%m-%d"),
                "total_executions": today_executions,
                "successful_executions": today_success,
                "failed_executions": today_failed,
                "running_executions": today_running,
                "success_rate": round(today_success_rate, 1),
                "active_testcases": active_testcases,
                "total_testcases": total_testcases,
            }
        )

    except Exception as e:
        return standard_error_response(f"获取今日统计失败: {str(e)}")


@api_bp.route("/system/status", methods=["GET"])
@log_api_call
def get_system_status():
    """获取系统状态"""
    try:
        import os
        import psutil
        from datetime import datetime

        # 系统基础信息
        system_info = {
            "server_time": datetime.utcnow().isoformat(),
            "uptime": "Running",  # 简化处理
            "status": "healthy",
        }

        # 尝试获取系统资源信息
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage("/")

            system_info.update(
                {
                    "cpu_usage": round(cpu_percent, 1),
                    "memory_usage": round(memory_info.percent, 1),
                    "disk_usage": round(disk_info.percent, 1),
                    "memory_total": round(memory_info.total / (1024**3), 2),  # GB
                    "disk_total": round(disk_info.total / (1024**3), 2),  # GB
                }
            )
        except:
            # 如果psutil不可用，返回基础信息
            system_info.update(
                {
                    "cpu_usage": 0,
                    "memory_usage": 0,
                    "disk_usage": 0,
                    "memory_total": 0,
                    "disk_total": 0,
                }
            )

        # 数据库连接状态
        try:
            from sqlalchemy import text

            db.session.execute(text("SELECT 1"))
            database_status = "connected"
        except:
            database_status = "disconnected"

        # 获取数据库统计
        total_testcases = TestCase.query.filter(TestCase.is_active == True).count()
        total_executions = ExecutionHistory.query.count()

        # 最近执行
        recent_executions = (
            ExecutionHistory.query.order_by(ExecutionHistory.start_time.desc())
            .limit(5)
            .all()
        )

        recent_list = []
        for exec in recent_executions:
            recent_list.append(
                {
                    "execution_id": exec.execution_id,
                    "testcase_name": exec.test_case.name if exec.test_case else "未知",
                    "status": exec.status,
                    "start_time": (
                        exec.start_time.isoformat() if exec.start_time else None
                    ),
                }
            )

        return standard_success_response(
            {
                "system": system_info,
                "database": {
                    "status": database_status,
                    "total_testcases": total_testcases,
                    "total_executions": total_executions,
                },
                "recent_executions": recent_list,
            }
        )

    except Exception as e:
        return standard_error_response(f"获取系统状态失败: {str(e)}")


# ==================== 统计报告 ====================


@api_bp.route("/statistics/overview", methods=["GET"])
@log_api_call
def get_statistics_overview():
    """获取统计概览"""
    try:
        # 获取时间范围参数
        days = request.args.get("days", 7, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 基础统计
        total_testcases = TestCase.query.filter(TestCase.is_active == True).count()
        total_executions = ExecutionHistory.query.filter(
            ExecutionHistory.start_time >= start_date
        ).count()

        # 执行统计
        execution_stats = (
            db.session.query(
                ExecutionHistory.status, func.count(ExecutionHistory.id).label("count")
            )
            .filter(ExecutionHistory.start_time >= start_date)
            .group_by(ExecutionHistory.status)
            .all()
        )

        status_counts = {
            "success": 0,
            "failed": 0,
            "cancelled": 0,
            "running": 0,
            "pending": 0,
        }

        for status, count in execution_stats:
            status_counts[status] = count

        # 计算成功率
        total_completed = status_counts["success"] + status_counts["failed"]
        success_rate = (
            (status_counts["success"] / total_completed * 100)
            if total_completed > 0
            else 0
        )

        # 最活跃的测试用例
        popular_testcases = (
            db.session.query(
                TestCase.name, func.count(ExecutionHistory.id).label("execution_count")
            )
            .join(ExecutionHistory)
            .filter(
                TestCase.is_active == True, ExecutionHistory.start_time >= start_date
            )
            .group_by(TestCase.id, TestCase.name)
            .order_by(desc("execution_count"))
            .limit(5)
            .all()
        )

        return standard_success_response(
            data={
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
                "overview": {
                    "total_testcases": total_testcases,
                    "total_executions": total_executions,
                    "success_rate": round(success_rate, 2),
                },
                "execution_status": status_counts,
                "popular_testcases": [
                    {"name": name, "count": count} for name, count in popular_testcases
                ],
            }
        )

    except Exception as e:
        return standard_error_response(f"获取统计概览失败: {str(e)}")


@api_bp.route("/statistics/execution-trends", methods=["GET"])
@log_api_call
def get_execution_trends():
    """获取执行趋势数据"""
    try:
        days = request.args.get("days", 7, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 按日期分组的执行统计
        daily_stats = (
            db.session.query(
                func.date(ExecutionHistory.start_time).label("date"),
                ExecutionHistory.status,
                func.count(ExecutionHistory.id).label("count"),
            )
            .filter(ExecutionHistory.start_time >= start_date)
            .group_by(func.date(ExecutionHistory.start_time), ExecutionHistory.status)
            .order_by(func.date(ExecutionHistory.start_time))
            .all()
        )

        # 组织数据
        trends = {}
        for date, status, count in daily_stats:
            date_str = date.strftime("%Y-%m-%d")
            if date_str not in trends:
                trends[date_str] = {
                    "success": 0,
                    "failed": 0,
                    "cancelled": 0,
                    "total": 0,
                }
            trends[date_str][status] = count
            trends[date_str]["total"] += count

        # 填补缺失的日期
        current_date = start_date.date()
        complete_trends = []

        while current_date <= end_date.date():
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in trends:
                complete_trends.append({"date": date_str, **trends[date_str]})
            else:
                complete_trends.append(
                    {
                        "date": date_str,
                        "success": 0,
                        "failed": 0,
                        "cancelled": 0,
                        "total": 0,
                    }
                )
            current_date += timedelta(days=1)

        return standard_success_response(
            data={
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
                "trends": complete_trends,
            }
        )

    except Exception as e:
        return standard_error_response(f"获取执行趋势失败: {str(e)}")


@api_bp.route("/statistics/step-analysis", methods=["GET"])
@log_api_call
def get_step_analysis():
    """获取步骤分析统计"""
    try:
        days = request.args.get("days", 7, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 最常见的失败步骤类型
        failed_steps = (
            db.session.query(
                StepExecution.action, func.count(StepExecution.id).label("count")
            )
            .join(ExecutionHistory)
            .filter(
                StepExecution.status == "failed",
                ExecutionHistory.start_time >= start_date,
            )
            .group_by(StepExecution.action)
            .order_by(desc("count"))
            .limit(10)
            .all()
        )

        # 平均执行时间最长的步骤类型
        slow_steps = (
            db.session.query(
                StepExecution.action,
                func.avg(StepExecution.duration).label("avg_duration"),
                func.count(StepExecution.id).label("count"),
            )
            .join(ExecutionHistory)
            .filter(
                StepExecution.status == "success",
                StepExecution.duration.isnot(None),
                ExecutionHistory.start_time >= start_date,
            )
            .group_by(StepExecution.action)
            .having(func.count(StepExecution.id) >= 5)  # 至少5次执行
            .order_by(desc("avg_duration"))
            .limit(10)
            .all()
        )

        # 步骤成功率统计
        step_success_rate = (
            db.session.query(
                StepExecution.action,
                func.count(func.case([(StepExecution.status == "success", 1)])).label(
                    "success_count"
                ),
                func.count(StepExecution.id).label("total_count"),
            )
            .join(ExecutionHistory)
            .filter(ExecutionHistory.start_time >= start_date)
            .group_by(StepExecution.action)
            .having(func.count(StepExecution.id) >= 10)  # 至少10次执行
            .all()
        )

        # 计算成功率
        success_rates = []
        for action, success_count, total_count in step_success_rate:
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            success_rates.append(
                {
                    "action": action,
                    "success_rate": round(success_rate, 2),
                    "total_executions": total_count,
                }
            )

        success_rates.sort(key=lambda x: x["success_rate"])

        return standard_success_response(
            data={
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
                "failed_steps": [
                    {"action": action, "count": count} for action, count in failed_steps
                ],
                "slow_steps": [
                    {
                        "action": action,
                        "avg_duration": round(float(avg_duration), 2),
                        "count": count,
                    }
                    for action, avg_duration, count in slow_steps
                ],
                "success_rates": success_rates,
            }
        )

    except Exception as e:
        return standard_error_response(f"获取步骤分析失败: {str(e)}")


@api_bp.route("/statistics/performance", methods=["GET"])
@log_api_call
def get_performance_stats():
    """获取性能统计"""
    try:
        days = request.args.get("days", 7, type=int)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 执行时长统计
        duration_stats = (
            db.session.query(
                func.avg(
                    func.extract(
                        "epoch", ExecutionHistory.end_time - ExecutionHistory.start_time
                    )
                ).label("avg_duration"),
                func.min(
                    func.extract(
                        "epoch", ExecutionHistory.end_time - ExecutionHistory.start_time
                    )
                ).label("min_duration"),
                func.max(
                    func.extract(
                        "epoch", ExecutionHistory.end_time - ExecutionHistory.start_time
                    )
                ).label("max_duration"),
                func.count(ExecutionHistory.id).label("count"),
            )
            .filter(
                ExecutionHistory.start_time >= start_date,
                ExecutionHistory.end_time.isnot(None),
                ExecutionHistory.status.in_(["success", "failed"]),
            )
            .first()
        )

        # 最耗时的测试用例
        slowest_testcases = (
            db.session.query(
                TestCase.name,
                func.avg(
                    func.extract(
                        "epoch", ExecutionHistory.end_time - ExecutionHistory.start_time
                    )
                ).label("avg_duration"),
            )
            .join(ExecutionHistory)
            .filter(
                ExecutionHistory.start_time >= start_date,
                ExecutionHistory.end_time.isnot(None),
                ExecutionHistory.status.in_(["success", "failed"]),
            )
            .group_by(TestCase.id, TestCase.name)
            .having(func.count(ExecutionHistory.id) >= 3)  # 至少3次执行
            .order_by(desc("avg_duration"))
            .limit(5)
            .all()
        )

        return standard_success_response(
            data={
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days,
                },
                "duration_stats": (
                    {
                        "avg_duration": round(
                            float(duration_stats.avg_duration or 0), 2
                        ),
                        "min_duration": round(
                            float(duration_stats.min_duration or 0), 2
                        ),
                        "max_duration": round(
                            float(duration_stats.max_duration or 0), 2
                        ),
                        "sample_size": duration_stats.count,
                    }
                    if duration_stats
                    else None
                ),
                "slowest_testcases": [
                    {"name": name, "avg_duration": round(float(avg_duration), 2)}
                    for name, avg_duration in slowest_testcases
                ],
            }
        )

    except Exception as e:
        return standard_error_response(f"获取性能统计失败: {str(e)}")


@api_bp.route("/statistics/export", methods=["GET"])
@log_api_call
def export_statistics():
    """导出统计报告"""
    try:
        # 获取参数
        days = request.args.get("days", 7, type=int)
        format_type = request.args.get("format", "json")  # json, csv

        if format_type not in ["json", "csv"]:
            return standard_error_response("不支持的导出格式", 400)

        # 收集所有统计数据
        from . import statistics as stats_module

        # 这里可以复用上面的函数获取数据
        # 简化处理，返回基本统计信息
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        export_data = {
            "export_time": datetime.utcnow().isoformat(),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "summary": {
                "total_testcases": TestCase.query.filter(
                    TestCase.is_active == True
                ).count(),
                "total_executions": ExecutionHistory.query.filter(
                    ExecutionHistory.start_time >= start_date
                ).count(),
            },
        }

        if format_type == "json":
            return jsonify(export_data)

        # CSV格式处理（简化）
        return standard_success_response(data=export_data, message="统计数据导出成功")

    except Exception as e:
        return standard_error_response(f"导出统计报告失败: {str(e)}")
