#!/usr/bin/env python3
"""
增强版AI测试GUI系统启动脚本
"""
import os
import sys
import subprocess
import time
from pathlib import Path


def check_dependencies():
    """检查依赖是否满足"""
    print("🔍 检查依赖...")

    try:
        # 检查Python模块
        import flask
        import flask_sqlalchemy
        import flask_cors
        import flask_socketio

        print("✅ Python依赖检查通过")

        # 检查现有AI框架
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from midscene_python import MidSceneAI

        print("✅ AI框架检查通过")

        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install flask flask-sqlalchemy flask-cors flask-socketio")
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
    server_file = Path("../midscene_server.js")
    if not server_file.exists():
        print("❌ 未找到midscene_server.js文件")
        return None

    try:
        # 启动Node.js服务器
        process = subprocess.Popen(
            ["node", str(server_file)],
            cwd="..",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

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


def init_database():
    """初始化数据库"""
    print("🗄️  初始化数据库...")

    try:
        # 导入应用和数据库
        from app_enhanced import app, db, init_database as app_init_db

        # 调用应用的初始化函数
        app_init_db()

        with app.app_context():
            # 检查是否需要创建示例数据
            from models import TestCase, Template

            if TestCase.query.count() == 0:
                create_sample_data(db)

            return True

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False


def create_sample_data(db):
    """创建示例数据"""
    print("📝 创建示例数据...")

    try:
        from models import TestCase, Template
        import json

        # 创建示例测试用例
        sample_testcase = TestCase(
            name="百度搜索测试",
            description="测试百度搜索功能的基本流程",
            steps=json.dumps(
                [
                    {
                        "action": "goto",
                        "params": {"url": "https://www.baidu.com"},
                        "description": "访问百度首页",
                    },
                    {
                        "action": "ai_input",
                        "params": {"text": "AI自动化测试", "locate": "搜索框"},
                        "description": "在搜索框输入关键词",
                    },
                    {
                        "action": "ai_tap",
                        "params": {"prompt": "百度一下按钮"},
                        "description": "点击搜索按钮",
                    },
                    {
                        "action": "ai_wait_for",
                        "params": {"prompt": "搜索结果页面加载完成", "timeout": 10000},
                        "description": "等待搜索结果加载",
                    },
                    {
                        "action": "ai_assert",
                        "params": {"prompt": "页面显示了搜索结果"},
                        "description": "验证搜索结果显示",
                    },
                ]
            ),
            tags="搜索,基础功能",
            category="功能测试",
            priority=1,
            created_by="system",
        )

        db.session.add(sample_testcase)

        # 创建登录测试模板
        login_template = Template(
            name="用户登录测试模板",
            description="标准的用户登录流程测试模板",
            category="认证",
            steps_template=json.dumps(
                [
                    {
                        "action": "goto",
                        "params": {"url": "{{login_url}}"},
                        "description": "访问登录页面",
                    },
                    {
                        "action": "ai_input",
                        "params": {"text": "{{username}}", "locate": "用户名输入框"},
                        "description": "输入用户名",
                    },
                    {
                        "action": "ai_input",
                        "params": {"text": "{{password}}", "locate": "密码输入框"},
                        "description": "输入密码",
                    },
                    {
                        "action": "ai_tap",
                        "params": {"prompt": "登录按钮"},
                        "description": "点击登录按钮",
                    },
                    {
                        "action": "ai_assert",
                        "params": {"prompt": "登录成功，显示用户首页"},
                        "description": "验证登录成功",
                    },
                ]
            ),
            parameters=json.dumps(
                {
                    "login_url": {
                        "type": "string",
                        "description": "登录页面URL",
                        "required": True,
                    },
                    "username": {
                        "type": "string",
                        "description": "用户名",
                        "required": True,
                    },
                    "password": {
                        "type": "string",
                        "description": "密码",
                        "required": True,
                    },
                }
            ),
            created_by="system",
            is_public=True,
        )

        db.session.add(login_template)
        db.session.commit()

        print("✅ 示例数据创建成功")

    except Exception as e:
        print(f"❌ 创建示例数据失败: {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 AI测试GUI系统增强版启动器")
    print("=" * 60)

    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请安装必要的依赖")
        return 1

    # 检查并启动Node.js服务器
    node_process = None
    if not check_node_server():
        node_process = start_node_server()
        if not node_process:
            print("\n⚠️  MidSceneJS服务器启动失败，AI功能可能无法正常工作")
            print("您可以手动启动服务器: cd .. && node midscene_server.js")

    # 初始化数据库
    if not init_database():
        print("\n❌ 数据库初始化失败")
        if node_process:
            node_process.terminate()
        return 1

    print("\n" + "=" * 60)
    print("✅ 系统启动准备完成")
    print("=" * 60)
    print("📍 Web界面: http://localhost:5001")
    print("📍 API接口: http://localhost:5001/api/v1/")
    print("📍 MidSceneJS: http://localhost:3001")
    print("=" * 60)
    print("💡 提示:")
    print("   - 首次使用请配置AI模型API密钥")
    print("   - 可以从示例测试用例开始体验")
    print("   - 按Ctrl+C停止服务")
    print("=" * 60)

    try:
        # 启动Flask应用
        from app_enhanced import app, socketio

        socketio.run(
            app, debug=True, host="0.0.0.0", port=5001, allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 正在停止服务...")
        if node_process:
            print("停止MidSceneJS服务器...")
            node_process.terminate()
            node_process.wait()
        print("✅ 服务已停止")
        return 0
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        if node_process:
            node_process.terminate()
        return 1


if __name__ == "__main__":
    sys.exit(main())
