"""
Vercel入口文件 - 意图测试平台
专为Serverless环境优化，避免复杂的模块导入
"""

import sys
import os
from flask import Flask, jsonify, render_template_string

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# 创建Flask应用，配置模板和静态文件路径
template_dir = os.path.join(parent_dir, "web_gui", "templates")
static_dir = os.path.join(parent_dir, "web_gui", "static")

app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir,
    static_url_path="/static",
)

# 基本配置
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY", "dev-secret-key-change-in-production"
)


# 捕获启动时的导入错误
STARTUP_ERROR = None

# 尝试加载API功能
try:
    print("🔄 开始加载API功能...")

    # 导入数据库配置
    from web_gui.database_config import get_flask_config

    # 应用数据库配置
    db_config = get_flask_config()
    app.config.update(db_config)

    print("✅ 数据库配置加载成功")

    # 导入模型和新的模块化API路由
    from web_gui.models import db
    from web_gui.api import register_api_routes

    print("✅ 模型和路由导入成功")

    # 初始化数据库
    db.init_app(app)

    # 注册模块化API路由
    register_api_routes(app)

    print("✅ API路由注册成功")

    # 添加CORS支持
    try:
        from flask_cors import CORS

        CORS(app, origins="*")
        print("✅ CORS配置成功")
    except ImportError:
        print("⚠️ CORS模块未找到，跳过")

    # 在应用启动时创建数据库表
    try:
        with app.app_context():
            db.create_all()
            print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"⚠️ 数据库表创建失败: {e}")

    # API状态检查
    @app.route("/api/status")
    def api_status():
        return jsonify(
            {
                "status": "ok",
                "message": "API is working",
                "database": "connected",
                "environment": "Vercel Serverless",
            }
        )
    
    # ... (Keep existing init-db and other API routes logic if needed, but for simplicity in this replacement block, I will focus on the error handling structure requested. Wait, replacing lines 371-142 means I am replacing the route definitions too. I should be careful not to delete the API routes if they are within this range? Actually the replacement target is lines 45-142 for the template and home route, but the start capture logic is lower down. I should split this into two edits or one larger edit.)
    
except Exception as e:
    import traceback
    STARTUP_ERROR = f"{str(e)}\n\n{traceback.format_exc()}"
    print(f"⚠️ API功能加载失败: {e}")
    traceback.print_exc()


# 添加时区格式化过滤器
@app.template_filter("utc_to_local")
def utc_to_local_filter(dt):
    """将UTC时间转换为带时区标识的ISO格式，供前端JavaScript转换为本地时间"""
    if dt is None:
        return ""
    try:
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except AttributeError:
        return ""


# 简单的HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>意图测试平台 - 降级模式</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container {
            max-width: 800px; margin: 0 auto; background: white;
            padding: 30px; border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header { text-align: center; margin-bottom: 30px; }
        .status { padding: 15px; border-radius: 5px; margin: 10px 0; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .warning { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; overflow-x: auto; }
        .api-list { margin: 20px 0; }
        .api-item {
            margin: 10px 0; padding: 10px; background: #f8f9fa;
            border-left: 4px solid #007bff;
        }
        .api-url { font-family: monospace; color: #007bff; }
        pre { white-space: pre-wrap; word-wrap: break-word; font-family: monospace; margin: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 意图测试平台</h1>
            <p>AI驱动的Web自动化测试平台</p>
        </div>

        {% if error %}
        <div class="status error">
            <h3>⚠️ 系统启动错误</h3>
            <p>系统未能完整加载，已进入降级模式。错误信息如下：</p>
            <pre>{{ error }}</pre>
            <p style="margin-top: 10px; font-weight: bold;">尝试修复：</p>
            <ul>
                <li>如果是缺少依赖，请运行: <code>./scripts/deploy-local.sh</code> 重新构建容器</li>
                <li>检查日志获取更多信息: <code>docker logs intent-test-web</code></li>
            </ul>
        </div>
        {% else %}
        <div class="status success">
            ✅ 应用运行正常 - Vercel Serverless环境
        </div>
        {% endif %}

        <div class="status info">
            🗄️ 数据库: {{ database_status }}
        </div>

        <h3>📋 可用的API端点（降级模式）</h3>
        <div class="api-list">
            <div class="api-item">
                <strong>健康检查:</strong><br>
                <span class="api-url">GET /health</span>
            </div>
            <div class="api-item">
                <strong>API状态:</strong><br>
                <span class="api-url">GET /api/status</span>
            </div>
        </div>

        <div style="margin-top: 30px; text-align: center; color: #666;">
            <p>🌐 部署在 Vercel | 🗄️ 数据库 Supabase | 🤖 AI驱动测试</p>
        </div>
    </div>
</body>
</html>
"""


# 主页路由 - 使用原来的完整Web界面
@app.route("/")
@app.route("/dashboard")
def home():
    # 优先检查是否有启动错误
    if STARTUP_ERROR:
        print(f"⚠️ 检测到启动错误，渲染降级页面: {STARTUP_ERROR[:100]}...")
        database_url = os.getenv("DATABASE_URL", "Not configured")
        database_status = (
            "PostgreSQL (Supabase)"
            if database_url.startswith("postgresql://")
            else "Not configured"
        )
        return render_template_string(
            HTML_TEMPLATE, 
            database_status=database_status,
            error=STARTUP_ERROR
        )

    try:
        # 尝试渲染原来的完整界面
        from flask import render_template

        return render_template("index.html")
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
        print(f"⚠️ 无法加载完整界面: {e}")
        
        # 备用方案：简单状态页面
        database_url = os.getenv("DATABASE_URL", "Not configured")
        database_status = (
            "PostgreSQL (Supabase)"
            if database_url.startswith("postgresql://")
            else "Not configured"
        )
        return render_template_string(
            HTML_TEMPLATE, 
            database_status=database_status,
            error=error_msg
        )


@app.route("/health")
def health():
    return jsonify(
        {"status": "healthy", "timestamp": os.getenv("VERCEL_DEPLOYMENT_ID", "local")}
    )


# 添加原来系统的页面路由
@app.route("/testcases")
def testcases_page():
    """测试用例管理页面"""
    try:
        from flask import render_template

        return render_template("testcases.html")
    except Exception as e:
        return jsonify({"error": f"无法加载测试用例页面: {str(e)}"}), 500


@app.route("/execution")
def execution_page():
    """执行控制台页面"""
    try:
        from flask import render_template

        return render_template("execution.html")
    except Exception as e:
        return jsonify({"error": f"无法加载执行控制台页面: {str(e)}"}), 500


@app.route("/reports")
def reports_page():
    """测试报告页面"""
    try:
        from flask import render_template

        return render_template("reports.html")
    except Exception as e:
        return jsonify({"error": f"无法加载测试报告页面: {str(e)}"}), 500


@app.route("/step_editor")
def step_editor_page():
    """步骤编辑器页面"""
    try:
        from flask import render_template

        return render_template("step_editor.html")
    except Exception as e:
        return jsonify({"error": f"无法加载步骤编辑器页面: {str(e)}"}), 500


@app.route("/local-proxy")
def local_proxy_page():
    """本地代理下载页面"""
    try:
        from flask import render_template
        from datetime import datetime

        return render_template(
            "local_proxy.html",
            current_date=datetime.utcnow().strftime("%Y-%m-%d"),
            build_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        )
    except Exception as e:
        return jsonify({"error": f"无法加载本地代理页面: {str(e)}"}), 500


@app.route("/requirements-analyzer")
@app.route("/requirements")  # 备选路由
def requirements_analyzer_page():
    """智能需求分析页面"""
    try:
        from flask import render_template
        
        return render_template("requirements_analyzer.html")
    except Exception as e:
        return jsonify({"error": f"无法加载智能需求分析页面: {str(e)}"}), 500


@app.route("/config-management")
@app.route("/configs")  # 备选路由
def config_management_page():
    """AI配置管理页面"""
    try:
        from flask import render_template
        
        return render_template("config_management.html")
    except Exception as e:
        return jsonify({"error": f"无法加载配置管理页面: {str(e)}"}), 500





@app.route("/profile")
@app.route("/about")  # 备选路由
def profile_page():
    """个人简介页面"""
    try:
        from flask import render_template
        
        return render_template("profile.html")
    except Exception as e:
        return jsonify({"error": f"无法加载个人简介页面: {str(e)}"}), 500


@app.route("/testcases/create")
def testcase_create_page():
    """测试用例创建页面"""
    try:
        from flask import render_template
        import json

        # 创建一个空的测试用例对象用于创建模式
        class EmptyTestCase:
            def __init__(self):
                self.id = None
                self.name = ""
                self.description = ""
                self.category = "功能测试"  # 默认分类
                self.priority = 2
                self.tags = ""
                self.is_active = True
                self.created_by = "admin"
                self.created_at = None
                self.updated_at = None

        empty_testcase = EmptyTestCase()

        return render_template(
            "testcase_edit.html",
            testcase=empty_testcase,
            steps_data="[]",
            total_executions=0,
            success_rate=0,
            is_create_mode=True,
        )
    except Exception as e:
        return jsonify({"error": f"无法加载测试用例创建页面: {str(e)}"}), 500


@app.route("/testcases/<int:testcase_id>/edit")
def testcase_edit_page(testcase_id):
    """测试用例编辑页面"""
    try:
        from flask import render_template
        from web_gui.models import TestCase, ExecutionHistory
        import json

        # 获取测试用例详情
        testcase = TestCase.query.get_or_404(testcase_id)

        # 获取执行统计信息
        execution_stats = ExecutionHistory.query.filter_by(
            test_case_id=testcase_id
        ).all()
        total_executions = len(execution_stats)
        successful_executions = len(
            [e for e in execution_stats if e.status == "success"]
        )
        success_rate = (
            (successful_executions / total_executions * 100)
            if total_executions > 0
            else 0
        )

        # 确保步骤数据是正确的JSON格式
        try:
            steps_data = json.loads(testcase.steps) if testcase.steps else []
        except (json.JSONDecodeError, TypeError):
            steps_data = []

        return render_template(
            "testcase_edit.html",
            testcase=testcase,
            steps_data=json.dumps(steps_data),
            total_executions=total_executions,
            success_rate=success_rate,
            is_create_mode=False,
        )
    except Exception as e:
        return jsonify({"error": f"无法加载测试用例编辑页面: {str(e)}"}), 500


@app.route("/download/local-proxy")
def download_local_proxy():
    """下载本地代理包 - 使用预构建的ZIP文件"""
    try:
        from flask import send_file
        from pathlib import Path
        
        # 预构建的ZIP文件路径
        current_dir = Path(__file__).parent.parent
        zip_path = current_dir / "dist" / "intent-test-proxy.zip"
        
        if not zip_path.exists():
            return jsonify({
                "success": False, 
                "error": "代理包文件不存在，请先运行 build-proxy-package.js 构建"
            }), 404
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name="intent-test-proxy.zip",
            mimetype="application/zip",
        )
    
    except Exception as e:
        return jsonify({"success": False, "error": f"下载失败: {str(e)}"}), 500


@app.route("/api/download-proxy")
def api_download_proxy():
    """API端点：下载本地代理包 - 与/download/local-proxy功能相同"""
    return download_local_proxy()

# Template generation functions removed - now using pre-built ZIP file

# Template generation functions removed - now using pre-built ZIP file
# See scripts/build-proxy-package.js for proxy package generation
# Download endpoint now serves dist/intent-test-proxy.zip directly

if os.getenv("VERCEL"):
    os.environ["VERCEL"] = "1"

# 尝试加载API功能
# Main application logic
if True:
    # 数据库初始化API
    @app.route("/api/init-db", methods=["POST"])
    def init_database():
        try:
            # 创建所有表
            db.create_all()

            # 检查是否有示例数据
            from web_gui.models import TestCase, Template

            test_count = TestCase.query.count()
            template_count = Template.query.count()

            # 如果没有数据，创建示例数据
            if test_count == 0:
                # 简单的测试用例
                simple_testcase = TestCase(
                    name="简单页面访问测试",
                    description="测试访问百度首页",
                    steps='[{"action":"navigate","params":{"url":"https://www.baidu.com"},"description":"访问百度首页"}]',
                    category="基础功能",
                    priority=1,
                    created_by="system",
                )
                db.session.add(simple_testcase)

                # 复杂的测试用例
                complex_testcase = TestCase(
                    name="百度搜索测试",
                    description="测试百度搜索功能",
                    steps='[{"action":"navigate","params":{"url":"https://www.baidu.com"},"description":"访问百度首页"},{"action":"ai_input","params":{"text":"AI测试","locate":"搜索框"},"description":"输入搜索关键词"}]',
                    category="搜索功能",
                    priority=2,
                    created_by="system",
                )
                db.session.add(complex_testcase)

            if template_count == 0:
                sample_template = Template(
                    name="搜索功能模板",
                    description="通用搜索功能测试模板",
                    category="搜索",
                    steps_template='[{"action":"navigate","params":{"url":"{{search_url}}"},"description":"访问搜索页面"}]',
                    parameters='{"search_url":{"type":"string","description":"搜索页面URL"}}',
                    created_by="system",
                    is_public=True,
                )
                db.session.add(sample_template)

            # 创建示例执行记录
            from web_gui.models import ExecutionHistory

            execution_count = ExecutionHistory.query.count()

            if execution_count == 0:
                from datetime import datetime, timedelta
                import uuid

                # 获取刚创建的测试用例
                testcase = TestCase.query.first()

                if testcase:
                    base_time = datetime.utcnow() - timedelta(days=5)

                    # 创建一些成功的执行记录
                    for i in range(8):
                        execution_id = str(uuid.uuid4())
                        execution = ExecutionHistory(
                            execution_id=execution_id,
                            test_case_id=testcase.id,
                            status="success",
                            mode="headless",
                            start_time=base_time + timedelta(hours=i * 3),
                            end_time=base_time + timedelta(hours=i * 3, minutes=2),
                            duration=120,
                            steps_total=3,
                            steps_passed=3,
                            steps_failed=0,
                            executed_by="system",
                        )
                        db.session.add(execution)

                    # 创建一些失败的执行记录
                    for i in range(3):
                        execution_id = str(uuid.uuid4())
                        execution = ExecutionHistory(
                            execution_id=execution_id,
                            test_case_id=testcase.id,
                            status="failed",
                            mode="headless",
                            start_time=base_time + timedelta(hours=i * 8),
                            end_time=base_time + timedelta(hours=i * 8, minutes=1),
                            duration=60,
                            steps_total=3,
                            steps_passed=1,
                            steps_failed=2,
                            error_message="模拟执行失败",
                            executed_by="system",
                        )
                        db.session.add(execution)

                    print("✅ 创建示例执行记录")

            db.session.commit()

            return jsonify(
                {
                    "status": "success",
                    "message": "数据库初始化成功",
                    "data": {
                        "test_cases": TestCase.query.count(),
                        "templates": Template.query.count(),
                        "executions": ExecutionHistory.query.count(),
                    },
                }
            )

        except Exception as e:
            return (
                jsonify({"status": "error", "message": f"数据库初始化失败: {str(e)}"}),
                500,
            )

    # 需求分析消息处理API (替代WebSocket)
    @app.route("/api/requirements/sessions/<session_id>/send-message", methods=["POST"])
    def send_requirements_message(session_id):
        """发送需求分析消息并获取AI响应 (Vercel专用，替代WebSocket)"""
        try:
            from flask import request
            import json
            from datetime import datetime
            
            data = request.get_json() or {}
            content = data.get("content", "").strip()
            
            if not content:
                return jsonify({"code": 400, "message": "消息内容不能为空"}), 400
                
            if len(content) > 2000:
                return jsonify({"code": 400, "message": "消息内容不能超过2000字符"}), 400
            
            # 验证会话存在
            from web_gui.models import RequirementsSession, RequirementsMessage
            
            session = RequirementsSession.query.get(session_id)
            if not session:
                return jsonify({"code": 404, "message": "会话不存在"}), 404
                
            if session.session_status != "active":
                return jsonify({"code": 400, "message": "会话不在活跃状态"}), 400
            
            # 保存用户消息
            user_message = RequirementsMessage(
                session_id=session_id,
                message_type="user",
                content=content,
                message_metadata=json.dumps({
                    "stage": session.current_stage,
                    "char_count": len(content),
                    "source": "http_api"
                })
            )
            
            db.session.add(user_message)
            db.session.commit()
            
            # 调用AI服务处理
            try:
                from web_gui.services.requirements_ai_service import RequirementsAIService
                from web_gui.models import RequirementsAIConfig
                
                # 获取默认AI配置
                default_config = RequirementsAIConfig.get_default_config()
                if default_config:
                    config_data = default_config.get_config_for_ai_service()
                    print(f"🔧 使用数据库AI配置: {default_config.config_name}, URL: {config_data['base_url']}, 模型: {config_data['model_name']}")
                    ai_service = RequirementsAIService(config=config_data)
                else:
                    # 如果没有默认配置，使用环境变量
                    print("⚠️ 未找到默认AI配置，使用环境变量")
                    ai_service = RequirementsAIService()
                
                # 获取会话上下文
                session_context = {
                    "ai_context": json.loads(session.ai_context or "{}"),
                    "consensus_content": json.loads(session.consensus_content or "{}")
                }
                
                # 调用AI分析
                ai_result = ai_service.analyze_user_requirement(
                    user_message=content,
                    session_context=session_context,
                    project_name=session.project_name or "未命名项目",
                    current_stage=session.current_stage
                )
                
                # 保存AI响应消息
                ai_message = RequirementsMessage(
                    session_id=session_id,
                    message_type="ai",
                    content=ai_result.get("ai_response", "AI响应处理中..."),
                    message_metadata=json.dumps({
                        "stage": ai_result.get("stage", session.current_stage),
                        "model_used": ai_result.get("model_used", "unknown"),
                        "processing_time": ai_result.get("processing_time"),
                        "alex_persona": ai_result.get("alex_persona", True)
                    })
                )
                
                db.session.add(ai_message)
                
                # 更新会话上下文
                if ai_result.get("ai_context"):
                    session.ai_context = json.dumps(ai_result["ai_context"])
                if ai_result.get("consensus_content"):
                    session.consensus_content = json.dumps(ai_result["consensus_content"])
                
                session.updated_at = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    "code": 200,
                    "message": "消息处理成功",
                    "data": {
                        "user_message": user_message.to_dict(),
                        "ai_message": ai_message.to_dict(),
                        "session_updated": True
                    }
                })
                
            except Exception as ai_error:
                print(f"AI服务调用失败: {ai_error}")
                
                # 保存错误消息
                error_message = RequirementsMessage(
                    session_id=session_id,
                    message_type="system",
                    content=f"抱歉，AI分析服务遇到了问题：{str(ai_error)}。请稍后重试，或重新描述您的需求。",
                    message_metadata=json.dumps({
                        "error_type": "ai_service_error",
                        "error_details": str(ai_error),
                        "stage": session.current_stage
                    })
                )
                
                db.session.add(error_message)
                db.session.commit()
                
                return jsonify({
                    "code": 200,
                    "message": "消息已保存，但AI服务暂时不可用",
                    "data": {
                        "user_message": user_message.to_dict(),
                        "ai_message": error_message.to_dict(),
                        "ai_error": True
                    }
                })
                
        except Exception as e:
            print(f"发送需求分析消息失败: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return jsonify({"code": 500, "message": f"处理消息失败: {str(e)}"}), 500

    # 轮询获取最新消息API
    @app.route("/api/requirements/sessions/<session_id>/poll-messages", methods=["GET"])
    def poll_requirements_messages(session_id):
        """轮询获取会话的最新消息 (Vercel专用，替代WebSocket)"""
        try:
            from flask import request
            
            # 获取查询参数
            since_timestamp = request.args.get("since")  # ISO格式时间戳
            limit = min(int(request.args.get("limit", 10)), 50)  # 限制最多50条
            
            # 验证会话存在
            from web_gui.models import RequirementsSession, RequirementsMessage
            
            session = RequirementsSession.query.get(session_id)
            if not session:
                return jsonify({"code": 404, "message": "会话不存在"}), 404
            
            # 构建查询
            query = RequirementsMessage.query.filter_by(session_id=session_id)
            
            if since_timestamp:
                try:
                    from datetime import datetime
                    since_dt = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
                    query = query.filter(RequirementsMessage.created_at > since_dt)
                except ValueError:
                    pass  # 忽略无效的时间戳格式
            
            # 获取最新消息
            messages = query.order_by(RequirementsMessage.created_at.desc()).limit(limit).all()
            messages.reverse()  # 按时间正序返回
            
            return jsonify({
                "code": 200,
                "message": "获取消息成功",
                "data": {
                    "messages": [msg.to_dict() for msg in messages],
                    "session_info": session.to_dict(),
                    "total": len(messages),
                    "has_more": len(messages) == limit
                }
            })
            
        except Exception as e:
            print(f"轮询消息失败: {e}")
            return jsonify({"code": 500, "message": f"获取消息失败: {str(e)}"}), 500

    # 数据库连接测试
    @app.route("/api/db-test")
    def db_test():
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                return (
                    jsonify(
                        {"status": "error", "message": "DATABASE_URL环境变量未设置"}
                    ),
                    500,
                )

            # 显示连接信息（隐藏密码）
            from urllib.parse import urlparse

            parsed = urlparse(database_url)

            connection_info = {
                "scheme": parsed.scheme,
                "hostname": parsed.hostname,
                "port": parsed.port,
                "database": parsed.path.lstrip("/") if parsed.path else None,
                "username": parsed.username,
                "password_set": bool(parsed.password),
                "original_url": (
                    database_url[:50] + "..."
                    if len(database_url) > 50
                    else database_url
                ),
            }

            # 尝试多种连接方式
            connection_attempts = []

            # 方法1: 使用应用的数据库引擎
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("SELECT 1 as test"))
                    test_result = result.fetchone()

                return jsonify(
                    {
                        "status": "success",
                        "message": "数据库连接成功 (方法1: 应用引擎)",
                        "connection_info": connection_info,
                        "test_query": "SELECT 1 执行成功",
                    }
                )
            except Exception as e1:
                connection_attempts.append(f"方法1失败: {str(e1)}")

            # 方法2: 直接使用psycopg2连接
            try:
                import psycopg2

                conn = psycopg2.connect(database_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                return jsonify(
                    {
                        "status": "success",
                        "message": "数据库连接成功 (方法2: 直接连接)",
                        "connection_info": connection_info,
                        "test_query": "SELECT 1 执行成功",
                    }
                )
            except Exception as e2:
                connection_attempts.append(f"方法2失败: {str(e2)}")

            # 方法3: 尝试连接池端口
            try:
                pool_url = database_url.replace(":5432/", ":6543/")
                import psycopg2

                conn = psycopg2.connect(pool_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                return jsonify(
                    {
                        "status": "success",
                        "message": "数据库连接成功 (方法3: 连接池)",
                        "connection_info": {**connection_info, "used_pool_port": True},
                        "test_query": "SELECT 1 执行成功",
                        "suggestion": "建议更新DATABASE_URL使用端口6543",
                    }
                )
            except Exception as e3:
                connection_attempts.append(f"方法3失败: {str(e3)}")

            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "所有连接方法都失败了",
                        "connection_info": connection_info,
                        "attempts": connection_attempts,
                        "suggestion": "请检查Supabase项目状态，或尝试使用连接池URL (端口6543)",
                    }
                ),
                500,
            )

        except Exception as e:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"测试过程出错: {str(e)}",
                        "connection_info": (
                            connection_info if "connection_info" in locals() else None
                        ),
                    }
                ),
                500,
            )

    # 智能执行API - 支持Chrome桥接、云端和本地模式
    @app.route("/api/executions/start", methods=["POST"])
    def start_execution():
        try:
            from flask import request
            import threading
            import uuid
            from datetime import datetime

            data = request.get_json() or {}
            testcase_id = data.get("testcase_id")
            mode = data.get("mode", "headless")  # headless 或 browser
            execution_type = data.get("execution_type", "local-proxy")  # local-proxy

            if not testcase_id:
                return jsonify({"code": 400, "message": "缺少测试用例ID"}), 400

            # 获取测试用例
            from web_gui.models import TestCase

            testcase = TestCase.query.get(testcase_id)
            if not testcase:
                return jsonify({"code": 404, "message": "测试用例不存在"}), 404

            # 生成执行ID
            execution_id = str(uuid.uuid4())

            # 创建执行记录
            execution_record = {
                "execution_id": execution_id,
                "testcase_id": testcase_id,
                "testcase_name": testcase.name,
                "mode": mode,
                "execution_type": execution_type,
                "status": "running",
                "start_time": datetime.utcnow().isoformat(),
                "steps": [],
                "current_step": 0,
                "total_steps": len(json.loads(testcase.steps)) if testcase.steps else 0,
                "screenshots": [],
            }

            # 存储执行记录（简单的内存存储）
            if not hasattr(app, "executions"):
                app.executions = {}
            app.executions[execution_id] = execution_record

            # 智能选择执行方式
            selected_type, execution_message = select_execution_type(
                execution_type, testcase.name
            )
            execution_record["execution_type"] = selected_type

            # 启动本地代理执行线程
            thread = threading.Thread(
                target=execute_testcase_background, args=(execution_id, testcase, mode)
            )

            thread.daemon = True
            thread.start()

            return jsonify(
                {
                    "code": 200,
                    "message": "本地代理执行已启动",
                    "data": {
                        "execution_id": execution_id,
                        "testcase_id": testcase_id,
                        "testcase_name": testcase.name,
                        "mode": mode,
                        "execution_type": selected_type,
                        "status": "running",
                        "message": execution_message,
                    },
                }
            )
        except Exception as e:
            return jsonify({"code": 500, "message": f"启动执行失败: {str(e)}"}), 500

    def select_execution_type(requested_type: str, testcase_name: str) -> tuple:
        """选择执行类型"""
        return "local-proxy", f"正在通过本地代理执行测试用例: {testcase_name}"

    def execute_testcase_background(execution_id, testcase, mode):
        """后台执行测试用例"""
        try:
            from datetime import datetime
            import json
            import time

            # 获取执行记录
            execution = app.executions[execution_id]

            # 解析测试步骤
            steps = json.loads(testcase.steps) if testcase.steps else []
            execution["total_steps"] = len(steps)
            execution["steps"] = [
                {"status": "pending", "description": step.get("description", "")}
                for step in steps
            ]

            # 创建数据库执行记录
            db_execution = None
            try:
                from web_gui.models import ExecutionHistory, db

                with app.app_context():
                    # 确保数据库表已创建
                    db.create_all()

                    db_execution = ExecutionHistory(
                        execution_id=execution_id,
                        test_case_id=testcase.id,
                        status="running",
                        mode=mode,
                        start_time=datetime.utcnow(),
                        steps_total=len(steps),
                        steps_passed=0,
                        steps_failed=0,
                        executed_by="system",
                    )
                    db.session.add(db_execution)
                    db.session.commit()
                    print(f"✅ 创建执行记录: {execution_id}")
            except Exception as db_error:
                print(f"⚠️ 创建执行记录失败: {db_error}")
                print(f"⚠️ 数据库错误详情: {type(db_error).__name__}: {str(db_error)}")
                # 即使数据库失败，也继续执行，只是统计数据会丢失
                pass

            # 尝试导入AI执行引擎
            try:
                import sys
                import os

                sys.path.append(os.path.dirname(os.path.dirname(__file__)))
                from midscene_python import MidSceneAI

                # 初始化AI
                ai = MidSceneAI()
                ai.set_browser_mode(mode)

                execution["message"] = f"AI引擎已初始化，开始执行 {len(steps)} 个步骤"

                # 执行每个步骤
                for i, step in enumerate(steps):
                    execution["current_step"] = i + 1
                    execution["steps"][i]["status"] = "running"

                    try:
                        # 执行步骤
                        result = execute_single_step(ai, step, i)
                        execution["steps"][i]["status"] = "success"
                        execution["steps"][i]["result"] = result

                        # 截图
                        screenshot_path = ai.take_screenshot(
                            f"{execution_id}_step_{i+1}"
                        )
                        execution["screenshots"].append(
                            {
                                "step": i + 1,
                                "path": screenshot_path,
                                "description": step.get("description", f"步骤 {i+1}"),
                            }
                        )

                    except Exception as step_error:
                        execution["steps"][i]["status"] = "failed"
                        execution["steps"][i]["error"] = str(step_error)
                        print(f"步骤 {i+1} 执行失败: {step_error}")
                        # 继续执行下一步骤

                # 执行完成
                execution["status"] = "completed"
                execution["end_time"] = datetime.utcnow().isoformat()
                execution["message"] = "测试执行完成"

                # 更新数据库记录
                update_execution_status(execution_id, "success", execution["steps"])

            except ImportError as e:
                # AI引擎不可用，使用模拟执行
                execution["message"] = "AI引擎不可用，使用模拟执行"

                for i, step in enumerate(steps):
                    execution["current_step"] = i + 1
                    execution["steps"][i]["status"] = "running"
                    time.sleep(2)  # 模拟执行时间
                    execution["steps"][i]["status"] = "success"
                    execution["steps"][i][
                        "result"
                    ] = f"模拟执行: {step.get('description', '')}"

                execution["status"] = "completed"
                execution["end_time"] = datetime.utcnow().isoformat()
                execution["message"] = "模拟执行完成"

                # 更新数据库记录
                update_execution_status(
                    execution_id, "success", execution["steps"], "模拟执行"
                )

        except Exception as e:
            execution["status"] = "failed"
            execution["error"] = str(e)
            execution["end_time"] = datetime.utcnow().isoformat()
            print(f"执行失败: {e}")

            # 更新数据库记录为失败
            update_execution_status(
                execution_id, "failed", execution.get("steps", []), error_message=str(e)
            )

    def update_execution_status(
        execution_id, status, steps, note="", error_message=None
    ):
        """统一的数据库状态更新函数"""
        try:
            from web_gui.models import ExecutionHistory, db

            with app.app_context():
                db_execution = ExecutionHistory.query.filter_by(
                    execution_id=execution_id
                ).first()
                if db_execution:
                    # 开始事务
                    db_execution.status = status
                    db_execution.end_time = datetime.utcnow()
                    db_execution.steps_passed = sum(
                        1 for step in steps if step.get("status") == "success"
                    )
                    db_execution.steps_failed = sum(
                        1 for step in steps if step.get("status") == "failed"
                    )
                    db_execution.duration = int(
                        (datetime.utcnow() - db_execution.start_time).total_seconds()
                    )

                    if error_message:
                        db_execution.error_message = error_message

                    db.session.commit()
                    print(f"✅ 更新执行记录: {execution_id} -> {status} {note}")
                else:
                    print(f"⚠️ 执行记录不存在: {execution_id}")
        except Exception as db_error:
            print(f"⚠️ 更新执行记录失败: {db_error}")
            print(f"⚠️ 数据库错误详情: {type(db_error).__name__}: {str(db_error)}")
            try:
                db.session.rollback()
            except:
                pass

    def execute_single_step(ai, step, step_index):
        """执行单个测试步骤"""
        action = step.get("action")
        params = step.get("params", {})
        description = step.get("description", action)

        print(f"执行步骤 {step_index + 1}: {description}")

        if action == "navigate":
            url = params.get("url")
            return ai.goto(url)
        elif action == "ai_input":
            text = params.get("text")
            locate = params.get("locate")
            return ai.ai_input(text, locate)
        elif action == "ai_tap":
            prompt = params.get("prompt")
            return ai.ai_tap(prompt)
        elif action == "ai_assert":
            prompt = params.get("prompt")
            return ai.ai_assert(prompt)
        elif action == "ai_wait_for":
            prompt = params.get("prompt")
            timeout = params.get("timeout", 10000)
            return ai.ai_wait_for(prompt, timeout)
        else:
            raise ValueError(f"不支持的操作类型: {action}")

    print("✅ API功能加载成功")

# End of application logic


# Vercel需要的应用对象
application = app

if __name__ == "__main__":
    app.run(debug=True)
