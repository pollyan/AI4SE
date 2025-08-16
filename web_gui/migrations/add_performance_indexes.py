"""
数据库性能优化迁移脚本
添加索引以提升查询性能
"""
import sys
import os

# 添加项目路径到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db
from app_enhanced import create_app

def create_indexes():
    """创建性能优化索引"""
    app = create_app()
    
    with app.app_context():
        print("开始创建性能优化索引...")
        
        # 测试用例索引
        try:
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_testcase_active 
                ON test_cases (is_active);
            """)
            print("✓ 创建测试用例活跃状态索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_testcase_category 
                ON test_cases (category, is_active);
            """)
            print("✓ 创建测试用例分类索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_testcase_created 
                ON test_cases (created_at);
            """)
            print("✓ 创建测试用例创建时间索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_testcase_priority 
                ON test_cases (priority, is_active);
            """)
            print("✓ 创建测试用例优先级索引")
            
        except Exception as e:
            print(f"创建测试用例索引时出错: {e}")
        
        # 执行历史索引
        try:
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_testcase_status 
                ON execution_history (test_case_id, status);
            """)
            print("✓ 创建执行历史测试用例状态索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_start_time 
                ON execution_history (start_time);
            """)
            print("✓ 创建执行历史开始时间索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_status 
                ON execution_history (status);
            """)
            print("✓ 创建执行历史状态索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_executed_by 
                ON execution_history (executed_by);
            """)
            print("✓ 创建执行历史执行者索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_created_at 
                ON execution_history (created_at);
            """)
            print("✓ 创建执行历史创建时间索引")
            
        except Exception as e:
            print(f"创建执行历史索引时出错: {e}")
        
        # 步骤执行索引
        try:
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_step_execution_id_index 
                ON step_executions (execution_id, step_index);
            """)
            print("✓ 创建步骤执行ID索引索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_step_status 
                ON step_executions (execution_id, status);
            """)
            print("✓ 创建步骤执行状态索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_step_start_time 
                ON step_executions (start_time);
            """)
            print("✓ 创建步骤执行开始时间索引")
            
        except Exception as e:
            print(f"创建步骤执行索引时出错: {e}")
        
        # 执行变量索引（如果表存在）
        try:
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_variable 
                ON execution_variables (execution_id, variable_name);
            """)
            print("✓ 创建执行变量索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_execution_step 
                ON execution_variables (execution_id, source_step_index);
            """)
            print("✓ 创建执行变量步骤索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_variable_type 
                ON execution_variables (execution_id, data_type);
            """)
            print("✓ 创建执行变量类型索引")
            
            db.engine.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uk_execution_variable_name 
                ON execution_variables (execution_id, variable_name);
            """)
            print("✓ 创建执行变量唯一约束")
            
        except Exception as e:
            print(f"创建执行变量索引时出错（可能表不存在）: {e}")
        
        # 变量引用索引（如果表存在）
        try:
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_reference_execution_step 
                ON variable_references (execution_id, step_index);
            """)
            print("✓ 创建变量引用执行步骤索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_reference_variable 
                ON variable_references (execution_id, variable_name);
            """)
            print("✓ 创建变量引用变量名索引")
            
            db.engine.execute("""
                CREATE INDEX IF NOT EXISTS idx_reference_status 
                ON variable_references (execution_id, resolution_status);
            """)
            print("✓ 创建变量引用状态索引")
            
        except Exception as e:
            print(f"创建变量引用索引时出错（可能表不存在）: {e}")
        
        print("✅ 所有性能优化索引创建完成!")

def analyze_query_performance():
    """分析查询性能并给出建议"""
    app = create_app()
    
    with app.app_context():
        print("\n开始分析查询性能...")
        
        try:
            # 检查表大小
            result = db.engine.execute("""
                SELECT 
                    name,
                    tbl_name,
                    sql
                FROM sqlite_master 
                WHERE type='table' AND name IN ('test_cases', 'execution_history', 'step_executions')
                ORDER BY name;
            """)
            
            print("\n📊 数据库表信息:")
            for row in result:
                print(f"  - {row[0]}")
            
            # 检查索引
            result = db.engine.execute("""
                SELECT name, tbl_name 
                FROM sqlite_master 
                WHERE type='index' AND tbl_name IN ('test_cases', 'execution_history', 'step_executions')
                ORDER BY tbl_name, name;
            """)
            
            print("\n📈 现有索引:")
            current_table = None
            for row in result:
                if row[1] != current_table:
                    current_table = row[1]
                    print(f"  {current_table}:")
                print(f"    - {row[0]}")
            
            # 基础统计
            testcase_count = db.engine.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
            execution_count = db.engine.execute("SELECT COUNT(*) FROM execution_history").fetchone()[0]
            
            print(f"\n📋 数据统计:")
            print(f"  - 测试用例数量: {testcase_count}")
            print(f"  - 执行历史数量: {execution_count}")
            
            if execution_count > 1000:
                print("⚠️  建议: 执行历史记录较多，建议定期清理旧数据")
            
            if testcase_count > 100:
                print("💡 建议: 测试用例较多，确保使用分页查询")
                
        except Exception as e:
            print(f"分析查询性能时出错: {e}")

if __name__ == "__main__":
    print("=== 数据库性能优化工具 ===")
    print("1. 创建性能索引")
    print("2. 分析查询性能")
    print("3. 全部执行")
    
    choice = input("请选择操作 (1/2/3): ").strip()
    
    if choice == "1":
        create_indexes()
    elif choice == "2":
        analyze_query_performance()
    elif choice == "3":
        create_indexes()
        analyze_query_performance()
    else:
        print("无效选择")