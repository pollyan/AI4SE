#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
默认AI配置初始化脚本
在本地开发环境启动时自动创建和更新默认AI配置
通过API调用来确保与Flask应用使用相同数据库
"""

import os
import sys
import requests
import time
import json
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def wait_for_flask_server(base_url="http://localhost:5001", timeout=30, check_interval=2):
    """等待Flask服务器启动"""
    print(f"⏳ 等待Flask服务器启动 ({base_url})...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{base_url}/api/status", timeout=5)
            if response.status_code == 200:
                print("✅ Flask服务器已就绪")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(check_interval)
    
    print(f"❌ Flask服务器启动超时 ({timeout}秒)")
    return False

def get_existing_configs(base_url="http://localhost:5001"):
    """获取现有AI配置"""
    try:
        response = requests.get(f"{base_url}/api/ai-configs", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("configs", [])
        else:
            print(f"⚠️ 获取配置列表失败: HTTP {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 获取配置列表失败: {e}")
        return []

def create_qwen_config(base_url="http://localhost:5001"):
    """创建Qwen配置"""
    config_data = {
        "config_name": "Qwen",
        "api_key": "sk-0b7ca376cfce4e2f82986eb5fea5124d",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_name": "qwen-plus"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/ai-configs",
            json=config_data,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            print("✅ Qwen配置创建成功")
            return response.json()
        else:
            print(f"❌ Qwen配置创建失败: HTTP {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Qwen配置创建失败: {e}")
        return None

def update_qwen_config(config_id, base_url="http://localhost:5001"):
    """更新现有Qwen配置"""
    config_data = {
        "config_name": "Qwen",
        "api_key": "sk-0b7ca376cfce4e2f82986eb5fea5124d", 
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model_name": "qwen-plus"
    }
    
    try:
        response = requests.put(
            f"{base_url}/api/ai-configs/{config_id}",
            json=config_data,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("🔄 Qwen配置更新成功")
            return response.json()
        else:
            print(f"❌ Qwen配置更新失败: HTTP {response.status_code}")
            print(f"响应内容: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Qwen配置更新失败: {e}")
        return None

def set_default_config(config_id, base_url="http://localhost:5001"):
    """设置配置为默认"""
    try:
        response = requests.post(
            f"{base_url}/api/ai-configs/{config_id}/set-default",
            timeout=10
        )
        
        if response.status_code == 200:
            print("🎯 已设置为默认配置")
            return True
        else:
            print(f"⚠️ 设置默认配置失败: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 设置默认配置失败: {e}")
        return False

def init_default_ai_config():
    """初始化默认AI配置 - 通过API调用"""
    
    base_url = "http://localhost:5001"
    
    # 等待Flask服务器启动
    if not wait_for_flask_server(base_url):
        print("⚠️ Flask服务器未就绪，跳过AI配置初始化")
        return False
    
    try:
        # 获取现有配置
        existing_configs = get_existing_configs(base_url)
        print(f"📋 发现现有配置: {len(existing_configs)} 个")
        
        # 查找是否已存在Qwen配置
        qwen_config = None
        for config in existing_configs:
            if config.get("config_name") == "Qwen":
                qwen_config = config
                break
        
        if qwen_config:
            # 更新现有Qwen配置
            config_id = qwen_config.get("id")
            print(f"✅ 发现现有 Qwen 配置 (ID: {config_id})")
            
            result = update_qwen_config(config_id, base_url)
            if result:
                # 设置为默认配置
                set_default_config(config_id, base_url)
                print(f"🎯 Qwen配置已更新并设为默认")
            else:
                print("⚠️ Qwen配置更新失败")
                return False
        else:
            # 创建新的Qwen配置
            print("🆕 创建新的 Qwen 配置...")
            result = create_qwen_config(base_url)
            if result:
                config_id = result.get("data", {}).get("id")
                if config_id:
                    # 设置为默认配置
                    set_default_config(config_id, base_url)
                    print(f"🎯 Qwen配置已创建并设为默认 (ID: {config_id})")
                else:
                    print("⚠️ 无法获取新创建配置的ID")
                    return False
            else:
                print("⚠️ Qwen配置创建失败")
                return False
        
        # 验证最终结果
        final_configs = get_existing_configs(base_url)
        default_config = None
        for config in final_configs:
            if config.get("is_default"):
                default_config = config
                break
        
        if default_config and default_config.get("config_name") == "Qwen":
            print(f"🎉 Qwen配置初始化成功！")
            print(f"   配置名称: {default_config.get('config_name')}")
            print(f"   模型: {default_config.get('model_name')}")
            print(f"   默认配置: {default_config.get('is_default')}")
            return True
        else:
            print("⚠️ Qwen配置未正确设置为默认")
            return False
            
    except Exception as e:
        print(f"❌ AI配置初始化失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 初始化默认AI配置...")
    success = init_default_ai_config()
    if success:
        print("🎉 默认AI配置初始化成功！")
        sys.exit(0)
    else:
        print("💥 默认AI配置初始化失败！")
        sys.exit(1)
