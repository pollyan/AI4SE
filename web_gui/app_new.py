"""
新的应用入口文件 - 重构后的轻量化版本
替换原来的app_enhanced.py，使用模块化架构
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.app_factory import create_app
from core.extensions import db, socketio
from config import get_config, validate_config
from models import TestCase, ExecutionHistory, StepExecution, Template

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database(app):
    """初始化数据库"""
    with app.app_context():
        try:
            # 创建表
            db.create_all()
            logger.info("✅ 数据库表创建完成")
            
            # 应用数据库优化
            try:
                from utils.db_optimization import create_database_indexes
                create_database_indexes(db)
                logger.info("✅ 数据库索引优化完成")
            except ImportError:
                try:
                    from web_gui.utils.db_optimization import create_database_indexes
                    create_database_indexes(db)
                    logger.info("✅ 数据库索引优化完成")
                except Exception as opt_e:
                    logger.warning(f"⚠️ 数据库优化失败: {opt_e}")

            # 创建默认模板
            create_default_templates()
            return True
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            return False

def create_default_templates():
    """创建默认测试模板"""
    try:
        # 检查是否已有模板
        if Template.query.count() > 0:
            return
        
        import json
        
        # 登录测试模板
        login_template = Template(
            name="用户登录测试",
            description="标准的用户登录流程测试",
            category="认证",
            steps_template=json.dumps([
                {
                    "action": "goto",
                    "params": {"url": "{{login_url}}"},
                    "description": "访问登录页面"
                },
                {
                    "action": "ai_input",
                    "params": {"text": "{{username}}", "locate": "用户名输入框"},
                    "description": "输入用户名"
                },
                {
                    "action": "ai_input",
                    "params": {"text": "{{password}}", "locate": "密码输入框"},
                    "description": "输入密码"
                },
                {
                    "action": "ai_tap",
                    "params": {"prompt": "登录按钮"},
                    "description": "点击登录按钮"
                },
                {
                    "action": "ai_assert",
                    "params": {"prompt": "登录成功，显示用户首页"},
                    "description": "验证登录成功"
                }
            ]),
            parameters=json.dumps({
                "login_url": {"type": "string", "description": "登录页面URL"},
                "username": {"type": "string", "description": "用户名"},
                "password": {"type": "string", "description": "密码"}
            }),
            created_by="system",
            is_public=True
        )
        
        db.session.add(login_template)
        db.session.commit()
        logger.info("✅ 默认模板创建完成")
        
    except Exception as e:
        logger.error(f"❌ 创建默认模板失败: {e}")

def main():
    """主函数"""
    logger.info("🚀 启动 Intent Test Framework (重构版)")
    
    # 加载和验证配置
    try:
        config = get_config()
        validate_config(config)
        logger.info("✅ 配置加载和验证成功")
    except Exception as e:
        logger.error(f"❌ 配置验证失败: {e}")
        sys.exit(1)
    
    # 创建应用
    app = create_app()
    
    # 初始化数据库
    if init_database(app):
        logger.info("✅ 数据库初始化成功")
    else:
        logger.error("❌ 数据库初始化失败")
        sys.exit(1)
    
    # 打印启动信息
    logger.info("📍 后端地址: http://localhost:5001")
    logger.info("📍 API文档: http://localhost:5001/api/v1/")
    logger.info("✨ 应用启动完成，等待连接...")
    
    return app

if __name__ == '__main__':
    app = main()
    
    # 启动服务器
    socketio.run(
        app,
        debug=True,
        host='0.0.0.0',
        port=5001,
        allow_unsafe_werkzeug=True
    )
