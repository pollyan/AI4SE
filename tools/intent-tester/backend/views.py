from flask import Blueprint, render_template, redirect

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    return redirect('testcases')

@views_bp.route('/testcases')
def testcases():
    return render_template('testcases.html')

@views_bp.route('/testcases/create')
def create_testcase():
    # 创建模式：传递空的 testcase 对象
    empty_testcase = {
        'id': None,
        'name': '',
        'description': '',
        'category': '功能测试',
        'priority': 2,
        'is_active': True,
        'tags': '',
        'created_by': 'admin',
        'created_at': None,
        'updated_at': None
    }
    return render_template(
        'testcase_edit.html',
        testcase=type('Testcase', (), empty_testcase)(),
        is_create_mode=True,
        steps_data='[]',
        total_executions=0,
        success_rate=0.0
    )

@views_bp.route('/testcases/<int:testcase_id>')
@views_bp.route('/testcases/<int:testcase_id>/edit')
def edit_testcase(testcase_id):
    from .models import TestCase, db
    import json
    testcase = TestCase.query.get_or_404(testcase_id)
    try:
        steps_list = json.loads(testcase.steps) if testcase.steps else []
    except json.JSONDecodeError:
        steps_list = []
    steps_data = json.dumps(steps_list)
    # 计算执行统计
    total_executions = 0
    success_rate = 0.0
    return render_template(
        'testcase_edit.html',
        testcase=testcase,
        is_create_mode=False,
        steps_data=steps_data,
        total_executions=total_executions,
        success_rate=success_rate
    )

@views_bp.route('/execution')
@views_bp.route('/executions/<int:execution_id>')
def view_execution(execution_id=None):
    return render_template('execution.html', execution_id=execution_id)

@views_bp.route('/local-proxy')
def local_proxy():
    from datetime import datetime
    return render_template(
        "local_proxy.html",
        current_date=datetime.utcnow().strftime("%Y-%m-%d"),
        build_time=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )




