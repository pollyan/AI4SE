#!/usr/bin/env python3
"""
测试AI助手激活调用
模拟线上环境的API调用，帮助诊断问题
"""

import requests
import json
import sys
from pathlib import Path

def test_ai_activation(base_url="http://localhost:5001"):
    """测试AI助手激活过程"""
    
    print("🧪 开始测试AI助手激活过程")
    print(f"🌐 使用服务地址: {base_url}")
    
    session = requests.Session()
    
    try:
        # 步骤1: 创建会话
        print("\n📝 步骤1: 创建会话")
        create_session_payload = {
            "project_name": "测试项目",
            "assistant_type": "song"  # 使用测试分析师Song
        }
        
        response = session.post(
            f"{base_url}/api/requirements/sessions",
            json=create_session_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ 创建会话失败: {response.status_code} - {response.text}")
            return False
        
        session_data = response.json()
        session_id = session_data['data']['id']
        print(f"✅ 会话创建成功: {session_id}")
        
        # 步骤2: 获取助手bundle
        print(f"\n📦 步骤2: 获取助手bundle")
        response = session.get(f"{base_url}/api/requirements/assistants/song/bundle")
        
        if response.status_code != 200:
            print(f"❌ 获取bundle失败: {response.status_code} - {response.text}")
            return False
        
        bundle_data = response.json()
        bundle_content = bundle_data['data']['bundle_content']
        print(f"✅ Bundle获取成功，长度: {len(bundle_content)} 字符")
        
        # 步骤3: 发送激活消息
        print(f"\n🤖 步骤3: 发送激活消息")
        activation_payload = {
            "content": bundle_content
        }
        
        print(f"📊 激活消息统计:")
        print(f"  - 消息长度: {len(bundle_content):,} 字符")
        print(f"  - 包含关键词: {'你的关键操作指令' in bundle_content}")
        print(f"  - 包含persona: {'persona执行' in bundle_content}")
        print(f"  - 包含bundle标识: {'Bundle' in bundle_content}")
        
        response = session.post(
            f"{base_url}/api/requirements/sessions/{session_id}/messages",
            json=activation_payload,
            headers={"Content-Type": "application/json"},
            timeout=180  # 3分钟超时
        )
        
        print(f"📡 HTTP状态码: {response.status_code}")
        print(f"📏 响应长度: {len(response.text)} 字符")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"✅ 激活消息发送成功")
                print(f"📋 响应结构: {list(response_data.keys())}")
                
                if 'data' in response_data and 'ai_message' in response_data['data']:
                    ai_message = response_data['data']['ai_message']
                    print(f"🤖 AI响应长度: {len(ai_message.get('content', ''))} 字符")
                    print(f"🤖 AI响应预览: {ai_message.get('content', '')[:200]}...")
                else:
                    print(f"⚠️ 响应格式异常: {response_data}")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"原始响应: {response.text[:500]}...")
                return False
                
        else:
            print(f"❌ 激活消息发送失败: {response.status_code}")
            print(f"错误响应: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return False

def main():
    """主函数"""
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5001"
    
    print("🔧 AI助手激活测试工具")
    print("=" * 50)
    
    success = test_ai_activation(base_url)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试通过！AI助手激活成功")
        return 0
    else:
        print("💥 测试失败！发现问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())
