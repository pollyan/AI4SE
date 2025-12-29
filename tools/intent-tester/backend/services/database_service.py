"""
数据库服务层
提供统一的数据库操作接口，解决SQLAlchemy上下文问题
遵循架构设计原则，统一管理数据访问逻辑
"""

from flask import current_app, has_app_context
from contextlib import contextmanager
import json
from datetime import datetime
import uuid
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# 确保导入与Flask应用初始化的相同db实例
try:
    from ..models import db, TestCase, ExecutionHistory, StepExecution, Template
except ImportError:
    from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template

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

    # ==================== 模板相关操作 ====================

    @staticmethod
    def get_templates():
        """获取模板列表"""
        with current_app.app_context():
            # 目前返回空列表，未来实现
            return []


# 创建全局服务实例
database_service = DatabaseService()
