"""AI 智能体 Flask 应用入口"""
import sys
import os

# 添加 shared 模块到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
# 添加项目根目录到路径
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
    from web_gui.models import db
    db.init_app(app)
    
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
    
    # 注册 AI 智能体相关的蓝图
    # 目前仍使用 web_gui.api 模块，后续将逐步迁移到本地 api 模块
    try:
        from web_gui.api.requirements import requirements_bp
        from web_gui.api.ai_configs import ai_configs_bp
        app.register_blueprint(requirements_bp)
        app.register_blueprint(ai_configs_bp)
        print("✅ API 蓝图注册成功")
    except Exception as e:
        import traceback
        print(f"⚠️ 蓝图注册失败: {e}")
        traceback.print_exc()
    
    # 注册页面路由
    from flask import render_template
    
    @app.route('/')
    def index():
        return render_template('requirements_analyzer.html')
    
    @app.route('/config')
    @app.route('/config-management')
    def config():
        return render_template('config_management.html')
    
    @app.route('/health')
    def health():
        return {"status": "ok", "service": "ai-agents"}
    
    return app


if __name__ == '__main__':
    app = create_app()
    print("=== AI 智能体应用启动中 ===")
    print("📍 Web界面: http://localhost:5002")
    print("📍 API接口: http://localhost:5002/api/")
    print("=========================")
    app.run(debug=True, host='0.0.0.0', port=5002)

