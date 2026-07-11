"""
数据库服务层
提供统一的数据库操作接口，解决SQLAlchemy上下文问题
遵循架构设计原则，统一管理数据访问逻辑
"""

from flask import current_app, has_app_context
from contextlib import contextmanager
import json
from datetime import datetime, timezone
import uuid
import logging
from functools import wraps
from typing import Any, Mapping, Sequence

logger = logging.getLogger(__name__)

# 确保导入与Flask应用初始化的相同db实例
try:
    from backend.models import db, TestCase, ExecutionHistory, StepExecution
except ImportError:
    from ..models import db, TestCase, ExecutionHistory, StepExecution

# 验证db实例导入
logger.debug(f"DatabaseService导入的db实例: {id(db)}")


def require_app_context(f):
    """装饰器：确保函数在Flask应用上下文中执行"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not has_app_context():
            raise RuntimeError(f"函数 {f.__name__} 需要Flask应用上下文")
        return f(*args, **kwargs)

    return decorated_function


class DatabaseService:
    """数据库服务类，提供统一的数据访问接口"""

    LIFECYCLE_CALLBACK_EXHAUSTED_CODE = "lifecycle_callback_exhausted"
    LIFECYCLE_CALLBACK_EXHAUSTED_MESSAGE = (
        "执行生命周期回调重试已耗尽，需要状态协调恢复"
    )

    @staticmethod
    @contextmanager
    def get_db_session():
        """获取数据库会话上下文管理器，统一处理事务"""
        try:
            yield db.session
            db.session.commit()
            logger.debug("数据库事务提交成功")
        except Exception as e:
            db.session.rollback()
            logger.error(f"数据库事务回滚: {str(e)}")
            raise e

    @staticmethod
    def ensure_app_context():
        """确保Flask应用上下文存在"""
        if not has_app_context():
            raise RuntimeError("需要Flask应用上下文才能访问数据库")

        logger.debug("Flask应用上下文检查通过")
        return True

    @staticmethod
    def handle_db_error(operation_name, error):
        """统一处理数据库错误"""
        error_msg = f"{operation_name}失败: {str(error)}"
        logger.error(error_msg)
        return {"error": error_msg}

    # ==================== 测试用例相关操作 ====================

    @staticmethod
    @require_app_context
    def get_testcases(page=1, size=20, search=None, category=None):
        """获取测试用例列表"""
        try:
            DatabaseService.ensure_app_context()

            query = TestCase.query.filter(TestCase.is_active == True)

            if category:
                query = query.filter(TestCase.category == category)

            if search:
                search_pattern = f"%{search}%"
                query = query.filter(
                    db.or_(
                        TestCase.name.ilike(search_pattern),
                        TestCase.description.ilike(search_pattern),
                        TestCase.tags.ilike(search_pattern),
                    )
                )

            query = query.order_by(TestCase.updated_at.desc())

            pagination = query.paginate(page=page, per_page=size, error_out=False)

            return {
                "items": [tc.to_dict(include_stats=False) for tc in pagination.items],
                "pagination": {
                    "page": page,
                    "per_page": size,
                    "total": pagination.total,
                    "pages": pagination.pages,
                },
            }
        except Exception as e:
            return DatabaseService.handle_db_error("获取测试用例列表", e)

    @staticmethod
    @require_app_context
    def get_testcase_by_id(testcase_id):
        """根据ID获取测试用例"""
        try:
            DatabaseService.ensure_app_context()

            return TestCase.query.filter(
                TestCase.id == testcase_id, TestCase.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"获取测试用例失败: {str(e)}")
            return None

    @staticmethod
    def create_testcase(data):
        """创建测试用例"""
        try:
            with DatabaseService.get_db_session():
                testcase = TestCase(
                    name=data.get("name"),
                    description=data.get("description", ""),
                    steps=json.dumps(data.get("steps", [])),
                    tags=(
                        data.get("tags", "")
                        if isinstance(data.get("tags"), str)
                        else ",".join(data.get("tags", []))
                    ),
                    category=data.get("category", ""),
                    priority=data.get("priority", 2),
                    created_by=data.get("created_by", "user"),
                )

                db.session.add(testcase)
                db.session.flush()  # 获取ID但不提交

                return testcase.to_dict(include_stats=False)
        except Exception as e:
            return DatabaseService.handle_db_error("创建测试用例", e)

    @staticmethod
    def update_testcase(testcase_id, data):
        """更新测试用例"""
        with current_app.app_context():
            testcase = DatabaseService.get_testcase_by_id(testcase_id)
            if not testcase:
                return None

            with DatabaseService.get_db_session():
                if "name" in data:
                    testcase.name = data["name"]
                if "description" in data:
                    testcase.description = data["description"]
                if "steps" in data:
                    testcase.steps = json.dumps(data["steps"])
                if "tags" in data:
                    testcase.tags = (
                        data["tags"]
                        if isinstance(data["tags"], str)
                        else ",".join(data["tags"])
                    )
                if "category" in data:
                    testcase.category = data["category"]
                if "priority" in data:
                    testcase.priority = data["priority"]

                testcase.updated_at = datetime.utcnow()

                return testcase.to_dict(include_stats=False)

    @staticmethod
    def delete_testcase(testcase_id):
        """删除测试用例（软删除）"""
        with current_app.app_context():
            testcase = DatabaseService.get_testcase_by_id(testcase_id)
            if not testcase:
                return False

            with DatabaseService.get_db_session():
                testcase.is_active = False
                testcase.updated_at = datetime.utcnow()

                return True

    # ==================== 执行历史相关操作 ====================

    @staticmethod
    def _parse_lifecycle_timestamp(
        value: object, field_name: str
    ) -> datetime | None:
        """Parse an optional ISO-8601 callback timestamp into naive UTC."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field_name}必须是ISO-8601时间字符串")

        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"{field_name}不是有效的ISO-8601时间") from error

        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @staticmethod
    def _replace_step_snapshots(
        execution: ExecutionHistory,
        steps: Sequence[Mapping[str, Any]],
        start_time: datetime,
        end_time: datetime,
        *,
        allowed_statuses: frozenset[str] = frozenset(
            {"success", "failed", "skipped", "stopped"}
        ),
        allow_open_end_time: bool = False,
    ) -> None:
        """Atomically replace one validated execution step projection."""
        validated_steps = []
        seen_step_indexes = set()
        for position, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValueError("steps必须是对象数组")
            step_index = step.get("index", step.get("step_index", position))
            if not isinstance(step_index, int) or isinstance(step_index, bool):
                raise ValueError("steps中的index必须是整数")
            if step_index in seen_step_indexes:
                raise ValueError("steps中的index必须唯一")
            seen_step_indexes.add(step_index)

            step_start_time = (
                DatabaseService._parse_lifecycle_timestamp(
                    step.get("start_time"), "steps.start_time"
                )
                or start_time
            )
            parsed_end_time = DatabaseService._parse_lifecycle_timestamp(
                step.get("end_time"), "steps.end_time"
            )
            step_end_time = (
                parsed_end_time
                if parsed_end_time is not None or allow_open_end_time
                else end_time
            )
            step_status = step.get("status")
            if step_status not in allowed_statuses:
                raise ValueError("steps中的status不在允许范围内")

            validated_steps.append(
                (step, step_index, step_start_time, step_end_time, step_status)
            )

        StepExecution.query.filter_by(execution_id=execution.execution_id).delete()

        for (
            step,
            step_index,
            step_start_time,
            step_end_time,
            step_status,
        ) in validated_steps:
            step_metadata = {
                "action": step.get("action", "unknown"),
                "result_data": step.get("result_data", {}),
            }
            db.session.add(
                StepExecution(
                    execution_id=execution.execution_id,
                    step_index=step_index,
                    step_description=step.get(
                        "description", f"{step_metadata['action']} 步骤"
                    ),
                    status=step_status,
                    start_time=step_start_time,
                    end_time=step_end_time,
                    duration=step.get("duration"),
                    screenshot_path=step.get("screenshot_path"),
                    ai_confidence=step.get("ai_confidence"),
                    ai_decision=json.dumps(step_metadata, ensure_ascii=False),
                    error_message=step.get("error_message"),
                )
            )

    @staticmethod
    def _normalize_progress_steps(steps: object) -> list[dict[str, Any]]:
        """Validate and strip a proxy running snapshot to its safe fields."""
        if not isinstance(steps, list):
            raise ValueError("steps必须是对象数组")

        normalized: list[dict[str, Any]] = []
        seen_indexes: set[int] = set()
        allowed_statuses = {
            "pending",
            "running",
            "success",
            "failed",
            "skipped",
            "stopped",
        }
        for step in steps:
            if not isinstance(step, dict):
                raise ValueError("steps必须是对象数组")
            step_index = step.get("index")
            if (
                isinstance(step_index, bool)
                or not isinstance(step_index, int)
                or step_index < 0
            ):
                raise ValueError("steps中的index必须是非负整数")
            if step_index in seen_indexes:
                raise ValueError("steps中的index必须唯一")
            seen_indexes.add(step_index)

            description = step.get("description")
            if not isinstance(description, str) or not description.strip():
                raise ValueError("steps中的description必须是非空字符串")
            status = step.get("status")
            if status not in allowed_statuses:
                raise ValueError("steps中的status不在允许范围内")
            duration = step.get("duration")
            if duration is not None and (
                isinstance(duration, bool)
                or not isinstance(duration, int)
                or duration < 0
            ):
                raise ValueError("steps中的duration必须是非负整数或null")
            for field in ("start_time", "end_time"):
                value = step.get(field)
                if value is not None:
                    DatabaseService._parse_lifecycle_timestamp(value, field)

            normalized.append(
                {
                    "index": step_index,
                    "description": description,
                    "status": status,
                    "start_time": step.get("start_time"),
                    "end_time": step.get("end_time"),
                    "duration": duration,
                }
            )
        return normalized

    @staticmethod
    @require_app_context
    def apply_execution_progress(
        execution_id: str, steps: object
    ) -> dict[str, Any]:
        """Replace safe active progress without becoming a terminal authority."""
        normalized_steps = DatabaseService._normalize_progress_steps(steps)
        with DatabaseService.get_db_session():
            execution_query = ExecutionHistory.query.filter_by(
                execution_id=execution_id
            )
            execution = execution_query.first()
            if execution is None:
                return {"outcome": "not_found"}
            if execution.status in {"success", "failed", "stopped"}:
                return {"outcome": "terminal_noop", "execution": execution.to_dict()}
            if execution.status not in {"pending", "running"}:
                return {"outcome": "invalid_transition"}

            values = {
                "steps_total": len(normalized_steps),
                "steps_passed": sum(
                    1 for step in normalized_steps if step["status"] == "success"
                ),
                "steps_failed": sum(
                    1 for step in normalized_steps if step["status"] == "failed"
                ),
            }
            claimed = execution_query.filter(
                ExecutionHistory.status.in_({"pending", "running"})
            ).update(values, synchronize_session=False)
            if claimed == 0:
                db.session.expire_all()
                current = execution_query.first()
                if current is not None and current.status in {
                    "success",
                    "failed",
                    "stopped",
                }:
                    return {
                        "outcome": "terminal_noop",
                        "execution": current.to_dict(),
                    }
                return {"outcome": "invalid_transition"}

            db.session.expire_all()
            execution = execution_query.one()
            DatabaseService._replace_step_snapshots(
                execution,
                normalized_steps,
                execution.start_time,
                datetime.utcnow(),
                allowed_statuses=frozenset(
                    {
                        "pending",
                        "running",
                        "success",
                        "failed",
                        "skipped",
                        "stopped",
                    }
                ),
                allow_open_end_time=True,
            )
            return {"outcome": "applied", "execution": execution.to_dict()}

    @staticmethod
    def _clear_lifecycle_callback_exhausted(
        execution: ExecutionHistory,
    ) -> None:
        """Remove the active-only callback diagnostic after a terminal result."""
        if (
            execution.error_message
            == DatabaseService.LIFECYCLE_CALLBACK_EXHAUSTED_MESSAGE
        ):
            execution.error_message = None

        if not execution.result_summary:
            return
        try:
            summary = json.loads(execution.result_summary)
        except (TypeError, ValueError):
            return
        if not isinstance(summary, dict):
            return

        diagnostics = summary.get("diagnostics")
        if not isinstance(diagnostics, list):
            return
        retained = [
            diagnostic
            for diagnostic in diagnostics
            if not (
                isinstance(diagnostic, dict)
                and diagnostic.get("code")
                == DatabaseService.LIFECYCLE_CALLBACK_EXHAUSTED_CODE
            )
        ]
        if len(retained) == len(diagnostics):
            return
        if retained:
            summary["diagnostics"] = retained
        else:
            summary.pop("diagnostics", None)
        execution.result_summary = (
            json.dumps(summary, ensure_ascii=False) if summary else None
        )

    @staticmethod
    @require_app_context
    def apply_execution_lifecycle(
        execution_id: str,
        event: str,
        status: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Apply one idempotent, durable execution lifecycle callback.

        The result status is committed with its step snapshot in the same
        transaction.  Replayed callbacks for the already-reached state are
        explicit no-ops, while all other backward or skipped transitions are
        rejected.
        """
        with DatabaseService.get_db_session():
            execution_query = ExecutionHistory.query.filter_by(
                execution_id=execution_id
            )
            execution = execution_query.first()
            if execution is None:
                return {"outcome": "not_found"}

            if event == "started":
                if execution.status == "running":
                    return {"outcome": "noop", "execution": execution.to_dict()}
                if execution.status != "pending":
                    return {"outcome": "invalid_transition"}

                start_time = DatabaseService._parse_lifecycle_timestamp(
                    payload.get("start_time"), "start_time"
                )
                values = {"status": "running"}
                if start_time is not None:
                    values["start_time"] = start_time
                claimed = execution_query.filter(
                    ExecutionHistory.status == "pending"
                ).update(values, synchronize_session=False)
                if claimed == 0:
                    db.session.expire_all()
                    current = execution_query.first()
                    if current is not None and current.status == "running":
                        return {"outcome": "noop", "execution": current.to_dict()}
                    return {"outcome": "invalid_transition"}
                db.session.expire_all()
                execution = execution_query.one()
                return {"outcome": "applied", "execution": execution.to_dict()}

            if execution.status == status:
                return {"outcome": "noop", "execution": execution.to_dict()}
            if execution.status != "running":
                return {"outcome": "invalid_transition"}

            end_time = (
                DatabaseService._parse_lifecycle_timestamp(
                    payload.get("end_time"), "end_time"
                )
                or datetime.utcnow()
            )
            claimed = execution_query.filter(
                ExecutionHistory.status == "running"
            ).update({"status": status}, synchronize_session=False)
            if claimed == 0:
                db.session.expire_all()
                current = execution_query.first()
                if current is not None and current.status == status:
                    return {"outcome": "noop", "execution": current.to_dict()}
                return {"outcome": "invalid_transition"}

            db.session.expire_all()
            execution = execution_query.one()
            DatabaseService._clear_lifecycle_callback_exhausted(execution)
            steps = payload.get("steps")
            if steps is not None:
                DatabaseService._replace_step_snapshots(
                    execution, steps, execution.start_time, end_time
                )

            execution.end_time = end_time
            execution.duration = int((end_time - execution.start_time).total_seconds())
            if steps is not None:
                execution.steps_total = len(steps)
                execution.steps_passed = sum(
                    1 for step in steps if step.get("status") == "success"
                )
                execution.steps_failed = sum(
                    1 for step in steps if step.get("status") == "failed"
                )
            if "result_summary" in payload:
                execution.result_summary = json.dumps(
                    payload["result_summary"], ensure_ascii=False
                )
            if "error_message" in payload:
                execution.error_message = payload["error_message"]
            if "error_stack" in payload:
                execution.error_stack = payload["error_stack"]
            if "screenshots_path" in payload:
                execution.screenshots_path = payload["screenshots_path"]
            if "logs_path" in payload:
                execution.logs_path = payload["logs_path"]

            return {"outcome": "applied", "execution": execution.to_dict()}

    @staticmethod
    @require_app_context
    def record_lifecycle_callback_exhausted(
        execution_id: str,
    ) -> dict[str, Any]:
        """Persist one fixed, non-sensitive active reconciliation diagnostic."""
        with DatabaseService.get_db_session():
            execution_query = ExecutionHistory.query.filter_by(
                execution_id=execution_id
            )
            execution = execution_query.first()
            if execution is None:
                return {"outcome": "not_found"}
            if execution.status not in {"pending", "running"}:
                return {"outcome": "invalid_transition"}

            summary = (
                json.loads(execution.result_summary)
                if execution.result_summary
                else {}
            )
            if not isinstance(summary, dict):
                summary = {}
            diagnostics = summary.get("diagnostics")
            if not isinstance(diagnostics, list):
                diagnostics = []
            diagnostic = {
                "code": DatabaseService.LIFECYCLE_CALLBACK_EXHAUSTED_CODE
            }
            if diagnostic not in diagnostics:
                diagnostics.append(diagnostic)
            summary["diagnostics"] = diagnostics

            serialized_summary = json.dumps(summary, ensure_ascii=False)
            message = DatabaseService.LIFECYCLE_CALLBACK_EXHAUSTED_MESSAGE
            unchanged = (
                execution.result_summary == serialized_summary
                and execution.error_message == message
            )

            claimed = execution_query.filter(
                ExecutionHistory.status.in_(("pending", "running"))
            ).update(
                {
                    "result_summary": serialized_summary,
                    "error_message": message,
                },
                synchronize_session=False,
            )
            db.session.expire_all()
            current = execution_query.first()
            if claimed == 0:
                if current is None:
                    return {"outcome": "not_found"}
                return {"outcome": "invalid_transition"}
            return {
                "outcome": "noop" if unchanged else "applied",
                "execution": current.to_dict(),
            }

    @staticmethod
    @require_app_context
    def create_execution(
        testcase_id, mode="headless", browser="chrome", executed_by="system"
    ):
        """创建执行记录"""
        try:
            DatabaseService.ensure_app_context()

            testcase = DatabaseService.get_testcase_by_id(testcase_id)
            if not testcase:
                return None

            with DatabaseService.get_db_session():
                execution_id = str(uuid.uuid4())
                execution = ExecutionHistory(
                    execution_id=execution_id,
                    test_case_id=testcase_id,
                    status="pending",
                    mode=mode,
                    browser=browser,
                    start_time=datetime.utcnow(),
                    executed_by=executed_by,
                )

                db.session.add(execution)
                db.session.flush()

                return {
                    "execution_id": execution_id,
                    "status": "pending",
                    "testcase_name": testcase.name,
                    "start_time": execution.start_time.isoformat(),
                }
        except Exception as e:
            return DatabaseService.handle_db_error("创建执行记录", e)

    @staticmethod
    def get_execution_by_id(execution_id):
        """根据执行ID获取执行记录"""
        with current_app.app_context():
            execution = ExecutionHistory.query.filter_by(
                execution_id=execution_id
            ).first()
            if not execution:
                return None

            # 获取步骤执行详情
            step_executions = (
                StepExecution.query.filter_by(execution_id=execution_id)
                .order_by(StepExecution.step_index)
                .all()
            )

            execution_data = execution.to_dict()
            execution_data["step_executions"] = [
                step.to_dict() for step in step_executions
            ]

            return execution_data

    @staticmethod
    def get_executions(
        page=1, size=20, testcase_id=None, status=None, executed_by=None
    ):
        """获取执行历史列表"""
        with current_app.app_context():
            query = ExecutionHistory.query

            if testcase_id:
                query = query.filter(ExecutionHistory.test_case_id == testcase_id)

            if status:
                query = query.filter(ExecutionHistory.status == status)

            if executed_by:
                query = query.filter(ExecutionHistory.executed_by == executed_by)

            query = query.order_by(ExecutionHistory.start_time.desc())

            pagination = query.paginate(page=page, per_page=size, error_out=False)

            return {
                "items": [exec.to_dict() for exec in pagination.items],
                "pagination": {
                    "page": page,
                    "per_page": size,
                    "total": pagination.total,
                    "pages": pagination.pages,
                },
            }

    @staticmethod
    def stop_execution(execution_id):
        """停止执行"""
        with current_app.app_context():
            execution = ExecutionHistory.query.filter_by(
                execution_id=execution_id
            ).first()
            if not execution:
                return None

            if execution.status not in ["pending", "running"]:
                return {"error": "执行已完成，无法停止"}

            with DatabaseService.get_db_session():
                execution.status = "cancelled"
                execution.end_time = datetime.utcnow()
                execution.error_message = "用户手动取消执行"

                return {"message": "执行已停止"}


# 创建全局服务实例
database_service = DatabaseService()
