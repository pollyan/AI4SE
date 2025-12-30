"""意图测试工具 Flask 应用入口"""
import sys
import os

# 添加当前目录到路径 (Removed: we use package structure now)
# sys.path.insert(0, os.path.dirname(__file__))

# 添加 shared 模块到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
# 添加项目根目录到路径（为了导入 shared 等）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from flask import Flask
from shared.config import SharedConfig

def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(
        __name__,
        template_folder='../frontend/templates',
        static_folder='../frontend/static',
        static_url_path='/static'
    )
    
    # 应用配置
    app.config.from_object(SharedConfig)
    
    # 数据库配置
    from shared.database import get_database_config
    app.config.update(get_database_config())
    
    # 初始化数据库
    # 使用本地 models 模块
    from .models import db
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created/verified")

    # 初始化SocketIO
    from .extensions import socketio
    socketio.init_app(app)
    
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
    def root_redirect():
        return redirect('/testcases')

    # 健康检查
    @app.route('/health')
    def health_check():
        return {"status": "ok", "message": "Service is running"}
    
    return app


if __name__ == '__main__':
    from .extensions import socketio
    app = create_app()
    print("=== 意图测试工具启动中 ===")
    print("📍 Web界面: http://localhost:5001")
    print("📍 API接口: http://localhost:5001/api/")
    print("=========================")
    socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)

