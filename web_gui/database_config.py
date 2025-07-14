"""
数据库配置管理器
支持SQLite (本地开发) 和 PostgreSQL (生产环境/Supabase)
"""

import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool


class DatabaseConfig:
    """数据库配置管理器"""
    
    def __init__(self):
        self.database_url = self._get_database_url()
        self.is_postgres = self._is_postgres()
        self.is_production = self._is_production()
    
    def _get_database_url(self) -> str:
        """获取数据库URL"""
        # 优先使用环境变量
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # 处理Heroku/Railway等平台的postgres://前缀
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            return database_url
        
        # Supabase特定配置
        supabase_url = os.getenv('SUPABASE_DATABASE_URL')
        if supabase_url:
            return supabase_url
        
        # 本地开发环境默认使用SQLite
        instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
        os.makedirs(instance_path, exist_ok=True)
        db_path = os.path.join(instance_path, 'gui_test_cases.db')
        return f'sqlite:///{db_path}'
    
    def _is_postgres(self) -> bool:
        """判断是否为PostgreSQL数据库"""
        return self.database_url.startswith(('postgresql://', 'postgres://'))
    
    def _is_production(self) -> bool:
        """判断是否为生产环境"""
        return os.getenv('VERCEL') == '1' or os.getenv('RAILWAY_ENVIRONMENT') or self.is_postgres
    
    def get_sqlalchemy_config(self) -> dict:
        """获取SQLAlchemy配置"""
        config = {
            'SQLALCHEMY_DATABASE_URI': self.database_url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        }
        
        if self.is_postgres:
            # PostgreSQL特定配置
            config.update({
                'SQLALCHEMY_ENGINE_OPTIONS': {
                    'pool_size': 10,
                    'pool_timeout': 30,
                    'pool_recycle': 3600,
                    'max_overflow': 20,
                    'pool_pre_ping': True,
                }
            })
        else:
            # SQLite特定配置
            config.update({
                'SQLALCHEMY_ENGINE_OPTIONS': {
                    'poolclass': StaticPool,
                    'pool_pre_ping': True,
                    'connect_args': {
                        'check_same_thread': False,
                        'timeout': 30
                    }
                }
            })
        
        return config
    
    def get_migration_config(self) -> dict:
        """获取数据库迁移配置"""
        return {
            'source_type': 'sqlite' if not self.is_postgres else 'postgresql',
            'target_type': 'postgresql' if self.is_postgres else 'sqlite',
            'batch_size': 1000,
            'enable_foreign_keys': self.is_postgres,
        }
    
    def create_engine_with_config(self):
        """创建配置好的数据库引擎"""
        config = self.get_sqlalchemy_config()
        engine_options = config.get('SQLALCHEMY_ENGINE_OPTIONS', {})
        
        return create_engine(
            self.database_url,
            **engine_options
        )
    
    def get_connection_info(self) -> dict:
        """获取连接信息用于调试"""
        parsed = urlparse(self.database_url)
        
        return {
            'scheme': parsed.scheme,
            'host': parsed.hostname or 'local',
            'port': parsed.port,
            'database': parsed.path.lstrip('/') if parsed.path else 'local',
            'is_postgres': self.is_postgres,
            'is_production': self.is_production,
        }


# 全局配置实例
db_config = DatabaseConfig()


def print_database_info():
    """打印数据库连接信息"""
    info = db_config.get_connection_info()
    
    print("🗄️  数据库配置信息:")
    print(f"   类型: {'PostgreSQL' if info['is_postgres'] else 'SQLite'}")
    print(f"   环境: {'生产环境' if info['is_production'] else '开发环境'}")
    print(f"   主机: {info['host']}")
    if info['port']:
        print(f"   端口: {info['port']}")
    print(f"   数据库: {info['database']}")


def get_flask_config() -> dict:
    """获取Flask应用的数据库配置"""
    return db_config.get_sqlalchemy_config()


def is_postgres_available() -> bool:
    """检查PostgreSQL是否可用"""
    try:
        import psycopg2
        return True
    except ImportError:
        return False


def validate_database_connection() -> bool:
    """验证数据库连接"""
    try:
        engine = db_config.create_engine_with_config()
        with engine.connect() as conn:
            if db_config.is_postgres:
                result = conn.execute(text("SELECT 1"))
            else:
                result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


if __name__ == '__main__':
    # 测试配置
    print_database_info()
    print(f"PostgreSQL可用: {is_postgres_available()}")
    print(f"数据库连接: {'✅ 成功' if validate_database_connection() else '❌ 失败'}")
