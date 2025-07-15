"""
数据库配置管理器
仅支持PostgreSQL数据库 (本地开发和生产环境都使用PostgreSQL)
"""

import os
from urllib.parse import urlparse
from sqlalchemy import create_engine, text


def is_postgres_available() -> bool:
    """检查PostgreSQL是否可用"""
    try:
        import psycopg2
        return True
    except ImportError:
        return False


class DatabaseConfig:
    """数据库配置管理器"""
    
    def __init__(self):
        # 确保PostgreSQL驱动可用
        if not is_postgres_available():
            raise ImportError(
                "❌ PostgreSQL驱动未安装！\n"
                "请安装PostgreSQL驱动：pip install psycopg2-binary\n"
                "或者：pip install psycopg2"
            )
        
        self.database_url = self._get_database_url()
        self.is_production = self._is_production()
    
    def _get_database_url(self) -> str:
        """获取PostgreSQL数据库URL"""
        # 优先使用环境变量
        database_url = os.getenv('DATABASE_URL')

        if database_url:
            # 处理Heroku/Railway等平台的postgres://前缀
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)

            # 为Serverless环境添加连接参数
            if os.getenv('VERCEL') == '1' and 'supabase.co' in database_url:
                # 添加Supabase Serverless优化参数
                if '?' not in database_url:
                    database_url += '?'
                else:
                    database_url += '&'
                database_url += 'sslmode=require&connect_timeout=10&application_name=vercel-intent-test'

            return database_url

        # Supabase特定配置
        supabase_url = os.getenv('SUPABASE_DATABASE_URL')
        if supabase_url:
            return supabase_url

        # 如果没有配置PostgreSQL，抛出错误
        raise ValueError(
            "❌ 未找到PostgreSQL数据库配置！\n"
            "请设置以下环境变量之一：\n"
            "  - DATABASE_URL=postgresql://user:password@host:port/dbname\n"
            "  - SUPABASE_DATABASE_URL=postgresql://user:password@host:port/dbname\n"
            "本系统仅支持PostgreSQL数据库。"
        )
    
    def _is_production(self) -> bool:
        """判断是否为生产环境"""
        return os.getenv('VERCEL') == '1' or os.getenv('RAILWAY_ENVIRONMENT') == 'production'
    
    def get_sqlalchemy_config(self) -> dict:
        """获取SQLAlchemy配置（仅支持PostgreSQL）"""
        # PostgreSQL特定配置
        engine_options = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
        }

        # Serverless环境优化
        if self.is_production:
            engine_options.update({
                'pool_size': 1,  # Serverless环境使用小连接池
                'max_overflow': 0,  # 不允许溢出连接
                'pool_timeout': 10,  # 快速超时
                'connect_args': {
                    'connect_timeout': 10,
                    'sslmode': 'require',
                    'application_name': 'vercel-intent-test'
                }
            })
        else:
            engine_options.update({
                'pool_size': 10,
                'pool_timeout': 30,
                'max_overflow': 20,
            })

        return {
            'SQLALCHEMY_DATABASE_URI': self.database_url,
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
            'SQLALCHEMY_ENGINE_OPTIONS': engine_options
        }
    
    def get_migration_config(self) -> dict:
        """获取数据库迁移配置（仅支持PostgreSQL）"""
        return {
            'source_type': 'postgresql',
            'target_type': 'postgresql',
            'batch_size': 1000,
            'enable_foreign_keys': True,
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
            'host': parsed.hostname or 'unknown',
            'port': parsed.port,
            'database': parsed.path.lstrip('/') if parsed.path else 'unknown',
            'is_postgres': True,  # 系统仅支持PostgreSQL
            'is_production': self.is_production,
        }


# 全局配置实例
db_config = DatabaseConfig()


def print_database_info():
    """打印数据库连接信息"""
    info = db_config.get_connection_info()
    
    print("🗄️  数据库配置信息:")
    print(f"   类型: PostgreSQL")
    print(f"   环境: {'生产环境' if info['is_production'] else '开发环境'}")
    print(f"   主机: {info['host']}")
    if info['port']:
        print(f"   端口: {info['port']}")
    print(f"   数据库: {info['database']}")


def get_flask_config() -> dict:
    """获取Flask应用的数据库配置"""
    return db_config.get_sqlalchemy_config()


def validate_database_connection() -> bool:
    """验证PostgreSQL数据库连接"""
    try:
        engine = db_config.create_engine_with_config()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        print(f"❌ PostgreSQL数据库连接失败: {e}")
        return False


if __name__ == '__main__':
    # 测试配置
    try:
        print_database_info()
        print(f"PostgreSQL驱动可用: {is_postgres_available()}")
        print(f"数据库连接: {'✅ 成功' if validate_database_connection() else '❌ 失败'}")
    except ValueError as e:
        print(e)
