"""
pytest配置文件 - 设置Playwright和MidSceneJS集成
"""

import os
import pytest
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()


@pytest.fixture(scope="session")
def nodejs_midscene_server():
    """启动Node.js MidSceneJS服务器"""
    server_script = Path(__file__).parent.parent / "midscene_server.js"

    # 启动Node.js服务器
    process = subprocess.Popen(
        ["node", str(server_script)],
        env={
            **os.environ,
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", ""),
            "MIDSCENE_MODEL_NAME": os.getenv("MIDSCENE_MODEL_NAME", ""),
            "MIDSCENE_USE_QWEN_VL": os.getenv("MIDSCENE_USE_QWEN_VL", ""),
        },
    )

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
        "base_url": os.getenv(
            "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ),
        "timeout": int(os.getenv("TIMEOUT", "30000")),
    }


@pytest.fixture(scope="function")
def db_session():
    """
    创建测试数据库会话
    每个测试函数都会获得一个独立的数据库会话，测试结束后自动回滚
    """
    from web_gui.models import db
    from web_gui.app_enhanced import create_app
    
    # 创建测试应用
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    app = create_app(test_config=test_config)
    
    with app.app_context():
        # 启用外键约束（SQLite默认关闭）
        from sqlalchemy import event
        from sqlalchemy.engine import Engine
        
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        
        # 创建所有表
        db.create_all()
        
        yield db.session
        
        # 清理 - 回滚任何未提交的事务
        db.session.rollback()
        
        # 删除所有表（可选）
        db.drop_all()
