from datetime import datetime, timedelta
from backend.services.query_optimizer import QueryOptimizer
from backend.models import ExecutionHistory

class TestQueryOptimizer:
    """Test cases for QueryOptimizer service"""

    def test_get_testcases_with_stats(self, db_session, test_data_manager):
        """Test getting testcases with execution statistics"""
        # Create test cases
        tc1 = test_data_manager.create_testcase({"name": "TC1", "category": "Cat1"})
        tc2 = test_data_manager.create_testcase({"name": "TC2", "category": "Cat2"})
        
        # Create executions for TC1
        # 1 success
        test_data_manager.create_execution({
            "test_case_id": tc1.id,
            "status": "success",
            "start_time": datetime.utcnow()
        })
        # 1 failure
        test_data_manager.create_execution({
            "test_case_id": tc1.id,
            "status": "failed",
            "start_time": datetime.utcnow()
        })
        
        # Query
        results, total = QueryOptimizer.get_testcases_with_stats(page=1, per_page=10)
        
        assert total >= 2
        
        # Find TC1 in results
        tc1_data = next((item for item in results if item["id"] == tc1.id), None)
        assert tc1_data is not None
        assert tc1_data["execution_count"] == 2
        # Success rate should be 50% (1 success / 2 total)
        assert tc1_data["success_rate"] == 50.0
        
        # Find TC2 in results
        tc2_data = next((item for item in results if item["id"] == tc2.id), None)
        assert tc2_data is not None
        assert tc2_data["execution_count"] == 0
        assert tc2_data["success_rate"] == 0

    def test_get_testcases_with_stats_filtering(self, db_session, test_data_manager):
        """Test filtering in get_testcases_with_stats"""
        tc1 = test_data_manager.create_testcase({"name": "SearchMe", "category": "FilterCat"})
        tc2 = test_data_manager.create_testcase({"name": "IgnoreMe", "category": "OtherCat"})
        
        # Filter by category
        results, total = QueryOptimizer.get_testcases_with_stats(category="FilterCat")
        assert total == 1
        assert results[0]["id"] == tc1.id
        
        # Filter by search
        results, total = QueryOptimizer.get_testcases_with_stats(search="Search")
        assert total == 1
        assert results[0]["id"] == tc1.id

    def test_get_execution_with_steps(self, db_session, test_data_manager):
        """Test getting full execution details"""
        # Create execution with steps and variables
        execution = test_data_manager.create_execution({
            "status": "success",
            "steps_total": 2
        })
        
        # Add steps
        test_data_manager.create_step_execution(
            execution.execution_id,
            {
                "step_index": 0,
                "status": "success"
            }
        )
        test_data_manager.create_step_execution(
            execution.execution_id,
            {
                "step_index": 1,
                "status": "success"
            }
        )
        
        # Query
        result = QueryOptimizer.get_execution_with_steps(execution.execution_id)
        
        assert result is not None
        assert result["execution_id"] == execution.execution_id
        assert "steps" in result
        assert len(result["steps"]) == 2
        
        # Test non-existent execution
        assert QueryOptimizer.get_execution_with_steps("non-existent") is None





    def test_cleanup_old_data(self, db_session, test_data_manager):
        """Test data cleanup"""
        # Create old execution (> 90 days)
        old_date = datetime.utcnow() - timedelta(days=91)
        exec_old = test_data_manager.create_execution({
            "execution_id": "old-exec-001",
            "start_time": old_date,
            "created_at": old_date # Important: cleanup uses created_at
        })
        
        # Create recent execution
        recent_date = datetime.utcnow() - timedelta(days=10)
        exec_recent = test_data_manager.create_execution({
            "execution_id": "recent-exec-001",
            "start_time": recent_date,
            "created_at": recent_date
        })
        
        # Force commit to ensure created_at is persisted
        # (created_at might be auto-set by DB default, so we override it in object for testing)
        # However, the model default is datetime.utcnow in python, so passing it works.
        # But we need to make sure sqlalchemy doesn't overwrite it on flush.
        # Let's check model definition.
        # created_at = db.Column(db.DateTime, default=datetime.utcnow)
        # Passing it in constructor should work.
        
        # Create associated steps for old execution
        test_data_manager.create_step_execution(
            exec_old.execution_id,
            {}
        )
        
        # Run cleanup
        stats = QueryOptimizer.cleanup_old_data(days_to_keep=90)
        
        assert stats["executions_deleted"] == 1
        assert stats["step_executions_deleted"] == 1
        
        # Verify old execution is gone
        assert db_session.query(ExecutionHistory).filter_by(execution_id="old-exec-001").first() is None
        # Verify recent execution remains
        assert db_session.query(ExecutionHistory).filter_by(execution_id="recent-exec-001").first() is not None
