"""共享配置管理"""
import os
from dotenv import load_dotenv

load_dotenv()

class SharedConfig:
    """共享配置基类"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
