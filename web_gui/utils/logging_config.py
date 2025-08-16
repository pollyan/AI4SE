"""
日志配置模块
提供统一的日志配置和管理功能
"""
import os
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置颜色
    }
    
    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # 设置格式
        record.levelname_colored = f"{color}{record.levelname:8}{reset}"
        record.name_colored = f"\033[94m{record.name}\033[0m"  # 蓝色模块名
        
        return super().format(record)


class RequestContextFilter(logging.Filter):
    """请求上下文过滤器，添加请求相关信息到日志"""
    
    def filter(self, record):
        try:
            from flask import request, has_request_context
            
            if has_request_context():
                record.request_id = getattr(request, 'request_id', 'unknown')
                record.method = request.method
                record.path = request.path
                record.remote_addr = request.remote_addr
            else:
                record.request_id = 'no-request'
                record.method = '-'
                record.path = '-'
                record.remote_addr = '-'
        except ImportError:
            # Flask不可用时的默认值
            record.request_id = 'no-flask'
            record.method = '-'
            record.path = '-'
            record.remote_addr = '-'
        
        return True


class LoggingConfig:
    """日志配置管理器"""
    
    def __init__(self, app=None):
        self.app = app
        self.log_dir = None
        self.setup_log_directory()
    
    def setup_log_directory(self):
        """设置日志目录"""
        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent
        self.log_dir = project_root / 'logs'
        
        # 创建日志目录
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建子目录
        (self.log_dir / 'api').mkdir(exist_ok=True)
        (self.log_dir / 'execution').mkdir(exist_ok=True)
        (self.log_dir / 'error').mkdir(exist_ok=True)
        (self.log_dir / 'performance').mkdir(exist_ok=True)
    
    def configure_logging(self, level=logging.INFO, enable_file_logging=True):
        """配置日志系统"""
        
        # 清理现有的handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 设置根日志级别
        root_logger.setLevel(level)
        
        # 创建格式化器
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s [%(levelname_colored)s] %(name_colored)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        file_formatter = logging.Formatter(
            fmt='%(asctime)s [%(levelname)-8s] [%(request_id)s] %(name)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        if enable_file_logging:
            # 应用日志文件处理器
            app_log_file = self.log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
            app_handler = logging.handlers.TimedRotatingFileHandler(
                filename=app_log_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            app_handler.setLevel(level)
            app_handler.setFormatter(file_formatter)
            app_handler.addFilter(RequestContextFilter())
            root_logger.addHandler(app_handler)
            
            # API访问日志处理器
            api_log_file = self.log_dir / 'api' / f"api_{datetime.now().strftime('%Y%m%d')}.log"
            api_handler = logging.handlers.TimedRotatingFileHandler(
                filename=api_log_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            api_handler.setLevel(logging.INFO)
            api_handler.setFormatter(file_formatter)
            api_handler.addFilter(RequestContextFilter())
            
            # 只有API相关的日志才写入API日志文件
            api_logger = logging.getLogger('web_gui.api')
            api_logger.addHandler(api_handler)
            api_logger.propagate = True  # 仍然传播到根日志器
            
            # 错误日志处理器
            error_log_file = self.log_dir / 'error' / f"error_{datetime.now().strftime('%Y%m%d')}.log"
            error_handler = logging.handlers.TimedRotatingFileHandler(
                filename=error_log_file,
                when='midnight',
                interval=1,
                backupCount=90,  # 错误日志保留更长时间
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            error_handler.addFilter(RequestContextFilter())
            root_logger.addHandler(error_handler)
            
            # 执行日志处理器
            execution_log_file = self.log_dir / 'execution' / f"execution_{datetime.now().strftime('%Y%m%d')}.log"
            execution_handler = logging.handlers.TimedRotatingFileHandler(
                filename=execution_log_file,
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            execution_handler.setLevel(logging.INFO)
            execution_handler.setFormatter(file_formatter)
            execution_handler.addFilter(RequestContextFilter())
            
            execution_logger = logging.getLogger('execution')
            execution_logger.addHandler(execution_handler)
            execution_logger.propagate = True
            
            # 性能日志处理器
            performance_log_file = self.log_dir / 'performance' / f"performance_{datetime.now().strftime('%Y%m%d')}.log"
            performance_handler = logging.handlers.TimedRotatingFileHandler(
                filename=performance_log_file,
                when='midnight',
                interval=1,
                backupCount=7,  # 性能日志保留时间较短
                encoding='utf-8'
            )
            performance_handler.setLevel(logging.INFO)
            performance_handler.setFormatter(file_formatter)
            
            performance_logger = logging.getLogger('performance')
            performance_logger.addHandler(performance_handler)
            performance_logger.propagate = False  # 不传播到根日志器，避免重复
        
        # 设置第三方库的日志级别
        logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Flask开发服务器日志
        logging.getLogger('urllib3').setLevel(logging.WARNING)   # HTTP请求库日志
        logging.getLogger('requests').setLevel(logging.WARNING)  # Requests库日志
        
        logging.info("日志系统配置完成")
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志器"""
        return logging.getLogger(name)
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """清理旧日志文件"""
        from datetime import datetime, timedelta
        import glob
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        log_patterns = [
            self.log_dir / '*.log',
            self.log_dir / '*' / '*.log'
        ]
        
        deleted_count = 0
        for pattern in log_patterns:
            for log_file in glob.glob(str(pattern)):
                log_path = Path(log_file)
                if log_path.stat().st_mtime < cutoff_date.timestamp():
                    try:
                        log_path.unlink()
                        deleted_count += 1
                        logging.info(f"删除旧日志文件: {log_path}")
                    except OSError as e:
                        logging.error(f"删除日志文件失败 {log_path}: {e}")
        
        logging.info(f"清理完成，删除了 {deleted_count} 个旧日志文件")
        return deleted_count


# 全局日志配置实例
_logging_config = None

def get_logging_config():
    """获取全局日志配置实例"""
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig()
    return _logging_config

def setup_logging(level=None, enable_file_logging=True):
    """设置日志配置"""
    if level is None:
        level = logging.DEBUG if os.getenv('DEBUG', '').lower() in ('1', 'true') else logging.INFO
    
    config = get_logging_config()
    config.configure_logging(level, enable_file_logging)
    return config

def get_logger(name: str) -> logging.Logger:
    """便捷函数：获取日志器"""
    return logging.getLogger(name)

# 性能监控装饰器
def log_performance(logger_name: str = 'performance'):
    """性能监控装饰器"""
    def decorator(func):
        from functools import wraps
        import time
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(logger_name)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"{func.__name__} 执行时间: {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{func.__name__} 执行失败 ({duration:.3f}s): {str(e)}")
                raise
        
        return wrapper
    return decorator