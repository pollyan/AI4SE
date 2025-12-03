#!/usr/bin/env python3
"""检查 Supabase 数据库中的表"""

import sys
from sqlalchemy import create_engine, text, MetaData

SUPABASE_URL = "postgresql://postgres.jzmqsuxphksbulrbhebp:Shunlian04@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

def check_supabase():
    try:
        print("连接 Supabase...")
        engine = create_engine(SUPABASE_URL, connect_args={"connect_timeout": 15})
        
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ 连接成功\n")
        
        # 获取所有 schema
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schema_name
            """))
            schemas = [row[0] for row in result]
        
        print(f"找到 {len(schemas)} 个 schema:")
        for schema in schemas:
            print(f"  - {schema}")
        
        # 获取每个 schema 中的表
        print("\n表列表:")
        for schema in schemas:
            metadata = MetaData()
            metadata.reflect(bind=engine, schema=schema)
            
            if metadata.tables:
                print(f"\n  Schema: {schema}")
                for table_name, table in metadata.tables.items():
                    # 获取行数
                    with engine.connect() as conn:
                        try:
                            count_result = conn.execute(text(f'SELECT COUNT(*) FROM "{schema}"."{table.name}"'))
                            count = count_result.scalar()
                            print(f"    - {table.name} ({count} 行)")
                        except Exception as e:
                            print(f"    - {table.name} (无法统计)")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_supabase()
