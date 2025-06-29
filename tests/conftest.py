"""
pytest配置文件 - 设置Playwright和MidSceneJS集成
"""
import os
import pytest
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

@pytest.fixture(scope="session")
def nodejs_midscene_server():
    """启动Node.js MidSceneJS服务器"""
    server_script = Path(__file__).parent.parent / "midscene_server.js"
    
    # 启动Node.js服务器
    process = subprocess.Popen([
        "node", str(server_script)
    ], env={
        **os.environ,
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", ""),
        "MIDSCENE_MODEL_NAME": os.getenv("MIDSCENE_MODEL_NAME", ""),
        "MIDSCENE_USE_QWEN_VL": os.getenv("MIDSCENE_USE_QWEN_VL", "")
    })
    
    # 等待服务器启动
    import time
    time.sleep(2)
    
    yield "http://localhost:3001"
    
    # 清理
    process.terminate()
    process.wait()

@pytest.fixture
def midscene_config():
    """MidSceneJS配置"""
    return {
        "model_name": os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        "timeout": int(os.getenv("TIMEOUT", "30000"))
    } 