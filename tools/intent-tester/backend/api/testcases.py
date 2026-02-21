"""
测试用例管理API模块
包含测试用例的CRUD操作和步骤管理
"""

import json
from datetime import datetime
from flask import request, jsonify, Response

from flask import Blueprint

# 提供 testcases_bp 以便 base.register_blueprints 注册
testcases_bp = Blueprint('testcases', __name__)

# api_bp removed

from .base import (
    format_success_response,
    get_pagination_params,
    standard_error_response,
    require_json,
    log_api_call,
    db,
    TestCase,
)

# 导入通用代码模式
from backend.utils.common_patterns import (
    safe_api_operation,
    validate_resource_exists,
    database_transaction,
    require_json_data,
)

# 导入查询优化器

# 定义有效的动作类型
VALID_ACTIONS = {
    "goto",
    "ai_input",
    "ai_tap",
    "ai_assert",
    "ai_wait_for",
    "ai_scroll",
    "ai_drag",
    "sleep",
    "screenshot",
    "refresh",
    "back",
    "ai_select",
    "ai_upload",
    "ai_check",
}


def validate_step_data(data, is_update=False):
    """验证步骤数据"""
    from backend.utils.error_handler import ValidationError

    action = data.get("action")

    # 在更新模式下，action字段是可选的
    if not is_update and not action:
        raise ValidationError("action字段是必需的")

    if action and action not in VALID_ACTIONS:
        raise ValidationError(
            f'无效的动作类型: {action}，支持的动作: {", ".join(sorted(VALID_ACTIONS))}'
        )

    params = data.get("params", {})

    # 在创建时进行严格验证，更新时允许部分更新
    if not is_update:
        # 根据动作类型验证参数
        if action == "goto":
            if not params.get("url"):
                raise ValidationError("goto动作需要url参数")

        elif action in ["ai_input", "ai_tap", "ai_assert", "ai_wait_for"]:
            # AI动作需要locate或prompt参数之一
            if not params.get("locate") and not params.get("prompt"):
                raise ValidationError(f"{action}动作需要locate或prompt参数之一")

    return True


# ==================== 测试用例CRUD操作 ====================


@testcases_bp.route("/testcases", methods=["GET"])
@log_api_call
def get_testcases() -> Response:
    """获取测试用例列表（使用SQLAlchemy）"""
    try:
        params = get_pagination_params()

        page = params["page"]
        size = params["size"]
        category = params.get("category")
        search = params.get("search")

        # 构建查询
        query = TestCase.query.filter_by(is_active=True)

        # 分类过滤
        if category:
            query = query.filter(TestCase.category == category)

        # 搜索过滤
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (TestCase.name.ilike(search_pattern))
                | (TestCase.description.ilike(search_pattern))
                | (TestCase.tags.ilike(search_pattern))
            )

        # 排序和分页
        query = query.order_by(TestCase.updated_at.desc())

        # 获取总数
        total_count = query.count()

        # 分页
        testcases = query.offset((page - 1) * size).limit(size).all()

        # 转换为字典
        testcases_data = [
            testcase.to_dict(include_stats=False) for testcase in testcases
        ]

        return jsonify(
            {
                "code": 200,
                "message": "获取成功",
                "data": {
                    "items": testcases_data,
                    "total": total_count,
                    "page": page,
                    "size": size,
                    "pages": (total_count + size - 1) // size,
                    "pagination": {
                        "page": page,
                        "per_page": size,
                        "total": total_count,
                        "pages": (total_count + size - 1) // size,
                    },
                },
            }
        )

    except Exception as e:
        return standard_error_response(f"获取失败: {str(e)}")


@testcases_bp.route("/testcases", methods=["POST"])
@log_api_call
@require_json
def create_testcase():
    """创建测试用例"""
    try:
        data = request.get_json()

        # 基本验证
        if not data or not data.get("name"):
            return standard_error_response("测试用例名称不能为空", 400)

        # 验证步骤数据格式
        steps = data.get("steps", [])
        if not isinstance(steps, list):
            return standard_error_response("测试步骤必须是数组格式", 500)

        # 如果有步骤，验证每个步骤的格式
        if len(steps) > 0:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    return standard_error_response(
                        f"步骤 {i+1} 格式不正确，必须是对象", 500
                    )

                if not step.get("action"):
                    return standard_error_response(f"步骤 {i+1} 缺少action字段", 500)

        # 处理tags - 转换数组为逗号分隔字符串存储
        tags = data.get("tags", "")
        if isinstance(tags, list):
            tags = ",".join(tags)

        # 使用SQLAlchemy创建测试用例
        testcase = TestCase(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=json.dumps(data.get("steps", [])),
            tags=tags,
            category=data.get("category", ""),
            priority=data.get("priority", 2),
            created_by=data.get("created_by", "user"),
        )

        db.session.add(testcase)
        db.session.commit()

        return jsonify(
            {
                "code": 200,
                "message": "测试用例创建成功",
                "data": testcase.to_dict(include_stats=False),
            }
        )

    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"创建失败: {str(e)}")


@testcases_bp.route("/testcases/<int:testcase_id>", methods=["GET"])
@log_api_call
def get_testcase(testcase_id):
    """获取测试用例详情"""
    try:
        # 使用SQLAlchemy查询（允许访问inactive测试用例）
        testcase = TestCase.query.filter_by(id=testcase_id).first()

        if not testcase:
            return standard_error_response("测试用例不存在", 404)

        return format_success_response(
            message="获取成功", data=testcase.to_dict(include_stats=False)
        )

    except Exception as e:
        return standard_error_response(f"获取失败: {str(e)}")


@testcases_bp.route("/testcases/<int:testcase_id>", methods=["PUT"])
@log_api_call
@require_json
def update_testcase(testcase_id):
    """更新测试用例"""
    try:
        data = request.get_json()

        if not data:
            return standard_error_response("请求数据不能为空", 400)

        # 使用SQLAlchemy查询（允许更新inactive测试用例）
        testcase = TestCase.query.filter_by(id=testcase_id).first()

        if not testcase:
            return standard_error_response("测试用例不存在", 404)

        # 更新字段
        if "name" in data:
            testcase.name = data["name"]
        if "description" in data:
            testcase.description = data["description"]
        if "steps" in data:
            testcase.steps = json.dumps(data["steps"])
        if "tags" in data:
            tags = data["tags"]
            testcase.tags = ",".join(tags) if isinstance(tags, list) else tags
        if "category" in data:
            testcase.category = data["category"]
        if "priority" in data:
            testcase.priority = data["priority"]
        if "is_active" in data:
            testcase.is_active = data["is_active"]

        testcase.updated_at = datetime.now()

        db.session.commit()

        return jsonify(
            {
                "code": 200,
                "message": "测试用例更新成功",
                "data": testcase.to_dict(include_stats=False),
            }
        )

    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"更新失败: {str(e)}")


@testcases_bp.route("/testcases/<int:testcase_id>", methods=["DELETE"])
@log_api_call
def delete_testcase(testcase_id):
    """删除测试用例（软删除）"""
    try:
        # 使用SQLAlchemy查询
        testcase = TestCase.query.filter_by(id=testcase_id, is_active=True).first()

        if not testcase:
            return standard_error_response("测试用例不存在", 404)

        # 软删除
        testcase.is_active = False
        testcase.updated_at = datetime.now()

        db.session.commit()

        return format_success_response(message="测试用例删除成功")

    except Exception as e:
        db.session.rollback()
        return standard_error_response(f"删除失败: {str(e)}")


# ==================== 测试用例步骤管理 ====================


@testcases_bp.route("/testcases/<int:testcase_id>/steps", methods=["GET"])
@log_api_call
@safe_api_operation("获取测试用例步骤")
@validate_resource_exists(TestCase, "testcase_id", "测试用例不存在")
def get_testcase_steps(testcase_id, testcase):
    """获取测试用例步骤"""
    steps = json.loads(testcase.steps) if testcase.steps else []

    return {
        "testcase_id": testcase_id,
        "steps": steps,
        "total_steps": len(steps),
        "total": len(steps),
    }


@testcases_bp.route("/testcases/<int:testcase_id>/steps", methods=["POST"])
@log_api_call
@safe_api_operation("添加测试用例步骤")
@validate_resource_exists(TestCase, "testcase_id", "测试用例不存在")
@require_json_data(required_fields=["action"])
@database_transaction()
def add_testcase_step(testcase_id, testcase, data):
    """添加测试用例步骤"""
    # 验证步骤数据
    validate_step_data(data)

    # 获取现有步骤
    steps = json.loads(testcase.steps) if testcase.steps else []

    # 添加新步骤
    new_step = {
        "action": data["action"],
        "params": data.get("params", {}),
        "description": data.get("description", ""),
        "wait_time": data.get("wait_time", 0),
        "retry_count": data.get("retry_count", 0),
        "output_variable": data.get("output_variable", ""),
    }

    # 支持指定位置插入
    position = data.get("position", len(steps))
    if position < 0 or position > len(steps):
        position = len(steps)

    steps.insert(position, new_step)

    # 更新数据库
    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()

    return {
        "step_index": position,
        "position": position,  # 兼容测试期望
        "step": new_step,
        "total_steps": len(steps),
    }


@testcases_bp.route("/testcases/<int:testcase_id>/steps/<int:step_index>", methods=["PUT"])
@log_api_call
@safe_api_operation("更新测试用例步骤")
@validate_resource_exists(TestCase, "testcase_id", "测试用例不存在")
@require_json_data(required_fields=[])
@database_transaction()
def update_testcase_step(testcase_id, step_index, testcase, data):
    """更新测试用例步骤"""
    # 验证步骤数据（更新模式）
    validate_step_data(data, is_update=True)

    steps = json.loads(testcase.steps) if testcase.steps else []

    if step_index < 0 or step_index >= len(steps):
        from backend.utils.error_handler import ValidationError

        raise ValidationError("步骤索引超出范围")

    # 部分更新步骤 - 只更新提供的字段
    current_step = steps[step_index]
    if "action" in data:
        current_step["action"] = data["action"]
    if "params" in data:
        current_step["params"] = data["params"]
    if "description" in data:
        current_step["description"] = data["description"]
    if "wait_time" in data:
        current_step["wait_time"] = data["wait_time"]
    if "retry_count" in data:
        current_step["retry_count"] = data["retry_count"]
    if "output_variable" in data:
        current_step["output_variable"] = data["output_variable"]
    if "required" in data:
        current_step["required"] = data["required"]

    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()

    return {
        "step_index": step_index,
        "index": step_index,  # 兼容测试期望
        "step": steps[step_index],
    }


@testcases_bp.route("/testcases/<int:testcase_id>/steps/<int:step_index>", methods=["DELETE"])
@log_api_call
@safe_api_operation("删除测试用例步骤")
@validate_resource_exists(TestCase, "testcase_id", "测试用例不存在")
@database_transaction()
def delete_testcase_step(testcase_id, step_index, testcase):
    """删除测试用例步骤"""
    steps = json.loads(testcase.steps) if testcase.steps else []

    if step_index < 0 or step_index >= len(steps):
        from backend.utils.error_handler import ValidationError

        raise ValidationError("步骤索引超出范围")

    # 删除步骤
    deleted_step = steps.pop(step_index)

    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()

    return {"deleted_step": deleted_step, "remaining_steps": len(steps)}


@testcases_bp.route("/testcases/<int:testcase_id>/steps/reorder", methods=["PUT"])
@log_api_call
@safe_api_operation("重新排序测试用例步骤")
@validate_resource_exists(TestCase, "testcase_id", "测试用例不存在")
@require_json_data(required_fields=["step_orders"])
@database_transaction()
def reorder_testcase_steps(testcase_id, testcase, data):
    """重新排序测试用例步骤"""
    step_orders = data["step_orders"]

    steps = json.loads(testcase.steps) if testcase.steps else []

    if len(step_orders) != len(steps):
        from backend.utils.error_handler import ValidationError

        raise ValidationError("步骤索引数量不匹配")

    # 验证索引有效性
    if not all(isinstance(idx, int) and 0 <= idx < len(steps) for idx in step_orders):
        from backend.utils.error_handler import ValidationError

        raise ValidationError("无效的步骤索引")

    # 重新排序
    reordered_steps = [steps[i] for i in step_orders]

    testcase.steps = json.dumps(reordered_steps)
    testcase.updated_at = datetime.utcnow()

    return {"steps": reordered_steps}


@testcases_bp.route(
    "/testcases/<int:testcase_id>/steps/<int:step_index>/duplicate", methods=["POST"]
)
@log_api_call
@safe_api_operation("复制测试用例步骤")
@validate_resource_exists(TestCase, "testcase_id", "测试用例不存在")
@database_transaction()
def duplicate_testcase_step(testcase_id, step_index, testcase):
    """复制测试用例步骤"""
    steps = json.loads(testcase.steps) if testcase.steps else []

    if step_index < 0 or step_index >= len(steps):
        from backend.utils.error_handler import ValidationError

        raise ValidationError("步骤索引超出范围")

    # 复制步骤
    original_step = steps[step_index].copy()

    # 修改描述以标识为复制
    if original_step.get("description"):
        original_step["description"] += " (副本)"
    else:
        original_step["description"] = "复制的步骤"

    # 插入到原步骤后面
    steps.insert(step_index + 1, original_step)

    testcase.steps = json.dumps(steps)
    testcase.updated_at = datetime.utcnow()

    return {
        "original_index": step_index,
        "duplicate_index": step_index + 1,
        "duplicate_step": original_step,
        "total_steps": len(steps),
    }
