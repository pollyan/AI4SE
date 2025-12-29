"""
API基础功能模块
提供通用的错误处理、验证和响应格式化功能
"""

from flask import jsonify, request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# 导入统一错误处理工具
try:
    from ..utils.error_handler import (
        api_error_handler,
        db_transaction_handler,
        validate_json_data,
        format_success_response,
        ValidationError,
        NotFoundError,
        DatabaseError,
    )
except ImportError:
    from web_gui.utils.error_handler import (
        api_error_handler,
        db_transaction_handler,
        validate_json_data,
        format_success_response,
        ValidationError,
        NotFoundError,
        DatabaseError,
    )

# 导入数据模型
try:
    from ..models import db, TestCase, ExecutionHistory, StepExecution, Template
except ImportError:
    from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template


def get_pagination_params():
    """获取分页参数"""
    return {
        "page": request.args.get("page", 1, type=int),
        "size": request.args.get("size", 20, type=int),
        "search": request.args.get("search", ""),
        "category": request.args.get("category", ""),
    }


def format_paginated_response(pagination, items_key="items"):
    """格式化分页响应"""
    return {
        "code": 200,
        "data": {
            items_key: [
                item.to_dict() if hasattr(item, "to_dict") else item
                for item in pagination.items
            ],
            "total": pagination.total,
            "page": pagination.page,
            "size": pagination.per_page,
            "pages": pagination.pages,
        },
        "message": "获取成功",
    }


def standard_error_response(message, code=500):
    """标准错误响应格式"""
    return jsonify({"code": code, "message": message}), code


def standard_success_response(data=None, message="操作成功", code=200):
    """标准成功响应格式"""
    response = {"code": code, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response)


def require_json(f):
    """要求请求包含JSON数据的装饰器"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return standard_error_response("请求必须包含JSON数据", 400)
        return f(*args, **kwargs)

    return wrapper


def log_api_call(f):
    """API调用日志装饰器"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        logger.info(f"API调用: {request.method} {request.path}")
        if request.is_json:
            logger.debug(f"请求数据: {request.get_json()}")
        try:
            result = f(*args, **kwargs)
            logger.info(f"API调用成功: {request.method} {request.path}")
            return result
        except (ValidationError, NotFoundError, DatabaseError) as e:
            logger.error(
                f"API调用失败: {request.method} {request.path}, 错误: {str(e)}"
            )
            # 处理API异常，转换为HTTP响应
            return jsonify({"code": e.code, "message": e.message}), e.code
        except Exception as e:
            logger.error(
                f"API调用失败: {request.method} {request.path}, 错误: {str(e)}"
            )
            # 其他异常继续抛出让Flask处理
            raise

    return wrapper


def register_blueprints(app):
    """注册所有API蓝图"""
    try:
        # 使用统一的API路由注册函数
        from . import register_api_routes
        register_api_routes(app)
        
        logger.info("✅ 所有API蓝图注册成功")
        
    except Exception as e:
        logger.error(f"❌ 蓝图注册失败: {e}")
        
    # 注册基本路由
    @app.route("/")
    def index():
        """主页路由"""
        try:
            from flask import render_template
            return render_template("index.html")
        except:
            return {"message": "AI4SE工具集", "status": "running"}
            
    @app.route("/testcases")
    def testcases():
        """测试用例页面"""
        try:
            from flask import render_template
            return render_template("testcases.html")
        except:
            return {"error": "无法加载页面"}
    
    @app.route("/execution")
    def execution():
        """执行控制台页面"""
        try:
            from flask import render_template
            return render_template("execution.html")
        except:
            return {"error": "无法加载页面"}
    
    @app.route("/requirements-analyzer")
    @app.route("/requirements")
    def requirements_analyzer_page():
        """智能需求分析助手页面"""
        try:
            from flask import render_template
            return render_template("requirements_analyzer.html")
        except Exception as e:
            logger.error(f"渲染需求分析页面失败: {str(e)}")
            return render_template("error.html", error_message=str(e)), 500
    
    @app.route("/testgen")
    def testgen_page():
        """测试用例生成器页面"""
        try:
            from flask import render_template
            return render_template("testgen.html")
        except Exception as e:
            logger.error(f"渲染测试生成页面失败: {str(e)}")
            return render_template("error.html", error_message=str(e)), 500

    @app.route("/config-management")
    @app.route("/configs")
    def config_management_page():
        """配置管理页面"""
        try:
            from flask import render_template
            return render_template("config_management.html")
        except:
            return {"error": "无法加载页面"}
    
    @app.route("/local-proxy")
    def local_proxy():
        """本地代理页面"""
        try:
            from flask import render_template
            from datetime import datetime
            return render_template(
                "local_proxy.html",
                current_date=datetime.utcnow().strftime("%Y-%m-%d"),
                build_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            )
        except:
            return {"error": "无法加载页面"}
    
    @app.route("/reports")
    def reports():
        """报告页面"""
        try:
            from flask import render_template
            return render_template("reports.html")
        except:
            return {"error": "无法加载页面"}
    
    @app.route("/profile")
    @app.route("/about")
    def profile_page():
        """个人简介页面"""
        try:
            from flask import render_template
            return render_template("profile.html")
        except:
            return {"error": "无法加载页面"}
            
    @app.route("/health")
    def health_check():
        """健康检查路由"""
        return {"status": "ok", "message": "Flask app is running"}

    # ==========================================
    # 补充确实的页面路由 (Create, Edit, View)
    # ==========================================
    @app.route("/testcases/create")
    def create_testcase_page():
        """创建测试用例页面"""
        try:
            from flask import render_template
            # 创建模式传递空的testcase对象
            empty_testcase = {
                'id': None,
                'name': '',
                'category': '功能测试',
                'priority': 2,
                'is_active': True,
                'tags': '',
                'created_by': 'admin',
                'description': '',
                'created_at': None,
                'updated_at': None,
            }
            return render_template("testcase_edit.html", is_create_mode=True, testcase=empty_testcase)
        except Exception as e:
            logger.error(f"渲染创建测试用例页面失败: {str(e)}")
            return {"error": "无法加载页面", "detail": str(e)}

    @app.route("/testcases/<int:testcase_id>/edit")
    def edit_testcase_page(testcase_id):
        """编辑测试用例页面"""
        try:
            from flask import render_template
            return render_template("testcase_edit.html", is_create_mode=False, testcase_id=testcase_id)
        except Exception as e:
            logger.error(f"渲染编辑测试用例页面失败: {str(e)}")
            return {"error": "无法加载页面", "detail": str(e)}
             
    @app.route("/testcases/<int:testcase_id>")
    def view_testcase_page(testcase_id):
         """查看测试用例页面"""
         try:
            from flask import render_template
            # 复用编辑页面，前端会根据ID加载数据
            return render_template("testcase_edit.html", is_create_mode=False, testcase_id=testcase_id) 
         except Exception as e:
            logger.error(f"渲染查看测试用例页面失败: {str(e)}")
            return {"error": "无法加载页面", "detail": str(e)}
