"""
WebSocket Service - WebSocket服务
从app_enhanced.py中提取的WebSocket事件处理逻辑
"""

import logging
from datetime import datetime
from flask import request
from flask_socketio import emit

from ..core.extensions import socketio
from .execution_service import get_execution_service
from .ai_service import get_ai_service

logger = logging.getLogger(__name__)

class WebSocketService:
    """WebSocket服务"""
    
    def __init__(self):
        self.execution_service = get_execution_service()
        self._register_handlers()
    
    def _register_handlers(self):
        """注册WebSocket事件处理器"""
        
        @socketio.on('connect')
        def handle_connect():
            """客户端连接"""
            logger.info(f'客户端已连接: {request.sid}')
            
            # 检查AI服务可用性
            try:
                ai = get_ai_service()
                ai_available = True
            except:
                ai_available = False
            
            emit('connected', {
                'message': '连接成功',
                'ai_available': ai_available,
                'server_time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            })
        
        @socketio.on('disconnect')
        def handle_disconnect():
            """客户端断开连接"""
            logger.info(f'客户端已断开: {request.sid}')
        
        @socketio.on('ping')
        def handle_ping():
            """心跳检测"""
            emit('pong', {'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')})
        
        @socketio.on('start_execution')
        def handle_start_execution(data):
            """开始执行测试用例"""
            try:
                testcase_id = data.get('testcase_id')
                mode = data.get('mode', 'headless')
                
                if not testcase_id:
                    emit('execution_error', {'message': '缺少testcase_id参数'})
                    return
                
                # 启动异步执行
                execution_id = self.execution_service.execute_testcase_async(testcase_id, mode)
                
                emit('execution_started', {
                    'execution_id': execution_id,
                    'message': '执行已启动'
                })
                
            except Exception as e:
                emit('execution_error', {'message': f'启动执行失败: {str(e)}'})
        
        @socketio.on('stop_execution')
        def handle_stop_execution(data):
            """停止执行测试用例"""
            execution_id = data.get('execution_id')
            if execution_id:
                # TODO: 实现停止执行逻辑
                emit('execution_stopped', {
                    'execution_id': execution_id,
                    'message': '执行已停止'
                })
            else:
                emit('error', {'message': '缺少execution_id参数'})

# 全局WebSocket服务实例
_websocket_service = None

def get_websocket_service() -> WebSocketService:
    """获取WebSocket服务实例（单例模式）"""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = WebSocketService()
    return _websocket_service

def init_websocket_service():
    """初始化WebSocket服务（在应用启动时调用）"""
    get_websocket_service()
