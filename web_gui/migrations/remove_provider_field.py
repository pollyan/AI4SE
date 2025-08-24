#!/usr/bin/env python3
"""
移除AI配置表provider字段的数据库迁移脚本
支持Story 1.4 AI配置管理简化
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


def remove_provider_field():
    """移除AI配置表的provider字段"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 开始移除provider字段...")
            
            # 检查数据库类型
            db_url = app.config.get('DATABASE_URL', os.getenv('DATABASE_URL', ''))
            print(f"📊 数据库URL: {db_url[:50]}...")
            is_postgres = 'postgresql' in db_url
            is_sqlite = 'sqlite' in db_url
            
            if is_postgres:
                print("📊 检测到PostgreSQL数据库")
                # PostgreSQL语法
                sql_commands = [
                    "ALTER TABLE requirements_ai_configs DROP COLUMN IF EXISTS provider;"
                ]
            elif is_sqlite:
                print("📊 检测到SQLite数据库") 
                # SQLite不支持DROP COLUMN，需要重建表
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
            else:
                raise Exception(f"不支持的数据库类型: {db_url}")
            
            # 执行SQL命令
            for i, sql in enumerate(sql_commands):
                try:
                    print(f"🔧 执行命令 {i+1}/{len(sql_commands)}: {sql[:50]}...")
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"✅ 命令 {i+1} 执行成功")
                except Exception as e:
                    print(f"⚠️  命令 {i+1} 执行失败: {str(e)}")
                    if "no such column" in str(e).lower():
                        print("ℹ️  字段可能已经不存在，继续执行...")
                        continue
                    else:
                        raise e
            
            print("✅ provider字段移除完成")
            print("🎉 数据库迁移成功！")
            
        except Exception as e:
            print(f"❌ 移除provider字段时出错: {str(e)}")
            db.session.rollback()
            raise e


if __name__ == "__main__":
    print("=" * 60)
    print("移除AI配置表provider字段的数据库迁移脚本")
    print("=" * 60)
    
    try:
        remove_provider_field()
    except Exception as e:
        print(f"💥 迁移失败: {str(e)}")
        sys.exit(1)
    
    print("🏆 数据库迁移成功完成！")