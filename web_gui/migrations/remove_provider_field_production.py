#!/usr/bin/env python3
"""
生产环境PostgreSQL数据库迁移脚本 - 移除provider字段
注意：这个脚本专门用于生产环境的PostgreSQL数据库
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


def remove_provider_field_production():
    """在生产环境PostgreSQL数据库中移除provider字段"""
    
    # 强制使用生产环境配置
    os.environ['DATABASE_URL'] = input("请输入生产环境PostgreSQL数据库URL: ")
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 开始在生产环境移除provider字段...")
            
            # 检查数据库类型
            db_url = app.config.get('DATABASE_URL', os.getenv('DATABASE_URL', ''))
            print(f"📊 数据库URL: {db_url.split('@')[0]}@***")
            
            if 'postgresql' not in db_url:
                raise Exception("❌ 这个脚本只能用于PostgreSQL数据库！")
            
            print("📊 确认为PostgreSQL生产数据库")
            
            # PostgreSQL移除字段的SQL命令
            sql_commands = [
                "ALTER TABLE requirements_ai_configs DROP COLUMN IF EXISTS provider;",
                "SELECT COUNT(*) as config_count FROM requirements_ai_configs;"
            ]
            
            # 执行SQL命令
            for i, sql in enumerate(sql_commands[:-1]):  # 最后一个是查询，单独处理
                try:
                    print(f"🔧 执行命令 {i+1}: {sql}")
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"✅ 命令 {i+1} 执行成功")
                except Exception as e:
                    if "does not exist" in str(e).lower():
                        print(f"ℹ️  字段可能已经不存在: {str(e)}")
                        continue
                    else:
                        raise e
            
            # 验证数据
            result = db.session.execute(text(sql_commands[-1])).fetchone()
            print(f"✅ 验证完成: 表中共有 {result[0]} 条配置记录")
            
            print("✅ provider字段移除完成")
            print("🎉 生产环境数据库迁移成功！")
            
        except Exception as e:
            print(f"❌ 移除provider字段时出错: {str(e)}")
            db.session.rollback()
            raise e


if __name__ == "__main__":
    print("=" * 60)
    print("⚠️  生产环境PostgreSQL数据库迁移脚本")
    print("移除AI配置表provider字段")
    print("=" * 60)
    print()
    print("⚠️  警告：这将修改生产数据库结构！")
    print("请确保：")
    print("1. 已备份生产数据库")
    print("2. 在低流量时间执行")
    print("3. 有回滚计划")
    print()
    
    confirm = input("确认要继续吗？(输入 'YES' 继续): ")
    if confirm != "YES":
        print("❌ 操作已取消")
        sys.exit(0)
    
    try:
        remove_provider_field_production()
    except Exception as e:
        print(f"💥 迁移失败: {str(e)}")
        sys.exit(1)
    
    print("🏆 生产环境数据库迁移成功完成！")