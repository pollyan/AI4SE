"""
Flask应用工厂模块
提供create_app函数用于创建Flask应用实例，支持测试和生产环境
"""

import sys
import os
from flask import Flask

def create_app(config=None):
    """
    Flask应用工厂函数
    
    Args:
        config: 可选的配置字典
        
    Returns:
        Flask: 配置好的Flask应用实例
    """
    # 添加项目根目录到Python路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    # 设置模板和静态文件路径
    template_dir = os.path.join(current_dir, "templates")
    static_dir = os.path.join(current_dir, "static")

    # 创建Flask应用
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
    
    # 测试环境配置
    if os.getenv("TESTING") == "true" or config and config.get("TESTING"):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["LOGIN_DISABLED"] = True

    # 数据库配置
    try:
        from .database_config import DatabaseConfig
        db_config = DatabaseConfig()
        app.config["SQLALCHEMY_DATABASE_URI"] = db_config.database_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        # 根据数据库类型设置引擎选项
        if db_config.database_url.startswith(("postgresql://", "postgres://")):
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                'pool_timeout': 20,
                'pool_recycle': -1,
                'pool_pre_ping': True
            }
        else:
            # SQLite配置
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                'pool_pre_ping': True
            }
            
    except ImportError:
        # 备用数据库配置
        database_url = os.getenv("DATABASE_URL", "sqlite:///:memory:")
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        # SQLite引擎选项
        if database_url.startswith("sqlite://"):
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {'pool_pre_ping': True}
            
    except Exception as e:
        # 如果数据库配置失败，使用内存数据库
        print(f"⚠️ 数据库配置失败，使用内存数据库: {e}")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {'pool_pre_ping': True}

    # 初始化数据库
    try:
        from .models import db
        db.init_app(app)
    except ImportError:
        pass

    # 应用配置覆盖
    if config:
        app.config.update(config)

    # 添加模板过滤器
    @app.template_filter("utc_to_local")
    def utc_to_local_filter(dt):
        """将UTC时间转换为带时区标识的ISO格式"""
        if dt is None:
            return ""
        try:
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        except AttributeError:
            return ""

    # 注册蓝图
    try:
        from .api.base import register_blueprints
        register_blueprints(app)
    except ImportError:
        # 如果无法导入蓝图注册函数，添加基本路由
        @app.route("/health")
        def health():
            return {"status": "ok", "message": "Flask app is running"}

    return app


if __name__ == "__main__":
    # 直接运行时启动开发服务器
    app = create_app()
    print("=== AI4SE工具集启动中 (开发模式) ===")
    print("📍 Web界面: http://localhost:5001")
    print("📍 API接口: http://localhost:5001/api/")
    print("=========================")
    app.run(debug=True, host="0.0.0.0", port=5001)
