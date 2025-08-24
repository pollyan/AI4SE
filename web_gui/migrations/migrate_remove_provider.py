#!/usr/bin/env python3
"""
通用数据库迁移脚本 - 移除provider字段
自动检测环境并执行相应的迁移策略
支持本地SQLite和生产PostgreSQL
"""

import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from web_gui.app_enhanced import create_app
from web_gui.models import db
from sqlalchemy import text


def migrate_remove_provider():
    """根据环境自动选择迁移策略移除provider字段"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 开始迁移：移除provider字段...")
            
            # 检查数据库类型
            db_url = app.config.get('DATABASE_URL', os.getenv('DATABASE_URL', ''))
            print(f"📊 数据库URL: {db_url.split('@')[0] if '@' in db_url else db_url[:50]}...")
            
            is_postgres = 'postgresql' in db_url
            is_sqlite = 'sqlite' in db_url
            
            if is_postgres:
                print("📊 检测到PostgreSQL数据库")
                migrate_postgresql()
            elif is_sqlite:
                print("📊 检测到SQLite数据库") 
                migrate_sqlite()
            else:
                raise Exception(f"不支持的数据库类型: {db_url}")
            
            # 验证迁移结果
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM requirements_ai_configs")).fetchone()
                print(f"✅ 迁移验证: 表中共有 {result[0]} 条配置记录")
            except Exception as e:
                print(f"⚠️  验证查询失败: {str(e)}")
            
            print("✅ provider字段移除完成")
            print("🎉 数据库迁移成功！")
            
        except Exception as e:
            print(f"❌ 迁移失败: {str(e)}")
            db.session.rollback()
            raise e


def migrate_postgresql():
    """PostgreSQL迁移策略"""
    print("🔧 执行PostgreSQL迁移...")
    
    sql_commands = [
        "ALTER TABLE requirements_ai_configs DROP COLUMN IF EXISTS provider;"
    ]
    
    for i, sql in enumerate(sql_commands):
        try:
            print(f"🔧 执行命令 {i+1}: {sql}")
            db.session.execute(text(sql))
            db.session.commit()
            print(f"✅ 命令 {i+1} 执行成功")
        except Exception as e:
            if "does not exist" in str(e).lower():
                print(f"ℹ️  字段已不存在，跳过: {str(e)}")
                continue
            else:
                raise e


def migrate_sqlite():
    """SQLite迁移策略"""
    print("🔧 执行SQLite迁移...")
    
    sql_commands = [
        """CREATE TABLE requirements_ai_configs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_name VARCHAR(255) NOT NULL,
            api_key TEXT NOT NULL,
            base_url VARCHAR(500) NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at DATETIME DEFAULT (datetime('now')),
            updated_at DATETIME DEFAULT (datetime('now'))
        );""",
        """INSERT INTO requirements_ai_configs_new 
           (id, config_name, api_key, base_url, model_name, is_default, is_active, created_at, updated_at)
           SELECT id, config_name, api_key, base_url, model_name, is_default, is_active, created_at, updated_at
           FROM requirements_ai_configs;""",
        "DROP TABLE requirements_ai_configs;",
        "ALTER TABLE requirements_ai_configs_new RENAME TO requirements_ai_configs;"
    ]
    
    for i, sql in enumerate(sql_commands):
        try:
            print(f"🔧 执行命令 {i+1}/{len(sql_commands)}: {sql[:50]}...")
            db.session.execute(text(sql))
            db.session.commit()
            print(f"✅ 命令 {i+1} 执行成功")
        except Exception as e:
            if "no such table" in str(e).lower() and "requirements_ai_configs" in sql:
                print("ℹ️  表可能已经是新结构，跳过...")
                continue
            else:
                raise e


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 通用数据库迁移脚本")
    print("移除AI配置表provider字段")
    print("=" * 60)
    
    # 显示当前环境信息
    db_url = os.getenv('DATABASE_URL', '')
    if 'postgresql' in db_url:
        print("🔍 检测到PostgreSQL环境")
        print("⚠️  将修改生产数据库结构，请确保已备份！")
    elif 'sqlite' in db_url:
        print("🔍 检测到SQLite环境") 
        print("ℹ️  本地开发环境，安全操作")
    else:
        print("❓ 未检测到明确的数据库类型")
    
    print(f"📊 数据库: {db_url.split('@')[0] if '@' in db_url else db_url[:50]}...")
    print()
    
    confirm = input("确认要继续迁移吗？(输入 'yes' 继续): ")
    if confirm.lower() != "yes":
        print("❌ 操作已取消")
        sys.exit(0)
    
    try:
        migrate_remove_provider()
    except Exception as e:
        print(f"💥 迁移失败: {str(e)}")
        sys.exit(1)
    
    print("🏆 数据库迁移成功完成！")
    print()
    print("📝 重要提醒：")
    print("- 本地和线上是两套数据库")
    print("- 修改逻辑时需要考虑两边环境")
    print("- 生产环境变更需要谨慎操作")