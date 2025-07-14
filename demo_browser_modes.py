#!/usr/bin/env python3
"""
演示浏览器模式和无头模式的区别
"""

import os
import sys
import time
import requests

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "sk-e6e1356d468f427fba9239afe8d641ba"
os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
os.environ["MIDSCENE_MODEL_NAME"] = "qwen-vl-max-latest"
os.environ["MIDSCENE_USE_QWEN_VL"] = "1"

# 导入MidScene AI
sys.path.append("/Users/huian@thoughtworks.com/PycharmProjects/AI-WebUIAuto")
from midscene_python import MidSceneAI


def demo_browser_mode():
    """演示浏览器模式"""
    print("🖥️ 演示浏览器模式 - 您应该能看到浏览器窗口打开")
    print("=" * 60)

    try:
        ai = MidSceneAI()

        # 设置浏览器模式
        print("🔧 设置浏览器模式...")
        ai.set_browser_mode("browser")

        # 访问百度首页
        print("🌐 访问百度首页...")
        result = ai.goto("https://www.baidu.com")
        print(f"✅ 页面加载成功: {result.get('title', 'Unknown')}")

        # 等待用户观察
        print("⏳ 请观察浏览器窗口，5秒后继续...")
        time.sleep(5)

        # 输入搜索关键词
        print("⌨️ 输入搜索关键词...")
        result = ai.ai_type("搜索框", "AI自动化测试")
        print(f"✅ 输入成功")

        # 点击搜索按钮
        print("👆 点击搜索按钮...")
        result = ai.ai_click('"百度一下"按钮')
        print(f"✅ 点击成功")

        # 等待用户观察结果
        print("⏳ 请观察搜索结果，5秒后关闭浏览器...")
        time.sleep(5)

        print("✅ 浏览器模式演示完成！")

    except Exception as e:
        print(f"❌ 浏览器模式演示失败: {e}")


def demo_headless_mode():
    """演示无头模式"""
    print("\n🚀 演示无头模式 - 浏览器将在后台运行，您看不到窗口")
    print("=" * 60)

    try:
        ai = MidSceneAI()

        # 设置无头模式
        print("🔧 设置无头模式...")
        ai.set_browser_mode("headless")

        # 访问百度首页
        print("🌐 访问百度首页...")
        result = ai.goto("https://www.baidu.com")
        print(f"✅ 页面加载成功: {result.get('title', 'Unknown')}")

        # 输入搜索关键词
        print("⌨️ 输入搜索关键词...")
        result = ai.ai_type("搜索框", "AI自动化测试")
        print(f"✅ 输入成功")

        # 点击搜索按钮
        print("👆 点击搜索按钮...")
        result = ai.ai_click('"百度一下"按钮')
        print(f"✅ 点击成功")

        print("✅ 无头模式演示完成！")

    except Exception as e:
        print(f"❌ 无头模式演示失败: {e}")


def demo_mode_comparison():
    """演示模式对比"""
    print("\n📊 模式对比总结")
    print("=" * 60)

    print("🖥️ 浏览器模式特点:")
    print("   • 显示浏览器窗口，可视化执行")
    print("   • 便于调试和观察执行过程")
    print("   • 失败时继续执行后续步骤")
    print("   • 适合开发和调试阶段")

    print("\n🚀 无头模式特点:")
    print("   • 后台执行，不显示浏览器窗口")
    print("   • 执行速度更快，资源占用更少")
    print("   • 失败时停止执行")
    print("   • 适合生产环境和批量执行")

    print("\n💡 使用建议:")
    print("   • 开发调试时使用浏览器模式")
    print("   • 生产环境使用无头模式")
    print("   • CI/CD流水线使用无头模式")


if __name__ == "__main__":
    print("🎭 浏览器模式 vs 无头模式演示")
    print("=" * 60)

    # 演示浏览器模式
    demo_browser_mode()

    # 演示无头模式
    demo_headless_mode()

    # 模式对比
    demo_mode_comparison()

    print("\n🎉 演示完成！")
    print("现在您可以在Web界面中选择不同的执行模式了！")
