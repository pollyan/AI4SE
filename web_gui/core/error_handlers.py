"""
Error Handlers - 统一错误处理
从app_enhanced.py中提取并优化的错误处理逻辑
"""

import logging
from flask import request, jsonify, render_template

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """注册全局错误处理器"""
    
    # 导入自定义异常类
    try:
        from ..utils.error_handler import APIError, ValidationError, NotFoundError, DatabaseError
    except ImportError:
        from web_gui.utils.error_handler import APIError, ValidationError, NotFoundError, DatabaseError
    
    @app.errorhandler(APIError)
    def handle_api_error(e):
        """处理API自定义异常"""
        logger.warning(f"API错误: {e.message} (代码: {e.code})")
        return jsonify(e.to_dict()), e.code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """处理验证错误"""
        return jsonify({
            'code': e.code,
            'message': e.message,
            'details': e.details
        }), e.code
    
    @app.errorhandler(NotFoundError)
    def handle_not_found_error(e):
        """处理404错误"""
        return jsonify({
            'code': 404,
            'message': e.message
        }), 404
    
    @app.errorhandler(DatabaseError)
    def handle_database_error(e):
        """处理数据库错误"""
        logger.error(f"数据库错误: {e.message}")
        return jsonify({
            'code': 500,
            'message': '数据库操作失败，请稍后重试'
        }), 500
    
    @app.errorhandler(404)
    def handle_404(e):
        """处理404错误"""
        if request.path.startswith('/api/'):
            return jsonify({
                'code': 404,
                'message': '接口不存在'
            }), 404
        # 返回404页面（如果存在）
        try:
            return render_template('404.html'), 404
        except:
            return jsonify({'error': 'Page not found'}), 404
    
    @app.errorhandler(500)
    def handle_500(e):
        """处理500错误"""
        logger.error(f"服务器内部错误: {str(e)}")
        
        if request.path.startswith('/api/'):
            return jsonify({
                'code': 500,
                'message': '服务器内部错误'
            }), 500
        # 返回500页面（如果存在）
        try:
            return render_template('500.html'), 500
        except:
            return jsonify({'error': 'Internal server error'}), 500

    return app
