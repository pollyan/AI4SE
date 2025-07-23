"""
数据库优化工具
"""
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def create_database_indexes(db):
    """创建数据库性能优化索引"""
    indexes = [
        # 测试用例表索引
        ("idx_testcases_is_active", "CREATE INDEX IF NOT EXISTS idx_testcases_is_active ON test_cases(is_active)"),
        ("idx_testcases_category", "CREATE INDEX IF NOT EXISTS idx_testcases_category ON test_cases(category)"),
        ("idx_testcases_updated_at", "CREATE INDEX IF NOT EXISTS idx_testcases_updated_at ON test_cases(updated_at DESC)"),
        ("idx_testcases_name", "CREATE INDEX IF NOT EXISTS idx_testcases_name ON test_cases(name)"),
        
        # 执行历史表索引
        ("idx_execution_history_test_case_id", "CREATE INDEX IF NOT EXISTS idx_execution_history_test_case_id ON execution_history(test_case_id)"),
        ("idx_execution_history_status", "CREATE INDEX IF NOT EXISTS idx_execution_history_status ON execution_history(status)"),
        ("idx_execution_history_created_at", "CREATE INDEX IF NOT EXISTS idx_execution_history_created_at ON execution_history(created_at DESC)"),
        ("idx_execution_history_execution_id", "CREATE INDEX IF NOT EXISTS idx_execution_history_execution_id ON execution_history(execution_id)"),
        
        # 步骤执行表索引
        ("idx_step_executions_execution_id", "CREATE INDEX IF NOT EXISTS idx_step_executions_execution_id ON step_executions(execution_id)"),
        ("idx_step_executions_step_index", "CREATE INDEX IF NOT EXISTS idx_step_executions_step_index ON step_executions(execution_id, step_index)"),
        ("idx_step_executions_status", "CREATE INDEX IF NOT EXISTS idx_step_executions_status ON step_executions(status)"),
        
        # 模板表索引
        ("idx_templates_category", "CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category)"),
        ("idx_templates_is_public", "CREATE INDEX IF NOT EXISTS idx_templates_is_public ON templates(is_public)"),
    ]
    
    created_count = 0
    failed_count = 0
    
    for index_name, sql in indexes:
        try:
            db.session.execute(text(sql))
            logger.info(f"✅ 索引创建成功: {index_name}")
            created_count += 1
        except Exception as e:
            logger.warning(f"⚠️ 索引创建失败: {index_name} - {str(e)}")
            failed_count += 1
    
    try:
        db.session.commit()
        logger.info(f"🎯 索引优化完成: 成功 {created_count}, 失败 {failed_count}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ 索引创建事务提交失败: {str(e)}")
        raise

def analyze_query_performance(db, query_sql: str):
    """分析查询性能（PostgreSQL专用）"""
    try:
        explain_sql = f"EXPLAIN ANALYZE {query_sql}"
        result = db.session.execute(text(explain_sql))
        
        performance_info = []
        for row in result:
            performance_info.append(str(row[0]))
        
        return "\n".join(performance_info)
    except Exception as e:
        logger.error(f"查询性能分析失败: {str(e)}")
        return f"分析失败: {str(e)}"

def get_table_statistics(db):
    """获取表统计信息"""
    try:
        tables = ['test_cases', 'execution_history', 'step_executions', 'templates']
        stats = {}
        
        for table in tables:
            count_sql = f"SELECT COUNT(*) FROM {table}"
            result = db.session.execute(text(count_sql))
            count = result.scalar()
            stats[table] = {'count': count}
            
            # 获取最近更新时间（如果表有相应字段）
            if table in ['test_cases', 'execution_history']:
                time_field = 'updated_at' if table == 'test_cases' else 'created_at'
                recent_sql = f"SELECT MAX({time_field}) FROM {table}"
                try:
                    result = db.session.execute(text(recent_sql))
                    recent_time = result.scalar()
                    stats[table]['latest_update'] = recent_time.isoformat() if recent_time else None
                except:
                    stats[table]['latest_update'] = None
        
        return stats
    except Exception as e:
        logger.error(f"获取表统计信息失败: {str(e)}")
        return {}

def cleanup_old_executions(db, days_to_keep: int = 30):
    """清理旧的执行记录"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # 先删除相关的步骤执行记录
        step_delete_sql = """
        DELETE FROM step_executions 
        WHERE execution_id IN (
            SELECT execution_id FROM execution_history 
            WHERE created_at < :cutoff_date
        )
        """
        
        # 删除执行历史记录
        history_delete_sql = """
        DELETE FROM execution_history 
        WHERE created_at < :cutoff_date
        """
        
        step_result = db.session.execute(text(step_delete_sql), {'cutoff_date': cutoff_date})
        history_result = db.session.execute(text(history_delete_sql), {'cutoff_date': cutoff_date})
        
        db.session.commit()
        
        logger.info(f"🧹 清理完成: 删除了 {history_result.rowcount} 条执行记录和 {step_result.rowcount} 条步骤记录")
        return {
            'execution_records_deleted': history_result.rowcount,
            'step_records_deleted': step_result.rowcount,
            'cutoff_date': cutoff_date.isoformat()
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"清理旧记录失败: {str(e)}")
        raise