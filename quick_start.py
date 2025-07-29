#!/usr/bin/env python3
"""
Intent Test Framework 快速启动脚本
用于启动本地调试环境，连接线上数据库
"""
import os
import sys
import subprocess
import time
import signal
from pathlib import Path

def setup_environment():
    """设置环境变量"""
    print("⚙️  设置环境变量...")
    
    # 设置调试模式
    os.environ['FLASK_ENV'] = 'development'
    os.environ['FLASK_DEBUG'] = '1'
    
    # 确保使用线上PostgreSQL数据库
    if not os.getenv('DATABASE_URL'):
        # 使用默认的Supabase数据库连接
        print("📡 使用默认线上数据库连接")
        os.environ['DATABASE_URL'] = "postgresql://postgres.jzmqsuxphksbulrbhebp:Shunlian04@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"
    
    # AI服务配置
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  未设置OPENAI_API_KEY，AI功能可能无法正常工作")
        print("   请在.env文件中配置API密钥或设置环境变量")

def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    required_modules = [
        'flask', 'flask_sqlalchemy', 'flask_cors', 'flask_socketio', 
        'psycopg2', 'sqlalchemy'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module.replace('_', '-'))
        except ImportError:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ 缺少依赖: {', '.join(missing_modules)}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_modules)}")
        if 'psycopg2' in missing_modules:
            print("或者: pip install psycopg2-binary")
        return False
    
    print("✅ Python依赖检查通过")
    return True

def check_database_connection():
    """检查数据库连接"""
    print("🗄️  检查数据库连接...")
    
    try:
        # 切换到web_gui目录
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_gui'))
        from database_config import validate_database_connection, print_database_info
        
        print_database_info()
        
        if validate_database_connection():
            print("✅ 数据库连接成功")
            return True
        else:
            print("❌ 数据库连接失败")
            return False
            
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def check_node_server():
    """检查Node.js服务器状态"""
    try:
        import requests
        response = requests.get("http://localhost:3001/health", timeout=3)
        if response.status_code == 200:
            print("✅ MidSceneJS服务器已运行")
            return True
    except:
        pass
    
    print("⚠️  MidSceneJS服务器未运行")
    return False

def start_node_server():
    """启动Node.js服务器"""
    print("🚀 启动MidSceneJS服务器...")
    
    # 检查服务器文件
    server_file = Path("midscene_server.js")
    if not server_file.exists():
        print("❌ 未找到midscene_server.js文件")
        return None
    
    # 检查node_modules
    if not Path("node_modules").exists():
        print("📦 安装Node.js依赖...")
        try:
            subprocess.run(["npm", "install"], check=True)
        except subprocess.CalledProcessError:
            print("❌ npm install 失败")
            return None
    
    try:
        # 启动Node.js服务器
        process = subprocess.Popen([
            "node", "midscene_server.js"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务器启动
        time.sleep(3)
        
        # 检查服务器是否启动成功
        if check_node_server():
            print("✅ MidSceneJS服务器启动成功")
            return process
        else:
            print("❌ MidSceneJS服务器启动失败")
            process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ 启动MidSceneJS服务器失败: {e}")
        return None

def start_flask_app():
    """启动Flask应用"""
    print("🌐 启动Web应用...")
    
    try:
        # 保存原始工作目录
        original_dir = os.getcwd()
        web_gui_dir = os.path.join(os.path.dirname(__file__), 'web_gui')
        
        # 添加web_gui目录到Python路径
        sys.path.insert(0, web_gui_dir)
        
        # 切换到web_gui目录
        os.chdir(web_gui_dir)
        
        # 直接导入app_enhanced模块并初始化
        from app_enhanced import init_app, init_database
        
        # 初始化数据库
        if not init_database():
            print("❌ 数据库初始化失败")
            return 1
        
        # 初始化应用
        app, socketio = init_app()
        
        # 设置Flask运行参数，禁用自动重载以避免路径问题
        socketio.run(
            app,
            debug=False,  # 关闭调试模式避免重启问题
            host='0.0.0.0',
            port=5001,
            allow_unsafe_werkzeug=True
        )
        return 0
        
    except Exception as e:
        print(f"❌ 启动Web应用失败: {e}")
        return 1
    finally:
        # 恢复原始工作目录
        try:
            os.chdir(original_dir)
        except:
            pass

def signal_handler(signum, frame):
    """处理中断信号"""
    print("\n\n🛑 正在停止服务...")
    sys.exit(0)

def main():
    """主函数"""
    print("=" * 70)
    print("🚀 Intent Test Framework - 快速启动")
    print("=" * 70)
    print("🎯 目标: 启动本地调试环境，连接线上数据库")
    print("=" * 70)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 1. 设置环境
    setup_environment()
    print()
    
    # 2. 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请安装必要的依赖")
        return 1
    print()
    
    # 3. 检查数据库连接
    if not check_database_connection():
        print("\n❌ 数据库连接失败，请检查网络连接或数据库配置")
        return 1
    print()
    
    # 4. 检查并启动Node.js服务器
    node_process = None
    if not check_node_server():
        node_process = start_node_server()
        if not node_process:
            print("\n⚠️  MidSceneJS服务器启动失败，AI功能可能无法正常工作")
            print("   您可以手动启动: node midscene_server.js")
    print()
    
    # 5. 启动主应用
    print("=" * 70)
    print("🎉 环境准备完成，启动应用...")
    print("=" * 70)
    print("📍 Web界面: http://localhost:5001")
    print("📍 API文档: http://localhost:5001/api/v1/")
    print("📍 AI服务: http://localhost:3001")
    print("=" * 70)
    print("💡 使用提示:")
    print("   - 当前连接线上PostgreSQL数据库")
    print("   - 首次使用请在设置中配置AI API密钥")
    print("   - 可以从测试用例管理页面开始体验")
    print("   - 按Ctrl+C停止所有服务")
    print("=" * 70)
    
    try:
        # 启动Flask应用
        return start_flask_app()
    except KeyboardInterrupt:
        print("\n\n🛑 用户中断")
        return 0
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return 1
    finally:
        if node_process:
            print("🛑 停止MidSceneJS服务器...")
            node_process.terminate()
            node_process.wait()

if __name__ == "__main__":
    sys.exit(main())