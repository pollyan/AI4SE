#!/usr/bin/env python3
"""
WebSocket客户端测试脚本
用于测试AI执行引擎的WebSocket功能
"""
import socketio
import time
import json

# 创建Socket.IO客户端
sio = socketio.Client()


@sio.event
def connect():
    print("✅ WebSocket连接成功")


@sio.event
def connected(data):
    print(f"📡 服务器响应: {data}")

    # 开始执行测试用例
    print("🚀 开始执行通义千问VL真实AI测试用例...")
    sio.emit(
        "start_execution",
        {
            "testcase_id": 7,  # 使用新创建的通义千问VL测试用例
            "mode": "headless",  # 使用无头模式
        },
    )


@sio.event
def execution_started(data):
    print(f"▶️  执行开始: {data}")


@sio.event
def step_started(data):
    print(f"📝 步骤开始: 第{data['step_index'] + 1}步 - {data['step_description']}")


@sio.event
def step_completed(data):
    status_icon = "✅" if data["status"] == "success" else "❌"
    print(f"{status_icon} 步骤完成: 第{data['step_index'] + 1}步 - {data['status']}")
    if data.get("error_message"):
        print(f"   错误: {data['error_message']}")
    if data.get("duration"):
        print(f"   耗时: {data['duration']}秒")


@sio.event
def execution_completed(data):
    print(f"🎉 执行完成!")
    print(f"   状态: {data['status']}")
    print(f"   总耗时: {data['duration']}秒")
    print(f"   成功步骤: {data['steps_passed']}/{data['total_steps']}")

    # 断开连接
    sio.disconnect()


@sio.event
def execution_error(data):
    print(f"❌ 执行错误: {data['message']}")
    sio.disconnect()


@sio.event
def disconnect():
    print("🔌 WebSocket连接断开")


def main():
    try:
        print("🔗 连接到WebSocket服务器...")
        sio.connect("http://localhost:5001")

        # 等待执行完成
        sio.wait()

    except Exception as e:
        print(f"❌ 连接失败: {e}")


if __name__ == "__main__":
    main()
