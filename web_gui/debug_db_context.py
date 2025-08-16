#!/usr/bin/env python3
"""
调试SQLAlchemy上下文问题
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== 调试SQLAlchemy上下文问题 ===")

# 导入Flask应用
from app_enhanced import create_app, db
from models import TestCase, ExecutionHistory

print(f"1. Flask app db实例ID: {id(db)}")

# 创建Flask应用
app = create_app()

print(f"2. 创建app后的db实例ID: {id(db)}")

# 检查Flask应用上下文
with app.app_context():
    print(f"3. 在app上下文中的db实例ID: {id(db)}")
    
    try:
        # 测试简单查询
        from sqlalchemy import text
        result = db.session.execute(text('SELECT 1'))
        print(f"4. ✅ 数据库连接测试成功: {result.fetchone()}")
        
        # 测试模型查询
        testcases = TestCase.query.limit(5).all()
        print(f"5. ✅ 测试用例查询成功: {len(testcases)} 条记录")
        
        # 测试执行历史查询
        executions = ExecutionHistory.query.limit(5).all()
        print(f"6. ✅ 执行历史查询成功: {len(executions)} 条记录")
        
    except Exception as e:
        print(f"4. ❌ 数据库操作失败: {e}")

print("=== 调试完成 ===")