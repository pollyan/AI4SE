"""
API模块化重构
将原来的大型api_routes.py文件拆分为多个模块
"""

from flask import Blueprint

# 创建主API蓝图
api_bp = Blueprint("api", __name__, url_prefix="/api")

# 导入各个子模块并注册路由
# 这些导入会自动注册路由到api_bp蓝图
from . import testcases
from . import executions
from . import templates
from . import statistics
from . import dashboard
from . import user
from . import midscene
from . import database
from . import health
from . import requirements


# 注册子模块的路由到主蓝图
def register_api_routes(app):
    """注册所有API路由到Flask应用"""
    app.register_blueprint(api_bp)
    
    # 注册需求分析API蓝图
    from .requirements import requirements_bp
    app.register_blueprint(requirements_bp, url_prefix="/api")
    
    # 注册AI配置管理API蓝图
    from .ai_configs import ai_configs_bp
    app.register_blueprint(ai_configs_bp, url_prefix="/api")
    
    # 兼容：部分模块使用独立蓝图（如 testcases_bp）而非 api_bp 装饰
    try:
        from .testcases import testcases_bp
        app.register_blueprint(testcases_bp, url_prefix="/api")
    except Exception:
        pass


# 导出主要组件供外部使用
__all__ = ["api_bp", "register_api_routes"]
