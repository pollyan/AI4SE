"""
Extensions module - 扩展初始化
统一管理Flask扩展的初始化
"""

from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from flask_cors import CORS

# 创建扩展实例（延迟初始化模式）
db = SQLAlchemy()
socketio = SocketIO()
cors = CORS()

def init_extensions(app):
    """初始化所有Flask扩展"""
    
    # 初始化数据库
    db.init_app(app)
    
    # 初始化CORS
    cors.init_app(app, origins="*")
    
    # 初始化SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    return app
