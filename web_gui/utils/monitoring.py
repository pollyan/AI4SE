"""
系统监控和指标收集模块
提供错误监控、性能指标、健康检查等功能
"""
import time
import threading
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from flask import request, has_request_context
import psutil
import json

logger = logging.getLogger(__name__)


@dataclass
class ErrorMetric:
    """错误指标数据类"""
    error_type: str
    message: str
    count: int
    last_occurrence: datetime
    endpoint: str
    status_code: int


@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    endpoint: str
    method: str
    response_time: float
    timestamp: datetime
    status_code: int
    memory_usage: float


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size
        self._lock = threading.Lock()
        
        # 错误统计
        self.error_counts = defaultdict(int)
        self.error_history = deque(maxlen=max_history_size)
        self.error_details = {}
        
        # 性能指标
        self.response_times = deque(maxlen=max_history_size)
        self.endpoint_stats = defaultdict(list)
        
        # 系统指标
        self.system_metrics = deque(maxlen=100)
        
        # 健康检查
        self.health_checks = {}
        
        # 启动监控线程
        self._start_system_monitoring()
    
    def record_error(self, error_type: str, message: str, endpoint: str = None, 
                    status_code: int = 500, details: Dict = None):
        """记录错误"""
        with self._lock:
            key = f"{error_type}_{endpoint or 'unknown'}"
            self.error_counts[key] += 1
            
            error_metric = ErrorMetric(
                error_type=error_type,
                message=message,
                count=self.error_counts[key],
                last_occurrence=datetime.utcnow(),
                endpoint=endpoint or 'unknown',
                status_code=status_code
            )
            
            self.error_history.append(error_metric)
            self.error_details[key] = {
                'details': details or {},
                'last_seen': datetime.utcnow().isoformat()
            }
            
            logger.error(f"错误记录: {error_type} - {message} [{endpoint}]")
    
    def record_performance(self, endpoint: str, method: str, response_time: float, 
                          status_code: int = 200):
        """记录性能指标"""
        try:
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        except:
            memory_usage = 0
        
        with self._lock:
            metric = PerformanceMetric(
                endpoint=endpoint,
                method=method,
                response_time=response_time,
                timestamp=datetime.utcnow(),
                status_code=status_code,
                memory_usage=memory_usage
            )
            
            self.response_times.append(metric)
            self.endpoint_stats[f"{method}_{endpoint}"].append(response_time)
            
            # 保持endpoint统计数据的大小限制
            if len(self.endpoint_stats[f"{method}_{endpoint}"]) > 100:
                self.endpoint_stats[f"{method}_{endpoint}"].pop(0)
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取错误摘要"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_errors = [
                error for error in self.error_history 
                if error.last_occurrence >= cutoff
            ]
            
            # 按错误类型分组
            error_by_type = defaultdict(list)
            for error in recent_errors:
                error_by_type[error.error_type].append(error)
            
            # 统计
            summary = {
                'total_errors': len(recent_errors),
                'unique_errors': len(error_by_type),
                'error_types': {},
                'top_endpoints': defaultdict(int),
                'error_trend': []
            }
            
            for error_type, errors in error_by_type.items():
                summary['error_types'][error_type] = {
                    'count': len(errors),
                    'latest': max(errors, key=lambda x: x.last_occurrence).message
                }
            
            # 统计出错最多的端点
            for error in recent_errors:
                summary['top_endpoints'][error.endpoint] += 1
            
            # 转换为列表并排序
            summary['top_endpoints'] = sorted(
                summary['top_endpoints'].items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            return summary
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取性能摘要"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_metrics = [
                metric for metric in self.response_times 
                if metric.timestamp >= cutoff
            ]
            
            if not recent_metrics:
                return {
                    'total_requests': 0,
                    'average_response_time': 0,
                    'p95_response_time': 0,
                    'p99_response_time': 0,
                    'slowest_endpoints': [],
                    'memory_usage': {'current': 0, 'average': 0}
                }
            
            response_times = [m.response_time for m in recent_metrics]
            memory_usages = [m.memory_usage for m in recent_metrics if m.memory_usage > 0]
            
            # 计算百分位数
            response_times.sort()
            p95_index = int(len(response_times) * 0.95)
            p99_index = int(len(response_times) * 0.99)
            
            # 统计最慢的端点
            endpoint_times = defaultdict(list)
            for metric in recent_metrics:
                endpoint_times[f"{metric.method} {metric.endpoint}"].append(metric.response_time)
            
            slowest_endpoints = []
            for endpoint, times in endpoint_times.items():
                avg_time = sum(times) / len(times)
                slowest_endpoints.append((endpoint, avg_time, len(times)))
            
            slowest_endpoints.sort(key=lambda x: x[1], reverse=True)
            
            return {
                'total_requests': len(recent_metrics),
                'average_response_time': sum(response_times) / len(response_times),
                'p95_response_time': response_times[p95_index] if p95_index < len(response_times) else 0,
                'p99_response_time': response_times[p99_index] if p99_index < len(response_times) else 0,
                'slowest_endpoints': slowest_endpoints[:10],
                'memory_usage': {
                    'current': memory_usages[-1] if memory_usages else 0,
                    'average': sum(memory_usages) / len(memory_usages) if memory_usages else 0
                }
            }
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            health = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': memory.available / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / (1024**3)
                },
                'application': {
                    'uptime_minutes': self._get_uptime_minutes(),
                    'error_rate_24h': self._calculate_error_rate(24),
                    'avg_response_time_1h': self._calculate_avg_response_time(1)
                },
                'checks': {}
            }
            
            # 执行健康检查
            for check_name, check_func in self.health_checks.items():
                try:
                    health['checks'][check_name] = check_func()
                except Exception as e:
                    health['checks'][check_name] = {'status': 'error', 'error': str(e)}
            
            # 根据各项指标确定整体健康状态
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                health['status'] = 'warning'
            
            if any(check.get('status') == 'error' for check in health['checks'].values()):
                health['status'] = 'error'
            
            return health
            
        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def register_health_check(self, name: str, check_func):
        """注册健康检查函数"""
        self.health_checks[name] = check_func
        logger.info(f"注册健康检查: {name}")
    
    def _start_system_monitoring(self):
        """启动系统监控线程"""
        def monitor_loop():
            while True:
                try:
                    cpu_percent = psutil.cpu_percent(interval=None)
                    memory = psutil.virtual_memory()
                    
                    with self._lock:
                        self.system_metrics.append({
                            'timestamp': datetime.utcnow(),
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory.percent,
                            'memory_used_gb': memory.used / (1024**3)
                        })
                    
                    time.sleep(60)  # 每分钟采集一次系统指标
                    
                except Exception as e:
                    logger.error(f"系统监控线程错误: {e}")
                    time.sleep(60)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
        logger.info("系统监控线程已启动")
    
    def _get_uptime_minutes(self) -> float:
        """获取应用运行时间（分钟）"""
        if hasattr(self, '_start_time'):
            return (time.time() - self._start_time) / 60
        else:
            self._start_time = time.time()
            return 0
    
    def _calculate_error_rate(self, hours: int) -> float:
        """计算错误率"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            total_requests = len([m for m in self.response_times if m.timestamp >= cutoff])
            error_requests = len([m for m in self.response_times 
                                if m.timestamp >= cutoff and m.status_code >= 400])
        
        return (error_requests / total_requests * 100) if total_requests > 0 else 0
    
    def _calculate_avg_response_time(self, hours: int) -> float:
        """计算平均响应时间"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            recent_times = [m.response_time for m in self.response_times if m.timestamp >= cutoff]
        
        return sum(recent_times) / len(recent_times) if recent_times else 0


# 全局监控实例
_monitor = None

def get_monitor() -> SystemMonitor:
    """获取全局监控实例"""
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor()
    return _monitor

def monitoring_middleware(app):
    """Flask监控中间件"""
    monitor = get_monitor()
    
    @app.before_request
    def before_request():
        request.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            
            monitor.record_performance(
                endpoint=request.endpoint or request.path,
                method=request.method,
                response_time=response_time,
                status_code=response.status_code
            )
        
        return response
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        if hasattr(request, 'start_time'):
            response_time = time.time() - request.start_time
            
            monitor.record_error(
                error_type=type(e).__name__,
                message=str(e),
                endpoint=request.endpoint or request.path,
                status_code=500,
                details={
                    'method': request.method,
                    'path': request.path,
                    'response_time': response_time
                }
            )
        
        raise e  # 重新抛出异常，让其他错误处理器处理
    
    return app

def setup_monitoring(app):
    """设置应用监控"""
    monitoring_middleware(app)
    
    # 注册基础健康检查
    monitor = get_monitor()
    
    def database_check():
        """数据库健康检查"""
        try:
            from web_gui.models import db
            db.session.execute('SELECT 1')
            return {'status': 'ok', 'message': '数据库连接正常'}
        except Exception as e:
            return {'status': 'error', 'message': f'数据库连接失败: {str(e)}'}
    
    def memory_check():
        """内存使用检查"""
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            return {'status': 'warning', 'message': f'内存使用率过高: {memory.percent}%'}
        return {'status': 'ok', 'message': f'内存使用正常: {memory.percent}%'}
    
    monitor.register_health_check('database', database_check)
    monitor.register_health_check('memory', memory_check)
    
    logger.info("应用监控设置完成")