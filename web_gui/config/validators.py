"""
Validators - 配置验证
验证配置的有效性和完整性
"""

import logging
from typing import List, Dict, Any
from .settings import AppConfig

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """配置验证错误"""
    def __init__(self, message: str, errors: List[str]):
        self.message = message
        self.errors = errors
        super().__init__(message)

def validate_config(config: AppConfig) -> Dict[str, Any]:
    """
    验证配置的有效性
    
    Args:
        config: 应用配置实例
    
    Returns:
        验证结果字典
    
    Raises:
        ConfigValidationError: 当配置验证失败时
    """
    
    errors = []
    warnings = []
    
    # 验证安全配置
    security_errors = _validate_security_config(config.security)
    errors.extend(security_errors)
    
    # 验证数据库配置
    db_errors, db_warnings = _validate_database_config(config.database)
    errors.extend(db_errors)
    warnings.extend(db_warnings)
    
    # 验证AI配置
    ai_errors, ai_warnings = _validate_ai_config(config.ai)
    errors.extend(ai_errors) 
    warnings.extend(ai_warnings)
    
    # 验证路径配置
    path_errors = _validate_path_config(config.paths)
    errors.extend(path_errors)
    
    # 验证执行配置
    exec_errors = _validate_execution_config(config.execution)
    errors.extend(exec_errors)
    
    # 报告结果
    for warning in warnings:
        logger.warning(f"配置警告: {warning}")
    
    if errors:
        error_message = f"配置验证失败，发现 {len(errors)} 个错误"
        for error in errors:
            logger.error(f"配置错误: {error}")
        raise ConfigValidationError(error_message, errors)
    
    logger.info(f"配置验证通过 ({len(warnings)} 个警告)")
    
    return {
        'valid': True,
        'errors': errors,
        'warnings': warnings,
        'summary': {
            'total_errors': len(errors),
            'total_warnings': len(warnings)
        }
    }

def _validate_security_config(security_config) -> List[str]:
    """验证安全配置"""
    errors = []
    
    if not security_config.secret_key:
        errors.append("SECRET_KEY 不能为空")
    
    if security_config.secret_key == 'dev-secret-key-change-in-production' and not security_config.debug:
        errors.append("生产环境不能使用默认 SECRET_KEY")
    
    if len(security_config.secret_key) < 16:
        errors.append("SECRET_KEY 长度至少需要 16 个字符")
    
    return errors

def _validate_database_config(database_config) -> tuple[List[str], List[str]]:
    """验证数据库配置"""
    errors = []
    warnings = []
    
    if not database_config.uri:
        errors.append("数据库 URI 不能为空")
    
    # 检查 SQLite 的安全性
    if database_config.uri.startswith('sqlite') and 'memory' not in database_config.uri:
        warnings.append("使用 SQLite 文件数据库，建议在生产环境使用 PostgreSQL")
    
    # 检查PostgreSQL配置
    if database_config.uri.startswith('postgresql'):
        if not database_config.engine_options:
            warnings.append("PostgreSQL 建议配置连接池参数")
    
    return errors, warnings

def _validate_ai_config(ai_config) -> tuple[List[str], List[str]]:
    """验证AI配置"""
    errors = []
    warnings = []
    
    if not ai_config.model_name:
        errors.append("AI模型名称不能为空")
    
    if not ai_config.api_key:
        warnings.append("AI API密钥未设置，将无法使用真实AI功能")
    
    if not ai_config.base_url:
        errors.append("AI服务基础URL不能为空")
    
    if not ai_config.server_url:
        errors.append("MidScene服务器URL不能为空")
    
    # 检查URL格式
    if ai_config.base_url and not (ai_config.base_url.startswith('http://') or ai_config.base_url.startswith('https://')):
        errors.append("AI服务基础URL格式不正确")
    
    if ai_config.server_url and not (ai_config.server_url.startswith('http://') or ai_config.server_url.startswith('https://')):
        errors.append("MidScene服务器URL格式不正确")
    
    return errors, warnings

def _validate_path_config(path_config) -> List[str]:
    """验证路径配置"""
    errors = []
    
    if not path_config.base_dir.exists():
        errors.append(f"基础目录不存在: {path_config.base_dir}")
    
    # 检查目录权限（尝试创建测试文件）
    try:
        test_file = path_config.screenshots_dir / '.write_test'
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        errors.append(f"截图目录没有写权限: {path_config.screenshots_dir} ({e})")
    
    try:
        test_file = path_config.logs_dir / '.write_test'
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        errors.append(f"日志目录没有写权限: {path_config.logs_dir} ({e})")
    
    return errors

def _validate_execution_config(execution_config) -> List[str]:
    """验证执行配置"""
    errors = []
    
    if execution_config.default_timeout <= 0:
        errors.append("默认超时时间必须大于0")
    
    if execution_config.max_concurrent_executions <= 0:
        errors.append("最大并发执行数必须大于0")
    
    if execution_config.max_concurrent_executions > 10:
        errors.append("最大并发执行数不建议超过10")
    
    # 检查各种超时设置
    timeouts = [
        ('页面超时', execution_config.page_timeout),
        ('操作超时', execution_config.action_timeout), 
        ('导航超时', execution_config.navigation_timeout)
    ]
    
    for name, timeout in timeouts:
        if timeout <= 0:
            errors.append(f"{name}必须大于0")
        elif timeout < 5000:
            errors.append(f"{name}不建议小于5秒")
        elif timeout > 120000:
            errors.append(f"{name}不建议大于2分钟")
    
    return errors

def check_environment_variables() -> Dict[str, Any]:
    """检查必要的环境变量"""
    import os
    
    required_vars = []
    optional_vars = [
        'SECRET_KEY',
        'DATABASE_URL', 
        'OPENAI_API_KEY',
        'MIDSCENE_MODEL_NAME',
        'OPENAI_BASE_URL',
        'MIDSCENE_SERVER_URL'
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    return {
        'missing_required': missing_required,
        'missing_optional': missing_optional,
        'has_critical_missing': bool(missing_required),
        'env_summary': {
            'total_required': len(required_vars),
            'total_optional': len(optional_vars),
            'missing_required_count': len(missing_required),
            'missing_optional_count': len(missing_optional)
        }
    }
