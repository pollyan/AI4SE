"""
API路由定义
"""
from flask import Blueprint, request, jsonify
import json
import uuid
from datetime import datetime

# 修复Serverless环境的导入路径
try:
    from models import db, TestCase, ExecutionHistory, StepExecution, Template
except ImportError:
    from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# ==================== 测试用例相关API ====================

@api_bp.route('/testcases', methods=['GET'])
def get_testcases():
    """获取测试用例列表"""
    try:
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 20, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        
        query = TestCase.query.filter(TestCase.is_active == True)
        
        if search:
            query = query.filter(TestCase.name.contains(search))
        
        if category:
            query = query.filter(TestCase.category == category)
        
        # 分页
        pagination = query.paginate(
            page=page, per_page=size, error_out=False
        )
        
        return jsonify({
            'code': 200,
            'data': {
                'items': [tc.to_dict() for tc in pagination.items],
                'total': pagination.total,
                'page': page,
                'size': size,
                'pages': pagination.pages
            },
            'message': '获取成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }), 500

@api_bp.route('/testcases', methods=['POST'])
def create_testcase():
    """创建测试用例"""
    try:
        data = request.get_json()
        
        # 记录请求数据进行调试
        print(f"创建测试用例请求数据: {data}")
        
        # 验证请求数据
        if not data:
            return jsonify({
                'code': 400,
                'message': '请求数据不能为空'
            }), 400
        
        # 验证必填字段
        if not data.get('name'):
            return jsonify({
                'code': 400,
                'message': '测试用例名称不能为空'
            }), 400
        
        # 验证步骤数据格式（允许为空，后续在步骤编辑器中完善）
        steps = data.get('steps', [])
        if not isinstance(steps, list):
            return jsonify({
                'code': 400,
                'message': '测试步骤必须是数组格式'
            }), 400
        
        # 如果有步骤，验证每个步骤的格式
        if len(steps) > 0:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    return jsonify({
                        'code': 400,
                        'message': f'步骤 {i+1} 格式不正确，必须是对象'
                    }), 400
                
                if not step.get('action'):
                    return jsonify({
                        'code': 400,
                        'message': f'步骤 {i+1} 缺少action字段'
                    }), 400
        
        # 创建测试用例实例
        print(f"准备创建测试用例，数据: {data}")
        testcase = TestCase.from_dict(data)
        print(f"创建的测试用例对象: name={testcase.name}, steps={testcase.steps}")
        
        # 添加到数据库
        db.session.add(testcase)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': testcase.to_dict(),
            'message': '测试用例创建成功'
        })
    except Exception as e:
        db.session.rollback()
        print(f"创建测试用例失败: {str(e)}")
        print(f"错误详情: {e}")
        return jsonify({
            'code': 500,
            'message': f'创建失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>', methods=['GET'])
def get_testcase(testcase_id):
    """获取测试用例详情"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        return jsonify({
            'code': 200,
            'data': testcase.to_dict()
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>', methods=['PUT'])
def update_testcase(testcase_id):
    """更新测试用例"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        data = request.get_json()
        
        # 更新字段
        if 'name' in data:
            testcase.name = data['name']
        if 'description' in data:
            testcase.description = data['description']
        if 'steps' in data:
            testcase.steps = json.dumps(data['steps'])
        if 'tags' in data:
            testcase.tags = ','.join(data['tags'])
        if 'category' in data:
            testcase.category = data['category']
        if 'priority' in data:
            testcase.priority = data['priority']
        
        testcase.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': testcase.to_dict(),
            'message': '测试用例更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'更新失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>', methods=['DELETE'])
def delete_testcase(testcase_id):
    """删除测试用例（软删除）"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        testcase.is_active = False
        testcase.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '测试用例删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'删除失败: {str(e)}'
        }), 500

# ==================== 执行相关API ====================

@api_bp.route('/executions', methods=['POST'])
def create_execution():
    """创建执行任务"""
    try:
        data = request.get_json()
        testcase_id = data.get('testcase_id')
        mode = data.get('mode', 'normal')
        browser = data.get('browser', 'chrome')
        
        # 验证测试用例存在
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=testcase_id,
            status='pending',
            mode=mode,
            browser=browser,
            start_time=datetime.utcnow(),
            executed_by=data.get('executed_by', 'system')
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # TODO: 这里应该调用实际的执行引擎
        # 现在先返回执行ID，后续实现异步执行
        
        return jsonify({
            'code': 200,
            'data': {
                'execution_id': execution_id,
                'status': 'pending'
            },
            'message': '执行任务创建成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'创建执行任务失败: {str(e)}'
        }), 500

@api_bp.route('/executions/<execution_id>', methods=['GET'])
def get_execution_status(execution_id):
    """获取执行状态"""
    try:
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if not execution:
            return jsonify({
                'code': 404,
                'message': '执行记录不存在'
            }), 404

        # 获取步骤执行详情
        step_executions = StepExecution.query.filter_by(execution_id=execution_id).order_by(StepExecution.step_index).all()

        execution_data = execution.to_dict()
        execution_data['step_executions'] = [step.to_dict() for step in step_executions]

        return jsonify({
            'code': 200,
            'data': execution_data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取执行状态失败: {str(e)}'
        }), 500

@api_bp.route('/executions', methods=['GET'])
def get_executions():
    """获取执行历史列表"""
    try:
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 20, type=int)
        testcase_id = request.args.get('testcase_id', type=int)
        
        query = ExecutionHistory.query
        
        if testcase_id:
            query = query.filter(ExecutionHistory.test_case_id == testcase_id)
        
        # 按创建时间倒序
        query = query.order_by(ExecutionHistory.created_at.desc())
        
        pagination = query.paginate(
            page=page, per_page=size, error_out=False
        )
        
        return jsonify({
            'code': 200,
            'data': {
                'items': [ex.to_dict() for ex in pagination.items],
                'total': pagination.total,
                'page': page,
                'size': size,
                'pages': pagination.pages
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取执行历史失败: {str(e)}'
        }), 500

# ==================== 模板相关API ====================

@api_bp.route('/templates', methods=['GET'])
def get_templates():
    """获取模板列表"""
    try:
        category = request.args.get('category', '')
        
        query = Template.query
        
        if category:
            query = query.filter(Template.category == category)
        
        templates = query.all()
        
        return jsonify({
            'code': 200,
            'data': [t.to_dict() for t in templates]
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取模板失败: {str(e)}'
        }), 500

@api_bp.route('/templates', methods=['POST'])
def create_template():
    """创建模板"""
    try:
        data = request.get_json()
        
        template = Template.from_dict(data)
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': template.to_dict(),
            'message': '模板创建成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'创建模板失败: {str(e)}'
        }), 500

# ==================== 统计相关API ====================

@api_bp.route('/stats/dashboard', methods=['GET'])
def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        # 测试用例统计
        total_testcases = TestCase.query.filter(TestCase.is_active == True).count()
        
        # 执行统计
        total_executions = ExecutionHistory.query.count()
        success_executions = ExecutionHistory.query.filter(ExecutionHistory.status == 'success').count()
        failed_executions = ExecutionHistory.query.filter(ExecutionHistory.status == 'failed').count()
        
        # 成功率
        success_rate = (success_executions / total_executions * 100) if total_executions > 0 else 0
        
        return jsonify({
            'code': 200,
            'data': {
                'total_testcases': total_testcases,
                'total_executions': total_executions,
                'success_executions': success_executions,
                'failed_executions': failed_executions,
                'success_rate': round(success_rate, 2)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取统计数据失败: {str(e)}'
        }), 500
