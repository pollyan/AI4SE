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

# 创建Flask应用
app = Flask(__name__)

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

# 主页路由
@app.route('/')
def home():
    database_url = os.getenv('DATABASE_URL', 'Not configured')
    database_status = 'PostgreSQL (Supabase)' if database_url.startswith('postgresql://') else 'Not configured'

    return render_template_string(HTML_TEMPLATE, database_status=database_status)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': os.getenv('VERCEL_DEPLOYMENT_ID', 'local')})

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
                'password_set': bool(parsed.password)
            }

            # 尝试连接数据库
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1 as test"))
                test_result = result.fetchone()

            return jsonify({
                'status': 'success',
                'message': '数据库连接成功',
                'connection_info': connection_info,
                'test_query': 'SELECT 1 执行成功'
            })

        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'数据库连接失败: {str(e)}',
                'connection_info': connection_info if 'connection_info' in locals() else None,
                'suggestion': '请检查DATABASE_URL环境变量和Supabase项目状态'
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
