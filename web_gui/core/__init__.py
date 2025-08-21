"""
Core module - 核心功能模块
包含应用工厂、扩展初始化、错误处理等核心功能
"""

from .app_factory import create_app
from .extensions import db, socketio
from .error_handlers import register_error_handlers

__all__ = [
    'create_app',
    'db',
    'socketio', 
    'register_error_handlers'
]
