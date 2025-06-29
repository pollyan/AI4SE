#!/usr/bin/env python3
"""
Python + MidSceneJS 环境设置脚本
自动安装和配置所需的依赖
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description, check=True):
    """运行命令并处理错误"""
    print(f"\n{description}...")
    print(f"执行: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    
    try:
        if isinstance(cmd, str):
            result = subprocess.run(cmd, shell=True, check=check, text=True)
        else:
            result = subprocess.run(cmd, check=check, text=True)
        
        if result.returncode == 0:
            print(f"✓ {description} 完成")
            return True
        else:
            print(f"✗ {description} 失败 (退出码: {result.returncode})")
            return False
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} 失败: {e}")
        return False
    except FileNotFoundError as e:
        print(f"✗ 命令未找到: {e}")
        return False

def check_prerequisites():
    """检查先决条件"""
    print("=== 检查先决条件 ===")
    
    # 检查Python版本
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("✗ Python版本过低，需要Python 3.8或更高版本")
        return False
    else:
        print("✓ Python版本满足要求")
    
    # 检查Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        print(f"✓ Node.js版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("✗ 未找到Node.js")
        print("请先安装Node.js: https://nodejs.org/")
        return False
    
    # 检查npm
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True)
        print(f"✓ npm版本: {result.stdout.strip()}")
    except FileNotFoundError:
        print("✗ 未找到npm")
        return False
    
    return True

def install_python_dependencies():
    """安装Python依赖"""
    print("\n=== 安装Python依赖 ===")
    
    # 检查是否有pip
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      check=True, capture_output=True)
    except subprocess.CalledProcessError:
        print("✗ pip未安装或不可用")
        return False
    
    # 升级pip
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                "升级pip", check=False)
    
    # 安装依赖
    if os.path.exists("requirements.txt"):
        return run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                          "安装Python依赖")
    else:
        print("✗ requirements.txt文件不存在")
        return False

def install_nodejs_dependencies():
    """安装Node.js依赖"""
    print("\n=== 安装Node.js依赖 ===")
    
    # 检查package.json
    if not os.path.exists("package.json"):
        print("✗ package.json文件不存在")
        return False
    
    # 安装npm依赖
    return run_command(["npm", "install"], "安装Node.js依赖")

def install_playwright_browsers():
    """安装Playwright浏览器"""
    print("\n=== 安装Playwright浏览器 ===")
    
    return run_command([sys.executable, "-m", "playwright", "install", "chromium"], 
                      "安装Chromium浏览器")

def setup_directories():
    """创建必要的目录"""
    print("\n=== 创建目录结构 ===")
    
    directories = [
        "screenshots",
        "test_results", 
        "logs",
        "examples"
    ]
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"✓ 创建目录: {directory}")
        else:
            print(f"✓ 目录已存在: {directory}")
    
    return True

def setup_environment_file():
    """设置环境配置文件"""
    print("\n=== 设置环境配置 ===")
    
    env_example = "env.example"
    env_file = ".env"
    
    if os.path.exists(env_example) and not os.path.exists(env_file):
        try:
            shutil.copy(env_example, env_file)
            print(f"✓ 已创建环境配置文件: {env_file}")
            print("⚠️  请编辑.env文件并配置您的AI模型API密钥")
            return True
        except Exception as e:
            print(f"✗ 创建环境配置文件失败: {e}")
            return False
    elif os.path.exists(env_file):
        print(f"✓ 环境配置文件已存在: {env_file}")
        return True
    else:
        print(f"⚠️  未找到环境配置示例文件: {env_example}")
        return False

def verify_installation():
    """验证安装"""
    print("\n=== 验证安装 ===")
    
    # 验证Python包
    try:
        import playwright
        print("✓ Playwright已安装")
    except ImportError:
        print("✗ Playwright未正确安装")
        return False
    
    try:
        import pytest
        print("✓ pytest已安装")
    except ImportError:
        print("✗ pytest未正确安装")
        return False
    
    # 验证Node.js包
    if os.path.exists("node_modules/@midscene/web"):
        print("✓ MidSceneJS已安装")
    else:
        print("✗ MidSceneJS未正确安装")
        return False
    
    return True

def print_next_steps():
    """打印后续步骤"""
    print("\n" + "="*60)
    print("🎉 安装完成！")
    print("="*60)
    
    print("\n📝 后续步骤:")
    print("1. 配置AI模型API密钥:")
    print("   - 编辑 .env 文件")
    print("   - 配置 OPENAI_API_KEY 或其他AI模型的API密钥")
    
    print("\n2. 运行测试:")
    print("   - Python测试: pytest tests/ -v -s")
    print("   - YAML测试: python run_yaml_test.py")
    
    print("\n3. 查看示例:")
    print("   - Python示例: tests/test_baidu_search.py")
    print("   - YAML示例: examples/baidu_search.yaml")
    
    print("\n4. 参考文档:")
    print("   - MidSceneJS官网: https://midscenejs.com")
    print("   - Playwright文档: https://playwright.dev/python/")
    
    print("\n💡 提示:")
    print("   - 第一次运行可能需要下载AI模型")
    print("   - 确保网络连接正常")
    print("   - 查看screenshots/目录获取测试截图")

def main():
    """主函数"""
    print("🚀 Python + MidSceneJS 环境设置")
    print("="*60)
    
    # 检查先决条件
    if not check_prerequisites():
        print("\n❌ 先决条件检查失败，请解决上述问题后重试")
        return 1
    
    # 安装依赖
    steps = [
        (install_python_dependencies, "Python依赖安装"),
        (install_nodejs_dependencies, "Node.js依赖安装"), 
        (install_playwright_browsers, "Playwright浏览器安装"),
        (setup_directories, "目录结构创建"),
        (setup_environment_file, "环境配置设置"),
        (verify_installation, "安装验证")
    ]
    
    failed_steps = []
    
    for step_func, step_name in steps:
        try:
            success = step_func()
            if not success:
                failed_steps.append(step_name)
        except Exception as e:
            print(f"✗ {step_name} 过程中发生错误: {e}")
            failed_steps.append(step_name)
    
    # 结果总结
    if failed_steps:
        print(f"\n⚠️  以下步骤失败: {', '.join(failed_steps)}")
        print("请手动解决这些问题")
        return 1
    else:
        print_next_steps()
        return 0

if __name__ == "__main__":
    sys.exit(main()) 