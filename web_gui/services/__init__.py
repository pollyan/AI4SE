"""
Services Package - 业务逻辑服务层
重构后的服务层，提供清晰的业务逻辑抽象
"""

try:
    from .variable_resolver_service import (
        VariableManager,
        VariableManagerFactory,
        get_variable_manager,
        cleanup_execution_variables,
    )
except ImportError:
    VariableManager = None
    VariableManagerFactory = None
    get_variable_manager = None
    cleanup_execution_variables = None

from .ai_service import AIServiceInterface, get_ai_service

try:
    from .execution_service import ExecutionService
except ImportError:
    ExecutionService = None

__all__ = [
    "VariableManager",
    "VariableManagerFactory", 
    "get_variable_manager",
    "cleanup_execution_variables",
    "AIServiceInterface",
    "get_ai_service",
    "ExecutionService",
]

