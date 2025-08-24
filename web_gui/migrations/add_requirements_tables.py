#!/usr/bin/env python3
"""
数据库迁移脚本 - 添加需求分析相关表
执行: python web_gui/migrations/add_requirements_tables.py
"""

import os
import sys
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    # 尝试本地导入
    from web_gui.app_enhanced import create_app
    from web_gui.models import db, RequirementsSession, RequirementsMessage
except ImportError:
    # 在某些环境下可能需要绝对导入
    import web_gui.app_enhanced as app_module
    from web_gui.models import db, RequirementsSession, RequirementsMessage
    create_app = app_module.create_app


def create_requirements_tables():
    """创建需求分析相关表"""
    print("🔧 开始创建需求分析数据表...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 检查表是否已存在
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            needs_creation = []
            if 'requirements_sessions' not in existing_tables:
                needs_creation.append('requirements_sessions')
            if 'requirements_messages' not in existing_tables:
                needs_creation.append('requirements_messages')
            
            if not needs_creation:
                print("✅ 需求分析数据表已存在，无需创建")
                return True
            
            print(f"📋 需要创建的表: {', '.join(needs_creation)}")
            
            # 创建表 - 只创建需要的表
            RequirementsSession.__table__.create(db.engine, checkfirst=True)
            RequirementsMessage.__table__.create(db.engine, checkfirst=True)
            
            # 验证表创建成功
            inspector = db.inspect(db.engine)
            new_tables = inspector.get_table_names()
            
            success = True
            for table_name in needs_creation:
                if table_name in new_tables:
                    print(f"✅ 表 {table_name} 创建成功")
                else:
                    print(f"❌ 表 {table_name} 创建失败")
                    success = False
            
            if success:
                print("✅ 所有需求分析数据表创建完成")
                
                # 创建一个测试会话以验证功能
                create_test_session()
                
            return success
            
        except Exception as e:
            print(f"❌ 创建数据表失败: {str(e)}")
            return False


def create_test_session():
    """创建一个测试会话"""
    try:
        import uuid
        import json
        
        # 创建测试会话
        test_session = RequirementsSession(
            id=str(uuid.uuid4()),
            project_name="测试项目",
            session_status="active",
            current_stage="initial",
            user_context=json.dumps({}),
            ai_context=json.dumps({}),
            consensus_content=json.dumps({})
        )
        
        db.session.add(test_session)
        
        # 创建欢迎消息
        welcome_message = RequirementsMessage(
            session_id=test_session.id,
            message_type="assistant",
            content="这是一个测试消息，验证需求分析系统正常工作。",
            message_metadata=json.dumps({
                "test": True,
                "created_by": "migration_script"
            })
        )
        
        db.session.add(welcome_message)
        db.session.commit()
        
        print(f"✅ 测试会话创建成功，会话ID: {test_session.id}")
        
        # 验证数据查询
        session_count = RequirementsSession.query.count()
        message_count = RequirementsMessage.query.count()
        
        print(f"📊 当前数据统计:")
        print(f"   - 会话总数: {session_count}")
        print(f"   - 消息总数: {message_count}")
        
    except Exception as e:
        print(f"⚠️ 创建测试会话失败: {str(e)}")
        db.session.rollback()


def verify_indexes():
    """验证索引是否正确创建"""
    try:
        inspector = db.inspect(db.engine)
        
        # 检查requirements_sessions表的索引
        session_indexes = inspector.get_indexes('requirements_sessions')
        print(f"📋 requirements_sessions 表索引: {len(session_indexes)} 个")
        for idx in session_indexes:
            print(f"   - {idx['name']}: {idx['column_names']}")
        
        # 检查requirements_messages表的索引
        message_indexes = inspector.get_indexes('requirements_messages')
        print(f"📋 requirements_messages 表索引: {len(message_indexes)} 个")
        for idx in message_indexes:
            print(f"   - {idx['name']}: {idx['column_names']}")
        
        return True
        
    except Exception as e:
        print(f"⚠️ 验证索引失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("需求分析数据表迁移脚本")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 创建表
        if not create_requirements_tables():
            print("❌ 数据表创建失败")
            sys.exit(1)
        
        # 验证索引
        print("\n🔍 验证数据库索引...")
        if verify_indexes():
            print("✅ 索引验证完成")
        
        print("\n🎉 需求分析模块数据库迁移完成!")
        print("📌 现在可以启动应用并访问 /requirements-analyzer 页面")
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 迁移过程中发生错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()