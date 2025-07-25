"""
测试数据工厂类
使用factory_boy创建测试数据
"""
import factory
from factory.alchemy import SQLAlchemyModelFactory
from datetime import datetime, timedelta
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template


class TestCaseFactory(SQLAlchemyModelFactory):
    """TestCase模型工厂"""
    class Meta:
        model = TestCase
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    name = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=200)
    steps = factory.LazyFunction(lambda: json.dumps([
        {
            "action": "navigate",
            "params": {"url": "https://example.com"},
            "description": "访问示例网站"
        },
        {
            "action": "ai_input",
            "params": {"text": "测试内容", "locate": "输入框"},
            "description": "输入测试内容"
        },
        {
            "action": "ai_tap",
            "params": {"locate": "提交按钮"},
            "description": "点击提交按钮"
        }
    ]))
    tags = factory.LazyFunction(lambda: ','.join(factory.Faker._get_faker().words(nb=3)))
    category = factory.Faker('word', ext_word_list=['功能测试', '回归测试', '集成测试', '性能测试'])
    priority = factory.Faker('random_int', min=1, max=5)
    created_by = factory.Faker('user_name')
    created_at = factory.Faker('date_time_this_year')
    updated_at = factory.LazyAttribute(lambda obj: obj.created_at)
    is_active = True


class ExecutionHistoryFactory(SQLAlchemyModelFactory):
    """ExecutionHistory模型工厂"""
    class Meta:
        model = ExecutionHistory
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    execution_id = factory.LazyFunction(lambda: f"exec_{factory.Faker._get_faker().uuid4()}")
    test_case_id = factory.LazyAttribute(lambda obj: TestCaseFactory.create().id)
    status = factory.Faker('random_element', elements=['success', 'failed', 'running', 'stopped'])
    mode = 'headless'
    browser = 'chrome'
    start_time = factory.Faker('date_time_this_month')
    end_time = factory.LazyAttribute(
        lambda obj: None if obj.status == 'running' else factory.Faker._get_faker().date_time_this_month()
    )
    duration = factory.LazyAttribute(
        lambda obj: None if obj.status == 'running' else factory.Faker._get_faker().random_int(min=10, max=300)
    )
    steps_total = factory.Faker('random_int', min=1, max=10)
    steps_passed = factory.LazyAttribute(
        lambda obj: obj.steps_total if obj.status == 'success' else factory.Faker._get_faker().random_int(min=0, max=obj.steps_total)
    )
    steps_failed = factory.LazyAttribute(
        lambda obj: 0 if obj.status == 'success' else factory.Faker._get_faker().random_int(min=0, max=obj.steps_total - obj.steps_passed)
    )
    result_summary = factory.LazyFunction(lambda: json.dumps({}))
    screenshots_path = None
    logs_path = None
    error_message = factory.LazyAttribute(
        lambda obj: None if obj.status == 'success' else factory.Faker._get_faker().sentence()
    )
    error_stack = None
    executed_by = factory.Faker('user_name')
    created_at = factory.Faker('date_time_this_month')


class StepExecutionFactory(SQLAlchemyModelFactory):
    """StepExecution模型工厂"""
    class Meta:
        model = StepExecution
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    execution_id = factory.LazyAttribute(lambda obj: ExecutionHistoryFactory.create().execution_id)
    step_index = factory.Sequence(lambda n: n)
    step_description = factory.Faker('sentence')
    status = factory.Faker('random_element', elements=['success', 'failed', 'skipped'])
    start_time = factory.LazyAttribute(
        lambda obj: factory.Faker._get_faker().date_time_between(start_date='-1hour', end_date='now') if obj.status != 'skipped' else datetime.utcnow()
    )
    end_time = factory.LazyAttribute(
        lambda obj: obj.start_time + timedelta(seconds=factory.Faker._get_faker().random_int(min=1, max=60)) if obj.start_time and obj.status != 'skipped' else None
    )
    duration = factory.LazyAttribute(
        lambda obj: (obj.end_time - obj.start_time).total_seconds() if obj.start_time and obj.end_time else None
    )
    screenshot_path = factory.LazyAttribute(
        lambda obj: f"/screenshots/step_{obj.id}.png" if obj.status == 'failed' else None
    )
    ai_confidence = factory.LazyAttribute(
        lambda obj: factory.Faker._get_faker().pyfloat(min_value=0.8, max_value=1.0) if obj.status == 'success' else factory.Faker._get_faker().pyfloat(min_value=0.3, max_value=0.8)
    )
    ai_decision = factory.LazyFunction(lambda: json.dumps({"element": "found", "confidence": "high"}))
    error_message = factory.LazyAttribute(
        lambda obj: None if obj.status == 'success' else factory.Faker._get_faker().sentence()
    )


class TemplateFactory(SQLAlchemyModelFactory):
    """Template模型工厂"""
    class Meta:
        model = Template
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    name = factory.Faker('sentence', nb_words=3)
    description = factory.Faker('text', max_nb_chars=150)
    steps_template = factory.LazyFunction(lambda: json.dumps([
        {
            "action": "navigate",
            "params": {"url": "{{url}}"},
            "description": "访问{{site_name}}"
        },
        {
            "action": "ai_input",
            "params": {"text": "{{search_text}}", "locate": "搜索框"},
            "description": "输入搜索内容"
        }
    ]))
    parameters = factory.LazyFunction(lambda: json.dumps({
        "url": {"type": "string", "description": "网站URL", "default": "https://example.com"},
        "site_name": {"type": "string", "description": "网站名称", "default": "示例网站"},
        "search_text": {"type": "string", "description": "搜索内容", "default": "测试"}
    }))
    category = factory.Faker('word', ext_word_list=['通用模板', '登录模板', '搜索模板', '表单模板'])
    created_by = factory.Faker('user_name')
    created_at = factory.Faker('date_time_this_year')
    is_public = False
    usage_count = factory.Faker('random_int', min=0, max=100)