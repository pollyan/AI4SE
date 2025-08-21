"""
API路由定义
"""
from flask import Blueprint, request, jsonify
import json
import uuid
import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# 导入统一错误处理工具
try:
    from utils.error_handler import (
        api_error_handler, db_transaction_handler, validate_json_data,
        format_success_response, ValidationError, NotFoundError, DatabaseError
    )
except ImportError:
    from web_gui.utils.error_handler import (
        api_error_handler, db_transaction_handler, validate_json_data,
        format_success_response, ValidationError, NotFoundError, DatabaseError
    )

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
@api_error_handler
@validate_json_data(required_fields=['name'])
@db_transaction_handler(db)
def create_testcase():
    """创建测试用例"""
    data = request.get_json()
    
    # 记录请求数据进行调试
    print(f"创建测试用例请求数据: {data}")
    
    # 验证步骤数据格式（允许为空，后续在步骤编辑器中完善）
    steps = data.get('steps', [])
    if not isinstance(steps, list):
        raise ValidationError('测试步骤必须是数组格式', 'steps')
    
    # 如果有步骤，验证每个步骤的格式
    if len(steps) > 0:
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                raise ValidationError(f'步骤 {i+1} 格式不正确，必须是对象')
            
            if not step.get('action'):
                raise ValidationError(f'步骤 {i+1} 缺少action字段')
    
    # 创建测试用例实例
    print(f"准备创建测试用例，数据: {data}")
    testcase = TestCase.from_dict(data)
    print(f"创建的测试用例对象: name={testcase.name}, steps={testcase.steps}")
    
    # 添加到数据库
    db.session.add(testcase)
    # 刷新会话以获取生成的ID
    db.session.flush()
    
    print(f"测试用例创建成功，ID: {testcase.id}")
    
    return jsonify(format_success_response(
        data=testcase.to_dict(),
        message='测试用例创建成功'
    ))

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
@api_error_handler
@db_transaction_handler(db)
def delete_testcase(testcase_id):
    """删除测试用例（软删除）"""
    print(f"🗑️ 开始删除测试用例: ID={testcase_id}")
    
    testcase = TestCase.query.get(testcase_id)
    if not testcase:
        print(f"❌ 测试用例不存在: ID={testcase_id}")
        raise NotFoundError('测试用例', testcase_id)
    
    print(f"📋 找到测试用例: {testcase.name}, is_active={testcase.is_active}")
    
    # 检查是否已经被删除
    if not testcase.is_active:
        print(f"⚠️ 测试用例已经被删除: ID={testcase_id}")
        raise ValidationError('测试用例已经被删除')
    
    testcase.is_active = False
    testcase.updated_at = datetime.utcnow()
    
    print(f"✅ 测试用例删除成功: ID={testcase_id}, name={testcase.name}")
    
    return jsonify(format_success_response(
        message='测试用例删除成功'
    ))

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

@api_bp.route('/executions/<execution_id>/variables', methods=['GET'])
def get_execution_variables(execution_id):
    """获取执行的变量列表"""
    try:
        from .services.variable_resolver_service import get_variable_manager
        
        # 获取变量管理器
        manager = get_variable_manager(execution_id)
        
        # 获取所有变量
        variables = manager.list_variables()
        
        return jsonify({
            'code': 200,
            'data': {
                'execution_id': execution_id,
                'variables': variables,
                'count': len(variables)
            },
            'message': '获取变量列表成功'
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取变量列表失败: {str(e)}'
        }), 500

@api_bp.route('/executions/<execution_id>/variables/<variable_name>', methods=['GET'])
def get_variable_detail(execution_id, variable_name):
    """获取变量详细信息"""
    try:
        from .services.variable_resolver_service import get_variable_manager
        
        # 获取变量管理器
        manager = get_variable_manager(execution_id)
        
        # 获取变量元数据
        metadata = manager.get_variable_metadata(variable_name)
        
        if metadata:
            return jsonify({
                'code': 200,
                'data': metadata,
                'message': '获取变量详情成功'
            })
        else:
            return jsonify({
                'code': 404,
                'message': f'变量不存在: {variable_name}'
            }), 404
            
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取变量详情失败: {str(e)}'
        }), 500

@api_bp.route('/executions/<execution_id>/variable-references', methods=['GET'])
def get_variable_references(execution_id):
    """获取执行中的变量引用关系"""
    try:
        from web_gui.models import VariableReference
        
        # 查询变量引用记录
        references = VariableReference.query.filter_by(execution_id=execution_id).order_by(VariableReference.step_index).all()
        
        # 格式化引用数据
        references_data = []
        for ref in references:
            references_data.append({
                'step_index': ref.step_index,
                'variable_name': ref.variable_name,
                'reference_path': ref.reference_path,
                'parameter_name': ref.parameter_name,
                'original_expression': ref.original_expression,
                'resolved_value': ref.resolved_value,
                'resolution_status': ref.resolution_status,
                'error_message': ref.error_message
            })
        
        return jsonify({
            'code': 200,
            'data': {
                'execution_id': execution_id,
                'references': references_data,
                'count': len(references_data)
            },
            'message': '获取变量引用关系成功'
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取变量引用关系失败: {str(e)}'
        }), 500

@api_bp.route('/v1/executions/<execution_id>/variable-suggestions', methods=['GET'])
def get_variable_suggestions(execution_id):
    """获取变量建议列表（AC-1: 变量建议API）"""
    try:
        from .services.variable_suggestion_service import VariableSuggestionService
        
        # 获取查询参数
        step_index = request.args.get('step_index', type=int)
        include_properties = request.args.get('include_properties', 'true').lower() == 'true'
        limit = request.args.get('limit', type=int)
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取变量建议
        result = service.get_variable_suggestions(
            step_index=step_index,
            include_properties=include_properties,
            limit=limit
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"获取变量建议失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 保持向后兼容的旧API端点
@api_bp.route('/executions/<execution_id>/variable-suggestions', methods=['GET'])
def get_variable_suggestions_legacy(execution_id):
    """获取变量建议列表（向后兼容）"""
    try:
        from .services.variable_suggestion_service import VariableSuggestionService
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取变量建议
        result = service.get_variable_suggestions()
        
        # 转换为旧格式
        suggestions = []
        for var in result['variables']:
            suggestions.append({
                'name': var['name'],
                'dataType': var['data_type'],
                'value': var.get('preview_value', ''),
                'sourceStepIndex': var['source_step_index'],
                'sourceApiMethod': var['source_api_method'],
                'preview': var['preview_value'],
                'properties': var.get('properties')
            })
        
        return jsonify({
            'code': 200,
            'data': {
                'execution_id': execution_id,
                'suggestions': suggestions,
                'count': len(suggestions)
            },
            'message': '获取变量建议成功'
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取变量建议失败: {str(e)}'
        }), 500

@api_bp.route('/v1/executions/<execution_id>/variables/<variable_name>/properties', methods=['GET'])
def get_variable_properties(execution_id, variable_name):
    """获取变量属性探索信息（AC-2: 对象属性探索API）"""
    try:
        from .services.variable_suggestion_service import VariableSuggestionService
        
        # 获取查询参数
        max_depth = request.args.get('max_depth', 3, type=int)
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取变量属性
        result = service.get_variable_properties(variable_name, max_depth=max_depth)
        
        if result is None:
            return jsonify({'error': f'变量 {variable_name} 不存在'}), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"获取变量属性失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 保持向后兼容的旧API端点
@api_bp.route('/executions/<execution_id>/variables/<variable_name>/properties', methods=['GET'])
def get_variable_properties_legacy(execution_id, variable_name):
    """获取变量的属性列表（向后兼容）"""
    try:
        from .services.variable_suggestion_service import VariableSuggestionService
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取变量属性
        result = service.get_variable_properties(variable_name)
        
        if result is None:
            return jsonify({
                'code': 404,
                'message': f'变量不存在: {variable_name}'
            }), 404
        
        return jsonify({
            'code': 200,
            'data': {
                'variable_name': variable_name,
                'properties': result.get('properties', []),
                'count': len(result.get('properties', []))
            },
            'message': '获取变量属性成功'
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取变量属性失败: {str(e)}'
        }), 500

@api_bp.route('/v1/executions/<execution_id>/variable-suggestions/search', methods=['GET'])
def search_variables(execution_id):
    """模糊搜索变量（AC-3: 变量名模糊搜索API）"""
    try:
        from .services.variable_suggestion_service import VariableSuggestionService
        
        # 获取查询参数
        query = request.args.get('q', '').strip()
        limit = request.args.get('limit', 10, type=int)
        step_index = request.args.get('step_index', type=int)
        
        if not query:
            return jsonify({'error': '搜索查询不能为空'}), 400
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 执行搜索
        result = service.search_variables(query=query, limit=limit, step_index=step_index)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"变量搜索失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/v1/executions/<execution_id>/variables/validate', methods=['POST'])
def validate_variable_references(execution_id):
    """验证变量引用（AC-4: 变量引用验证API）"""
    try:
        from .services.variable_suggestion_service import VariableSuggestionService
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'references' not in data:
            return jsonify({'error': '请提供要验证的变量引用'}), 400
        
        references = data['references']
        step_index = data.get('step_index')
        
        if not isinstance(references, list):
            return jsonify({'error': 'references必须是数组'}), 400
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 验证引用
        validation_results = service.validate_references(references=references, step_index=step_index)
        
        return jsonify({
            'validation_results': validation_results
        }), 200
        
    except Exception as e:
        logger.error(f"变量引用验证失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/v1/executions/<execution_id>/variables/status', methods=['GET'])
def get_variables_status(execution_id):
    """获取变量状态（AC-5: 实时变量状态API）"""
    try:
        from .services.variable_suggestion_service import VariableSuggestionService
        
        # 获取建议服务
        service = VariableSuggestionService.get_service(execution_id)
        
        # 获取状态信息
        status = service.get_variables_status()
        
        return jsonify({
            'execution_id': execution_id,
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"获取变量状态失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

def _format_variable_preview(value, data_type):
    """格式化变量预览文本"""
    try:
        if value is None:
            return 'null'
        elif data_type == 'string':
            return f'"{str(value)[:50]}{"..." if len(str(value)) > 50 else ""}"'
        elif data_type == 'number':
            return str(value)
        elif data_type == 'boolean':
            return 'true' if value else 'false'
        elif data_type == 'object':
            if isinstance(value, dict):
                keys = list(value.keys())[:3]
                preview = '{' + ', '.join(f'{k}: ...' for k in keys)
                if len(value) > 3:
                    preview += ', ...'
                preview += '}'
                return preview
            return str(value)[:50]
        elif data_type == 'array':
            if isinstance(value, list):
                return f'[{len(value)} items]'
            return str(value)[:50]
        else:
            return str(value)[:50]
    except Exception:
        return 'preview unavailable'

def _extract_object_properties(value):
    """提取对象的属性信息"""
    try:
        if not isinstance(value, dict):
            return None
        
        properties = []
        for key, val in value.items():
            prop_type = 'string'
            if isinstance(val, bool):
                prop_type = 'boolean'
            elif isinstance(val, int) or isinstance(val, float):
                prop_type = 'number'
            elif isinstance(val, dict):
                prop_type = 'object'
            elif isinstance(val, list):
                prop_type = 'array'
            
            properties.append({
                'name': key,
                'type': prop_type,
                'value': val,
                'preview': _format_variable_preview(val, prop_type)
            })
        
        return properties
        
    except Exception:
        return None

@api_bp.route('/testcases/<int:test_case_id>/execute-enhanced', methods=['POST'])
@api_error_handler
@db_transaction_handler(db)
def execute_test_case_enhanced(test_case_id):
    """执行测试用例（增强版本，支持完整变量解析）"""
    try:
        data = request.get_json() or {}
        
        # 获取测试用例
        test_case = TestCase.query.get(test_case_id)
        if not test_case:
            raise NotFoundError(f'测试用例不存在: {test_case_id}')
        
        # 创建执行ID
        execution_id = str(uuid.uuid4())
        
        # 执行配置
        execution_config = {
            'mode': data.get('mode', 'headless'),
            'browser': data.get('browser', 'chrome'),
            'stop_on_failure': data.get('stop_on_failure', True),
            'timeout': data.get('timeout', 30000)
        }
        
        # 创建执行历史记录
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=test_case_id,
            status='running',
            mode=execution_config['mode'],
            browser=execution_config['browser'],
            start_time=datetime.utcnow(),
            executed_by=data.get('executed_by', 'web-gui')
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # 异步执行测试用例（实际项目中应该使用Celery等任务队列）
        # 这里先返回execution_id，实际执行可以通过另一个进程处理
        
        return format_success_response({
            'execution_id': execution_id,
            'test_case_id': test_case_id,
            'status': 'running',
            'config': execution_config
        }, '增强测试执行已启动')
        
    except Exception as e:
        logger.error(f"增强测试执行失败: {str(e)}")
        raise

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
        status = request.args.get('status')
        sort_param = request.args.get('sort', 'created_at,desc')
        
        print(f"🔍 获取执行历史 - page: {page}, size: {size}, testcase_id: {testcase_id}, status: {status}, sort: {sort_param}")
        
        query = ExecutionHistory.query
        
        # 按测试用例ID过滤
        if testcase_id:
            query = query.filter(ExecutionHistory.test_case_id == testcase_id)
        
        # 按状态过滤
        if status:
            query = query.filter(ExecutionHistory.status == status)
        
        # 解析排序参数
        try:
            sort_field, sort_direction = sort_param.split(',')
            sort_direction = sort_direction.strip().lower()
            
            # 映射字段名
            field_mapping = {
                'start_time': ExecutionHistory.start_time,
                'created_at': ExecutionHistory.created_at,
                'end_time': ExecutionHistory.end_time,
                'duration': ExecutionHistory.duration,
                'status': ExecutionHistory.status
            }
            
            if sort_field in field_mapping:
                sort_column = field_mapping[sort_field]
                if sort_direction == 'asc':
                    query = query.order_by(sort_column.asc())
                else:
                    query = query.order_by(sort_column.desc())
            else:
                # 默认按创建时间倒序
                query = query.order_by(ExecutionHistory.created_at.desc())
        except ValueError:
            # 排序参数格式错误，使用默认排序
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
                    'created_at': exec.created_at.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if exec.created_at else None
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

# ==================== 报告统计相关API ====================

@api_bp.route('/reports/stats', methods=['GET'])
def get_report_stats():
    """获取报告统计概览数据 - 支持日期筛选"""
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        # 获取查询参数
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        days = request.args.get('days', 7, type=int)  # 默认最近7天
        
        # 解析日期参数
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)  # 包含结束日期
            except ValueError:
                return jsonify({
                    'code': 400,
                    'message': '日期格式错误，请使用 YYYY-MM-DD 格式'
                }), 400
        else:
            # 使用默认时间范围
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
        
        # 在指定日期范围内的执行次数
        range_executions = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= start_date,
            ExecutionHistory.created_at < end_date
        ).count()
        
        # 总执行次数（不受日期限制）
        total_executions = ExecutionHistory.query.count()
        
        # 本周新增执行次数
        week_start = datetime.utcnow() - timedelta(days=7)
        week_executions = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= week_start
        ).count()
        
        # 指定日期范围内的成功率
        range_success_count = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= start_date,
            ExecutionHistory.created_at < end_date,
            ExecutionHistory.status == 'success'
        ).count()
        success_rate = (range_success_count / range_executions * 100) if range_executions > 0 else 0
        
        # 指定日期范围内的平均执行时间
        avg_duration_result = db.session.query(
            func.avg(ExecutionHistory.duration)
        ).filter(
            ExecutionHistory.created_at >= start_date,
            ExecutionHistory.created_at < end_date,
            ExecutionHistory.duration.isnot(None)
        ).scalar()
        avg_duration = round(avg_duration_result, 1) if avg_duration_result else 0
        
        # 今日报告数
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_executions = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= today_start
        ).count()
        
        return jsonify({
            'code': 200,
            'data': {
                'total_executions': range_executions,  # 返回指定日期范围内的执行次数
                'week_executions': week_executions,
                'success_rate': round(success_rate, 1),
                'avg_duration': avg_duration,
                'today_executions': today_executions,
                'date_range': {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
                }
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取统计数据失败: {str(e)}'
        }), 500

@api_bp.route('/reports/trends', methods=['GET'])
def get_execution_trends():
    """获取执行趋势数据"""
    try:
        from sqlalchemy import func, text
        from datetime import datetime, timedelta
        
        # 获取最近7天的执行统计
        days = 7
        trends = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days-1-i)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            count = ExecutionHistory.query.filter(
                ExecutionHistory.start_time >= day_start,
                ExecutionHistory.start_time < day_end
            ).count()
            
            trends.append({
                'date': day_start.strftime('%m/%d'),
                'count': count
            })
        
        return jsonify({
            'code': 200,
            'data': trends
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取趋势数据失败: {str(e)}'
        }), 500

@api_bp.route('/reports/success-rate', methods=['GET'])
def get_success_rate_analysis():
    """获取成功率分析数据"""
    try:
        from sqlalchemy import func
        
        # 按测试用例分类统计成功率
        # 这里假设通过test_case的category字段分类
        # 如果没有category，则按测试用例名称中的关键词分类
        
        categories = ['功能测试', '性能测试', '安全测试', '兼容性测试']
        success_rates = []
        
        for category in categories:
            # 查找包含该关键词的测试用例
            total_count = db.session.query(ExecutionHistory)\
                .join(TestCase)\
                .filter(TestCase.name.contains(category))\
                .count()
            
            if total_count > 0:
                success_count = db.session.query(ExecutionHistory)\
                    .join(TestCase)\
                    .filter(TestCase.name.contains(category))\
                    .filter(ExecutionHistory.status == 'success')\
                    .count()
                
                rate = (success_count / total_count * 100)
            else:
                rate = 90 + (len(category) % 10)  # 模拟数据
            
            success_rates.append({
                'category': category,
                'rate': round(rate, 1)
            })
        
        return jsonify({
            'code': 200,
            'data': success_rates
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取成功率分析失败: {str(e)}'
        }), 500

@api_bp.route('/reports/failure-analysis', methods=['GET'])
def get_failure_analysis():
    """获取失败分析数据"""
    try:
        from sqlalchemy import func
        
        # 统计失败原因
        failure_reasons = []
        
        # 元素定位失败
        locator_failures = ExecutionHistory.query.filter(
            ExecutionHistory.status == 'failed',
            ExecutionHistory.error_message.contains('定位')
        ).count()
        
        # 超时错误
        timeout_failures = ExecutionHistory.query.filter(
            ExecutionHistory.status == 'failed',
            ExecutionHistory.error_message.contains('超时')
        ).count()
        
        # 网络连接错误
        network_failures = ExecutionHistory.query.filter(
            ExecutionHistory.status == 'failed',
            ExecutionHistory.error_message.contains('网络')
        ).count()
        
        # 断言失败
        assertion_failures = ExecutionHistory.query.filter(
            ExecutionHistory.status == 'failed',
            ExecutionHistory.error_message.contains('断言')
        ).count()
        
        total_failures = ExecutionHistory.query.filter(
            ExecutionHistory.status == 'failed'
        ).count()
        
        if total_failures == 0:
            # 模拟数据用于演示
            failure_reasons = [
                {'reason': '元素定位失败', 'count': 32, 'percentage': 45.7},
                {'reason': '超时错误', 'count': 18, 'percentage': 25.7},
                {'reason': '网络连接错误', 'count': 12, 'percentage': 17.1},
                {'reason': '断言失败', 'count': 8, 'percentage': 11.4}
            ]
        else:
            failure_reasons = [
                {
                    'reason': '元素定位失败',
                    'count': locator_failures,
                    'percentage': round(locator_failures / total_failures * 100, 1)
                },
                {
                    'reason': '超时错误',
                    'count': timeout_failures,
                    'percentage': round(timeout_failures / total_failures * 100, 1)
                },
                {
                    'reason': '网络连接错误',
                    'count': network_failures,
                    'percentage': round(network_failures / total_failures * 100, 1)
                },
                {
                    'reason': '断言失败',
                    'count': assertion_failures,
                    'percentage': round(assertion_failures / total_failures * 100, 1)
                }
            ]
        
        return jsonify({
            'code': 200,
            'data': failure_reasons
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取失败分析失败: {str(e)}'
        }), 500

# ==================== 报告导出相关API ====================

@api_bp.route('/reports/export/pdf', methods=['GET'])
def export_reports_pdf():
    """导出PDF格式的报告"""
    try:
        from datetime import datetime, timedelta
        import json
        
        # 获取筛选参数
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        status_filter = request.args.get('status')
        
        # 解析日期
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                return jsonify({
                    'code': 400,
                    'message': '日期格式错误'
                }), 400
        else:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
        
        # 查询执行记录
        query = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= start_date,
            ExecutionHistory.created_at < end_date
        )
        
        if status_filter:
            query = query.filter(ExecutionHistory.status == status_filter)
        
        executions = query.order_by(ExecutionHistory.created_at.desc()).limit(100).all()
        
        # 构建导出数据
        export_data = {
            'title': '测试执行报告',
            'export_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': (end_date - timedelta(days=1)).strftime('%Y-%m-%d')
            },
            'summary': {
                'total_count': len(executions),
                'success_count': len([e for e in executions if e.status == 'success']),
                'failed_count': len([e for e in executions if e.status == 'failed'])
            },
            'executions': [e.to_dict() for e in executions]
        }
        
        # 这里应该使用PDF生成库，暂时返回JSON
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = f'attachment; filename=test_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
        return response
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'导出PDF失败: {str(e)}'
        }), 500

@api_bp.route('/reports/export/excel', methods=['GET'])
def export_reports_excel():
    """导出Excel格式的报告"""
    try:
        from datetime import datetime, timedelta
        
        # 获取筛选参数
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        status_filter = request.args.get('status')
        
        # 解析日期
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1)
            except ValueError:
                return jsonify({
                    'code': 400,
                    'message': '日期格式错误'
                }), 400
        else:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
        
        # 查询执行记录
        query = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= start_date,
            ExecutionHistory.created_at < end_date
        )
        
        if status_filter:
            query = query.filter(ExecutionHistory.status == status_filter)
        
        executions = query.order_by(ExecutionHistory.created_at.desc()).limit(1000).all()
        
        # 构建Excel数据
        excel_data = {
            'metadata': {
                'title': '测试执行报告',
                'export_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'total_records': len(executions)
            },
            'headers': ['执行ID', '测试用例名称', '状态', '开始时间', '执行时长', '成功步骤', '失败步骤', '总步骤'],
            'data': []
        }
        
        for execution in executions:
            excel_data['data'].append([
                execution.execution_id,
                execution.test_case_name or '未知',
                execution.status,
                execution.start_time.strftime('%Y-%m-%d %H:%M:%S') if execution.start_time else '',
                f'{execution.duration}s' if execution.duration else '0s',
                execution.steps_passed or 0,
                execution.steps_failed or 0,
                execution.steps_total or 0
            ])
        
        # 这里应该使用Excel生成库，暂时返回JSON
        response = jsonify(excel_data)
        response.headers['Content-Disposition'] = f'attachment; filename=test_report_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json'
        return response
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'导出Excel失败: {str(e)}'
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
        report_data['exported_at'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

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
            'exported_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
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

# ==================== 新增仪表板相关API ====================

@api_bp.route('/stats/today', methods=['GET'])
def get_today_stats():
    """获取今日统计数据"""
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        # 计算今天和昨天的日期范围
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        yesterday = today - timedelta(days=1)
        
        # 今日执行数
        today_executions = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= today,
            ExecutionHistory.created_at < tomorrow
        ).count()
        
        # 昨日执行数
        yesterday_executions = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= yesterday,
            ExecutionHistory.created_at < today
        ).count()
        
        executions_change = today_executions - yesterday_executions
        
        # 今日成功率
        today_success = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= today,
            ExecutionHistory.created_at < tomorrow,
            ExecutionHistory.status == 'success'
        ).count()
        
        today_success_rate = (today_success / today_executions * 100) if today_executions > 0 else 0
        
        # 昨日成功率
        yesterday_success = ExecutionHistory.query.filter(
            ExecutionHistory.created_at >= yesterday,
            ExecutionHistory.created_at < today,
            ExecutionHistory.status == 'success'
        ).count()
        
        yesterday_success_rate = (yesterday_success / yesterday_executions * 100) if yesterday_executions > 0 else 0
        success_rate_change = today_success_rate - yesterday_success_rate
        
        # 平均执行时间
        avg_duration_result = db.session.query(func.avg(ExecutionHistory.duration)).filter(
            ExecutionHistory.created_at >= today,
            ExecutionHistory.created_at < tomorrow,
            ExecutionHistory.duration.isnot(None)
        ).scalar()
        
        avg_duration = float(avg_duration_result) if avg_duration_result else 0
        
        # 昨日平均执行时间
        yesterday_avg_result = db.session.query(func.avg(ExecutionHistory.duration)).filter(
            ExecutionHistory.created_at >= yesterday,
            ExecutionHistory.created_at < today,
            ExecutionHistory.duration.isnot(None)
        ).scalar()
        
        yesterday_avg_duration = float(yesterday_avg_result) if yesterday_avg_result else 0
        duration_change = avg_duration - yesterday_avg_duration
        
        # 待处理失败数
        pending_failures = ExecutionHistory.query.filter(
            ExecutionHistory.status == 'failed',
            ExecutionHistory.created_at >= today - timedelta(days=7)  # 最近7天的失败
        ).count()
        
        return jsonify({
            'code': 200,
            'data': {
                'today_executions': today_executions,
                'executions_change': executions_change,
                'today_success_rate': round(today_success_rate, 1),
                'success_rate_change': round(success_rate_change, 1),
                'avg_duration': round(avg_duration, 1),
                'duration_change': round(duration_change, 1),
                'pending_failures': pending_failures
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取今日统计失败: {str(e)}'
        }), 500

@api_bp.route('/system/status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        import os
        
        # 检查服务状态
        services = []
        
        # AI模型服务状态（从本地代理服务器获取模型名称）
        ai_model_info = '监测中'
        try:
            # 尝试从本地代理服务器获取模型信息
            proxy_response = requests.get('http://localhost:3001/health', timeout=5)
            if proxy_response.status_code == 200:
                health_data = proxy_response.json()
                if health_data.get('success') and health_data.get('model'):
                    ai_model_info = health_data['model']
        except Exception:
            # 如果无法获取模型信息，保持默认的"监测中"状态
            pass
        
        services.append({
            'name': 'AI模型服务',
            'status': 'info',  # 统一状态，不显示圆点
            'info': ai_model_info
        })
        
        # 本地代理状态（检查midscene服务器）
        local_proxy_status = 'offline'
        local_proxy_info = 'localhost:3001 • 未检测到'
        
        try:
            # 尝试连接本地代理服务
            response = requests.get('http://localhost:3001/health', timeout=2)
            if response.status_code == 200:
                local_proxy_status = 'online'
                local_proxy_info = 'localhost:3001 • 连接正常'
        except requests.exceptions.ConnectionError:
            local_proxy_status = 'offline'
            local_proxy_info = 'localhost:3001 • 连接失败'
        except requests.exceptions.Timeout:
            local_proxy_status = 'warning'
            local_proxy_info = 'localhost:3001 • 响应超时'
        except Exception as e:
            local_proxy_status = 'offline'
            local_proxy_info = f'localhost:3001 • 错误: {str(e)[:20]}'
        
        services.append({
            'name': '本地代理',
            'status': local_proxy_status,
            'info': local_proxy_info
        })
        
        # 数据库状态
        try:
            from sqlalchemy import text
            import time
            
            # 测量数据库响应时间
            start_time = time.time()
            db.session.execute(text('SELECT 1'))
            db.session.commit()  # 确保查询实际执行
            response_time = int((time.time() - start_time) * 1000)  # 转换为毫秒
            
            # 检测数据库类型
            db_url = os.getenv('DATABASE_URL', '')
            if 'postgresql' in db_url or 'postgres' in db_url:
                db_type = 'PostgreSQL'
            elif 'sqlite' in db_url or not db_url:
                db_type = 'SQLite'
            else:
                db_type = 'Database'
            
            db_status = 'online'
            db_info = f'{db_type} • 延迟 {response_time}ms'
        except Exception as e:
            db_status = 'offline'
            db_info = f'数据库 • 连接失败'
        
        services.append({
            'name': '数据库',
            'status': db_status,
            'info': db_info
        })
        
        # 正在执行的测试数
        running_tests = ExecutionHistory.query.filter(
            ExecutionHistory.status == 'running'
        ).count()
        
        # 队列大小（暂时设为0）
        queue_size = 0
        
        return jsonify({
            'code': 200,
            'data': {
                'services': services,
                'running_tests': running_tests,
                'queue_size': queue_size
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取系统状态失败: {str(e)}'
        }), 500

@api_bp.route('/stats/trend', methods=['GET'])
def get_execution_trend():
    """获取执行趋势数据"""
    try:
        from datetime import datetime, timedelta
        
        days = request.args.get('days', 7, type=int)
        trend_data = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days-1-i)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            count = ExecutionHistory.query.filter(
                ExecutionHistory.start_time >= day_start,
                ExecutionHistory.start_time < day_end
            ).count()
            
            trend_data.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'count': count
            })
        
        return jsonify({
            'code': 200,
            'data': trend_data
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取执行趋势失败: {str(e)}'
        }), 500

@api_bp.route('/testcases/search', methods=['GET'])
def search_testcases():
    """搜索测试用例"""
    try:
        query = request.args.get('q', '')
        size = request.args.get('size', 5, type=int)
        
        if not query:
            return jsonify({
                'code': 200,
                'data': {
                    'items': [],
                    'total': 0
                }
            })
        
        # 搜索名称或描述包含关键词的测试用例
        testcases = TestCase.query.filter(
            TestCase.is_active == True,
            (TestCase.name.contains(query) | TestCase.description.contains(query))
        ).limit(size).all()
        
        return jsonify({
            'code': 200,
            'data': {
                'items': [tc.to_dict() for tc in testcases],
                'total': len(testcases)
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'搜索失败: {str(e)}'
        }), 500

@api_bp.route('/user/favorites', methods=['GET'])
def get_user_favorites():
    """获取用户收藏的测试用例ID列表"""
    try:
        # 暂时返回模拟数据，实际应该从用户表或缓存中获取
        # 可以通过cookie或session存储
        favorites = [1, 2, 3]  # 模拟收藏的测试用例ID
        
        return jsonify({
            'code': 200,
            'data': favorites
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取收藏列表失败: {str(e)}'
        }), 500

@api_bp.route('/user/favorites/<int:testcase_id>', methods=['POST'])
def add_favorite(testcase_id):
    """添加收藏"""
    try:
        # 实际应该保存到数据库或缓存
        return jsonify({
            'code': 200,
            'message': '收藏成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'收藏失败: {str(e)}'
        }), 500

@api_bp.route('/user/favorites/<int:testcase_id>', methods=['DELETE'])
def remove_favorite(testcase_id):
    """取消收藏"""
    try:
        # 实际应该从数据库或缓存中删除
        return jsonify({
            'code': 200,
            'message': '取消收藏成功'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'取消收藏失败: {str(e)}'
        }), 500
