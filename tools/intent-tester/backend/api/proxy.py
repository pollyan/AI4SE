from flask import Blueprint, send_file, jsonify
import os
from datetime import datetime
import logging

from backend.intent_security.policy import EndpointPolicy, intent_policy

logger = logging.getLogger(__name__)

proxy_bp = Blueprint('proxy', __name__)

@proxy_bp.route('/download-proxy')
@intent_policy(EndpointPolicy.PUBLIC_READONLY)
def download_proxy():
    """下载本地代理包"""
    try:
        # 定位 zip 文件路径
        # 当前文件: tools/intent-tester/backend/api/proxy.py
        # 目标文件: dist/intent-test-proxy.zip (相对于项目根目录)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # current_dir: .../backend/api
        # target: .../frontend/static/intent-test-proxy.zip
        # path: ../../frontend/static/intent-test-proxy.zip
        
        static_dir = os.path.abspath(os.path.join(current_dir, '../../frontend/static'))
        zip_path = os.path.join(static_dir, 'intent-test-proxy.zip')
        
        logger.info(f"Serving proxy package from: {zip_path}")
        
        if not os.path.exists(zip_path):
             logger.error(f"本地代理包未找到: {zip_path}")
             return jsonify({"code": 404, "message": "本地代理包未找到"}), 404
            
        logger.info(f"开始下载本地代理包: {zip_path}")
        return send_file(zip_path, as_attachment=True, download_name='intent-test-proxy.zip')
        
    except Exception as e:
        logger.error(f"下载本地代理包失败: {str(e)}")
        return jsonify({"code": 500, "message": "下载失败"}), 500

@proxy_bp.route('/proxy-version')
@intent_policy(EndpointPolicy.PUBLIC_READONLY)
def proxy_version():
    """获取本地代理版本信息"""
    try:
        # 尝试读取文件修改时间作为版本日期
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, '../../../../'))
        zip_path = os.path.join(root_dir, 'dist', 'intent-test-proxy.zip')
        
        version_date = datetime.now().strftime("%Y-%m-%d")
        
        if os.path.exists(zip_path):
             mtime = os.path.getmtime(zip_path)
             version_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        
        return jsonify({
            "code": 200, 
            "data": {
                "version": "v1.0.0", # 暂时硬编码版本号
                "date": version_date
            }
        })
    except Exception as e:
        logger.error(f"获取版本信息失败: {str(e)}")
        return jsonify({"code": 500, "message": "获取版本信息失败"}), 500
