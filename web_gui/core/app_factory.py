"""
Application Factory - 应用工厂
使用工厂模式创建Flask应用，支持不同配置环境
"""

import os
import sys
import logging
from flask import Flask

def create_app(test_config=None):
    """
    应用工厂函数
    
    Args:
        test_config: 测试配置（可选）
    
    Returns:
        Flask应用实例
    """
    
    app = Flask(__name__)
    
    # 配置日志系统
    _setup_logging(app)
    
    # 加载配置
    _load_config(app, test_config)
    
    # 初始化扩展
    _init_extensions(app)
    
    # 注册路由
    _register_routes(app)
    
    # 注册错误处理器
    _register_error_handlers(app)
    
    # 注册过滤器
    _register_filters(app)
    
    return app

def _setup_logging(app):
    """设置日志系统"""
    try:
        from ..utils.logging_config import setup_logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Intent Test Framework 启动中...")
    except ImportError:
        try:
            from web_gui.utils.logging_config import setup_logging
            setup_logging()
            logger = logging.getLogger(__name__)
            logger.info("Intent Test Framework 启动中...")
        except ImportError:
            logging.basicConfig(level=logging.INFO)
            logger = logging.getLogger(__name__)
            logger.warning("高级日志配置不可用，使用基础日志配置")

def _load_config(app, test_config):
    """加载应用配置"""
    
    # 设置基础配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    if test_config:
        # 使用测试配置
        app.config.update(test_config)
        # 确保SQLite不使用连接池参数
        if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
            app.config.pop('SQLALCHEMY_ENGINE_OPTIONS', None)
    else:
        # 加载生产配置
        try:
            from ..database_config import get_flask_config, print_database_info, validate_database_connection
            db_config = get_flask_config()
            app.config.update(db_config)
            print_database_info()
        except (ValueError, ImportError) as e:
            print(f"❌ 数据库配置失败: {e}")
            print("请确保已正确配置PostgreSQL数据库连接。")
            sys.exit(1)

def _init_extensions(app):
    """初始化扩展"""
    from .extensions import init_extensions
    init_extensions(app)

def _register_routes(app):
    """注册路由"""
    # 注册API路由
    try:
        from ..api import register_api_routes
        register_api_routes(app)
    except ImportError:
        from web_gui.api import register_api_routes
        register_api_routes(app)
    
    # 注册主要页面路由
    try:
        from ..routes import register_main_routes
        register_main_routes(app)
    except ImportError:
        print("⚠️  主页面路由模块未找到，将在后续步骤中创建")

def _register_error_handlers(app):
    """注册错误处理器"""
    from .error_handlers import register_error_handlers
    register_error_handlers(app)

def _register_filters(app):
    """注册模板过滤器"""
    
    @app.template_filter('utc_to_local')
    def utc_to_local_filter(dt):
        """将UTC时间转换为带时区标识的ISO格式"""
        if dt is None:
            return ''
        try:
            return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        except AttributeError:
            return ''
