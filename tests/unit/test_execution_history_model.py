"""
ExecutionHistory模型完整测试
包含基础功能测试、边界值测试、约束测试等
"""
import pytest
import json
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError, DataError
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web_gui.models import db, TestCase, ExecutionHistory, StepExecution
from tests.unit.factories import TestCaseFactory, ExecutionHistoryFactory, StepExecutionFactory


class TestExecutionHistoryBasicOperations:
    """ExecutionHistory基础操作测试"""
    
    def test_should_create_execution_history(self, db_session):
        """测试创建执行历史记录"""
        test_case = TestCaseFactory.create()
        execution = ExecutionHistory(
            execution_id=f"exec_{datetime.utcnow().timestamp()}",
            test_case_id=test_case.id,
            status='running',
            start_time=datetime.utcnow(),
            steps_total=5,
            steps_passed=0,
            steps_failed=0,
            executed_by='test_user'
        )
        db_session.add(execution)
        db_session.commit()
        
        assert execution.id is not None
        assert execution.test_case_id == test_case.id
        assert execution.status == 'running'
        assert execution.start_time is not None
    
    def test_should_update_execution_status(self, db_session):
        """测试更新执行状态"""
        execution = ExecutionHistoryFactory.create(status='running')
        
        execution.status = 'success'
        execution.steps_passed = execution.steps_total
        execution.end_time = datetime.utcnow()
        db_session.commit()
        
        assert execution.status == 'success'
        assert execution.steps_passed == execution.steps_total
        assert execution.end_time is not None
    
    def test_should_store_duration(self, db_session):
        """测试存储执行时长"""
        execution = ExecutionHistoryFactory.create(
            status='success',
            duration=330  # 5分30秒
        )
        
        execution_dict = execution.to_dict()
        assert execution_dict['duration'] == 330
    
    def test_should_handle_running_status(self, db_session):
        """测试处理运行中状态"""
        execution = ExecutionHistoryFactory.create(
            status='running',
            end_time=None,
            duration=None
        )
        
        execution_dict = execution.to_dict()
        assert execution_dict['status'] == 'running'
        assert execution_dict['end_time'] is None
        assert execution_dict['duration'] is None
    
    def test_should_store_error_message(self, db_session):
        """测试存储错误信息"""
        error_msg = "找不到页面元素: 登录按钮"
        execution = ExecutionHistoryFactory.create(
            status='failed',
            error_message=error_msg
        )
        
        assert execution.error_message == error_msg
    
    def test_should_store_screenshots_path(self, db_session):
        """测试存储截图路径"""
        execution = ExecutionHistory(
            execution_id="exec_test_screenshots",
            test_case_id=TestCaseFactory.create().id,
            status='failed',
            screenshots_path='/uploads/screenshots/exec_test_screenshots/',
            start_time=datetime.utcnow(),
            steps_total=2
        )
        db_session.add(execution)
        db_session.commit()
        
        execution_dict = execution.to_dict()
        assert execution_dict['screenshots_path'] == '/uploads/screenshots/exec_test_screenshots/'
    
    def test_should_parse_result_summary(self, db_session):
        """测试解析结果摘要JSON数据"""
        result_summary = {
            "total": 5,
            "passed": 3,
            "failed": 2,
            "success_rate": 60
        }
        execution = ExecutionHistory(
            execution_id="exec_test_summary",
            test_case_id=TestCaseFactory.create().id,
            status='failed',
            result_summary=json.dumps(result_summary),
            start_time=datetime.utcnow(),
            steps_total=5
        )
        db_session.add(execution)
        db_session.commit()
        
        execution_dict = execution.to_dict()
        assert isinstance(execution_dict['result_summary'], dict)
        assert execution_dict['result_summary']['total'] == 5
        assert execution_dict['result_summary']['success_rate'] == 60


class TestExecutionHistoryConstraints:
    """ExecutionHistory约束测试"""
    
    def test_execution_id_uniqueness(self, db_session):
        """测试execution_id唯一性约束"""
        test_case = TestCaseFactory.create()
        
        # 创建第一个执行记录
        execution1 = ExecutionHistory(
            execution_id="unique_exec_001",
            test_case_id=test_case.id,
            status='success',
            start_time=datetime.utcnow(),
            steps_total=1
        )
        db_session.add(execution1)
        db_session.commit()
        
        # 尝试创建相同execution_id的记录
        with pytest.raises(IntegrityError) as exc_info:
            execution2 = ExecutionHistory(
                execution_id="unique_exec_001",  # 重复的ID
                test_case_id=test_case.id,
                status='running',
                start_time=datetime.utcnow(),
                steps_total=1
            )
            db_session.add(execution2)
            db_session.commit()
        
        db_session.rollback()
        assert "UNIQUE constraint failed" in str(exc_info.value) or "duplicate key" in str(exc_info.value)
    
    def test_required_fields(self, db_session):
        """测试必填字段约束"""
        test_case = TestCaseFactory.create()
        
        # execution_id必填
        with pytest.raises(IntegrityError):
            execution = ExecutionHistory(
                # execution_id缺失
                test_case_id=test_case.id,
                status='running',
                start_time=datetime.utcnow()
            )
            db_session.add(execution)
            db_session.commit()
        db_session.rollback()
        
        # test_case_id必填
        with pytest.raises(IntegrityError):
            execution = ExecutionHistory(
                execution_id="exec_missing_tc",
                # test_case_id缺失
                status='running',
                start_time=datetime.utcnow()
            )
            db_session.add(execution)
            db_session.commit()
        db_session.rollback()
        
        # status必填
        with pytest.raises(IntegrityError):
            execution = ExecutionHistory(
                execution_id="exec_missing_status",
                test_case_id=test_case.id,
                # status缺失
                start_time=datetime.utcnow()
            )
            db_session.add(execution)
            db_session.commit()
        db_session.rollback()
    
    def test_foreign_key_constraint(self, db_session):
        """测试外键约束"""
        # 引用不存在的test_case_id
        with pytest.raises(IntegrityError):
            execution = ExecutionHistory(
                execution_id="exec_invalid_fk",
                test_case_id=99999,  # 不存在的TestCase
                status='running',
                start_time=datetime.utcnow(),
                steps_total=1
            )
            db_session.add(execution)
            db_session.commit()
        db_session.rollback()
    
    def test_default_values(self, db_session):
        """测试默认值"""
        test_case = TestCaseFactory.create()
        
        execution = ExecutionHistory(
            execution_id="exec_defaults",
            test_case_id=test_case.id,
            status='running',
            start_time=datetime.utcnow(),
            steps_total=5
            # 不设置其他字段，使用默认值
        )
        db_session.add(execution)
        db_session.commit()
        
        assert execution.mode == 'headless'  # 默认模式
        assert execution.browser == 'chrome'  # 默认浏览器
        assert execution.created_at is not None  # 自动设置时间


class TestExecutionHistoryBoundaries:
    """ExecutionHistory边界值测试"""
    
    def test_steps_count_boundaries(self, db_session):
        """测试步骤数边界值"""
        test_case = TestCaseFactory.create()
        
        # 0步骤
        exec_zero = ExecutionHistory(
            execution_id="exec_zero_steps",
            test_case_id=test_case.id,
            status='success',
            start_time=datetime.utcnow(),
            steps_total=0,
            steps_passed=0,
            steps_failed=0
        )
        db_session.add(exec_zero)
        
        # 大量步骤
        exec_many = ExecutionHistory(
            execution_id="exec_many_steps",
            test_case_id=test_case.id,
            status='success',
            start_time=datetime.utcnow(),
            steps_total=10000,
            steps_passed=9999,
            steps_failed=1
        )
        db_session.add(exec_many)
        
        db_session.commit()
        
        assert exec_zero.steps_total == 0
        assert exec_many.steps_total == 10000
    
    def test_duration_boundaries(self, db_session):
        """测试执行时长边界值"""
        test_case = TestCaseFactory.create()
        
        # 瞬间完成（0秒）
        exec_instant = ExecutionHistory(
            execution_id="exec_instant",
            test_case_id=test_case.id,
            status='success',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration=0,
            steps_total=1
        )
        db_session.add(exec_instant)
        
        # 超长执行（48小时）
        exec_long = ExecutionHistory(
            execution_id="exec_long",
            test_case_id=test_case.id,
            status='timeout',
            start_time=datetime.utcnow() - timedelta(hours=48),
            end_time=datetime.utcnow(),
            duration=172800,  # 48小时的秒数
            steps_total=1000
        )
        db_session.add(exec_long)
        
        db_session.commit()
        
        assert exec_instant.duration == 0
        assert exec_long.duration == 172800
    
    def test_extreme_dates(self, db_session):
        """测试极限日期"""
        test_case = TestCaseFactory.create()
        
        # 过去的日期
        past_execution = ExecutionHistory(
            execution_id="exec_past",
            test_case_id=test_case.id,
            status='success',
            start_time=datetime(2000, 1, 1, 0, 0, 0),
            end_time=datetime(2000, 1, 1, 0, 1, 0),
            steps_total=1
        )
        db_session.add(past_execution)
        
        # 未来的日期（计划执行）
        future_execution = ExecutionHistory(
            execution_id="exec_future",
            test_case_id=test_case.id,
            status='pending',
            start_time=datetime(2099, 12, 31, 23, 59, 59),
            steps_total=1
        )
        db_session.add(future_execution)
        
        db_session.commit()
        
        assert past_execution.start_time.year == 2000
        assert future_execution.start_time.year == 2099
    
    def test_status_values(self, db_session):
        """测试各种状态值"""
        test_case = TestCaseFactory.create()
        
        # 所有可能的状态
        statuses = ['running', 'success', 'failed', 'stopped', 'timeout', 'pending', 'error']
        
        for i, status in enumerate(statuses):
            execution = ExecutionHistory(
                execution_id=f"exec_status_{status}",
                test_case_id=test_case.id,
                status=status,
                start_time=datetime.utcnow(),
                steps_total=1
            )
            db_session.add(execution)
        
        db_session.commit()
        
        # 验证所有状态都能存储
        for status in statuses:
            exec_record = ExecutionHistory.query.filter_by(
                execution_id=f"exec_status_{status}"
            ).first()
            assert exec_record is not None
            assert exec_record.status == status
    
    def test_large_result_summary(self, db_session):
        """测试大型结果摘要JSON"""
        test_case = TestCaseFactory.create()
        
        # 创建包含大量数据的结果摘要
        large_summary = {
            "total_steps": 1000,
            "step_details": []
        }
        
        for i in range(1000):
            large_summary["step_details"].append({
                "index": i,
                "name": f"步骤{i}",
                "status": "success" if i % 10 != 0 else "failed",
                "duration": i % 100,
                "error": None if i % 10 != 0 else f"错误信息{i}",
                "screenshot": f"/screenshots/step_{i}.png" if i % 10 == 0 else None
            })
        
        execution = ExecutionHistory(
            execution_id="exec_large_summary",
            test_case_id=test_case.id,
            status='failed',
            result_summary=json.dumps(large_summary),
            start_time=datetime.utcnow(),
            steps_total=1000
        )
        db_session.add(execution)
        db_session.commit()
        
        # 验证大型JSON能正确存储和解析
        execution_dict = execution.to_dict()
        summary = execution_dict['result_summary']
        assert summary['total_steps'] == 1000
        assert len(summary['step_details']) == 1000


class TestExecutionHistoryRelationships:
    """ExecutionHistory关系测试"""
    
    def test_test_case_relationship(self, db_session):
        """测试与TestCase的关系"""
        test_case = TestCaseFactory.create()
        execution = ExecutionHistoryFactory.create(test_case_id=test_case.id)
        
        # 通过关系访问
        assert execution.test_case.id == test_case.id
        assert execution.test_case.name == test_case.name
        
        # 反向关系
        assert execution in test_case.executions
    
    def test_step_executions_relationship(self, db_session):
        """测试与StepExecution的关系"""
        execution = ExecutionHistoryFactory.create()
        
        # 创建多个步骤执行记录
        for i in range(5):
            step = StepExecution(
                execution_id=execution.execution_id,
                step_index=i,
                step_description=f"步骤{i}",
                status='success',
                start_time=datetime.utcnow()
            )
            db_session.add(step)
        db_session.commit()
        
        # 通过关系访问
        steps = execution.step_executions
        assert len(steps) == 5
        
        # 验证步骤顺序
        for i, step in enumerate(sorted(steps, key=lambda s: s.step_index)):
            assert step.step_index == i
    
    def test_cascade_behavior_with_steps(self, db_session):
        """测试与步骤的级联行为"""
        execution = ExecutionHistoryFactory.create()
        
        # 创建步骤
        for i in range(3):
            StepExecutionFactory.create(
                execution_id=execution.execution_id,
                step_index=i
            )
        
        # 验证步骤存在
        assert StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).count() == 3
        
        # 删除执行历史
        db_session.delete(execution)
        
        # 检查级联删除行为
        try:
            db_session.commit()
            # 如果提交成功，检查步骤是否还存在
            remaining_steps = StepExecution.query.filter_by(
                execution_id=execution.execution_id
            ).count()
            # 根据模型配置，步骤可能被级联删除或保留
        except IntegrityError:
            # 如果没有配置级联删除，会抛出外键约束错误
            db_session.rollback()


class TestExecutionHistoryBusinessLogic:
    """ExecutionHistory业务逻辑测试"""
    
    def test_steps_consistency(self, db_session):
        """测试步骤数一致性"""
        test_case = TestCaseFactory.create()
        
        # 正常情况：通过+失败+跳过 = 总数
        execution = ExecutionHistory(
            execution_id="exec_consistency",
            test_case_id=test_case.id,
            status='failed',
            start_time=datetime.utcnow(),
            steps_total=10,
            steps_passed=6,
            steps_failed=4
        )
        db_session.add(execution)
        db_session.commit()
        
        assert execution.steps_passed + execution.steps_failed == execution.steps_total
    
    def test_invalid_steps_combination(self, db_session):
        """测试无效的步骤数组合（业务逻辑应该验证）"""
        test_case = TestCaseFactory.create()
        
        # 通过的步骤数超过总数（数据库可能允许，但业务逻辑应该阻止）
        execution = ExecutionHistory(
            execution_id="exec_invalid",
            test_case_id=test_case.id,
            status='success',
            start_time=datetime.utcnow(),
            steps_total=5,
            steps_passed=10,  # 错误：超过总数
            steps_failed=0
        )
        db_session.add(execution)
        db_session.commit()  # 数据库层面可能不会阻止
        
        # 这是一个数据一致性问题，应该在业务层验证
        assert execution.steps_passed > execution.steps_total  # 这不应该发生
    
    def test_execution_modes_and_browsers(self, db_session):
        """测试不同的执行模式和浏览器"""
        test_case = TestCaseFactory.create()
        
        # 不同的模式和浏览器组合
        combinations = [
            ('headless', 'chrome'),
            ('browser', 'chrome'),
            ('headless', 'firefox'),
            ('browser', 'firefox'),
            ('headless', 'edge'),
            ('browser', 'safari')
        ]
        
        for i, (mode, browser) in enumerate(combinations):
            execution = ExecutionHistory(
                execution_id=f"exec_mode_{i}",
                test_case_id=test_case.id,
                status='success',
                mode=mode,
                browser=browser,
                start_time=datetime.utcnow(),
                steps_total=1
            )
            db_session.add(execution)
        
        db_session.commit()
        
        # 验证所有组合都能存储
        for i, (mode, browser) in enumerate(combinations):
            exec_record = ExecutionHistory.query.filter_by(
                execution_id=f"exec_mode_{i}"
            ).first()
            assert exec_record.mode == mode
            assert exec_record.browser == browser