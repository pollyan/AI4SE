"""
测试执行相关API模块
包含执行任务管理、变量管理和执行历史查询
"""

import uuid
from datetime import datetime
from typing import Any, Mapping, Protocol

from flask import current_app, request, jsonify, Response

from flask import Blueprint
from sqlalchemy.exc import SQLAlchemyError

executions_bp = Blueprint("executions", __name__)
# from . import api_bp # Refactored to use own blueprint
from .base import (
    format_success_response,
    get_pagination_params,
    standard_error_response,
    standard_success_response,
    log_api_call,
)

# 导入数据模型
from backend.models import db, TestCase, ExecutionHistory, StepExecution
from backend.services.database_service import DatabaseService
from backend.services.proxy_execution_client import (
    ProxyExecutionClient,
    ProxyExecutionClientError,
)

# 导入通用代码模式

# 变量管理服务已简化 - 核心变量功能在其他服务中实现


# ==================== 执行任务管理 ====================


class _ExecutionProxy(Protocol):
    def dispatch_execution(self, payload: Mapping[str, Any]) -> dict[str, Any]: ...

    def get_execution_status(self, execution_id: str) -> dict[str, Any]: ...

    def stop_execution(self, execution_id: str) -> dict[str, Any]: ...


def _get_proxy_execution_client() -> _ExecutionProxy:
    injected_client = current_app.config.get("PROXY_EXECUTION_CLIENT")
    if injected_client is not None:
        return injected_client
    return ProxyExecutionClient(
        base_url=current_app.config.get("MIDSCENE_SERVER_URL"),
        timeout=current_app.config.get("MIDSCENE_API_TIMEOUT"),
    )


def _require_proxy_acceptance(result: object) -> None:
    if not isinstance(result, dict) or result.get("success") is not True:
        raise ProxyExecutionClientError("proxy did not explicitly accept the request")


def _proxy_failure_response(
    action: str, execution_id: str, _error: ProxyExecutionClientError
) -> tuple[Response, int]:
    current_app.logger.warning(
        "%s失败: execution_id=%s proxy_error_code=proxy_request_failed",
        action,
        execution_id,
    )
    return (
        jsonify(
            {
                "code": 502,
                "message": f"{action}失败",
                "data": {"execution_id": execution_id},
            }
        ),
        502,
    )


def _log_unexpected_execution_failure(action: str, execution_id: str) -> None:
    current_app.logger.error(
        "%s失败: execution_id=%s error_code=unexpected_execution_error",
        action,
        execution_id,
    )


def _build_dispatch_payload(
    execution: ExecutionHistory,
    testcase: TestCase,
    dispatch_options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the single Flask-to-proxy execution payload contract."""
    options = dispatch_options or {}
    return {
        "executionId": execution.execution_id,
        "testcase": testcase.to_dict(include_stats=False),
        "mode": execution.mode,
        "enable_cache": options.get("enable_cache", True),
        "timeout_settings": options.get("timeout_settings", {}),
    }


def _is_iso8601_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validate_lifecycle_payload(data: object) -> str | None:
    """Return a client-safe lifecycle payload validation error, if any."""
    if not isinstance(data, dict):
        return "请求体必须是JSON对象"

    event = data.get("event")
    status = data.get("status")
    if event not in {"started", "result"}:
        return "event必须是started或result"
    if status not in {"running", "success", "failed", "stopped"}:
        return "status必须是running、success、failed或stopped"
    if event == "started" and status != "running":
        return "started事件的status必须是running"
    if event == "result" and status not in {"success", "failed", "stopped"}:
        return "result事件的status必须是success、failed或stopped"

    steps = data.get("steps")
    if steps is not None:
        if not isinstance(steps, list) or any(
            not isinstance(step, dict) for step in steps
        ):
            return "steps必须是对象数组"
        seen_step_indexes: set[int] = set()
        for position, step in enumerate(steps):
            step_index = step.get("index", step.get("step_index", position))
            if isinstance(step_index, bool) or not isinstance(step_index, int):
                return "steps中的index必须是整数"
            if step_index in seen_step_indexes:
                return "steps中的index必须唯一"
            seen_step_indexes.add(step_index)
            for field in ("description", "action", "status"):
                if field in step and (
                    not isinstance(step[field], str) or not step[field].strip()
                ):
                    return f"steps中的{field}必须是非空字符串"
            if step.get("status") not in {"success", "failed", "skipped", "stopped"}:
                return "steps中的status必须是success、failed、skipped或stopped"
            duration = step.get("duration")
            if duration is not None and (
                isinstance(duration, bool)
                or not isinstance(duration, int)
                or duration < 0
            ):
                return "steps中的duration必须是非负整数"
            confidence = step.get("ai_confidence")
            if confidence is not None and (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
                or not 0 <= confidence <= 1
            ):
                return "steps中的ai_confidence必须在0到1之间"
            if "result_data" in step and not isinstance(step["result_data"], dict):
                return "steps中的result_data必须是对象"
            for field in ("screenshot_path", "error_message"):
                if field in step and not isinstance(step[field], (str, type(None))):
                    return f"steps中的{field}必须是字符串或null"
            for timestamp_field in ("start_time", "end_time"):
                if timestamp_field in step and not _is_iso8601_timestamp(
                    step[timestamp_field]
                ):
                    return f"steps中的{timestamp_field}必须是有效的ISO-8601时间"

    for timestamp_field in ("start_time", "end_time"):
        if timestamp_field in data and not _is_iso8601_timestamp(
            data[timestamp_field]
        ):
            return f"{timestamp_field}必须是有效的ISO-8601时间"
    for optional_text_field in (
        "error_message",
        "error_stack",
        "screenshots_path",
        "logs_path",
    ):
        if optional_text_field in data and not isinstance(
            data[optional_text_field], (str, type(None))
        ):
            return f"{optional_text_field}必须是字符串或null"
    if "result_summary" in data and not isinstance(data["result_summary"], dict):
        return "result_summary必须是对象"
    return None


def _get_durable_execution_details(execution_id: str) -> dict[str, Any] | None:
    execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
    if execution is None:
        return None
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


def _reconcile_execution_from_proxy(
    execution_id: str,
    durable_status: str,
    proxy_state: Mapping[str, Any],
) -> None:
    if proxy_state.get("executionId") != execution_id:
        raise ProxyExecutionClientError("proxy execution ID mismatch")

    proxy_status = proxy_state.get("status")
    if proxy_status not in {"running", "success", "failed", "stopped"}:
        raise ProxyExecutionClientError("proxy returned an invalid execution status")

    if durable_status == "pending":
        started_payload: dict[str, Any] = {"event": "started", "status": "running"}
        if "startTime" in proxy_state:
            started_payload["start_time"] = proxy_state["startTime"]
        validation_error = _validate_lifecycle_payload(started_payload)
        if validation_error:
            raise ProxyExecutionClientError("proxy returned invalid start state")
        started = DatabaseService.apply_execution_lifecycle(
            execution_id, "started", "running", started_payload
        )
        if started["outcome"] == "invalid_transition":
            current = _get_durable_execution_details(execution_id)
            if current is None or current["status"] not in {
                "running",
                "success",
                "failed",
                "stopped",
            }:
                raise ProxyExecutionClientError("durable start reconciliation failed")

    if proxy_status == "running":
        callback_errors = proxy_state.get("callbackErrors", [])
        callback_exhausted = isinstance(callback_errors, list) and any(
            isinstance(item, dict)
            and item.get("code")
            == DatabaseService.LIFECYCLE_CALLBACK_EXHAUSTED_CODE
            for item in callback_errors
        )
        if callback_exhausted:
            diagnostic = DatabaseService.record_lifecycle_callback_exhausted(
                execution_id
            )
            if diagnostic["outcome"] not in {"applied", "noop"}:
                current = _get_durable_execution_details(execution_id)
                if current is not None and current["status"] in {
                    "success",
                    "failed",
                    "stopped",
                }:
                    return
                raise ProxyExecutionClientError(
                    "durable reconciliation diagnostic failed"
                )
        return

    raw_steps = proxy_state.get("steps", [])
    if not isinstance(raw_steps, list) or any(
        not isinstance(step, dict) for step in raw_steps
    ):
        raise ProxyExecutionClientError("proxy returned invalid execution steps")

    safe_steps: list[dict[str, Any]] = []
    for position, step in enumerate(raw_steps):
        safe_step: dict[str, Any] = {
            "index": step.get("index", step.get("step_index", position)),
            "description": step.get("description", "状态协调恢复步骤"),
            "status": step.get("status"),
        }
        for field in ("start_time", "end_time", "duration"):
            if field in step:
                safe_step[field] = step[field]
        safe_steps.append(safe_step)

    result_payload: dict[str, Any] = {
        "event": "result",
        "status": proxy_status,
        "steps": safe_steps,
    }
    if "endTime" in proxy_state:
        result_payload["end_time"] = proxy_state["endTime"]
    if proxy_status == "failed":
        result_payload["error_message"] = "代理报告执行失败（已通过状态协调确认）"

    validation_error = _validate_lifecycle_payload(result_payload)
    if validation_error:
        raise ProxyExecutionClientError("proxy returned invalid terminal state")
    result = DatabaseService.apply_execution_lifecycle(
        execution_id, "result", proxy_status, result_payload
    )
    if result["outcome"] == "invalid_transition":
        current = _get_durable_execution_details(execution_id)
        if current is None or current["status"] != proxy_status:
            raise ProxyExecutionClientError("durable terminal reconciliation failed")


@executions_bp.route("/executions/<execution_id>/lifecycle", methods=["POST"])
@log_api_call
def record_execution_lifecycle(
    execution_id: str,
) -> dict[str, Any] | tuple[Response, int]:
    """Apply one idempotent lifecycle callback from the execution proxy."""
    if not request.is_json:
        return standard_error_response("请求必须包含JSON数据", 400)

    data = request.get_json(silent=True)
    validation_error = _validate_lifecycle_payload(data)
    if validation_error:
        return standard_error_response(validation_error, 400)

    try:
        update = DatabaseService.apply_execution_lifecycle(
            execution_id, data["event"], data["status"], data
        )
    except ValueError as error:
        return standard_error_response(str(error), 400)

    if update["outcome"] == "not_found":
        return standard_error_response("执行记录不存在", 404)
    if update["outcome"] == "invalid_transition":
        return standard_error_response("非法的执行生命周期状态迁移", 409)

    return format_success_response(
        message="执行生命周期已记录",
        data={
            "execution_id": execution_id,
            "status": update["execution"]["status"],
            "idempotent": update["outcome"] == "noop",
        },
    )


@executions_bp.route("/executions", methods=["POST"])
@log_api_call
def create_execution() -> Response | tuple[Response, int]:
    """创建执行任务"""
    execution_id = None
    try:
        data = request.get_json()

        if not data or not data.get("testcase_id"):
            return jsonify({"code": 400, "message": "testcase_id参数不能为空"}), 400

        # 验证测试用例存在
        testcase = TestCase.query.filter(
            TestCase.id == data["testcase_id"], TestCase.is_active == True
        ).first()

        if not testcase:
            return jsonify({"code": 404, "message": "测试用例不存在"}), 404

        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=data["testcase_id"],
            status="pending",
            mode=data.get("mode", "headless"),
            browser=data.get("browser", "chrome"),
            start_time=datetime.utcnow(),
            executed_by=data.get("executed_by", "system"),
        )

        db.session.add(execution)
        db.session.commit()

        dispatch_payload = _build_dispatch_payload(execution, testcase, data)
        try:
            dispatch_result = _get_proxy_execution_client().dispatch_execution(
                dispatch_payload
            )
            _require_proxy_acceptance(dispatch_result)
        except ProxyExecutionClientError as error:
            return _proxy_failure_response("调度执行", execution_id, error)

        return jsonify(
            {
                "code": 200,
                "message": "执行任务创建成功",
                "data": {
                    "execution_id": execution_id,
                    "status": "pending",
                    "testcase_name": testcase.name,
                    "start_time": execution.start_time.isoformat(),
                },
            }
        )

    except (SQLAlchemyError, RuntimeError, ValueError, TypeError):
        db.session.rollback()
        _log_unexpected_execution_failure(
            "创建执行任务", execution_id or "unassigned"
        )
        response = {"code": 500, "message": "创建执行任务失败"}
        if execution_id is not None:
            response["data"] = {"execution_id": execution_id}
        return jsonify(response), 500


@executions_bp.route("/executions/<execution_id>/retry", methods=["POST"])
@log_api_call
def retry_execution(execution_id: str) -> Response | tuple[Response, int]:
    """Redispatch one durable active execution with its canonical ID."""
    try:
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if execution is None:
            return standard_error_response("执行记录不存在", 404)
        if execution.status not in {"pending", "running"}:
            return standard_error_response("执行已进入终态，无法重试", 409)

        dispatch_result = _get_proxy_execution_client().dispatch_execution(
            _build_dispatch_payload(execution, execution.test_case)
        )
        _require_proxy_acceptance(dispatch_result)
    except ProxyExecutionClientError as error:
        return _proxy_failure_response("重试调度", execution_id, error)
    except (SQLAlchemyError, RuntimeError, ValueError, TypeError):
        _log_unexpected_execution_failure("重试调度", execution_id)
        return (
            jsonify(
                {
                    "code": 500,
                    "message": "重试调度失败",
                    "data": {"execution_id": execution_id},
                }
            ),
            500,
        )

    return format_success_response(
        message="执行任务已重新调度",
        data={"execution_id": execution_id, "status": execution.status},
    )


@executions_bp.route("/executions/<execution_id>/reconcile", methods=["POST"])
@log_api_call
def reconcile_execution(execution_id: str) -> Response | tuple[Response, int]:
    """Pull one proxy state into the durable execution lifecycle."""
    try:
        durable_execution = _get_durable_execution_details(execution_id)
        if durable_execution is None:
            return standard_error_response("执行记录不存在", 404)
        if durable_execution["status"] in {"success", "failed", "stopped"}:
            return format_success_response(
                message="获取成功", data=durable_execution
            )

        try:
            proxy_state = _get_proxy_execution_client().get_execution_status(
                execution_id
            )
            _reconcile_execution_from_proxy(
                execution_id, durable_execution["status"], proxy_state
            )
        except ProxyExecutionClientError as error:
            return _proxy_failure_response("状态协调", execution_id, error)

        reconciled = _get_durable_execution_details(execution_id)
        if reconciled is None:
            return standard_error_response("执行记录不存在", 404)
        return format_success_response(message="获取成功", data=reconciled)
    except (SQLAlchemyError, RuntimeError, ValueError, TypeError):
        db.session.rollback()
        _log_unexpected_execution_failure("状态协调", execution_id)
        return (
            jsonify(
                {
                    "code": 500,
                    "message": "状态协调失败",
                    "data": {"execution_id": execution_id},
                }
            ),
            500,
        )


@executions_bp.route("/executions/<execution_id>", methods=["GET"])
@log_api_call
def get_execution_status(execution_id):
    """获取执行状态"""
    try:
        execution_data = _get_durable_execution_details(execution_id)
        if execution_data is None:
            return standard_error_response("执行记录不存在", 404)
        return format_success_response(message="获取成功", data=execution_data)

    except Exception as e:
        return standard_error_response(f"获取执行状态失败: {str(e)}")


@executions_bp.route("/executions", methods=["GET"])
@log_api_call
def get_executions():
    """获取执行历史列表"""
    try:
        params = get_pagination_params()

        # 构建查询
        query = ExecutionHistory.query

        # 按测试用例过滤
        testcase_id = request.args.get("testcase_id", type=int)
        if testcase_id:
            query = query.filter(ExecutionHistory.test_case_id == testcase_id)

        # 排序
        query = query.order_by(ExecutionHistory.start_time.desc())

        # 分页
        page = params["page"]
        size = params["size"]

        # 获取总数
        total_count = query.count()

        # 获取分页数据
        executions = query.offset((page - 1) * size).limit(size).all()

        # 转换为字典
        executions_data = [execution.to_dict() for execution in executions]

        return jsonify(
            {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "items": executions_data,
                    "total": total_count,
                    "page": page,
                    "size": size,
                    "pages": (total_count + size - 1) // size,
                },
            }
        )

    except Exception as e:
        return standard_error_response(f"获取执行历史失败: {str(e)}")


@executions_bp.route("/executions/<execution_id>/stop", methods=["POST"])
@log_api_call
def stop_execution(execution_id: str) -> Response | tuple[Response, int]:
    """停止执行任务"""
    try:
        # 使用SQLAlchemy查询
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()

        if not execution:
            return standard_error_response("执行记录不存在", 404)

        if execution.status not in ["pending", "running"]:
            return standard_error_response("执行已完成，无法停止", 400)

        try:
            stop_result = _get_proxy_execution_client().stop_execution(execution_id)
            _require_proxy_acceptance(stop_result)
        except ProxyExecutionClientError as error:
            return _proxy_failure_response("停止执行", execution_id, error)

        if execution.status == "pending":
            started_update = DatabaseService.apply_execution_lifecycle(
                execution_id,
                "started",
                "running",
                {"event": "started", "status": "running"},
            )
            if started_update["outcome"] not in {"applied", "noop"}:
                return standard_error_response("停止执行时生命周期状态已变化", 409)

        stopped_update = DatabaseService.apply_execution_lifecycle(
            execution_id,
            "result",
            "stopped",
            {
                "event": "result",
                "status": "stopped",
                "error_message": "用户手动停止执行",
            },
        )
        if stopped_update["outcome"] not in {"applied", "noop"}:
            return standard_error_response("停止执行时生命周期状态已变化", 409)

        return format_success_response(
            message="执行已停止", data=stopped_update["execution"]
        )

    except (SQLAlchemyError, RuntimeError, ValueError, TypeError):
        db.session.rollback()
        _log_unexpected_execution_failure("停止执行", execution_id)
        return (
            jsonify(
                {
                    "code": 500,
                    "message": "停止执行失败",
                    "data": {"execution_id": execution_id},
                }
            ),
            500,
        )


@executions_bp.route("/executions/<execution_id>", methods=["DELETE"])
@log_api_call
def delete_execution(execution_id):
    """删除执行记录"""
    try:
        # 使用SQLAlchemy查询
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()

        if not execution:
            return standard_error_response("执行记录不存在", 404)

        # 删除相关的步骤执行记录
        StepExecution.query.filter_by(execution_id=execution_id).delete()

        # 删除执行记录
        db.session.delete(execution)
        db.session.commit()

        return format_success_response(message="执行记录删除成功")

    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"删除执行记录失败: {str(e)}")


@executions_bp.route("/executions/<execution_id>/export", methods=["GET"])
@log_api_call
def export_execution(execution_id):
    """导出单个执行报告"""
    try:
        # 使用SQLAlchemy查询执行记录
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()

        if not execution:
            return standard_error_response("执行记录不存在", 404)

        # 获取步骤执行详情
        step_executions = (
            StepExecution.query.filter_by(execution_id=execution_id)
            .order_by(StepExecution.step_index)
            .all()
        )

        # 构建导出数据，符合测试期望的格式
        execution_data = execution.to_dict()
        # 按照测试期望，直接返回导出数据（不用标准API响应格式）
        export_data = {
            "execution_id": execution.execution_id,
            "test_case_id": execution.test_case_id,
            "status": execution.status,
            "start_time": execution_data["start_time"],
            "end_time": execution_data["end_time"],
            "duration": execution.duration,
            "steps_total": execution.steps_total,
            "steps_passed": execution.steps_passed,
            "steps_failed": execution.steps_failed,
            "result_summary": execution_data["result_summary"],
            "step_executions": [step.to_dict() for step in step_executions],
            "exported_at": datetime.now().isoformat(),  # 使用测试期望的字段名
            "report_type": "single_execution",
        }

        return jsonify(export_data)

    except Exception as e:
        return standard_error_response(f"导出执行报告失败: {str(e)}")


@executions_bp.route("/executions/export-all", methods=["GET"])
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
        page = params["page"]
        size = params["size"]

        # 获取分页数据
        executions = query.offset((page - 1) * size).limit(size).all()

        # 按照测试期望，构建导出数据
        export_data = {
            "reports": [execution.to_dict() for execution in executions],
            "exported_at": datetime.now().isoformat(),
            "report_type": "batch_executions",
            "total_reports": len(executions),  # 当前页的报告数量
            "page": page,
            "size": size,
            "pagination": {"page": page, "size": size, "total": query.count()},
        }

        return jsonify(export_data)

    except Exception as e:
        return standard_error_response(f"导出执行报告失败: {str(e)}")


# ==================== 简化变量管理API ====================
# 核心变量功能已集成在执行引擎中，这里保留基础API接口


@executions_bp.route("/executions/<execution_id>/variable-references", methods=["GET"])
@log_api_call
def get_variable_references(execution_id):
    """获取变量引用历史"""
    try:
        # 验证执行记录存在
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if not execution:
            return standard_error_response("执行记录不存在", 404)

        # 简化实现：返回空列表，实际变量管理由执行引擎处理
        return standard_success_response(
            data={
                "execution_id": execution_id,
                "references": [],
                "total_count": 0,
                "message": "变量引用功能已集成在执行引擎中",
            }
        )

    except Exception as e:
        return standard_error_response(f"获取变量引用失败: {str(e)}")


# ==================== 辅助函数 ====================


def _trigger_test_execution(execution_id: str, testcase: TestCase, data: dict):
    """触发测试执行（待实现）"""
    # TODO: 实现实际的测试执行逻辑
    # 这里应该：
    # 1. 解析测试用例步骤
    # 2. 调用MidSceneJS执行引擎
    # 3. 更新执行状态
    # 4. 记录步骤执行结果


def _stop_test_execution(execution_id: str):
    """停止测试执行（待实现）"""
    # TODO: 实现停止执行逻辑
    # 这里应该：
    # 1. 向执行引擎发送停止信号
    # 2. 清理执行资源
    # 3. 更新执行状态
