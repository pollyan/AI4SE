#!/usr/bin/env python3
"""
SQLite到Supabase PostgreSQL数据迁移脚本

使用方法:
    python scripts/migrate_to_supabase.py --source sqlite:///path/to/db.db --target postgresql://...
    python scripts/migrate_to_supabase.py --auto  # 自动检测配置
"""

import os
import sys
import argparse
import json
from datetime import datetime
from typing import Dict, List, Any
import sqlite3
import psycopg2
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_gui.database_config import DatabaseConfig


class DatabaseMigrator:
    """数据库迁移器"""
    
    def __init__(self, source_url: str, target_url: str):
        self.source_url = source_url
        self.target_url = target_url
        self.source_engine = create_engine(source_url)
        self.target_engine = create_engine(target_url)
        self.migration_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """记录迁移日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        print(log_entry)
        self.migration_log.append(log_entry)
    
    def validate_connections(self) -> bool:
        """验证数据库连接"""
        try:
            # 测试源数据库连接
            with self.source_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.log("✅ 源数据库连接成功")
            
            # 测试目标数据库连接
            with self.target_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.log("✅ 目标数据库连接成功")
            
            return True
        except Exception as e:
            self.log(f"❌ 数据库连接失败: {e}", "ERROR")
            return False
    
    def get_table_schema(self, engine) -> Dict[str, Any]:
        """获取表结构"""
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        schema = {}
        for table_name, table in metadata.tables.items():
            schema[table_name] = {
                'columns': [
                    {
                        'name': col.name,
                        'type': str(col.type),
                        'nullable': col.nullable,
                        'primary_key': col.primary_key,
                        'foreign_keys': [str(fk) for fk in col.foreign_keys]
                    }
                    for col in table.columns
                ],
                'indexes': [str(idx) for idx in table.indexes],
                'foreign_keys': [str(fk) for fk in table.foreign_key_constraints]
            }
        
        return schema
    
    def create_postgresql_schema(self) -> bool:
        """在PostgreSQL中创建表结构"""
        try:
            # PostgreSQL建表语句
            create_tables_sql = """
            -- 测试用例表
            CREATE TABLE IF NOT EXISTS test_cases (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                steps TEXT NOT NULL,
                tags VARCHAR(500),
                category VARCHAR(100),
                priority INTEGER DEFAULT 3,
                created_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            );
            
            -- 执行历史表
            CREATE TABLE IF NOT EXISTS execution_history (
                id SERIAL PRIMARY KEY,
                execution_id VARCHAR(50) UNIQUE NOT NULL,
                test_case_id INTEGER NOT NULL,
                status VARCHAR(50) NOT NULL,
                mode VARCHAR(20) DEFAULT 'normal',
                browser VARCHAR(50) DEFAULT 'chrome',
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration INTEGER,
                steps_total INTEGER,
                steps_passed INTEGER,
                steps_failed INTEGER,
                result_summary TEXT,
                screenshots_path TEXT,
                logs_path TEXT,
                error_message TEXT,
                error_stack TEXT,
                executed_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_case_id) REFERENCES test_cases(id)
            );
            
            -- 步骤执行详情表
            CREATE TABLE IF NOT EXISTS step_executions (
                id SERIAL PRIMARY KEY,
                execution_id VARCHAR(50) NOT NULL,
                step_index INTEGER NOT NULL,
                step_description TEXT NOT NULL,
                status VARCHAR(20) NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                duration INTEGER,
                screenshot_path TEXT,
                ai_confidence REAL,
                ai_decision TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (execution_id) REFERENCES execution_history(execution_id)
            );
            
            -- 模板表
            CREATE TABLE IF NOT EXISTS templates (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100),
                steps_template TEXT NOT NULL,
                parameters TEXT,
                usage_count INTEGER DEFAULT 0,
                created_by VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_public BOOLEAN DEFAULT FALSE
            );
            
            -- 创建索引
            CREATE INDEX IF NOT EXISTS idx_test_cases_name ON test_cases(name);
            CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category);
            CREATE INDEX IF NOT EXISTS idx_test_cases_created_at ON test_cases(created_at);
            CREATE INDEX IF NOT EXISTS idx_execution_history_test_case_id ON execution_history(test_case_id);
            CREATE INDEX IF NOT EXISTS idx_execution_history_status ON execution_history(status);
            CREATE INDEX IF NOT EXISTS idx_execution_history_start_time ON execution_history(start_time);
            CREATE INDEX IF NOT EXISTS idx_step_executions_execution_id ON step_executions(execution_id);
            CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);
            """
            
            with self.target_engine.connect() as conn:
                # 分割并执行每个语句
                statements = [stmt.strip() for stmt in create_tables_sql.split(';') if stmt.strip()]
                for stmt in statements:
                    conn.execute(text(stmt))
                conn.commit()
            
            self.log("✅ PostgreSQL表结构创建成功")
            return True
            
        except Exception as e:
            self.log(f"❌ 创建PostgreSQL表结构失败: {e}", "ERROR")
            return False
    
    def migrate_table_data(self, table_name: str) -> bool:
        """迁移单个表的数据"""
        try:
            self.log(f"🔄 开始迁移表: {table_name}")
            
            # 从源数据库读取数据
            with self.source_engine.connect() as source_conn:
                result = source_conn.execute(text(f"SELECT * FROM {table_name}"))
                rows = result.fetchall()
                columns = result.keys()
            
            if not rows:
                self.log(f"⚠️  表 {table_name} 无数据，跳过")
                return True
            
            self.log(f"📊 表 {table_name} 共有 {len(rows)} 条记录")
            
            # 构建插入语句
            column_names = ', '.join(columns)
            placeholders = ', '.join([f'%({col})s' for col in columns])
            insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            
            # 转换数据格式
            data_to_insert = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                # 处理特殊字段类型转换
                if table_name == 'test_cases' and 'id' in row_dict:
                    # PostgreSQL使用SERIAL，不需要插入id
                    row_dict.pop('id', None)
                data_to_insert.append(row_dict)
            
            # 批量插入到目标数据库
            with self.target_engine.connect() as target_conn:
                if table_name == 'test_cases':
                    # 对于test_cases表，需要特殊处理id字段
                    insert_sql = insert_sql.replace('id, ', '').replace('%(id)s, ', '')
                
                for row_data in data_to_insert:
                    target_conn.execute(text(insert_sql), row_data)
                target_conn.commit()
            
            self.log(f"✅ 表 {table_name} 迁移完成，共 {len(data_to_insert)} 条记录")
            return True
            
        except Exception as e:
            self.log(f"❌ 迁移表 {table_name} 失败: {e}", "ERROR")
            return False
    
    def migrate_all_data(self) -> bool:
        """迁移所有数据"""
        # 按依赖顺序迁移表
        tables_order = [
            'test_cases',
            'templates', 
            'execution_history',
            'step_executions'
        ]
        
        success_count = 0
        for table_name in tables_order:
            if self.migrate_table_data(table_name):
                success_count += 1
            else:
                self.log(f"❌ 停止迁移，表 {table_name} 迁移失败", "ERROR")
                return False
        
        self.log(f"🎉 数据迁移完成！成功迁移 {success_count} 个表")
        return True
    
    def verify_migration(self) -> bool:
        """验证迁移结果"""
        try:
            self.log("🔍 开始验证迁移结果...")
            
            tables = ['test_cases', 'execution_history', 'step_executions', 'templates']
            
            for table_name in tables:
                # 检查源数据库记录数
                with self.source_engine.connect() as source_conn:
                    source_result = source_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    source_count = source_result.scalar()
                
                # 检查目标数据库记录数
                with self.target_engine.connect() as target_conn:
                    target_result = target_conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    target_count = target_result.scalar()
                
                if source_count == target_count:
                    self.log(f"✅ 表 {table_name}: {source_count} -> {target_count} 记录")
                else:
                    self.log(f"⚠️  表 {table_name}: {source_count} -> {target_count} 记录不匹配", "WARNING")
            
            self.log("✅ 迁移验证完成")
            return True
            
        except Exception as e:
            self.log(f"❌ 验证迁移失败: {e}", "ERROR")
            return False
    
    def run_migration(self) -> bool:
        """执行完整迁移流程"""
        self.log("🚀 开始数据库迁移...")
        
        # 1. 验证连接
        if not self.validate_connections():
            return False
        
        # 2. 创建目标表结构
        if not self.create_postgresql_schema():
            return False
        
        # 3. 迁移数据
        if not self.migrate_all_data():
            return False
        
        # 4. 验证迁移结果
        if not self.verify_migration():
            return False
        
        self.log("🎉 数据库迁移成功完成！")
        return True
    
    def save_migration_log(self, log_file: str = None):
        """保存迁移日志"""
        if not log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"migration_log_{timestamp}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.migration_log))
        
        print(f"📝 迁移日志已保存到: {log_file}")


def main():
    parser = argparse.ArgumentParser(description="SQLite到Supabase PostgreSQL数据迁移工具")
    parser.add_argument('--source', help='源数据库URL (SQLite)')
    parser.add_argument('--target', help='目标数据库URL (PostgreSQL)')
    parser.add_argument('--auto', action='store_true', help='自动检测配置')
    parser.add_argument('--log', help='日志文件路径')
    
    args = parser.parse_args()
    
    if args.auto:
        # 自动检测配置
        db_config = DatabaseConfig()
        
        # 源数据库 (SQLite)
        instance_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_gui', 'instance')
        source_db_path = os.path.join(instance_path, 'gui_test_cases.db')
        source_url = f'sqlite:///{source_db_path}'
        
        # 目标数据库 (从环境变量获取)
        target_url = os.getenv('SUPABASE_DATABASE_URL') or os.getenv('DATABASE_URL')
        
        if not target_url:
            print("❌ 请设置 SUPABASE_DATABASE_URL 或 DATABASE_URL 环境变量")
            return False
        
        print(f"🔍 自动检测配置:")
        print(f"   源数据库: {source_url}")
        print(f"   目标数据库: {target_url[:50]}...")
        
    else:
        if not args.source or not args.target:
            print("❌ 请提供源数据库和目标数据库URL，或使用 --auto 参数")
            return False
        
        source_url = args.source
        target_url = args.target
    
    # 执行迁移
    migrator = DatabaseMigrator(source_url, target_url)
    success = migrator.run_migration()
    
    # 保存日志
    migrator.save_migration_log(args.log)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
