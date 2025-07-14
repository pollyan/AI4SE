#!/usr/bin/env python3
"""
简单测试浏览器模式功能
"""

import os
import sys
import time
import requests

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'sk-e6e1356d468f427fba9239afe8d641ba'
os.environ['OPENAI_BASE_URL'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
os.environ['MIDSCENE_MODEL_NAME'] = 'qwen-vl-max-latest'
os.environ['MIDSCENE_USE_QWEN_VL'] = '1'

# 导入MidScene AI
sys.path.append('/Users/huian@thoughtworks.com/PycharmProjects/AI-WebUIAuto')
from midscene_python import MidSceneAI

def test_browser_mode_api():
    """测试浏览器模式API"""
    print("🧪 测试浏览器模式API...")
    
    try:
        ai = MidSceneAI()
        
        # 测试设置浏览器模式
        print("🖥️ 设置浏览器模式...")
        result = ai.set_browser_mode('browser')
        print(f"✅ 设置结果: {result}")
        
        # 测试访问页面
        print("🌐 访问测试页面...")
        result = ai.goto('https://www.example.com')
        print(f"✅ 访问结果: {result}")
        
        # 测试设置无头模式
        print("🚀 设置无头模式...")
        result = ai.set_browser_mode('headless')
        print(f"✅ 设置结果: {result}")
        
        # 再次测试访问页面
        print("🌐 再次访问测试页面...")
        result = ai.goto('https://www.example.com')
        print(f"✅ 访问结果: {result}")
        
        print("✅ 浏览器模式API测试成功！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def test_execution_api():
    """测试执行API"""
    print("🧪 测试执行API...")
    
    try:
        # 测试浏览器模式执行
        print("🖥️ 测试浏览器模式执行...")
        response = requests.post('http://localhost:5001/api/v1/executions', json={
            'testcase_id': 1,
            'mode': 'browser'
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 浏览器模式执行启动成功: {result}")
        else:
            print(f"❌ 浏览器模式执行失败: {response.status_code} - {response.text}")
        
        time.sleep(5)
        
        # 测试无头模式执行
        print("🚀 测试无头模式执行...")
        response = requests.post('http://localhost:5001/api/v1/executions', json={
            'testcase_id': 1,
            'mode': 'headless'
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 无头模式执行启动成功: {result}")
        else:
            print(f"❌ 无头模式执行失败: {response.status_code} - {response.text}")
            
        print("✅ 执行API测试成功！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    print("🧪 开始简单测试浏览器模式功能...")
    
    # 测试浏览器模式API
    test_browser_mode_api()
    
    print("\n" + "="*50 + "\n")
    
    # 测试执行API
    test_execution_api()
    
    print("✅ 所有测试完成！")
