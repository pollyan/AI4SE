"""AI 智能体 Flask 应用入口"""
import sys
import os

# 添加 shared 模块到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from flask import Flask, send_from_directory

# React 静态文件目录 (npm run build 后的产物)
REACT_BUILD_DIR = os.path.join(os.path.dirname(__file__), '../frontend/dist')

def create_app():
    """创建并配置 Flask 应用"""
    from shared.config import SharedConfig
    
    app = Flask(
        __name__,
        static_folder=REACT_BUILD_DIR,
        static_url_path=''
    )
    
    # 应用配置
    app.config.from_object(SharedConfig)
    
    # 数据库配置
    from shared.database import get_database_config
    app.config.update(get_database_config())
    
    # 初始化数据库
    from backend.models import db
    db.init_app(app)
    
    with app.app_context():
        # 确保数据库表存在
        try:
            db.create_all()
            print("✅ 数据库表验证完成")
        except Exception as e:
            print(f"⚠️ 数据库表创建失败: {e}")
    
    # 注册 AI 智能体相关的蓝图
    try:
        from backend.api import requirements_bp, ai_configs_bp
        app.register_blueprint(requirements_bp)
        app.register_blueprint(ai_configs_bp)
        print("✅ API 蓝图注册成功")
    except Exception as e:
        import traceback
        print(f"⚠️ 蓝图注册失败: {e}")
        traceback.print_exc()
    
    # 健康检查路由
    @app.route('/health')
    @app.route('/ai-agents/health')
    def health():
        return {"status": "ok", "service": "ai-agents"}
    
    # React SPA 路由 - 所有非 API 路由都返回 index.html
    @app.route('/')
    @app.route('/ai-agents/')
    @app.route('/ai-agents/config')
    @app.route('/config')
    def serve_react():
        """服务 React 单页应用"""
        index_path = os.path.join(REACT_BUILD_DIR, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(REACT_BUILD_DIR, 'index.html')
        else:
            # 开发模式下，React dev server 运行在 localhost:3000
            return """
            <h1>React 前端未构建</h1>
            <p>请运行以下命令构建 React 应用:</p>
            <pre>cd tools/ai-agents/frontend && npm run build</pre>
            <p>或者访问 <a href="http://localhost:3000">http://localhost:3000</a> (开发模式)</p>
            """, 404
    
    # 处理 React 路由的静态资源 (Nginx 转发时保留 /ai-agents 前缀)
    @app.route('/ai-agents/assets/<path:filename>')
    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        return send_from_directory(os.path.join(REACT_BUILD_DIR, 'assets'), filename)
    
    return app


if __name__ == '__main__':
    app = create_app()
    print("=== AI 智能体应用启动中 ===")
    print("📍 Web界面: http://localhost:5002")
    print("📍 API接口: http://localhost:5002/api/")
    print("=========================")
    app.run(debug=True, host='0.0.0.0', port=5002)

