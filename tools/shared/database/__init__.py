"""共享数据库配置模块"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_database_config():
    """获取数据库配置"""
    import os
    return {
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///local.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {'pool_pre_ping': True}
    }
