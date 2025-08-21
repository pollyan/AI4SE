#!/usr/bin/env python3
"""
重构后的启动脚本
提供更清晰的启动选项和配置验证
"""

import os
import sys
import argparse
import logging

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_environment():
    """设置环境变量和路径"""
    # 设置基础环境变量
    if not os.getenv('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'
    
    if not os.getenv('PYTHONPATH'):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.environ['PYTHONPATH'] = project_root

def main():
    """主启动函数"""
    parser = argparse.ArgumentParser(description='Intent Test Framework - 重构版启动器')
    parser.add_argument('--env', choices=['development', 'production', 'testing'], 
                       default='development', help='运行环境')
    parser.add_argument('--port', type=int, default=5001, help='服务器端口')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--validate-only', action='store_true', help='仅验证配置不启动服务')
    
    args = parser.parse_args()
    
    # 设置环境
    setup_environment()
    os.environ['FLASK_ENV'] = args.env
    
    # 配置日志
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # 导入应用
        from app_new import main as create_app, socketio
        
        logger.info(f"🚀 启动 Intent Test Framework")
        logger.info(f"📊 环境: {args.env}")
        logger.info(f"🌐 地址: http://{args.host}:{args.port}")
        
        # 创建应用
        app = create_app()
        
        if args.validate_only:
            logger.info("✅ 配置验证完成，退出")
            return
        
        # 启动服务器
        logger.info("🚀 启动服务器...")
        socketio.run(
            app,
            debug=args.debug,
            host=args.host,
            port=args.port,
            allow_unsafe_werkzeug=True
        )
        
    except KeyboardInterrupt:
        logger.info("👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
