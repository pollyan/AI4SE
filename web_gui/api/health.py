from flask import Blueprint
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health():
    # 与测试预期对齐，包含状态/时间戳/版本
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0"
    }

"""
系统健康检查和监控API
提供系统状态、错误监控、性能指标等信息
"""

from flask import request, jsonify
import logging

from . import api_bp
from .base import standard_success_response, standard_error_response, log_api_call

# 导入监控工具
try:
    from ..utils.monitoring import get_monitor

    MONITORING_AVAILABLE = True
except ImportError:
    try:
        from web_gui.utils.monitoring import get_monitor

        MONITORING_AVAILABLE = True
    except ImportError:
        MONITORING_AVAILABLE = False

logger = logging.getLogger(__name__)


@api_bp.route("/health", methods=["GET"])
def health_check():
    """基础健康检查端点"""
    try:
        health_data = {
            "status": "ok",
            "message": "Intent Test Framework is running",
            "timestamp": "2025-08-16T10:30:00.000Z",
            "version": "1.0.0",
        }
        return standard_success_response(data=health_data)
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return standard_error_response(str(e), 500)


@api_bp.route("/health/detailed", methods=["GET"])
@log_api_call
def detailed_health_check():
    """详细的系统健康检查"""
    if not MONITORING_AVAILABLE:
        return standard_error_response("监控系统不可用", 503)

    try:
        monitor = get_monitor()
        health_data = monitor.get_system_health()

        return standard_success_response(data=health_data)
    except Exception as e:
        logger.error(f"详细健康检查失败: {e}")
        return standard_error_response(f"健康检查失败: {str(e)}", 500)


@api_bp.route("/monitoring/errors", methods=["GET"])
@log_api_call
def get_error_metrics():
    """获取错误指标"""
    if not MONITORING_AVAILABLE:
        return standard_error_response("监控系统不可用", 503)

    try:
        hours = request.args.get("hours", 24, type=int)
        monitor = get_monitor()
        error_summary = monitor.get_error_summary(hours=hours)

        return standard_success_response(data=error_summary)
    except Exception as e:
        logger.error(f"获取错误指标失败: {e}")
        return standard_error_response(f"获取错误指标失败: {str(e)}", 500)


@api_bp.route("/monitoring/performance", methods=["GET"])
@log_api_call
def get_performance_metrics():
    """获取性能指标"""
    if not MONITORING_AVAILABLE:
        return standard_error_response("监控系统不可用", 503)

    try:
        hours = request.args.get("hours", 24, type=int)
        monitor = get_monitor()
        perf_summary = monitor.get_performance_summary(hours=hours)

        return standard_success_response(data=perf_summary)
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        return standard_error_response(f"获取性能指标失败: {str(e)}", 500)


@api_bp.route("/monitoring/system", methods=["GET"])
@log_api_call
def get_system_metrics():
    """获取系统资源使用指标"""
    if not MONITORING_AVAILABLE:
        return standard_error_response("监控系统不可用", 503)

    try:
        import psutil

        system_info = {
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            },
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage("/")._asdict(),
            "network": {
                "connections": len(psutil.net_connections()),
                "stats": psutil.net_io_counters()._asdict(),
            },
        }

        return standard_success_response(data=system_info)
    except Exception as e:
        logger.error(f"获取系统指标失败: {e}")
        return standard_error_response(f"获取系统指标失败: {str(e)}", 500)
