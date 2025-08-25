"""
Core module - 核心功能模块
包含应用工厂、扩展初始化、错误处理等核心功能
"""

from .extensions import db, socketio

__all__ = ["db", "socketio"]
