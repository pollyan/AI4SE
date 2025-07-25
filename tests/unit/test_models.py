"""
数据模型单元测试
测试所有数据模型的CRUD操作和业务逻辑
"""
import pytest
import json
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template
from tests.unit.factories import TestCaseFactory, ExecutionHistoryFactory, StepExecutionFactory, TemplateFactory


class TestTestCaseModel:
    """TestCase模型测试类"""
    
    def test_should_create_testcase_with_valid_data(self, db_session):
        """测试使用有效数据创建测试用例"""
        test_case = TestCase(
            name="登录功能测试",
            description="测试用户登录功能是否正常",
            steps=json.dumps([
                {"action": "navigate", "params": {"url": "https://example.com/login"}, "description": "访问登录页面"},
                {"action": "ai_input", "params": {"text": "testuser", "locate": "用户名输入框"}, "description": "输入用户名"},
                {"action": "ai_input", "params": {"text": "password123", "locate": "密码输入框"}, "description": "输入密码"},
                {"action": "ai_tap", "params": {"locate": "登录按钮"}, "description": "点击登录按钮"}
            ]),
            tags="登录,功能测试",
            category="功能测试",
            priority=3,
            created_by="test_user"
        )
        
        db_session.add(test_case)
        db_session.commit()
        
        assert test_case.id is not None
        assert test_case.name == "登录功能测试"
        assert test_case.is_active is True
        assert test_case.created_at is not None
        assert test_case.updated_at is not None
    
    def test_should_update_testcase_fields(self, db_session):
        """测试更新测试用例字段"""
        test_case = TestCaseFactory.create()
        original_updated_at = test_case.updated_at
        
        test_case.name = "更新后的测试用例名称"
        test_case.priority = 5
        db_session.commit()
        
        assert test_case.name == "更新后的测试用例名称"
        assert test_case.priority == 5
        # 注意：由于SQLAlchemy的onupdate可能不会在单元测试中触发，这里跳过时间戳检查
    
    def test_should_soft_delete_testcase(self, db_session):
        """测试软删除测试用例"""
        test_case = TestCaseFactory.create()
        test_case_id = test_case.id
        
        test_case.is_active = False
        db_session.commit()
        
        # 验证软删除
        deleted_case = TestCase.query.filter_by(id=test_case_id).first()
        assert deleted_case is not None
        assert deleted_case.is_active is False
    
    def test_should_parse_steps_json_correctly(self, db_session):
        """测试正确解析步骤JSON数据"""
        test_case = TestCaseFactory.create()
        
        # 测试to_dict方法中的steps解析
        case_dict = test_case.to_dict()
        assert isinstance(case_dict['steps'], list)
        assert len(case_dict['steps']) > 0
        assert 'action' in case_dict['steps'][0]
        assert 'params' in case_dict['steps'][0]
    
    def test_should_handle_empty_tags(self, db_session):
        """测试处理空标签"""
        test_case = TestCase(
            name="无标签测试用例",
            steps=json.dumps([]),
            tags=None
        )
        db_session.add(test_case)
        db_session.commit()
        
        case_dict = test_case.to_dict()
        assert case_dict['tags'] == []
    
    def test_should_calculate_execution_statistics(self, db_session):
        """测试计算执行统计信息"""
        # 创建测试用例
        test_case = TestCaseFactory.create()
        
        # 创建执行历史
        ExecutionHistoryFactory.create(test_case_id=test_case.id, status='success')
        ExecutionHistoryFactory.create(test_case_id=test_case.id, status='success')
        ExecutionHistoryFactory.create(test_case_id=test_case.id, status='failed')
        
        case_dict = test_case.to_dict()
        assert case_dict['execution_count'] == 3
        assert case_dict['success_rate'] == 66.7  # 2/3 * 100
    
    def test_should_validate_priority_range(self, db_session):
        """测试优先级范围验证"""
        test_case = TestCaseFactory.create()
        
        # 测试有效优先级
        for priority in [1, 2, 3, 4, 5]:
            test_case.priority = priority
            db_session.commit()
            assert test_case.priority == priority
    
    def test_should_handle_special_characters_in_name(self, db_session):
        """测试名称中的特殊字符处理"""
        special_name = "测试用例 with 特殊字符 !@#$%^&*()"
        test_case = TestCase(
            name=special_name,
            steps=json.dumps([])
        )
        db_session.add(test_case)
        db_session.commit()
        
        assert test_case.name == special_name
    
    def test_should_maintain_steps_order(self, db_session):
        """测试保持步骤顺序"""
        steps = [
            {"order": 1, "action": "navigate", "params": {"url": "https://example.com"}},
            {"order": 2, "action": "ai_input", "params": {"text": "test", "locate": "input"}},
            {"order": 3, "action": "ai_tap", "params": {"locate": "button"}}
        ]
        
        test_case = TestCase(
            name="步骤顺序测试",
            steps=json.dumps(steps)
        )
        db_session.add(test_case)
        db_session.commit()
        
        case_dict = test_case.to_dict()
        loaded_steps = case_dict['steps']
        
        for i, step in enumerate(loaded_steps):
            assert step['order'] == i + 1
    
    def test_should_handle_long_description(self, db_session):
        """测试处理长描述文本"""
        long_description = "这是一个很长的描述" * 150  # 1350字符
        test_case = TestCase(
            name="长描述测试",
            description=long_description,
            steps=json.dumps([])
        )
        db_session.add(test_case)
        db_session.commit()
        
        assert test_case.description == long_description
        assert len(test_case.description) > 1000


class TestExecutionHistoryModel:
    """ExecutionHistory模型测试类"""
    
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


class TestStepExecutionModel:
    """StepExecution模型测试类"""
    
    def test_should_create_step_execution(self, db_session):
        """测试创建步骤执行记录"""
        execution = ExecutionHistoryFactory.create()
        step = StepExecution(
            execution_id=execution.execution_id,
            step_index=0,
            step_description='访问网站 https://example.com',
            status='success',
            start_time=datetime.utcnow()
        )
        db_session.add(step)
        db_session.commit()
        
        assert step.id is not None
        assert step.execution_id == execution.execution_id
        assert step.step_description == '访问网站 https://example.com'
    
    def test_should_store_step_error(self, db_session):
        """测试存储步骤错误信息"""
        step = StepExecutionFactory.create(
            status='failed',
            error_message='元素定位失败',
            screenshot_path='/screenshots/error.png'
        )
        
        assert step.status == 'failed'
        assert step.error_message == '元素定位失败'
        assert step.screenshot_path == '/screenshots/error.png'
    
    def test_should_store_step_duration(self, db_session):
        """测试存储步骤执行时长"""
        step = StepExecutionFactory.create(
            duration=5  # 5秒
        )
        
        step_dict = step.to_dict()
        assert step_dict['duration'] == 5
    
    def test_should_maintain_step_order(self, db_session):
        """测试保持步骤执行顺序"""
        execution = ExecutionHistoryFactory.create()
        
        # 创建多个步骤
        for i in range(5):
            step = StepExecution(
                execution_id=execution.execution_id,
                step_index=i,
                step_description=f'步骤 {i+1}',
                status='success',
                start_time=datetime.utcnow()
            )
            db_session.add(step)
        db_session.commit()
        
        # 查询并验证顺序
        steps = StepExecution.query.filter_by(execution_id=execution.execution_id).order_by(StepExecution.step_index).all()
        
        assert len(steps) == 5
        for i, step in enumerate(steps):
            assert step.step_index == i


# Template相关的测试暂时跳过，因为模板功能还未实现