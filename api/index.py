"""
Vercel入口文件 - Intent Test Framework
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
template_dir = os.path.join(parent_dir, 'web_gui', 'templates')
static_dir = os.path.join(parent_dir, 'web_gui', 'static')

app = Flask(__name__,
           template_folder=template_dir,
           static_folder=static_dir,
           static_url_path='/static')

# 基本配置
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# 简单的HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Intent Test Framework</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .status { padding: 15px; border-radius: 5px; margin: 10px 0; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .api-list { margin: 20px 0; }
        .api-item { margin: 10px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #007bff; }
        .api-url { font-family: monospace; color: #007bff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Intent Test Framework</h1>
            <p>AI驱动的Web自动化测试平台</p>
        </div>

        <div class="status success">
            ✅ 应用运行正常 - Vercel Serverless环境
        </div>

        <div class="status info">
            🗄️ 数据库: {{ database_status }}
        </div>

        <h3>📋 可用的API端点</h3>
        <div class="api-list">
            <div class="api-item">
                <strong>健康检查:</strong><br>
                <span class="api-url">GET /health</span>
            </div>
            <div class="api-item">
                <strong>API状态:</strong><br>
                <span class="api-url">GET /api/status</span>
            </div>
            <div class="api-item">
                <strong>测试用例:</strong><br>
                <span class="api-url">GET /api/testcases</span>
            </div>
            <div class="api-item">
                <strong>执行历史:</strong><br>
                <span class="api-url">GET /api/executions</span>
            </div>
            <div class="api-item">
                <strong>模板管理:</strong><br>
                <span class="api-url">GET /api/templates</span>
            </div>
            <div class="api-item">
                <strong>统计数据:</strong><br>
                <span class="api-url">GET /api/stats/dashboard</span>
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
@app.route('/')
def home():
    try:
        # 尝试渲染原来的完整界面
        from flask import render_template
        return render_template('index_enhanced.html')
    except Exception as e:
        print(f"⚠️ 无法加载完整界面: {e}")
        # 备用方案：简单状态页面
        database_url = os.getenv('DATABASE_URL', 'Not configured')
        database_status = 'PostgreSQL (Supabase)' if database_url.startswith('postgresql://') else 'Not configured'
        return render_template_string(HTML_TEMPLATE, database_status=database_status)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': os.getenv('VERCEL_DEPLOYMENT_ID', 'local')})

# 添加原来系统的页面路由
@app.route('/testcases')
def testcases_page():
    """测试用例管理页面"""
    try:
        from flask import render_template
        return render_template('testcases.html')
    except Exception as e:
        return jsonify({'error': f'无法加载测试用例页面: {str(e)}'}), 500

@app.route('/execution')
def execution_page():
    """执行控制台页面"""
    try:
        from flask import render_template
        return render_template('execution.html')
    except Exception as e:
        return jsonify({'error': f'无法加载执行控制台页面: {str(e)}'}), 500

@app.route('/reports')
def reports_page():
    """测试报告页面"""
    try:
        from flask import render_template
        return render_template('reports.html')
    except Exception as e:
        return jsonify({'error': f'无法加载测试报告页面: {str(e)}'}), 500

@app.route('/step_editor')
def step_editor_page():
    """步骤编辑器页面"""
    try:
        from flask import render_template
        return render_template('step_editor.html')
    except Exception as e:
        return jsonify({'error': f'无法加载步骤编辑器页面: {str(e)}'}), 500

# 设置环境变量
os.environ['VERCEL'] = '1'

# 尝试加载API功能
try:
    print("🔄 开始加载API功能...")

    # 导入数据库配置
    from web_gui.database_config import get_flask_config

    # 应用数据库配置
    db_config = get_flask_config()
    app.config.update(db_config)

    print("✅ 数据库配置加载成功")

    # 导入模型和路由
    from web_gui.models import db
    from web_gui.api_routes import api_bp

    print("✅ 模型和路由导入成功")

    # 初始化数据库
    db.init_app(app)

    # 注册API路由
    app.register_blueprint(api_bp)

    print("✅ API路由注册成功")

    # 添加CORS支持
    try:
        from flask_cors import CORS
        CORS(app, origins="*")
        print("✅ CORS配置成功")
    except ImportError:
        print("⚠️ CORS模块未找到，跳过")

    # API状态检查
    @app.route('/api/status')
    def api_status():
        return jsonify({
            'status': 'ok',
            'message': 'API is working',
            'database': 'connected',
            'environment': 'Vercel Serverless'
        })

    # 数据库初始化API
    @app.route('/api/init-db', methods=['POST'])
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
                sample_testcase = TestCase(
                    name='百度搜索测试',
                    description='测试百度搜索功能',
                    steps='[{"action":"navigate","params":{"url":"https://www.baidu.com"},"description":"访问百度首页"},{"action":"ai_input","params":{"text":"AI测试","locate":"搜索框"},"description":"输入搜索关键词"}]',
                    category='搜索功能',
                    priority=1,
                    created_by='system'
                )
                db.session.add(sample_testcase)

            if template_count == 0:
                sample_template = Template(
                    name='搜索功能模板',
                    description='通用搜索功能测试模板',
                    category='搜索',
                    steps_template='[{"action":"navigate","params":{"url":"{{search_url}}"},"description":"访问搜索页面"}]',
                    parameters='{"search_url":{"type":"string","description":"搜索页面URL"}}',
                    created_by='system',
                    is_public=True
                )
                db.session.add(sample_template)

            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': '数据库初始化成功',
                'data': {
                    'test_cases': TestCase.query.count(),
                    'templates': Template.query.count()
                }
            })

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据库初始化失败: {str(e)}'
            }), 500

    # 数据库连接测试
    @app.route('/api/db-test')
    def db_test():
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                return jsonify({
                    'status': 'error',
                    'message': 'DATABASE_URL环境变量未设置'
                }), 500

            # 显示连接信息（隐藏密码）
            from urllib.parse import urlparse
            parsed = urlparse(database_url)

            connection_info = {
                'scheme': parsed.scheme,
                'hostname': parsed.hostname,
                'port': parsed.port,
                'database': parsed.path.lstrip('/') if parsed.path else None,
                'username': parsed.username,
                'password_set': bool(parsed.password),
                'original_url': database_url[:50] + '...' if len(database_url) > 50 else database_url
            }

            # 尝试多种连接方式
            connection_attempts = []

            # 方法1: 使用应用的数据库引擎
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(db.text("SELECT 1 as test"))
                    test_result = result.fetchone()

                return jsonify({
                    'status': 'success',
                    'message': '数据库连接成功 (方法1: 应用引擎)',
                    'connection_info': connection_info,
                    'test_query': 'SELECT 1 执行成功'
                })
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

                return jsonify({
                    'status': 'success',
                    'message': '数据库连接成功 (方法2: 直接连接)',
                    'connection_info': connection_info,
                    'test_query': 'SELECT 1 执行成功'
                })
            except Exception as e2:
                connection_attempts.append(f"方法2失败: {str(e2)}")

            # 方法3: 尝试连接池端口
            try:
                pool_url = database_url.replace(':5432/', ':6543/')
                import psycopg2
                conn = psycopg2.connect(pool_url)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                conn.close()

                return jsonify({
                    'status': 'success',
                    'message': '数据库连接成功 (方法3: 连接池)',
                    'connection_info': {**connection_info, 'used_pool_port': True},
                    'test_query': 'SELECT 1 执行成功',
                    'suggestion': '建议更新DATABASE_URL使用端口6543'
                })
            except Exception as e3:
                connection_attempts.append(f"方法3失败: {str(e3)}")

            return jsonify({
                'status': 'error',
                'message': '所有连接方法都失败了',
                'connection_info': connection_info,
                'attempts': connection_attempts,
                'suggestion': '请检查Supabase项目状态，或尝试使用连接池URL (端口6543)'
            }), 500

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'测试过程出错: {str(e)}',
                'connection_info': connection_info if 'connection_info' in locals() else None
            }), 500

    # 简化的执行API（不依赖WebSocket）
    @app.route('/api/executions/start', methods=['POST'])
    def start_execution():
        try:
            from flask import request
            data = request.get_json() or {}
            testcase_id = data.get('testcase_id')
            mode = data.get('mode', 'normal')

            if not testcase_id:
                return jsonify({
                    'code': 400,
                    'message': '缺少测试用例ID'
                }), 400

            # 模拟执行ID
            import uuid
            execution_id = str(uuid.uuid4())

            return jsonify({
                'code': 200,
                'message': '执行已启动',
                'data': {
                    'execution_id': execution_id,
                    'testcase_id': testcase_id,
                    'mode': mode,
                    'status': 'started',
                    'message': '测试执行已启动，请注意这是演示版本'
                }
            })
        except Exception as e:
            return jsonify({
                'code': 500,
                'message': f'启动执行失败: {str(e)}'
            }), 500

    # 执行状态查询API
    @app.route('/api/executions/<execution_id>/status')
    def get_execution_status(execution_id):
        try:
            # 模拟执行状态
            return jsonify({
                'code': 200,
                'data': {
                    'execution_id': execution_id,
                    'status': 'completed',
                    'message': '演示执行已完成',
                    'total_steps': 4,
                    'completed_steps': 4,
                    'steps': [
                        {'status': 'success', 'description': '访问百度首页'},
                        {'status': 'success', 'description': '输入搜索关键词'},
                        {'status': 'success', 'description': '点击搜索按钮'},
                        {'status': 'success', 'description': '验证搜索结果'}
                    ]
                }
            })
        except Exception as e:
            return jsonify({
                'code': 500,
                'message': f'获取执行状态失败: {str(e)}'
            }), 500

    print("✅ API功能加载成功")

except Exception as e:
    print(f"⚠️ API功能加载失败: {e}")
    import traceback
    traceback.print_exc()

    # 简单的错误API
    @app.route('/api/status')
    def api_status_error():
        return jsonify({
            'status': 'error',
            'message': f'API加载失败: {str(e)}',
            'suggestion': '请检查环境变量和依赖配置'
        }), 500

# Vercel需要的应用对象
application = app

if __name__ == '__main__':
    app.run(debug=True)
