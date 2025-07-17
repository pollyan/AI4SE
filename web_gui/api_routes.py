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
        
        # 按时间排序，最新的在前面（优先按更新时间，其次按创建时间）
        query = query.order_by(TestCase.updated_at.desc(), TestCase.created_at.desc())
        
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

# ==================== 步骤管理相关API ====================

@api_bp.route('/testcases/<int:testcase_id>/steps', methods=['GET'])
def get_testcase_steps(testcase_id):
    """获取测试用例的步骤列表"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        steps = json.loads(testcase.steps) if testcase.steps else []
        
        return jsonify({
            'code': 200,
            'data': {
                'steps': steps,
                'total': len(steps)
            },
            'message': '获取步骤列表成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取步骤列表失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>/steps', methods=['POST'])
def add_testcase_step(testcase_id):
    """添加新步骤到测试用例"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        data = request.get_json()
        
        # 验证步骤数据
        if not data or 'action' not in data:
            return jsonify({
                'code': 400,
                'message': '步骤数据不完整，需要action字段'
            }), 400
        
        # 验证动作类型
        valid_actions = ['goto', 'ai_input', 'ai_tap', 'ai_assert', 'ai_wait_for', 'ai_scroll', 'ai_drag', 'sleep', 'screenshot', 'refresh', 'back', 'ai_select', 'ai_upload', 'ai_check']
        if data['action'] not in valid_actions:
            return jsonify({
                'code': 400,
                'message': f'无效的动作类型: {data["action"]}'
            }), 400
        
        # 验证必需参数
        params = data.get('params', {})
        if data['action'] == 'goto' and not params.get('url'):
            return jsonify({
                'code': 400,
                'message': 'goto动作需要url参数'
            }), 400
        elif data['action'] in ['ai_input', 'ai_tap', 'ai_assert', 'ai_wait_for'] and not params.get('prompt') and not params.get('locate'):
            return jsonify({
                'code': 400,
                'message': f'{data["action"]}动作需要prompt或locate参数'
            }), 400
        
        # 获取现有步骤
        steps = json.loads(testcase.steps) if testcase.steps else []
        
        # 构建新步骤
        new_step = {
            'action': data['action'],
            'params': data.get('params', {}),
            'description': data.get('description', ''),
            'required': data.get('required', True)
        }
        
        # 添加步骤（默认添加到末尾）
        insert_position = data.get('position', len(steps))
        steps.insert(insert_position, new_step)
        
        # 更新测试用例
        testcase.steps = json.dumps(steps)
        testcase.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': {
                'step': new_step,
                'position': insert_position,
                'total_steps': len(steps)
            },
            'message': '步骤添加成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'添加步骤失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>/steps/<int:step_index>', methods=['PUT'])
def update_testcase_step(testcase_id, step_index):
    """更新特定步骤"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        data = request.get_json()
        steps = json.loads(testcase.steps) if testcase.steps else []
        
        # 验证步骤索引
        if step_index < 0 or step_index >= len(steps):
            return jsonify({
                'code': 400,
                'message': '步骤索引超出范围'
            }), 400
        
        # 更新步骤
        if 'action' in data:
            steps[step_index]['action'] = data['action']
        if 'params' in data:
            steps[step_index]['params'] = data['params']
        if 'description' in data:
            steps[step_index]['description'] = data['description']
        if 'required' in data:
            steps[step_index]['required'] = data['required']
        
        # 保存更改
        testcase.steps = json.dumps(steps)
        testcase.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': {
                'step': steps[step_index],
                'index': step_index
            },
            'message': '步骤更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'更新步骤失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>/steps/<int:step_index>', methods=['DELETE'])
def delete_testcase_step(testcase_id, step_index):
    """删除特定步骤"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        steps = json.loads(testcase.steps) if testcase.steps else []
        
        # 验证步骤索引
        if step_index < 0 or step_index >= len(steps):
            return jsonify({
                'code': 400,
                'message': '步骤索引超出范围'
            }), 400
        
        # 删除步骤
        deleted_step = steps.pop(step_index)
        
        # 保存更改
        testcase.steps = json.dumps(steps)
        testcase.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': {
                'deleted_step': deleted_step,
                'remaining_steps': len(steps)
            },
            'message': '步骤删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'删除步骤失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>/steps/reorder', methods=['PUT'])
def reorder_testcase_steps(testcase_id):
    """重新排序步骤"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        data = request.get_json()
        if not data or 'step_orders' not in data:
            return jsonify({
                'code': 400,
                'message': '缺少步骤排序数据'
            }), 400
        
        steps = json.loads(testcase.steps) if testcase.steps else []
        step_orders = data['step_orders']
        
        # 验证排序数据
        if len(step_orders) != len(steps):
            return jsonify({
                'code': 400,
                'message': '步骤排序数据长度不匹配'
            }), 400
        
        # 重新排序
        new_steps = []
        for index in step_orders:
            if 0 <= index < len(steps):
                new_steps.append(steps[index])
            else:
                return jsonify({
                    'code': 400,
                    'message': f'步骤索引 {index} 超出范围'
                }), 400
        
        # 保存更改
        testcase.steps = json.dumps(new_steps)
        testcase.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': {
                'steps': new_steps,
                'total': len(new_steps)
            },
            'message': '步骤排序成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'步骤排序失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/<int:testcase_id>/steps/<int:step_index>/duplicate', methods=['POST'])
def duplicate_testcase_step(testcase_id, step_index):
    """复制步骤"""
    try:
        testcase = TestCase.query.get(testcase_id)
        if not testcase or not testcase.is_active:
            return jsonify({
                'code': 404,
                'message': '测试用例不存在'
            }), 404
        
        steps = json.loads(testcase.steps) if testcase.steps else []
        
        # 验证步骤索引
        if step_index < 0 or step_index >= len(steps):
            return jsonify({
                'code': 400,
                'message': '步骤索引超出范围'
            }), 400
        
        # 复制步骤
        original_step = steps[step_index]
        duplicated_step = json.loads(json.dumps(original_step))  # 深拷贝
        
        # 修改描述以区分复制的步骤
        if 'description' in duplicated_step:
            duplicated_step['description'] = f"{duplicated_step['description']} (复制)"
        
        # 获取插入位置（默认在原步骤后面）
        data = request.get_json() or {}
        insert_position = data.get('position', step_index + 1)
        
        # 插入复制的步骤
        steps.insert(insert_position, duplicated_step)
        
        # 保存更改
        testcase.steps = json.dumps(steps)
        testcase.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'data': {
                'duplicated_step': duplicated_step,
                'original_index': step_index,
                'new_index': insert_position,
                'total_steps': len(steps)
            },
            'message': '步骤复制成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'复制步骤失败: {str(e)}'
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
        
        print(f"🔍 获取执行历史 - page: {page}, size: {size}, testcase_id: {testcase_id}")
        
        query = ExecutionHistory.query
        
        if testcase_id:
            query = query.filter(ExecutionHistory.test_case_id == testcase_id)
        
        # 按创建时间倒序
        query = query.order_by(ExecutionHistory.created_at.desc())
        
        pagination = query.paginate(
            page=page, per_page=size, error_out=False
        )
        
        print(f"📊 执行历史查询结果: 总数={pagination.total}, 当前页={pagination.page}, 项目数={len(pagination.items)}")
        
        result = {
            'code': 200,
            'data': {
                'items': [ex.to_dict() for ex in pagination.items],
                'total': pagination.total,
                'page': page,
                'size': size,
                'pages': pagination.pages
            }
        }
        
        print(f"📊 执行历史返回: {len(result['data']['items'])} 条记录")
        return jsonify(result)
    except Exception as e:
        print(f"❌ 获取执行历史失败: {str(e)}")
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
        print("🔍 开始获取仪表板统计数据...")
        
        # 测试用例统计
        total_testcases = TestCase.query.filter(TestCase.is_active == True).count()
        print(f"📊 测试用例总数: {total_testcases}")
        
        # 执行统计
        total_executions = ExecutionHistory.query.count()
        success_executions = ExecutionHistory.query.filter(ExecutionHistory.status == 'success').count()
        failed_executions = ExecutionHistory.query.filter(ExecutionHistory.status == 'failed').count()
        print(f"📊 执行总数: {total_executions}, 成功: {success_executions}, 失败: {failed_executions}")
        
        # 成功率
        success_rate = (success_executions / total_executions * 100) if total_executions > 0 else 0
        print(f"📊 成功率: {success_rate}%")
        
        result = {
            'code': 200,
            'data': {
                'total_testcases': total_testcases,
                'total_executions': total_executions,
                'success_executions': success_executions,
                'failed_executions': failed_executions,
                'success_rate': round(success_rate, 2)
            }
        }
        
        print(f"📊 统计数据返回: {result}")
        return jsonify(result)
    except Exception as e:
        print(f"❌ 获取统计数据失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取统计数据失败: {str(e)}'
        }), 500

@api_bp.route('/db-status', methods=['GET'])
def get_db_status():
    """获取数据库状态和调试信息"""
    try:
        # 数据库连接状态
        db_info = {
            'connected': False,
            'tables': [],
            'errors': []
        }
        
        # 测试数据库连接
        try:
            # 尝试执行简单查询
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            db_info['connected'] = True
            print("✅ 数据库连接正常")
        except Exception as conn_error:
            db_info['connected'] = False
            db_info['errors'].append(f"数据库连接失败: {str(conn_error)}")
            print(f"❌ 数据库连接失败: {conn_error}")
        
        # 检查表结构
        try:
            # 检查主要表是否存在
            from sqlalchemy import text
            tables_to_check = ['test_cases', 'execution_history', 'step_executions', 'templates']
            for table in tables_to_check:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    db_info['tables'].append({
                        'name': table,
                        'exists': True,
                        'count': count
                    })
                    print(f"✅ 表 {table}: {count} 条记录")
                except Exception as table_error:
                    db_info['tables'].append({
                        'name': table,
                        'exists': False,
                        'error': str(table_error)
                    })
                    print(f"❌ 表 {table} 检查失败: {table_error}")
        except Exception as table_check_error:
            db_info['errors'].append(f"表检查失败: {str(table_check_error)}")
        
        # 检查最近的执行记录
        recent_executions = []
        try:
            executions = ExecutionHistory.query.order_by(ExecutionHistory.created_at.desc()).limit(5).all()
            for exec in executions:
                recent_executions.append({
                    'execution_id': exec.execution_id,
                    'test_case_id': exec.test_case_id,
                    'status': exec.status,
                    'created_at': exec.created_at.isoformat() if exec.created_at else None
                })
            print(f"📊 最近执行记录: {len(recent_executions)} 条")
        except Exception as exec_error:
            db_info['errors'].append(f"获取执行记录失败: {str(exec_error)}")
            print(f"❌ 获取执行记录失败: {exec_error}")
        
        # 环境信息
        import os
        env_info = {
            'database_url': os.getenv('DATABASE_URL', 'Not set')[:50] + '...' if os.getenv('DATABASE_URL') else 'Not set',
            'environment': os.getenv('VERCEL_ENV', 'local'),
            'region': os.getenv('VERCEL_REGION', 'unknown')
        }
        
        return jsonify({
            'code': 200,
            'data': {
                'database': db_info,
                'recent_executions': recent_executions,
                'environment': env_info
            }
        })
    except Exception as e:
        print(f"❌ 数据库状态检查失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'数据库状态检查失败: {str(e)}'
        }), 500

@api_bp.route('/db-status/create-test-data', methods=['POST'])
def create_test_data():
    """创建测试数据来验证数据库功能"""
    try:
        import uuid
        from datetime import datetime, timedelta
        
        # 确保数据库表存在
        db.create_all()
        
        # 创建测试用例
        test_case = TestCase(
            name='测试用例 - 数据库验证',
            description='用于验证数据库功能的测试用例',
            steps='[{"action": "navigate", "params": {"url": "https://www.baidu.com"}, "description": "打开百度首页"}]',
            category='系统测试',
            priority=3,
            created_by='系统',
            created_at=datetime.utcnow()
        )
        
        db.session.add(test_case)
        db.session.flush()  # 获取ID
        
        # 创建执行历史记录
        execution_records = []
        for i in range(5):
            execution_id = str(uuid.uuid4())
            status = ['success', 'failed', 'success', 'success', 'failed'][i]
            
            execution = ExecutionHistory(
                execution_id=execution_id,
                test_case_id=test_case.id,
                status=status,
                mode='headless',
                start_time=datetime.utcnow() - timedelta(days=i),
                end_time=datetime.utcnow() - timedelta(days=i) + timedelta(minutes=2),
                duration=120,
                steps_total=3,
                steps_passed=3 if status == 'success' else 2,
                steps_failed=0 if status == 'success' else 1,
                executed_by='系统',
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            execution_records.append(execution)
            db.session.add(execution)
        
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '测试数据创建成功',
            'data': {
                'test_case_id': test_case.id,
                'execution_count': len(execution_records),
                'execution_ids': [e.execution_id for e in execution_records]
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ 创建测试数据失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'创建测试数据失败: {str(e)}'
        }), 500

# ==================== 报告导出API ====================

@api_bp.route('/executions/<execution_id>/export', methods=['GET'])
def export_execution_report(execution_id):
    """导出单个执行报告"""
    try:
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if not execution:
            return jsonify({
                'code': 404,
                'message': '执行记录不存在'
            }), 404

        # 获取步骤执行详情
        step_executions = StepExecution.query.filter_by(execution_id=execution_id).order_by(StepExecution.step_index).all()

        # 构建报告数据
        report_data = execution.to_dict()
        report_data['step_executions'] = [step.to_dict() for step in step_executions]
        
        # 添加导出时间戳
        report_data['exported_at'] = datetime.utcnow().isoformat()

        response = jsonify(report_data)
        response.headers['Content-Disposition'] = f'attachment; filename=execution_report_{execution_id}.json'
        
        return response
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'导出报告失败: {str(e)}'
        }), 500

@api_bp.route('/executions/export-all', methods=['GET'])
def export_all_execution_reports():
    """导出所有执行报告"""
    try:
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 100, type=int)  # 限制导出数量避免过大
        
        # 获取执行记录
        query = ExecutionHistory.query.order_by(ExecutionHistory.created_at.desc())
        pagination = query.paginate(page=page, per_page=size, error_out=False)
        
        # 构建所有报告数据
        all_reports = []
        for execution in pagination.items:
            # 获取步骤执行详情
            step_executions = StepExecution.query.filter_by(execution_id=execution.execution_id).order_by(StepExecution.step_index).all()
            
            report_data = execution.to_dict()
            report_data['step_executions'] = [step.to_dict() for step in step_executions]
            all_reports.append(report_data)
        
        # 构建导出数据
        export_data = {
            'exported_at': datetime.utcnow().isoformat(),
            'total_reports': len(all_reports),
            'page': page,
            'size': size,
            'reports': all_reports
        }

        response = jsonify(export_data)
        filename = f'all_execution_reports_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        
        return response
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'导出所有报告失败: {str(e)}'
        }), 500

@api_bp.route('/executions/<execution_id>', methods=['DELETE'])
def delete_execution_report(execution_id):
    """删除执行报告"""
    try:
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if not execution:
            return jsonify({
                'code': 404,
                'message': '执行记录不存在'
            }), 404

        # 删除相关的步骤执行记录
        StepExecution.query.filter_by(execution_id=execution_id).delete()
        
        # 删除执行记录
        db.session.delete(execution)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '执行报告删除成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'code': 500,
            'message': f'删除执行报告失败: {str(e)}'
        }), 500

# ==================== MidScene执行结果接收API ====================

@api_bp.route('/midscene/execution-result', methods=['POST'])
def receive_execution_result():
    """接收MidScene服务器的执行结果并更新数据库记录"""
    try:
        data = request.get_json()
        print(f"🔄 接收到MidScene执行结果: {data}")
        
        # 验证必要字段
        required_fields = ['execution_id', 'testcase_id', 'status', 'mode']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必要字段: {field}'
                }), 400
        
        execution_id = data['execution_id']
        testcase_id = data['testcase_id']
        status = data['status']
        mode = data['mode']
        
        # 查找现有的执行记录
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if not execution:
            return jsonify({
                'code': 404,
                'message': f'执行记录不存在: {execution_id}'
            }), 404
        
        # 解析步骤数据
        steps_data = data.get('steps', [])
        steps_total = len(steps_data)
        steps_passed = sum(1 for step in steps_data if step.get('status') == 'success')
        steps_failed = sum(1 for step in steps_data if step.get('status') == 'failed')
        
        # 计算执行时间
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00')) if data.get('start_time') else execution.start_time
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00')) if data.get('end_time') else datetime.utcnow()
        duration = int((end_time - start_time).total_seconds())
        
        # 更新ExecutionHistory记录
        execution.status = status
        execution.end_time = end_time
        execution.duration = duration
        execution.steps_total = steps_total
        execution.steps_passed = steps_passed
        execution.steps_failed = steps_failed
        execution.error_message = data.get('error_message')
        
        db.session.flush()  # 获取ID
        
        # 创建StepExecution记录
        step_executions = []
        for i, step_data in enumerate(steps_data):
            step_execution = StepExecution(
                execution_id=execution_id,
                step_index=i,
                step_description=step_data.get('description', ''),
                status=step_data.get('status', 'pending'),
                start_time=datetime.fromisoformat(step_data['start_time'].replace('Z', '+00:00')) if step_data.get('start_time') else start_time,
                end_time=datetime.fromisoformat(step_data['end_time'].replace('Z', '+00:00')) if step_data.get('end_time') else end_time,
                duration=step_data.get('duration', 0),
                screenshot_path=step_data.get('screenshot_path'),
                error_message=step_data.get('error_message')
            )
            step_executions.append(step_execution)
            db.session.add(step_execution)
        
        db.session.commit()
        
        print(f"✅ 成功创建执行记录: {execution_id}, 包含 {len(step_executions)} 个步骤")
        
        return jsonify({
            'code': 200,
            'message': '执行结果记录成功',
            'data': {
                'execution_id': execution_id,
                'database_id': execution.id,
                'steps_count': len(step_executions)
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ 记录执行结果失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'记录执行结果失败: {str(e)}'
        }), 500

@api_bp.route('/midscene/execution-start', methods=['POST'])
def receive_execution_start():
    """接收MidScene服务器的执行开始通知并创建初始记录"""
    try:
        data = request.get_json()
        print(f"🚀 接收到MidScene执行开始通知: {data}")
        
        # 验证必要字段
        required_fields = ['execution_id', 'testcase_id', 'mode']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'code': 400,
                    'message': f'缺少必要字段: {field}'
                }), 400
        
        execution_id = data['execution_id']
        testcase_id = data['testcase_id']
        mode = data['mode']
        
        # 创建初始ExecutionHistory记录
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=testcase_id,
            status='running',
            mode=mode,
            browser=data.get('browser', 'chrome'),
            start_time=datetime.utcnow(),
            steps_total=data.get('steps_total', 0),
            steps_passed=0,
            steps_failed=0,
            executed_by=data.get('executed_by', 'midscene-server'),
            created_at=datetime.utcnow()
        )
        
        db.session.add(execution)
        db.session.commit()
        
        print(f"✅ 成功创建初始执行记录: {execution_id}")
        
        return jsonify({
            'code': 200,
            'message': '执行开始记录成功',
            'data': {
                'execution_id': execution_id,
                'database_id': execution.id
            }
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ 记录执行开始失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'记录执行开始失败: {str(e)}'
        }), 500
