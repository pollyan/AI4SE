"""
数据库查询优化服务
提供优化的查询方法，减少N+1查询问题，提升性能
"""

from sqlalchemy import func, and_, or_, desc, case
from sqlalchemy.orm import joinedload, selectinload
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

try:
    # 相对导入（用于模块内调用）
    from ..models import (
        db,
        TestCase,
        ExecutionHistory,
        StepExecution,
        ExecutionVariable,
        VariableReference,
    )
except ImportError:
    try:
        # 绝对导入（用于测试环境）
        from ..models import (
            db,
            TestCase,
            ExecutionHistory,
            StepExecution,
            ExecutionVariable,
            VariableReference,
        )
    except ImportError:
        # 直接导入（用于独立运行）
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from ..models import (
            db,
            TestCase,
            ExecutionHistory,
            StepExecution,
            ExecutionVariable,
            VariableReference,
        )


class QueryOptimizer:
    """数据库查询优化器"""

    @staticmethod
    def get_testcases_with_stats(
        page: int = 1,
        per_page: int = 20,
        category: Optional[str] = None,
        search: Optional[str] = None,
        status: str = "active",
    ) -> Tuple[List[Dict], int]:
        """
        优化的测试用例列表查询，避免N+1问题

        Args:
            page: 页码
            per_page: 每页数量
            category: 分类过滤
            search: 搜索关键词
            status: 状态过滤

        Returns:
            (testcases_data, total_count)
        """
        # 构建执行统计子查询
        execution_stats = (
            db.session.query(
                ExecutionHistory.test_case_id,
                func.count(ExecutionHistory.id).label("total_executions"),
                func.sum(
                    case((ExecutionHistory.status == "success", 1), else_=0)
                ).label("successful_executions"),
                func.max(ExecutionHistory.start_time).label("last_execution_time"),
            )
            .group_by(ExecutionHistory.test_case_id)
            .subquery()
        )

        # 主查询
        query = db.session.query(
            TestCase,
            func.coalesce(execution_stats.c.total_executions, 0).label(
                "execution_count"
            ),
            func.coalesce(execution_stats.c.successful_executions, 0).label(
                "success_count"
            ),
            execution_stats.c.last_execution_time.label("last_execution"),
        ).outerjoin(execution_stats, TestCase.id == execution_stats.c.test_case_id)

        # 应用过滤条件
        if status == "active":
            query = query.filter(TestCase.is_active == True)
        elif status == "inactive":
            query = query.filter(TestCase.is_active == False)

        if category:
            query = query.filter(TestCase.category == category)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    TestCase.name.ilike(search_pattern),
                    TestCase.description.ilike(search_pattern),
                    TestCase.tags.ilike(search_pattern),
                )
            )

        # 获取总数
        total_count = query.count()

        # 分页和排序
        query = query.order_by(desc(TestCase.updated_at))
        offset = (page - 1) * per_page
        results = query.offset(offset).limit(per_page).all()

        # 构建返回数据
        testcases_data = []
        for testcase, exec_count, success_count, last_exec in results:
            data = testcase.to_dict(include_stats=False)  # 不包含统计信息，避免重复查询

            # 添加优化查询得到的统计信息
            data["execution_count"] = exec_count or 0
            data["success_rate"] = round(
                (success_count / exec_count * 100) if exec_count > 0 else 0, 1
            )
            data["last_execution_time"] = (
                last_exec.strftime("%Y-%m-%dT%H:%M:%S.%fZ") if last_exec else None
            )

            testcases_data.append(data)

        return testcases_data, total_count

    @staticmethod
    def get_execution_with_steps(execution_id: str) -> Optional[Dict]:
        """
        优化的执行详情查询，一次性加载所有相关数据

        Args:
            execution_id: 执行ID

        Returns:
            执行详情数据
        """
        execution = (
            db.session.query(ExecutionHistory)
            .options(
                joinedload(ExecutionHistory.test_case),
                selectinload(ExecutionHistory.step_executions),
                selectinload(ExecutionHistory.variables),
                selectinload(ExecutionHistory.variable_references),
            )
            .filter_by(execution_id=execution_id)
            .first()
        )

        if not execution:
            return None

        return execution.to_dict()

    @staticmethod
    def get_dashboard_stats(days: int = 30) -> Dict[str, Any]:
        """
        优化的仪表板统计查询

        Args:
            days: 统计天数

        Returns:
            统计数据
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 使用单个查询获取所有统计数据
        stats = (
            db.session.query(
                func.count(TestCase.id).label("total_testcases"),
                func.sum(case((TestCase.is_active == True, 1), else_=0)).label(
                    "active_testcases"
                ),
                func.count(ExecutionHistory.id).label("total_executions"),
                func.sum(
                    case((ExecutionHistory.status == "success", 1), else_=0)
                ).label("successful_executions"),
                func.sum(case((ExecutionHistory.status == "failed", 1), else_=0)).label(
                    "failed_executions"
                ),
                func.avg(ExecutionHistory.duration).label("avg_duration"),
            )
            .select_from(TestCase)
            .outerjoin(
                ExecutionHistory,
                and_(
                    TestCase.id == ExecutionHistory.test_case_id,
                    ExecutionHistory.start_time >= start_date,
                ),
            )
            .first()
        )

        # 获取最近执行历史
        recent_executions = (
            db.session.query(ExecutionHistory)
            .options(joinedload(ExecutionHistory.test_case))
            .filter(ExecutionHistory.start_time >= start_date)
            .order_by(desc(ExecutionHistory.start_time))
            .limit(10)
            .all()
        )

        # 获取分类统计
        category_stats = (
            db.session.query(TestCase.category, func.count(TestCase.id).label("count"))
            .filter(TestCase.is_active == True)
            .group_by(TestCase.category)
            .all()
        )

        return {
            "summary": {
                "total_testcases": stats.total_testcases or 0,
                "active_testcases": stats.active_testcases or 0,
                "total_executions": stats.total_executions or 0,
                "success_rate": round(
                    (
                        (stats.successful_executions / stats.total_executions * 100)
                        if stats.total_executions > 0
                        else 0
                    ),
                    1,
                ),
                "average_duration": round(stats.avg_duration or 0, 2),
            },
            "recent_executions": [exec.to_dict() for exec in recent_executions],
            "category_distribution": [
                {"category": cat or "Uncategorized", "count": count}
                for cat, count in category_stats
            ],
        }

    @staticmethod
    def get_execution_variables_batch(
        execution_ids: List[str],
    ) -> Dict[str, List[Dict]]:
        """
        批量获取多个执行的变量数据

        Args:
            execution_ids: 执行ID列表

        Returns:
            {execution_id: [variables]}
        """
        if not execution_ids:
            return {}

        variables = (
            db.session.query(ExecutionVariable)
            .filter(ExecutionVariable.execution_id.in_(execution_ids))
            .order_by(
                ExecutionVariable.execution_id, ExecutionVariable.source_step_index
            )
            .all()
        )

        # 按execution_id分组
        result = {}
        for var in variables:
            if var.execution_id not in result:
                result[var.execution_id] = []
            result[var.execution_id].append(var.to_dict())

        return result

    @staticmethod
    def get_performance_stats(
        testcase_id: Optional[int] = None, days: int = 7
    ) -> Dict[str, Any]:
        """
        获取性能统计数据

        Args:
            testcase_id: 测试用例ID（可选）
            days: 统计天数

        Returns:
            性能统计数据
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        query = db.session.query(
            ExecutionHistory.start_time,
            ExecutionHistory.duration,
            ExecutionHistory.status,
            ExecutionHistory.steps_total,
            ExecutionHistory.steps_failed,
        ).filter(ExecutionHistory.start_time >= start_date)

        if testcase_id:
            query = query.filter(ExecutionHistory.test_case_id == testcase_id)

        executions = query.all()

        if not executions:
            return {
                "execution_count": 0,
                "avg_duration": 0,
                "success_rate": 0,
                "trend_data": [],
            }

        # 计算统计指标
        durations = [e.duration for e in executions if e.duration]
        success_count = sum(1 for e in executions if e.status == "success")

        # 按日期分组统计趋势
        from collections import defaultdict

        daily_stats = defaultdict(
            lambda: {"success": 0, "failed": 0, "total_duration": 0, "count": 0}
        )

        for execution in executions:
            date_key = execution.start_time.date().isoformat()
            daily_stats[date_key]["count"] += 1
            if execution.status == "success":
                daily_stats[date_key]["success"] += 1
            else:
                daily_stats[date_key]["failed"] += 1
            if execution.duration:
                daily_stats[date_key]["total_duration"] += execution.duration

        trend_data = []
        for date, stats in sorted(daily_stats.items()):
            trend_data.append(
                {
                    "date": date,
                    "success_count": stats["success"],
                    "failed_count": stats["failed"],
                    "success_rate": (
                        round(stats["success"] / stats["count"] * 100, 1)
                        if stats["count"] > 0
                        else 0
                    ),
                    "avg_duration": (
                        round(stats["total_duration"] / stats["count"], 2)
                        if stats["count"] > 0
                        else 0
                    ),
                }
            )

        return {
            "execution_count": len(executions),
            "avg_duration": (
                round(sum(durations) / len(durations), 2) if durations else 0
            ),
            "success_rate": round(success_count / len(executions) * 100, 1),
            "trend_data": trend_data,
        }

    @staticmethod
    def cleanup_old_data(days_to_keep: int = 90) -> Dict[str, int]:
        """
        清理旧数据，提升查询性能

        Args:
            days_to_keep: 保留天数

        Returns:
            清理统计结果
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # 获取要删除的执行记录
        old_executions = (
            db.session.query(ExecutionHistory)
            .filter(ExecutionHistory.created_at < cutoff_date)
            .all()
        )

        execution_ids = [e.execution_id for e in old_executions]

        # 统计删除数量
        stats = {
            "executions_deleted": len(old_executions),
            "step_executions_deleted": 0,
            "variables_deleted": 0,
            "references_deleted": 0,
        }

        if execution_ids:
            # 删除相关的步骤执行记录
            step_count = (
                db.session.query(StepExecution)
                .filter(StepExecution.execution_id.in_(execution_ids))
                .count()
            )
            stats["step_executions_deleted"] = step_count

            # 删除相关的变量记录
            var_count = (
                db.session.query(ExecutionVariable)
                .filter(ExecutionVariable.execution_id.in_(execution_ids))
                .count()
            )
            stats["variables_deleted"] = var_count

            # 删除相关的变量引用记录
            ref_count = (
                db.session.query(VariableReference)
                .filter(VariableReference.execution_id.in_(execution_ids))
                .count()
            )
            stats["references_deleted"] = ref_count

            # 批量删除
            db.session.query(StepExecution).filter(
                StepExecution.execution_id.in_(execution_ids)
            ).delete(synchronize_session=False)

            db.session.query(ExecutionVariable).filter(
                ExecutionVariable.execution_id.in_(execution_ids)
            ).delete(synchronize_session=False)

            db.session.query(VariableReference).filter(
                VariableReference.execution_id.in_(execution_ids)
            ).delete(synchronize_session=False)

            db.session.query(ExecutionHistory).filter(
                ExecutionHistory.execution_id.in_(execution_ids)
            ).delete(synchronize_session=False)

            db.session.commit()

        return stats
