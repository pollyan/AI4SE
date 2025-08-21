"""
Main Routes - 主要页面路由
从app_enhanced.py中提取的页面路由逻辑
"""

import json
import logging
from datetime import datetime
from flask import render_template, send_from_directory, redirect, url_for

from ..core.extensions import db
from ..models import TestCase, ExecutionHistory
from ..services.websocket_service import init_websocket_service

logger = logging.getLogger(__name__)

def register_main_routes(app):
    """注册主要页面路由"""
    
    # 初始化WebSocket服务
    init_websocket_service()
    
    @app.route('/')
    @app.route('/dashboard')
    def index():
        """主页"""
        return render_template('index.html')

    @app.route('/testcases')
    def testcases_page():
        """测试用例管理页面"""
        return render_template('testcases.html')

    @app.route('/testcases/create')
    def testcase_create_page():
        """测试用例创建页面"""
        # 创建一个空的测试用例对象用于创建模式
        class EmptyTestCase:
            def __init__(self):
                self.id = None
                self.name = ''
                self.description = ''
                self.category = '功能测试'  # 默认分类
                self.priority = 2
                self.tags = ''
                self.is_active = True
                self.created_by = 'admin'
                self.created_at = None
                self.updated_at = None
        
        empty_testcase = EmptyTestCase()
        
        return render_template('testcase_edit.html', 
                             testcase=empty_testcase,
                             steps_data='[]',
                             total_executions=0,
                             success_rate=0,
                             is_create_mode=True)

    @app.route('/testcases/<int:testcase_id>/edit')
    def testcase_edit_page(testcase_id):
        """测试用例编辑页面"""
        # 获取测试用例详情
        testcase = TestCase.query.get_or_404(testcase_id)
        
        # 获取执行统计信息
        execution_stats = db.session.query(ExecutionHistory).filter_by(test_case_id=testcase_id).all()
        total_executions = len(execution_stats)
        successful_executions = len([e for e in execution_stats if e.status == 'success'])
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        # 确保步骤数据是正确的JSON格式
        try:
            steps_data = json.loads(testcase.steps) if testcase.steps else []
        except (json.JSONDecodeError, TypeError):
            steps_data = []
        
        return render_template('testcase_edit.html', 
                             testcase=testcase,
                             steps_data=json.dumps(steps_data),
                             total_executions=total_executions,
                             success_rate=success_rate,
                             is_create_mode=False)

    @app.route('/execution')
    def execution_page():
        """执行控制台页面"""
        return render_template('execution.html')

    @app.route('/reports')
    def reports_page():
        """测试报告页面"""
        return render_template('reports.html')

    @app.route('/local-proxy')
    def local_proxy_page():
        """本地代理下载页面"""
        return render_template('local_proxy.html', current_date=datetime.utcnow().strftime('%Y-%m-%d'))

    @app.route('/step_editor')
    def step_editor_page():
        """步骤编辑器页面"""
        return render_template('step_editor.html')

    @app.route('/static/screenshots/<filename>')
    def screenshot_file(filename):
        """提供截图文件访问"""
        import os
        screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'screenshots')
        return send_from_directory(screenshot_dir, filename)

    @app.route('/debug_screenshot_history.html')
    def debug_screenshot_history():
        """调试截图历史功能"""
        import os
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'debug_screenshot_history.html')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "Debug screenshot history file not found", 404
    
    return app
