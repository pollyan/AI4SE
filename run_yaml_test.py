#!/usr/bin/env python3
"""
运行YAML格式的MidSceneJS测试脚本
支持通过Python调用MidSceneJS的YAML测试功能
"""
import os
import sys
import subprocess
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def check_dependencies():
    """检查依赖是否安装"""
    print("检查依赖...")
    
    # 检查Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"✓ Node.js版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("✗ 未找到Node.js，请先安装Node.js")
        return False
    
    # 检查npm包
    if not os.path.exists("node_modules"):
        print("✗ 未找到node_modules，请先运行: npm install")
        return False
    else:
        print("✓ Node.js依赖已安装")
    
    # 检查MidSceneJS CLI
    try:
        result = subprocess.run(["npx", "@midscene/cli", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ MidSceneJS CLI可用")
        else:
            print("! MidSceneJS CLI不可用，将尝试通过npx运行")
    except Exception as e:
        print(f"! MidSceneJS CLI检查失败: {e}")
    
    return True

def check_ai_config():
    """检查AI模型配置"""
    print("\n检查AI模型配置...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("MIDSCENE_MODEL_NAME", "gpt-4o")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    if not api_key:
        print("⚠️  未配置OPENAI_API_KEY")
        print("   请复制env.example为.env文件并配置API密钥")
        print("   或者设置环境变量:")
        print("   export OPENAI_API_KEY='your_api_key_here'")
        return False
    else:
        print(f"✓ API密钥已配置 (长度: {len(api_key)})")
        print(f"✓ 模型名称: {model_name}")
        print(f"✓ API地址: {base_url}")
    
    return True

def run_yaml_test(yaml_file, headed=False, keep_window=False):
    """运行YAML测试文件"""
    if not os.path.exists(yaml_file):
        print(f"✗ 测试文件不存在: {yaml_file}")
        return False
    
    print(f"\n运行YAML测试: {yaml_file}")
    
    # 构建命令
    cmd = ["npx", "midscene", yaml_file]
    
    if headed:
        cmd.append("--headed")
    
    if keep_window:
        cmd.append("--keep-window")
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        # 运行测试
        result = subprocess.run(cmd, text=True, capture_output=False)
        
        if result.returncode == 0:
            print(f"✓ 测试完成: {yaml_file}")
            return True
        else:
            print(f"✗ 测试失败: {yaml_file} (退出码: {result.returncode})")
            return False
            
    except Exception as e:
        print(f"✗ 运行测试时出错: {e}")
        return False

def main():
    """主函数"""
    print("=== MidSceneJS Python + YAML 测试运行器 ===\n")
    
    # 检查依赖
    if not check_dependencies():
        print("\n请先安装必要的依赖")
        return 1
    
    # 检查AI配置
    has_ai_config = check_ai_config()
    if not has_ai_config:
        print("\n⚠️  没有AI配置，某些AI功能可能无法使用")
        print("但仍可以运行基础的页面操作测试")
    
    # 准备测试文件
    yaml_files = [
        "examples/baidu_search.yaml"
    ]
    
    # 检查测试文件
    available_files = []
    for yaml_file in yaml_files:
        if os.path.exists(yaml_file):
            available_files.append(yaml_file)
        else:
            print(f"⚠️  测试文件不存在: {yaml_file}")
    
    if not available_files:
        print("✗ 没有找到可用的测试文件")
        return 1
    
    # 运行测试
    print(f"\n找到 {len(available_files)} 个测试文件")
    
    for yaml_file in available_files:
        print(f"\n{'='*50}")
        success = run_yaml_test(
            yaml_file, 
            headed=True,  # 显示浏览器窗口
            keep_window=False  # 测试完成后关闭窗口
        )
        
        if not success:
            print(f"测试失败: {yaml_file}")
            # 继续运行其他测试
    
    print(f"\n{'='*50}")
    print("所有测试运行完成")
    
    # 检查测试结果
    result_dir = Path("test_results")
    if result_dir.exists():
        result_files = list(result_dir.glob("*.json"))
        if result_files:
            print(f"\n测试结果文件:")
            for result_file in result_files:
                print(f"  - {result_file}")
    
    # 检查报告文件
    report_dir = Path("midscene_run/report")
    if report_dir.exists():
        report_files = list(report_dir.glob("*.html"))
        if report_files:
            print(f"\n测试报告文件:")
            for report_file in report_files:
                print(f"  - {report_file}")
                print(f"    在浏览器中打开: file://{report_file.absolute()}")

if __name__ == "__main__":
    sys.exit(main()) 