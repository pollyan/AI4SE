#!/usr/bin/env python3
"""
Web GUI测试用例管理系统启动脚本
"""
import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import flask
        import flask_sqlalchemy
        import flask_cors
        import requests

        print("✅ Python依赖检查通过")
        return True
    except ImportError as e:
        print(f"❌ 缺少Python依赖: {e}")
        print("请运行: pip install -r web_gui/requirements.txt")
        return False


def check_node_server():
    """检查Node.js服务器是否运行"""
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

    # 检查Node.js是否安装
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未找到Node.js，请先安装Node.js")
        return None

    # 启动服务器
    try:
        process = subprocess.Popen(
            ["node", "midscene_server.js"],
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # 等待服务器启动
        for i in range(10):
            time.sleep(1)
            if check_node_server():
                print("✅ MidSceneJS服务器启动成功")
                return process
            print(f"⏳ 等待服务器启动... ({i+1}/10)")

        print("❌ MidSceneJS服务器启动失败")
        process.terminate()
        return None

    except Exception as e:
        print(f"❌ 启动MidSceneJS服务器失败: {e}")
        return None


def check_environment():
    """检查环境变量"""
    required_vars = ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"⚠️  缺少环境变量: {', '.join(missing_vars)}")
        print("请设置以下环境变量或创建.env文件:")
        print("  OPENAI_API_KEY=your_api_key")
        print("  OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1")
        print("  MIDSCENE_MODEL_NAME=qwen-vl-max-latest")
        print("  MIDSCENE_USE_QWEN_VL=1")
        return False

    print("✅ 环境变量检查通过")
    return True


def start_web_gui():
    """启动Web GUI"""
    print("🌐 启动Web GUI...")

    # 切换到web_gui目录
    os.chdir(Path(__file__).parent)

    # 启动Flask应用
    try:
        from app import app

        app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
    except Exception as e:
        print(f"❌ Web GUI启动失败: {e}")


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n🛑 正在关闭服务...")
    sys.exit(0)


def main():
    """主函数"""
    print("=" * 60)
    print("🤖 AI Web测试用例管理系统启动器")
    print("=" * 60)

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 检查依赖
    if not check_dependencies():
        return 1

    # 检查环境变量
    if not check_environment():
        print("\n💡 提示: 你可以继续启动系统，但AI功能可能无法正常工作")
        response = input("是否继续启动? (y/N): ")
        if response.lower() != "y":
            return 1

    # 检查并启动Node.js服务器
    node_process = None
    if not check_node_server():
        node_process = start_node_server()
        if not node_process:
            print("⚠️  MidSceneJS服务器启动失败，AI功能将不可用")
            response = input("是否继续启动Web GUI? (y/N): ")
            if response.lower() != "y":
                return 1

    try:
        # 启动Web GUI
        print("\n" + "=" * 60)
        print("🎉 系统启动成功!")
        print("📱 Web界面: http://localhost:5000")
        print("🤖 AI服务: http://localhost:3001")
        print("=" * 60)
        print("按 Ctrl+C 停止服务")
        print("=" * 60)

        start_web_gui()

    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    except Exception as e:
        print(f"\n❌ 系统运行错误: {e}")
    finally:
        # 清理Node.js进程
        if node_process:
            print("🧹 清理MidSceneJS服务器...")
            node_process.terminate()
            try:
                node_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                node_process.kill()

    return 0


if __name__ == "__main__":
    sys.exit(main())
