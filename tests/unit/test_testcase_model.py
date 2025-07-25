"""
TestCase模型完整测试
包含基础功能测试、边界值测试、约束测试等
"""
import pytest
import json
from datetime import datetime
from sqlalchemy.exc import IntegrityError, DataError
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web_gui.models import db, TestCase, ExecutionHistory
from tests.unit.factories import TestCaseFactory, ExecutionHistoryFactory


class TestTestCaseBasicOperations:
    """TestCase基础操作测试"""
    
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
        original_name = test_case.name
        
        test_case.name = "更新后的测试用例名称"
        test_case.priority = 5
        db_session.commit()
        
        assert test_case.name == "更新后的测试用例名称"
        assert test_case.priority == 5
        assert test_case.name != original_name
    
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


class TestTestCaseValidation:
    """TestCase数据验证测试"""
    
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


class TestTestCaseConstraints:
    """TestCase约束测试"""
    
    def test_name_required_constraint(self, db_session):
        """测试name字段必填约束"""
        with pytest.raises(IntegrityError):
            test_case = TestCase(
                # name字段缺失
                steps=json.dumps([])
            )
            db_session.add(test_case)
            db_session.commit()
        db_session.rollback()
    
    def test_steps_required_constraint(self, db_session):
        """测试steps字段必填约束"""
        with pytest.raises(IntegrityError):
            test_case = TestCase(
                name="测试用例",
                # steps字段缺失
            )
            db_session.add(test_case)
            db_session.commit()
        db_session.rollback()
    
    def test_default_values(self, db_session):
        """测试默认值"""
        test_case = TestCase(
            name="默认值测试",
            steps=json.dumps([])
            # 不设置其他字段，使用默认值
        )
        db_session.add(test_case)
        db_session.commit()
        
        assert test_case.priority == 3  # 默认优先级
        assert test_case.is_active is True  # 默认激活
        assert test_case.created_at is not None
        assert test_case.updated_at is not None
    
    def test_cascade_delete_protection(self, db_session):
        """测试级联删除保护"""
        # 创建有执行历史的测试用例
        test_case = TestCaseFactory.create()
        ExecutionHistoryFactory.create(test_case_id=test_case.id)
        
        # 尝试删除测试用例
        db_session.delete(test_case)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


class TestTestCaseBoundaries:
    """TestCase边界值测试"""
    
    def test_name_length_boundaries(self, db_session):
        """测试名称长度边界"""
        # 最大长度（255字符）
        max_name = "a" * 255
        test_case = TestCase(
            name=max_name,
            steps=json.dumps([])
        )
        db_session.add(test_case)
        db_session.commit()
        assert len(test_case.name) == 255
        
        # 空名称
        test_case2 = TestCase(
            name="",
            steps=json.dumps([])
        )
        db_session.add(test_case2)
        db_session.commit()  # SQLite可能允许
        assert test_case2.name == ""
    
    def test_priority_boundaries(self, db_session):
        """测试优先级边界值"""
        # 边界内外的值
        priorities = [0, 1, 3, 5, 6, 100, -1]
        for priority in priorities:
            test_case = TestCase(
                name=f"优先级{priority}测试",
                priority=priority,
                steps=json.dumps([])
            )
            db_session.add(test_case)
        
        db_session.commit()
        # 数据库应该接受所有值，但业务逻辑可能需要验证
    
    def test_large_steps_json(self, db_session):
        """测试大型JSON步骤数据"""
        # 创建1000个步骤
        large_steps = []
        for i in range(1000):
            large_steps.append({
                "action": f"action_{i}",
                "params": {
                    "text": f"这是第{i}个步骤" * 10,
                    "locate": f"元素{i}"
                },
                "description": f"执行第{i}个操作"
            })
        
        test_case = TestCase(
            name="千步测试用例",
            steps=json.dumps(large_steps)
        )
        db_session.add(test_case)
        db_session.commit()
        
        # 验证存储和解析
        case_dict = test_case.to_dict()
        assert len(case_dict['steps']) == 1000
        assert case_dict['steps'][0]['action'] == 'action_0'
        assert case_dict['steps'][999]['action'] == 'action_999'
    
    def test_special_characters_in_json(self, db_session):
        """测试JSON中的特殊字符"""
        special_steps = [
            {
                "action": "input",
                "params": {
                    "text": "包含'单引号'的文本",
                    "text2": '包含"双引号"的文本',
                    "text3": "包含\\反斜杠\\的文本",
                    "text4": "包含\n换行\n的文本",
                    "text5": "包含emoji😀🎉的文本"
                }
            }
        ]
        
        test_case = TestCase(
            name="特殊字符JSON测试",
            steps=json.dumps(special_steps)
        )
        db_session.add(test_case)
        db_session.commit()
        
        # 验证特殊字符正确保存
        case_dict = test_case.to_dict()
        params = case_dict['steps'][0]['params']
        assert "单引号" in params['text']
        assert "双引号" in params['text2']
        assert "反斜杠" in params['text3']
        assert "\n" in params['text4']
        assert "😀" in params['text5']
    
    def test_unicode_support(self, db_session):
        """测试Unicode支持"""
        unicode_name = "测试用例🌟 العربية 日本語 한국어"
        unicode_steps = [{
            "action": "test",
            "params": {
                "中文": "测试",
                "العربية": "اختبار",
                "日本語": "テスト",
                "한국어": "테스트"
            }
        }]
        
        test_case = TestCase(
            name=unicode_name,
            steps=json.dumps(unicode_steps, ensure_ascii=False)
        )
        db_session.add(test_case)
        db_session.commit()
        
        assert test_case.name == unicode_name
        case_dict = test_case.to_dict()
        assert case_dict['steps'][0]['params']['中文'] == "测试"


class TestTestCaseRelationships:
    """TestCase关系测试"""
    
    def test_execution_history_relationship(self, db_session):
        """测试与ExecutionHistory的关系"""
        test_case = TestCaseFactory.create()
        
        # 创建多个执行历史
        for i in range(5):
            ExecutionHistoryFactory.create(
                test_case_id=test_case.id,
                status='success' if i % 2 == 0 else 'failed'
            )
        
        # 通过关系访问
        executions = test_case.executions
        assert len(executions) == 5
        
        # 验证反向关系
        for execution in executions:
            assert execution.test_case.id == test_case.id
    
    def test_massive_executions(self, db_session):
        """测试大量执行历史的性能"""
        test_case = TestCaseFactory.create()
        
        # 创建100个执行历史
        for i in range(100):
            ExecutionHistoryFactory.create(
                test_case_id=test_case.id,
                status='success' if i < 80 else 'failed'
            )
        
        # 测试统计计算性能
        case_dict = test_case.to_dict()
        assert case_dict['execution_count'] == 100
        assert case_dict['success_rate'] == 80.0