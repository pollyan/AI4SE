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
        self.database_url = self._get_database_url()
        self.is_production = self._is_production()

        # 如果是PostgreSQL，确保驱动可用
        if self.database_url.startswith(("postgresql://", "postgres://")):
            if not is_postgres_available():
                raise ImportError(
                    "❌ PostgreSQL驱动未安装！\n"
                    "请安装PostgreSQL驱动：pip install psycopg2-binary\n"
                    "或者：pip install psycopg2"
                )
        # SQLite是Python标准库，无需额外检查

    def _get_database_url(self) -> str:
        """获取数据库URL (支持PostgreSQL和SQLite)"""
        # 优先使用环境变量
        database_url = os.getenv("DATABASE_URL")

        if database_url:
            # 如果是SQLite (测试环境)，直接返回
            if database_url.startswith("sqlite://"):
                return database_url

            # 处理Heroku/Railway等平台的postgres://前缀
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)

            # 为Serverless环境添加连接参数
            if os.getenv("VERCEL") == "1" and "supabase.co" in database_url:
                # 添加Supabase Serverless优化参数
                if "?" not in database_url:
                    database_url += "?"
                else:
                    database_url += "&"
                database_url += "sslmode=require&connect_timeout=10&application_name=vercel-intent-test"

            return database_url

        # Supabase特定配置（仅生产环境）
        supabase_url = os.getenv("SUPABASE_DATABASE_URL")
        if supabase_url and self._is_production():
            return supabase_url

        # 本地开发环境默认使用SQLite
        if not self._is_production():
            # 使用项目根目录下的SQLite数据库
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, "instance", "intent_test_framework.db")
            return f"sqlite:///{db_path}"

        # 生产环境才使用PostgreSQL（如果没有其他配置）
        return "postgresql://postgres.jzmqsuxphksbulrbhebp:Shunlian04@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require&connect_timeout=15&application_name=prod"

    def _is_production(self) -> bool:
        """判断是否为生产环境"""
        return (
            os.getenv("VERCEL") == "1"
            or os.getenv("RAILWAY_ENVIRONMENT") == "production"
        )

    def _test_postgres_connection(self, url: str) -> bool:
        """测试PostgreSQL连接是否可用"""
        try:
            if not is_postgres_available():
                return False

            engine = create_engine(
                url, pool_pre_ping=True, connect_args={"connect_timeout": 5}
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def get_sqlalchemy_config(self) -> dict:
        """获取SQLAlchemy配置"""
        config = {
            "SQLALCHEMY_DATABASE_URI": self.database_url,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }

        if self.database_url.startswith("sqlite://"):
            # SQLite特定配置 (主要用于测试环境)
            # SQLite使用单线程模式，不支持连接池参数
            engine_options = {
                "pool_pre_ping": True,
                "pool_recycle": -1,
                "connect_args": {"check_same_thread": False},  # 允许多线程访问
            }
            config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

        elif self.database_url.startswith(("postgresql://", "postgres://")):
            # PostgreSQL特定配置
            engine_options = {
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            }

            # Serverless环境优化
            if self.is_production:
                engine_options.update(
                    {
                        "pool_size": 1,  # Serverless环境使用小连接池
                        "max_overflow": 0,  # 不允许溢出连接
                        "pool_timeout": 10,  # 快速超时
                        "connect_args": {
                            "connect_timeout": 10,
                            "sslmode": "require",
                            "application_name": "vercel-intent-test",
                        },
                    }
                )
            else:
                engine_options.update(
                    {
                        "pool_size": 5,
                        "pool_timeout": 60,
                        "max_overflow": 10,
                        "connect_args": {
                            "connect_timeout": 15,
                            "sslmode": "disable",
                            "application_name": "local-dev",
                        },
                    }
                )

            config.update({"SQLALCHEMY_ENGINE_OPTIONS": engine_options})
        else:
            # 默认PostgreSQL配置
            config.update(
                {
                    "SQLALCHEMY_ENGINE_OPTIONS": {
                        "pool_pre_ping": True,
                        "pool_recycle": 3600,
                        "pool_size": 10,
                        "pool_timeout": 30,
                        "max_overflow": 20,
                    }
                }
            )

        return config

    def get_migration_config(self) -> dict:
        """获取数据库迁移配置（仅支持PostgreSQL）"""
        return {
            "source_type": "postgresql",
            "target_type": "postgresql",
            "batch_size": 1000,
            "enable_foreign_keys": True,
        }

    def create_engine_with_config(self):
        """创建配置好的数据库引擎"""
        config = self.get_sqlalchemy_config()
        engine_options = config.get("SQLALCHEMY_ENGINE_OPTIONS", {})

        return create_engine(self.database_url, **engine_options)

    def get_connection_info(self) -> dict:
        """获取连接信息用于调试"""
        parsed = urlparse(self.database_url)

        is_sqlite = self.database_url.startswith("sqlite://")
        is_postgres = self.database_url.startswith(("postgresql://", "postgres://"))

        return {
            "scheme": parsed.scheme,
            "host": parsed.hostname
            or ("内存数据库" if ":memory:" in self.database_url else "本地文件"),
            "port": parsed.port,
            "database": parsed.path.lstrip("/") if parsed.path else "unknown",
            "is_postgres": is_postgres,
            "is_sqlite": is_sqlite,
            "is_production": self.is_production,
        }


# 全局配置实例
db_config = DatabaseConfig()


def print_database_info():
    """打印数据库连接信息"""
    info = db_config.get_connection_info()

    print("🗄️  数据库配置信息:")
    if info["is_postgres"]:
        print(f"   类型: PostgreSQL")
    elif info["is_sqlite"]:
        print(f"   类型: SQLite")
    else:
        print(f"   类型: 未知")

    print(f"   环境: {'生产环境' if info['is_production'] else '开发环境'}")
    print(f"   主机: {info['host']}")
    if info["port"]:
        print(f"   端口: {info['port']}")
    print(f"   数据库: {info['database']}")


def get_flask_config() -> dict:
    """获取Flask应用的数据库配置"""
    return db_config.get_sqlalchemy_config()


def validate_database_connection() -> bool:
    """验证数据库连接 (支持PostgreSQL和SQLite)"""
    try:
        engine = db_config.create_engine_with_config()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        db_type = (
            "SQLite" if db_config.database_url.startswith("sqlite://") else "PostgreSQL"
        )
        print(f"❌ {db_type}数据库连接失败: {e}")
        return False


if __name__ == "__main__":
    # 测试配置
    try:
        print_database_info()
        print(f"PostgreSQL驱动可用: {is_postgres_available()}")
        print(
            f"数据库连接: {'✅ 成功' if validate_database_connection() else '❌ 失败'}"
        )
    except ValueError as e:
        print(e)
