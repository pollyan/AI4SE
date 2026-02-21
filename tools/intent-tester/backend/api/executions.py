"""
测试执行相关API模块
包含执行任务管理、变量管理和执行历史查询
"""

import uuid
from datetime import datetime
from flask import request, jsonify

from flask import Blueprint

executions_bp = Blueprint('executions', __name__)
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

# 导入通用代码模式

# 变量管理服务已简化 - 核心变量功能在其他服务中实现


# ==================== 执行任务管理 ====================


@executions_bp.route("/executions", methods=["POST"])
@log_api_call
def create_execution():
    """创建执行任务"""
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

        # TODO: 集成实际的执行引擎
        # 异步启动执行任务
        # _trigger_test_execution(execution_id, testcase, data)

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

    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": f"创建执行任务失败: {str(e)}"})


@executions_bp.route("/executions/<execution_id>", methods=["GET"])
@log_api_call
def get_execution_status(execution_id):
    """获取执行状态"""
    try:
        # 使用SQLAlchemy查询
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()

        if not execution:
            return standard_error_response("执行记录不存在", 404)

        # 获取步骤执行详情
        step_executions = (
            StepExecution.query.filter_by(execution_id=execution_id)
            .order_by(StepExecution.step_index)
            .all()
        )

        # 构建包含步骤信息的响应数据
        execution_data = execution.to_dict()
        execution_data["step_executions"] = [step.to_dict() for step in step_executions]

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
def stop_execution(execution_id):
    """停止执行任务"""
    try:
        # 使用SQLAlchemy查询
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()

        if not execution:
            return standard_error_response("执行记录不存在", 404)

        if execution.status not in ["pending", "running"]:
            return standard_error_response("执行已完成，无法停止", 400)

        # TODO: 实现实际的停止执行逻辑
        # 需要向执行引擎发送停止信号
        # _stop_test_execution(execution_id)

        # 更新执行状态
        execution.status = "stopped"
        execution.end_time = datetime.now()
        execution.error_message = "用户手动停止执行"

        db.session.commit()

        return format_success_response(message="执行已停止", data=execution.to_dict())

    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"停止执行失败: {str(e)}")


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
