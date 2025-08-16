"""
模板管理API模块
包含测试模板的CRUD操作和应用功能
"""
import json
from datetime import datetime
from flask import request, jsonify

from . import api_bp
from .base import (
    api_error_handler, db_transaction_handler, validate_json_data,
    format_success_response, ValidationError, NotFoundError,
    get_pagination_params, format_paginated_response,
    standard_error_response, standard_success_response,
    require_json, log_api_call, db, Template, TestCase
)


# ==================== 模板管理 ====================

@api_bp.route('/templates', methods=['GET'])
@log_api_call
def get_templates():
    """获取模板列表（临时简化版本）"""
    try:
        # 返回空模板列表
        return jsonify({
            'code': 200,
            'message': '获取成功',
            'data': []
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取模板列表失败: {str(e)}'
        })


@api_bp.route('/templates', methods=['POST'])
@api_error_handler
@validate_json_data(required_fields=['name', 'content'])
@db_transaction_handler(db)
@log_api_call
def create_template():
    """创建模板"""
    data = request.get_json()
    
    # 验证模板内容格式
    content = data.get('content', {})
    if not isinstance(content, dict):
        raise ValidationError('模板内容必须是对象格式')
    
    # 创建模板
    template = Template(
        name=data['name'],
        description=data.get('description', ''),
        category=data.get('category', 'general'),
        content=json.dumps(content),
        created_by=data.get('created_by', 'system'),
        is_public=data.get('is_public', False)
    )
    
    db.session.add(template)
    
    return jsonify(format_success_response(
        data=template.to_dict(),
        message='模板创建成功'
    ))


@api_bp.route('/templates/<int:template_id>', methods=['GET'])
@log_api_call
def get_template(template_id):
    """获取模板详情"""
    try:
        template = Template.query.get(template_id)
        if not template or not template.is_active:
            return standard_error_response('模板不存在', 404)
        
        return standard_success_response(data=template.to_dict())
        
    except Exception as e:
        return standard_error_response(f'获取模板失败: {str(e)}')


@api_bp.route('/templates/<int:template_id>', methods=['PUT'])
@require_json
@log_api_call
def update_template(template_id):
    """更新模板"""
    try:
        template = Template.query.get(template_id)
        if not template or not template.is_active:
            return standard_error_response('模板不存在', 404)
        
        data = request.get_json()
        
        # 更新字段
        if 'name' in data:
            template.name = data['name']
        if 'description' in data:
            template.description = data['description']
        if 'category' in data:
            template.category = data['category']
        if 'content' in data:
            if isinstance(data['content'], dict):
                template.content = json.dumps(data['content'])
            else:
                return standard_error_response('模板内容必须是对象格式', 400)
        if 'is_public' in data:
            template.is_public = data['is_public']
        
        template.updated_at = datetime.utcnow()
        db.session.commit()
        
        return standard_success_response(
            data=template.to_dict(),
            message='模板更新成功'
        )
        
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f'更新模板失败: {str(e)}')


@api_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@log_api_call
def delete_template(template_id):
    """删除模板（软删除）"""
    try:
        template = Template.query.get(template_id)
        if not template:
            return standard_error_response('模板不存在', 404)
        
        template.is_active = False
        template.updated_at = datetime.utcnow()
        db.session.commit()
        
        return standard_success_response(message='模板删除成功')
        
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f'删除模板失败: {str(e)}')


@api_bp.route('/templates/<int:template_id>/apply', methods=['POST'])
@require_json
@log_api_call
def apply_template(template_id):
    """应用模板创建测试用例"""
    try:
        template = Template.query.get(template_id)
        if not template or not template.is_active:
            return standard_error_response('模板不存在', 404)
        
        data = request.get_json()
        
        # 解析模板内容
        template_content = json.loads(template.content)
        
        # 应用用户自定义参数
        custom_data = data.get('custom_data', {})
        
        # 创建测试用例数据
        testcase_data = {
            'name': data.get('name', f"{template.name}_测试用例"),
            'description': data.get('description', template.description),
            'category': data.get('category', template.category),
            'steps': template_content.get('steps', []),
            'tags': template_content.get('tags', []),
            'priority': data.get('priority', 'medium'),
            'template_id': template_id
        }
        
        # 应用自定义参数到步骤中
        if custom_data and 'steps' in testcase_data:
            testcase_data['steps'] = _apply_custom_parameters(
                testcase_data['steps'], custom_data
            )
        
        # 创建测试用例
        testcase = TestCase.from_dict(testcase_data)
        db.session.add(testcase)
        
        # 更新模板使用次数
        template.usage_count += 1
        template.last_used_at = datetime.utcnow()
        
        db.session.commit()
        
        return standard_success_response(
            data=testcase.to_dict(),
            message='模板应用成功，测试用例已创建'
        )
        
    except Exception as e:
        db.session.rollback()
        return standard_error_response(f'应用模板失败: {str(e)}')


@api_bp.route('/templates/categories', methods=['GET'])
@log_api_call
def get_template_categories():
    """获取模板分类列表"""
    try:
        # 从数据库查询所有分类
        categories = db.session.query(Template.category).filter(
            Template.is_active == True
        ).distinct().all()
        
        category_list = [cat[0] for cat in categories if cat[0]]
        
        return standard_success_response(data={
            'categories': category_list,
            'count': len(category_list)
        })
        
    except Exception as e:
        return standard_error_response(f'获取模板分类失败: {str(e)}')


# ==================== 辅助函数 ====================

def _apply_custom_parameters(steps, custom_data):
    """将自定义参数应用到模板步骤中"""
    try:
        import re
        
        # 将步骤转换为JSON字符串以便进行参数替换
        steps_json = json.dumps(steps)
        
        # 替换参数占位符（格式：{{parameter_name}}）
        for key, value in custom_data.items():
            placeholder = f"{{{{{key}}}}}"
            steps_json = steps_json.replace(placeholder, str(value))
        
        # 替换通用占位符
        common_placeholders = {
            '{{timestamp}}': datetime.utcnow().strftime('%Y%m%d_%H%M%S'),
            '{{date}}': datetime.utcnow().strftime('%Y-%m-%d'),
            '{{time}}': datetime.utcnow().strftime('%H:%M:%S')
        }
        
        for placeholder, value in common_placeholders.items():
            steps_json = steps_json.replace(placeholder, value)
        
        return json.loads(steps_json)
        
    except Exception as e:
        # 如果参数替换失败，返回原始步骤
        return steps