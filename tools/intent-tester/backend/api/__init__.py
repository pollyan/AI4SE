from flask import Blueprint

# 定义主API蓝图，所有API路由都挂载在这里
api_bp = Blueprint('api', __name__, url_prefix='/api')

def register_api_routes(app):
    """注册所有API蓝图"""
    # 导入各个功能模块的蓝图
    # 注意：为了避免循环导入，函数内部导入
    from .testcases import testcases_bp
    from .executions import executions_bp
    from .templates import templates_bp
    from .dashboard import dashboard_bp

    from .midscene import midscene_bp
    from .proxy import proxy_bp

    # 注册主API蓝图
    app.register_blueprint(api_bp)

    # 注册功能蓝图
    # 统一挂载到 /api 前缀下
    app.register_blueprint(testcases_bp, url_prefix='/api')
    app.register_blueprint(executions_bp, url_prefix='/api')
    app.register_blueprint(templates_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')

    app.register_blueprint(midscene_bp, url_prefix='/api')
    app.register_blueprint(proxy_bp, url_prefix='/api')
