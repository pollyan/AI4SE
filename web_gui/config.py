"""
Web GUI配置文件
"""

import os
from pathlib import Path


# 基础配置
class Config:
    """基础配置类"""

    # Flask配置
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key-change-in-production"

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL") or "sqlite:///test_cases.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI服务配置
    MIDSCENE_SERVER_URL = (
        os.environ.get("MIDSCENE_SERVER_URL") or "http://localhost:3001"
    )

    # 文件路径配置
    BASE_DIR = Path(__file__).parent.parent
    SCREENSHOTS_DIR = BASE_DIR / "screenshots"
    LOGS_DIR = BASE_DIR / "web_gui" / "logs"

    # 确保目录存在
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)

    # 执行配置
    DEFAULT_TIMEOUT = 30000  # 默认超时时间（毫秒）
    MAX_CONCURRENT_EXECUTIONS = 3  # 最大并发执行数

    # AI配置
    AI_MODEL_NAME = os.environ.get("MIDSCENE_MODEL_NAME") or "qwen-vl-max-latest"
    AI_API_KEY = os.environ.get("OPENAI_API_KEY")
    AI_BASE_URL = (
        os.environ.get("OPENAI_BASE_URL")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    USE_QWEN_VL = os.environ.get("MIDSCENE_USE_QWEN_VL", "1") == "1"


class DevelopmentConfig(Config):
    """开发环境配置"""

    DEBUG = True


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG = False


class TestingConfig(Config):
    """测试环境配置"""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


# 配置字典
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
