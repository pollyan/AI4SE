"""
API路由兼容性文件
保持与原api_routes.py的向后兼容
在重构完成后可以删除此文件
"""

# 导入重构后的API蓝图
try:
    from api import api_bp
    print("✅ 从重构模块导入API蓝图成功")
except ImportError:
    from web_gui.api import api_bp
    print("✅ 从重构模块导入API蓝图成功 (Serverless模式)")

# 保持原有的导入兼容性
__all__ = ['api_bp']