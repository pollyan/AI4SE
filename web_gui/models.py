"""
数据模型定义
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class TestCase(db.Model):
    """测试用例模型"""
    __tablename__ = 'test_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.Text, nullable=False)  # JSON string
    tags = db.Column(db.String(500))
    category = db.Column(db.String(100))
    priority = db.Column(db.Integer, default=3)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': json.loads(self.steps) if self.steps else [],
            'tags': self.tags.split(',') if self.tags else [],
            'category': self.category,
            'priority': self.priority,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            name=data.get('name'),
            description=data.get('description'),
            steps=json.dumps(data.get('steps', [])),
            tags=','.join(data.get('tags', [])),
            category=data.get('category'),
            priority=data.get('priority', 3),
            created_by=data.get('created_by', 'system')
        )

class ExecutionHistory(db.Model):
    """执行历史模型"""
    __tablename__ = 'execution_history'
    
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(50), unique=True, nullable=False)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_cases.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # running, success, failed, stopped
    mode = db.Column(db.String(20), default='headless')  # browser, headless
    browser = db.Column(db.String(50), default='chrome')
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # 执行时间(秒)
    steps_total = db.Column(db.Integer)
    steps_passed = db.Column(db.Integer)
    steps_failed = db.Column(db.Integer)
    result_summary = db.Column(db.Text)  # JSON string
    screenshots_path = db.Column(db.Text)
    logs_path = db.Column(db.Text)
    error_message = db.Column(db.Text)
    error_stack = db.Column(db.Text)
    executed_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关系
    test_case = db.relationship('TestCase', backref=db.backref('executions', lazy=True))
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'test_case_id': self.test_case_id,
            'test_case_name': self.test_case.name if self.test_case else None,
            'status': self.status,
            'mode': self.mode,
            'browser': self.browser,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'steps_total': self.steps_total,
            'steps_passed': self.steps_passed,
            'steps_failed': self.steps_failed,
            'result_summary': json.loads(self.result_summary) if self.result_summary else {},
            'screenshots_path': self.screenshots_path,
            'logs_path': self.logs_path,
            'error_message': self.error_message,
            'executed_by': self.executed_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class StepExecution(db.Model):
    """步骤执行详情模型"""
    __tablename__ = 'step_executions'
    
    id = db.Column(db.Integer, primary_key=True)
    execution_id = db.Column(db.String(50), db.ForeignKey('execution_history.execution_id'), nullable=False)
    step_index = db.Column(db.Integer, nullable=False)
    step_description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # success, failed, skipped
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)
    screenshot_path = db.Column(db.Text)
    ai_confidence = db.Column(db.Float)
    ai_decision = db.Column(db.Text)  # JSON string
    error_message = db.Column(db.Text)
    
    # 关系
    execution = db.relationship('ExecutionHistory', backref=db.backref('step_executions', lazy=True))
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'execution_id': self.execution_id,
            'step_index': self.step_index,
            'step_description': self.step_description,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'screenshot_path': self.screenshot_path,
            'ai_confidence': self.ai_confidence,
            'ai_decision': json.loads(self.ai_decision) if self.ai_decision else {},
            'error_message': self.error_message
        }

class Template(db.Model):
    """测试模板模型"""
    __tablename__ = 'templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    steps_template = db.Column(db.Text, nullable=False)  # JSON string
    parameters = db.Column(db.Text)  # JSON string - 模板参数定义
    usage_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'steps_template': json.loads(self.steps_template) if self.steps_template else [],
            'parameters': json.loads(self.parameters) if self.parameters else {},
            'usage_count': self.usage_count,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_public': self.is_public
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建实例"""
        return cls(
            name=data.get('name'),
            description=data.get('description'),
            category=data.get('category'),
            steps_template=json.dumps(data.get('steps_template', [])),
            parameters=json.dumps(data.get('parameters', {})),
            created_by=data.get('created_by', 'system'),
            is_public=data.get('is_public', False)
        )
