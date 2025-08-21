"""
Settings - 应用配置定义
使用数据类和环境变量的统一配置管理
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """数据库配置"""
    uri: str
    track_modifications: bool = False
    engine_options: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # 为PostgreSQL设置连接池配置
        if self.uri.startswith('postgresql') and self.engine_options is None:
            self.engine_options = {
                'pool_pre_ping': True,
                'pool_recycle': 300,
                'pool_timeout': 20,
                'max_overflow': 0
            }

@dataclass
class AIConfig:
    """AI服务配置"""
    model_name: str = "qwen-vl-max-latest"
    api_key: Optional[str] = None
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    use_qwen_vl: bool = True
    server_url: str = "http://localhost:3001"
    
    def is_available(self) -> bool:
        """检查AI配置是否可用"""
        return self.api_key is not None

@dataclass
class PathConfig:
    """路径配置"""
    base_dir: Path
    screenshots_dir: Path
    logs_dir: Path
    
    def __post_init__(self):
        # 确保目录存在
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

@dataclass
class ExecutionConfig:
    """执行配置"""
    default_timeout: int = 30000  # 默认超时时间（毫秒）
    max_concurrent_executions: int = 3  # 最大并发执行数
    page_timeout: int = 30000
    action_timeout: int = 30000 
    navigation_timeout: int = 30000

@dataclass 
class SecurityConfig:
    """安全配置"""
    secret_key: str
    debug: bool = False
    testing: bool = False
    
    def __post_init__(self):
        if self.debug and self.secret_key == 'dev-secret-key-change-in-production':
            logger.warning("⚠️  使用默认密钥，请在生产环境中修改 SECRET_KEY")

@dataclass
class AppConfig:
    """应用主配置"""
    security: SecurityConfig
    database: DatabaseConfig
    ai: AIConfig
    paths: PathConfig
    execution: ExecutionConfig
    
    # Flask特定配置
    flask_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # 生成Flask配置字典
        self.flask_config = self._generate_flask_config()
    
    def _generate_flask_config(self) -> Dict[str, Any]:
        """生成Flask配置字典"""
        config = {
            # 安全配置
            'SECRET_KEY': self.security.secret_key,
            'DEBUG': self.security.debug,
            'TESTING': self.security.testing,
            
            # 数据库配置
            'SQLALCHEMY_DATABASE_URI': self.database.uri,
            'SQLALCHEMY_TRACK_MODIFICATIONS': self.database.track_modifications,
            
            # AI服务配置
            'MIDSCENE_SERVER_URL': self.ai.server_url,
            'AI_MODEL_NAME': self.ai.model_name,
            'AI_API_KEY': self.ai.api_key,
            'AI_BASE_URL': self.ai.base_url,
            'USE_QWEN_VL': self.ai.use_qwen_vl,
            
            # 执行配置
            'DEFAULT_TIMEOUT': self.execution.default_timeout,
            'MAX_CONCURRENT_EXECUTIONS': self.execution.max_concurrent_executions,
            
            # 路径配置
            'SCREENSHOTS_DIR': str(self.paths.screenshots_dir),
            'LOGS_DIR': str(self.paths.logs_dir),
        }
        
        # 添加数据库引擎选项
        if self.database.engine_options:
            config['SQLALCHEMY_ENGINE_OPTIONS'] = self.database.engine_options
        
        return config
    
    @classmethod
    def from_env(cls, env_name: str = None) -> 'AppConfig':
        """从环境变量创建配置"""
        if env_name is None:
            env_name = os.getenv('FLASK_ENV', 'development')
        
        # 基础路径配置
        base_dir = Path(__file__).parent.parent.parent
        paths = PathConfig(
            base_dir=base_dir,
            screenshots_dir=base_dir / "web_gui" / "static" / "screenshots",
            logs_dir=base_dir / "logs"
        )
        
        # 安全配置
        security = SecurityConfig(
            secret_key=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
            debug=env_name == 'development',
            testing=env_name == 'testing'
        )
        
        # 数据库配置
        if env_name == 'testing':
            db_uri = "sqlite:///:memory:"
        else:
            db_uri = os.getenv('DATABASE_URL', 'sqlite:///test_cases.db')
        
        database = DatabaseConfig(
            uri=db_uri,
            track_modifications=False
        )
        
        # AI配置
        ai = AIConfig(
            model_name=os.getenv('MIDSCENE_MODEL_NAME', 'qwen-vl-max-latest'),
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1'),
            use_qwen_vl=os.getenv('MIDSCENE_USE_QWEN_VL', '1') == '1',
            server_url=os.getenv('MIDSCENE_SERVER_URL', 'http://localhost:3001')
        )
        
        # 执行配置
        execution = ExecutionConfig(
            default_timeout=int(os.getenv('DEFAULT_TIMEOUT', '30000')),
            max_concurrent_executions=int(os.getenv('MAX_CONCURRENT_EXECUTIONS', '3')),
            page_timeout=int(os.getenv('PAGE_TIMEOUT', '30000')),
            action_timeout=int(os.getenv('ACTION_TIMEOUT', '30000')),
            navigation_timeout=int(os.getenv('NAVIGATION_TIMEOUT', '30000'))
        )
        
        return cls(
            security=security,
            database=database,
            ai=ai,
            paths=paths,
            execution=execution
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'security': {
                'debug': self.security.debug,
                'testing': self.security.testing,
                'secret_key_set': bool(self.security.secret_key and 
                                     self.security.secret_key != 'dev-secret-key-change-in-production')
            },
            'database': {
                'uri_type': 'postgresql' if self.database.uri.startswith('postgresql') else 'sqlite',
                'track_modifications': self.database.track_modifications,
                'has_engine_options': bool(self.database.engine_options)
            },
            'ai': {
                'model_name': self.ai.model_name,
                'has_api_key': bool(self.ai.api_key),
                'base_url': self.ai.base_url,
                'use_qwen_vl': self.ai.use_qwen_vl,
                'server_url': self.ai.server_url,
                'is_available': self.ai.is_available()
            },
            'execution': {
                'default_timeout': self.execution.default_timeout,
                'max_concurrent_executions': self.execution.max_concurrent_executions
            },
            'paths': {
                'base_dir': str(self.paths.base_dir),
                'screenshots_dir': str(self.paths.screenshots_dir),
                'logs_dir': str(self.paths.logs_dir)
            }
        }

# 配置实例管理
_config_instance: Optional[AppConfig] = None

def get_config(env_name: str = None, force_reload: bool = False) -> AppConfig:
    """
    获取配置实例（单例模式）
    
    Args:
        env_name: 环境名称
        force_reload: 是否强制重新加载
    
    Returns:
        配置实例
    """
    global _config_instance
    
    if _config_instance is None or force_reload:
        _config_instance = AppConfig.from_env(env_name)
        logger.info(f"配置已加载: {env_name or 'default'}")
    
    return _config_instance

def reload_config(env_name: str = None) -> AppConfig:
    """重新加载配置"""
    return get_config(env_name, force_reload=True)
