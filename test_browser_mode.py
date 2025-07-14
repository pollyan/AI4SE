#!/usr/bin/env python3
"""
测试浏览器模式功能
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
def step_status(data):
    print(f"🔄 步骤状态: {data}")

def test_browser_mode():
    """测试浏览器模式"""
    print("🖥️ 测试浏览器模式...")
    
    # 连接到WebSocket服务器
    sio.connect('http://localhost:5001')
    
    # 开始执行测试用例 - 浏览器模式
    print("🚀 开始执行测试用例 - 浏览器模式...")
    sio.emit('start_execution', {
        'testcase_id': 1,  # 使用百度搜索测试用例
        'mode': 'browser'  # 使用浏览器模式
    })
    
    # 等待执行完成
    time.sleep(30)
    
    # 断开连接
    sio.disconnect()

def test_headless_mode():
    """测试无头模式"""
    print("🚀 测试无头模式...")
    
    # 连接到WebSocket服务器
    sio.connect('http://localhost:5001')
    
    # 开始执行测试用例 - 无头模式
    print("🚀 开始执行测试用例 - 无头模式...")
    sio.emit('start_execution', {
        'testcase_id': 1,  # 使用百度搜索测试用例
        'mode': 'headless'  # 使用无头模式
    })
    
    # 等待执行完成
    time.sleep(30)
    
    # 断开连接
    sio.disconnect()

if __name__ == "__main__":
    print("🧪 开始测试浏览器模式功能...")
    
    # 测试浏览器模式
    test_browser_mode()
    
    print("\n" + "="*50 + "\n")
    
    # 测试无头模式
    test_headless_mode()
    
    print("✅ 测试完成！")
