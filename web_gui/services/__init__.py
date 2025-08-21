"""
Services Package - 业务逻辑服务层
"""

from .variable_resolver_service import VariableManager, VariableManagerFactory, get_variable_manager, cleanup_execution_variables

__all__ = [
    'VariableManager',
    'VariableManagerFactory',
    'get_variable_manager',
    'cleanup_execution_variables'
]