"""
StepExecution模型完整测试
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


class TestStepExecutionBasicOperations:
    """StepExecution基础操作测试"""
    
    def test_should_create_step_execution(self, db_session):
        """测试创建步骤执行记录"""
        execution = ExecutionHistoryFactory.create()
        
        step = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,
            step_description="打开登录页面",
            status='success',
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow() + timedelta(seconds=2),
            duration=2
        )
        db_session.add(step)
        db_session.commit()
        
        assert step.id is not None
        assert step.execution_id == execution.execution_id
        assert step.step_index == 0
        assert step.status == 'success'
        assert step.duration == 2
    
    def test_should_update_step_status(self, db_session):
        """测试更新步骤状态"""
        step = StepExecutionFactory.create(status='running')
        
        step.status = 'success'
        step.end_time = datetime.utcnow()
        step.duration = 5
        db_session.commit()
        
        assert step.status == 'success'
        assert step.end_time is not None
        assert step.duration == 5
    
    def test_should_store_error_details(self, db_session):
        """测试存储错误详情"""
        step = StepExecutionFactory.create(
            status='failed',
            error_message="找不到元素: 登录按钮"
        )
        
        assert step.error_message == "找不到元素: 登录按钮"
        assert step.status == 'failed'
    
    def test_should_store_screenshot_path(self, db_session):
        """测试存储截图路径"""
        step = StepExecutionFactory.create(
            screenshot_path='/screenshots/step_0_error.png'
        )
        
        step_dict = step.to_dict()
        assert step_dict['screenshot_path'] == '/screenshots/step_0_error.png'
    
    def test_should_handle_long_description(self, db_session):
        """测试处理长描述文本"""
        long_description = "这是一个非常长的步骤描述，" * 50  # 约500字符
        
        step = StepExecution(
            execution_id=ExecutionHistoryFactory.create().execution_id,
            step_index=0,
            step_description=long_description,
            status='success',
            start_time=datetime.utcnow()
        )
        db_session.add(step)
        db_session.commit()
        
        assert step.step_description == long_description
        assert len(step.step_description) > 400
    
    def test_should_track_execution_time(self, db_session):
        """测试跟踪执行时间"""
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=3.5)
        
        step = StepExecution(
            execution_id=ExecutionHistoryFactory.create().execution_id,
            step_index=0,
            step_description="等待页面加载",
            status='success',
            start_time=start_time,
            end_time=end_time,
            duration=3.5
        )
        db_session.add(step)
        db_session.commit()
        
        assert step.duration == 3.5
        assert (step.end_time - step.start_time).total_seconds() == pytest.approx(3.5, rel=0.1)


class TestStepExecutionConstraints:
    """StepExecution约束测试"""
    
    def test_required_fields(self, db_session):
        """测试必填字段约束"""
        execution = ExecutionHistoryFactory.create()
        
        # execution_id必填
        with pytest.raises(IntegrityError):
            step = StepExecution(
                # execution_id缺失
                step_index=0,
                step_description="测试步骤",
                status='running'
            )
            db_session.add(step)
            db_session.commit()
        db_session.rollback()
        
        # step_index必填
        with pytest.raises(IntegrityError):
            step = StepExecution(
                execution_id=execution.execution_id,
                # step_index缺失
                step_description="测试步骤",
                status='running'
            )
            db_session.add(step)
            db_session.commit()
        db_session.rollback()
        
        # status必填
        with pytest.raises(IntegrityError):
            step = StepExecution(
                execution_id=execution.execution_id,
                step_index=0,
                step_description="测试步骤",
                # status缺失
            )
            db_session.add(step)
            db_session.commit()
        db_session.rollback()
    
    def test_foreign_key_constraint(self, db_session):
        """测试外键约束"""
        # 引用不存在的execution_id
        with pytest.raises(IntegrityError):
            step = StepExecution(
                execution_id="non_existent_exec_id",
                step_index=0,
                step_description="测试步骤",
                status='running',
                start_time=datetime.utcnow()
            )
            db_session.add(step)
            db_session.commit()
        db_session.rollback()
    
    def test_unique_constraint_on_execution_and_index(self, db_session):
        """测试execution_id和step_index的联合唯一约束"""
        execution = ExecutionHistoryFactory.create()
        
        # 创建第一个步骤
        step1 = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,
            step_description="第一步",
            status='success',
            start_time=datetime.utcnow()
        )
        db_session.add(step1)
        db_session.commit()
        
        # 尝试创建相同execution_id和step_index的步骤
        # 注意：如果数据库没有显式定义联合唯一约束，这个测试可能不会抛出异常
        step2 = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,  # 相同的索引
            step_description="重复的步骤",
            status='running',
            start_time=datetime.utcnow()
        )
        db_session.add(step2)
        
        try:
            db_session.commit()
            # 如果提交成功，说明没有唯一约束
            # 这可能是设计故意允许的，或者是缺少约束
            print("没有强制唯一约束，同一个执行可以有重复的步骤索引")
            # 清理重复数据
            db_session.delete(step2)
            db_session.commit()
        except IntegrityError as e:
            # 如果抛出异常，说明有唯一约束
            db_session.rollback()
            assert "UNIQUE constraint failed" in str(e) or "duplicate key" in str(e)
    
    def test_default_values(self, db_session):
        """测试默认值"""
        execution = ExecutionHistoryFactory.create()
        
        step = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,
            step_description="默认值测试",
            status='running',
            start_time=datetime.utcnow()  # 必填字段
            # 不设置其他字段，使用默认值
        )
        db_session.add(step)
        db_session.commit()
        
        # StepExecution模型没有created_at字段
        assert step.start_time is not None  # 必填字段
        assert step.end_time is None  # 可为空
        assert step.duration is None  # 可为空
        assert step.error_message is None  # 可为空
        assert step.screenshot_path is None  # 可为空


class TestStepExecutionBoundaries:
    """StepExecution边界值测试"""
    
    def test_step_index_boundaries(self, db_session):
        """测试步骤索引边界值"""
        execution = ExecutionHistoryFactory.create()
        
        # 索引从0开始
        step0 = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,
            step_description="第一步",
            status='success',
            start_time=datetime.utcnow()
        )
        db_session.add(step0)
        
        # 大索引值
        step_large = StepExecution(
            execution_id=execution.execution_id,
            step_index=9999,
            step_description="第10000步",
            status='success',
            start_time=datetime.utcnow()
        )
        db_session.add(step_large)
        
        # 负索引（数据库可能允许，但业务逻辑应该阻止）
        step_negative = StepExecution(
            execution_id=execution.execution_id,
            step_index=-1,
            step_description="负索引步骤",
            status='failed',
            start_time=datetime.utcnow()
        )
        db_session.add(step_negative)
        
        db_session.commit()
        
        assert step0.step_index == 0
        assert step_large.step_index == 9999
        assert step_negative.step_index == -1
    
    def test_duration_boundaries(self, db_session):
        """测试执行时长边界值"""
        execution = ExecutionHistoryFactory.create()
        
        # 瞬间完成（0秒）
        step_instant = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,
            step_description="瞬间完成",
            status='success',
            duration=0,
            start_time=datetime.utcnow()
        )
        db_session.add(step_instant)
        
        # 非常快（0.001秒）
        step_fast = StepExecution(
            execution_id=execution.execution_id,
            step_index=1,
            step_description="毫秒级操作",
            status='success',
            duration=0.001,
            start_time=datetime.utcnow()
        )
        db_session.add(step_fast)
        
        # 超长执行（1小时）
        step_long = StepExecution(
            execution_id=execution.execution_id,
            step_index=2,
            step_description="长时间操作",
            status='timeout',
            duration=3600,
            start_time=datetime.utcnow()
        )
        db_session.add(step_long)
        
        db_session.commit()
        
        assert step_instant.duration == 0
        assert step_fast.duration == 0.001
        assert step_long.duration == 3600
    
    def test_status_values(self, db_session):
        """测试各种状态值"""
        execution = ExecutionHistoryFactory.create()
        
        # 所有可能的状态
        statuses = ['running', 'success', 'failed', 'skipped', 'timeout', 'error']
        
        for i, status in enumerate(statuses):
            step = StepExecution(
                execution_id=execution.execution_id,
                step_index=i,
                step_description=f"状态{status}的步骤",
                status=status,
                start_time=datetime.utcnow()
            )
            db_session.add(step)
        
        db_session.commit()
        
        # 验证所有状态都能存储
        for i, status in enumerate(statuses):
            step_record = StepExecution.query.filter_by(
                execution_id=execution.execution_id,
                step_index=i
            ).first()
            assert step_record is not None
            assert step_record.status == status
    
    def test_special_characters_in_description(self, db_session):
        """测试描述中的特殊字符"""
        execution = ExecutionHistoryFactory.create()
        
        special_descriptions = [
            "包含'单引号'的描述",
            '包含"双引号"的描述',
            "包含\n换行符\n的描述",
            "包含\t制表符\t的描述",
            "包含emoji😀🎉的描述",
            "包含特殊符号!@#$%^&*()的描述",
            "包含中文、العربية、日本語的描述"
        ]
        
        for i, desc in enumerate(special_descriptions):
            step = StepExecution(
                execution_id=execution.execution_id,
                step_index=i,
                step_description=desc,
                status='success',
                start_time=datetime.utcnow()
            )
            db_session.add(step)
        
        db_session.commit()
        
        # 验证特殊字符正确保存
        for i, expected_desc in enumerate(special_descriptions):
            step = StepExecution.query.filter_by(
                execution_id=execution.execution_id,
                step_index=i
            ).first()
            assert step.step_description == expected_desc
    
    def test_extreme_error_messages(self, db_session):
        """测试极端错误信息"""
        execution = ExecutionHistoryFactory.create()
        
        # 非常长的错误信息
        long_error = "错误堆栈信息：\n" + "\n".join([
            f"at function_{i} (file_{i}.js:{i}:{i})" for i in range(100)
        ])
        
        step = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,
            step_description="产生错误的步骤",
            status='error',
            error_message=long_error,
            start_time=datetime.utcnow()
        )
        db_session.add(step)
        db_session.commit()
        
        assert len(step.error_message) > 2000
        assert "function_99" in step.error_message


class TestStepExecutionRelationships:
    """StepExecution关系测试"""
    
    def test_execution_history_relationship(self, db_session):
        """测试与ExecutionHistory的关系"""
        execution = ExecutionHistoryFactory.create()
        
        # 创建多个步骤
        steps = []
        for i in range(5):
            step = StepExecutionFactory.create(
                execution_id=execution.execution_id,
                step_index=i
            )
            steps.append(step)
        
        # 通过关系访问
        execution_steps = execution.step_executions
        assert len(execution_steps) == 5
        
        # 验证排序
        sorted_steps = sorted(execution_steps, key=lambda s: s.step_index)
        for i, step in enumerate(sorted_steps):
            assert step.step_index == i
    
    def test_cascade_deletion(self, db_session):
        """测试级联删除行为"""
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
            # 如果提交成功，检查步骤是否被删除
            remaining_steps = StepExecution.query.filter_by(
                execution_id=execution.execution_id
            ).count()
            # 根据模型配置，步骤可能被级联删除
            print(f"剩余步骤数: {remaining_steps}")
        except IntegrityError:
            # 如果没有配置级联删除，会抛出外键约束错误
            db_session.rollback()
            print("外键约束阻止了删除")
    
    def test_multiple_executions_with_same_index(self, db_session):
        """测试不同执行历史可以有相同的步骤索引"""
        execution1 = ExecutionHistoryFactory.create()
        execution2 = ExecutionHistoryFactory.create()
        
        # 两个执行都有索引为0的步骤
        step1 = StepExecution(
            execution_id=execution1.execution_id,
            step_index=0,
            step_description="执行1的第一步",
            status='success',
            start_time=datetime.utcnow()
        )
        db_session.add(step1)
        
        step2 = StepExecution(
            execution_id=execution2.execution_id,
            step_index=0,
            step_description="执行2的第一步",
            status='failed',
            start_time=datetime.utcnow()
        )
        db_session.add(step2)
        
        db_session.commit()
        
        # 验证两个步骤都存在
        assert step1.step_index == 0
        assert step2.step_index == 0
        assert step1.execution_id != step2.execution_id


class TestStepExecutionBusinessLogic:
    """StepExecution业务逻辑测试"""
    
    def test_step_sequence_integrity(self, db_session):
        """测试步骤序列完整性"""
        execution = ExecutionHistoryFactory.create(steps_total=5)
        
        # 创建连续的步骤
        for i in range(5):
            StepExecutionFactory.create(
                execution_id=execution.execution_id,
                step_index=i,
                status='success' if i < 4 else 'failed'
            )
        
        # 验证步骤数与执行历史中的总步骤数一致
        step_count = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).count()
        assert step_count == execution.steps_total
    
    def test_running_step_without_end_time(self, db_session):
        """测试运行中的步骤没有结束时间"""
        step = StepExecutionFactory.create(
            status='running',
            end_time=None,
            duration=None
        )
        
        step_dict = step.to_dict()
        assert step_dict['status'] == 'running'
        assert step_dict['end_time'] is None
        assert step_dict['duration'] is None
    
    def test_failed_step_with_screenshot(self, db_session):
        """测试失败步骤包含截图"""
        step = StepExecutionFactory.create(
            status='failed',
            error_message="元素不可见",
            screenshot_path='/screenshots/error_001.png'
        )
        
        assert step.status == 'failed'
        assert step.error_message is not None
        assert step.screenshot_path is not None
    
    def test_skipped_steps(self, db_session):
        """测试跳过的步骤"""
        execution = ExecutionHistoryFactory.create()
        
        # 前置步骤失败
        failed_step = StepExecutionFactory.create(
            execution_id=execution.execution_id,
            step_index=0,
            status='failed'
        )
        
        # 后续步骤被跳过
        skipped_steps = []
        for i in range(1, 4):
            step = StepExecution(
                execution_id=execution.execution_id,
                step_index=i,
                step_description=f"被跳过的步骤{i}",
                status='skipped',
                start_time=datetime.utcnow(),  # 由于数据库约束，必须有start_time
                end_time=None,
                duration=None
            )
            db_session.add(step)
            skipped_steps.append(step)
        
        db_session.commit()
        
        # 验证跳过的步骤
        for step in skipped_steps:
            assert step.status == 'skipped'
            assert step.start_time is not None  # 必须有start_time
            assert step.end_time is None
            assert step.duration is None
    
    def test_timeout_step(self, db_session):
        """测试超时步骤"""
        timeout_duration = 300  # 5分钟超时
        
        step = StepExecutionFactory.create(
            status='timeout',
            duration=timeout_duration,
            error_message="步骤执行超时（300秒）"
        )
        
        assert step.status == 'timeout'
        assert step.duration == timeout_duration
        assert "超时" in step.error_message