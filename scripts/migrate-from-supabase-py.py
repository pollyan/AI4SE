#!/usr/bin/env python3
"""
Supabase PostgreSQL到本地PostgreSQL数据迁移脚本

使用方法:
    python scripts/migrate-from-supabase-py.py
"""

import os
import sys
from sqlalchemy import create_engine, text, MetaData
from datetime import datetime

# Supabase连接信息
SUPABASE_URL = "postgresql://postgres.jzmqsuxphksbulrbhebp:Shunlian04@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

# 本地PostgreSQL连接信息 (Docker容器，host.docker.internal或localhost:5432)
# Docker默认无密码，使用trust认证
LOCAL_URL = "postgresql://intent_user:change_me_in_production@localhost:5432/intent_test"

def log(message, level="INFO"):
    """输出日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def migrate():
    """执行数据迁移"""
    log("========================================")
    log("数据库迁移：Supabase → 本地 PostgreSQL")
    log("========================================")
    
    try:
        # 1. 连接数据库
        log("连接 Supabase...")
        source_engine = create_engine(SUPABASE_URL, connect_args={"connect_timeout": 15})
        
        log("连接本地 PostgreSQL...")
        target_engine = create_engine(LOCAL_URL)
        
        # 测试连接
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log("✅ Supabase 连接成功")
        
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log("✅ 本地 PostgreSQL 连接成功")
        
        # 2. 核心表列表（只迁移这些表）
        core_tables = ['test_cases', 'execution_history', 'step_executions', 'templates']
        log(f"将迁移 {len(core_tables)} 个核心表: {', '.join(core_tables)}")
        
        # 3. 备份本地数据
        log("备份本地数据...")
        backup_dir = "./database_backups"
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/local_backup_before_migration_{timestamp}.sql"
        os.system(f"docker exec intent-test-db pg_dump -U intent_user intent_test > {backup_file}")
        log(f"✅ 本地数据已备份到: {backup_file}")
        
        # 4. 清空本地核心表
        log("清空本地表...")
        with target_engine.connect() as conn:
            # 禁用外键约束
            conn.execute(text("SET session_replication_role = 'replica';"))
            
            for table_name in reversed(core_tables):
                try:
                    conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                    log(f"  清空表: {table_name}")
                except Exception as e:
                    log(f"  跳过表 {table_name}: {e}", "WARNING")
            
            # 恢复外键约束
            conn.execute(text("SET session_replication_role = 'origin';"))
            conn.commit()
        
        log("✅ 本地表已准备好")
        
        # 5. 复制数据
        log("开始复制数据...")
        total_rows = 0
        
        for table_name in core_tables:
            # 从 Supabase 读取 (指定 public schema)
            with source_engine.connect() as source_conn:
                result = source_conn.execute(text(f'SELECT * FROM public."{table_name}"'))
                rows = result.fetchall()
                columns = result.keys()
            
            if not rows:
                log(f"  表 {table_name}: 无数据")
                continue
            
            # 写入本地
            column_list = ", ".join(columns)
            placeholders = ", ".join([f":{col}" for col in columns])
            insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
            
            with target_engine.connect() as target_conn:
                for row in rows:
                    row_dict = dict(zip(columns, row))
                    target_conn.execute(text(insert_sql), row_dict)
                target_conn.commit()
            
            log(f"  ✅ 表 {table_name}: {len(rows)} 条记录")
            total_rows += len(rows)
        
        log(f"✅ 数据复制完成，共 {total_rows} 条记录")
        
        # 6. 验证
        log("验证数据...")
        for table_name in core_tables:
            with source_engine.connect() as source_conn:
                source_count = source_conn.execute(
                    text(f'SELECT COUNT(*) FROM public."{table_name}"')
                ).scalar()
            
            with target_engine.connect() as target_conn:
                target_count = target_conn.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()
            
            if source_count == target_count:
                log(f"  ✅ {table_name}: {source_count} 条记录")
            else:
                log(f"  ⚠️  {table_name}: 源={source_count}, 本地={target_count}", "WARNING")
        
        log("========================================")
        log("🎉 迁移完成！")
        log("========================================")
        log(f"备份文件: {backup_file}")
        log("========================================")
        
        return True
        
    except Exception as e:
        log(f"❌ 迁移失败: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
