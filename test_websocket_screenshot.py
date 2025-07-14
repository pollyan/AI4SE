#!/usr/bin/env python3
"""
测试WebSocket截图事件
"""

import os
import sys
import time
import socketio

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'sk-e6e1356d468f427fba9239afe8d641ba'
os.environ['OPENAI_BASE_URL'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
os.environ['MIDSCENE_MODEL_NAME'] = 'qwen-vl-max-latest'
os.environ['MIDSCENE_USE_QWEN_VL'] = '1'

# 创建Socket.IO客户端
sio = socketio.Client()

@sio.event
def connect():
    print("✅ 连接到WebSocket服务器")

@sio.event
def disconnect():
    print("❌ 断开WebSocket连接")

@sio.event
def execution_log(data):
    print(f"📝 执行日志: {data}")

@sio.event
def execution_status(data):
    print(f"📊 执行状态: {data}")

@sio.event
def step_completed(data):
    print(f"🔄 步骤完成: {data}")
    
    # 检查截图数据
    if 'screenshot' in data:
        print(f"📸 新格式截图数据: {data['screenshot']}")
    elif 'screenshot_path' in data:
        print(f"📸 旧格式截图路径: {data['screenshot_path']}")
    else:
        print("❌ 没有截图数据")

@sio.event
def execution_started(data):
    print(f"▶️ 执行开始: {data}")

@sio.event
def execution_completed(data):
    print(f"✅ 执行完成: {data}")

def test_screenshot_websocket():
    """测试截图WebSocket事件"""
    print("🧪 测试截图WebSocket事件...")
    
    # 连接到WebSocket服务器
    sio.connect('http://localhost:5001')
    
    # 开始执行测试用例
    print("🚀 开始执行测试用例...")
    sio.emit('start_execution', {
        'testcase_id': 1,  # 使用百度搜索测试用例
        'mode': 'headless'  # 使用无头模式
    })
    
    # 等待执行完成
    time.sleep(30)
    
    # 断开连接
    sio.disconnect()

if __name__ == "__main__":
    print("🧪 开始测试截图WebSocket事件...")
    test_screenshot_websocket()
    print("✅ 测试完成！")
