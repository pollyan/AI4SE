"""意图测试工具 Flask 应用入口"""
import sys
import os
from collections.abc import Mapping
from typing import Any

# 添加当前目录到路径 (Removed: we use package structure now)
# sys.path.insert(0, os.path.dirname(__file__))

# 添加 shared 模块到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
# 添加项目根目录到路径（为了导入 shared 等）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from flask import Flask
from shared.config import SharedConfig

_ISOLATED_TEST_DATABASE_URI = 'sqlite:///:memory:'
_INTENT_SECURITY_ENVIRONMENT_KEYS = (
    'AI4SE_ENV',
    'INTENT_ACCESS_MODE',
    'INTENT_EXECUTION_ENABLED',
    'INTENT_PUBLIC_ORIGIN',
    'INTENT_PROXY_TOPOLOGY',
    'INTENT_PROXY_TOKEN',
    'INTENT_TESTER_ADMIN_PASSWORD_HASH',
    'OPENAI_API_KEY',
    'OPENAI_BASE_URL',
    'MIDSCENE_MODEL_NAME',
)
_PRODUCTION_GUNICORN_COMMAND = (
    "gunicorn --worker-class gthread --threads 100 --bind 0.0.0.0:5001 "
    "backend.app:create_app()"
)


def _validate_test_database_config(app: Flask) -> None:
    if not app.config.get('TESTING'):
        return

    database_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if database_uri != _ISOLATED_TEST_DATABASE_URI:
        raise ValueError(
            'Testing database must use the isolated in-memory SQLite URI '
            f'{_ISOLATED_TEST_DATABASE_URI!r}; got {database_uri!r}.'
        )


def create_app(test_config: Mapping[str, Any] | None = None):
    """创建并配置 Flask 应用"""
    app = Flask(
        __name__,
        template_folder='../frontend/templates',
        static_folder='../frontend/static',
        static_url_path='/intent-tester/static'
    )
    
    # 应用配置
    app.config.from_object(SharedConfig)
    
    # 数据库配置
    from shared.database import get_database_config
    app.config.update(get_database_config())
    app.config.update(
        {
            key: os.environ[key]
            for key in _INTENT_SECURITY_ENVIRONMENT_KEYS
            if key in os.environ
        }
    )
    if test_config is not None:
        app.config.update(test_config)
    _validate_test_database_config(app)
    
    # 添加时区格式化过滤器
    @app.template_filter('utc_to_local')
    def utc_to_local_filter(dt):
        """将UTC时间转换为带时区标识的ISO格式"""
        if dt is None:
            return ""
        try:
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except AttributeError:
            return ""
    
    # 注册API蓝图
    from .api import register_api_routes
    register_api_routes(app)

    # 注册视图蓝图 (Frontend Pages)
    from .views import views_bp
    
    # 注册蓝图到根路径 (由 Nginx 处理 /intent-tester 前缀)
    app.register_blueprint(views_bp, url_prefix='/')

    # 根路径重定向到标准路径
    from flask import redirect
    @app.route('/redirect-to-testcases')
    @app.route('/intent-tester/redirect-to-testcases')
    def root_redirect():
        return redirect('/intent-tester/testcases')

    # 健康检查
    @app.route('/health')
    @app.route('/intent-tester/health')
    def health_check():
        return {"status": "ok", "message": "Service is running"}

    # Security installation sees the complete URL map and must fail closed before
    # SQLAlchemy is initialized or opens a connection.
    from .intent_security import install_intent_security
    install_intent_security(app)

    # 初始化数据库
    # 使用本地 models 模块
    from .models import db
    db.init_app(app)

    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created/verified")
    
    return app


def run_direct_main(port: int) -> None:
    """Run the loopback development server or reject a production direct main."""
    if os.getenv('AI4SE_ENV', 'development').strip().lower() == 'production':
        raise SystemExit(
            'Production direct main is disabled; use the container Gunicorn entry: '
            + _PRODUCTION_GUNICORN_COMMAND
        )

    from .extensions import socketio

    app = create_app()
    socketio.run(app, debug=True, host='127.0.0.1', port=port)


if __name__ == '__main__':
    print("=== 意图测试工具启动中 ===")
    print("📍 Web界面: http://localhost:5001")
    print("📍 API接口: http://localhost:5001/api/")
    print("=========================")
    run_direct_main(port=5001)
