"""
Services Package - 业务逻辑服务层
重构后的服务层，提供清晰的业务逻辑抽象
"""

from .variable_resolver_service import (
    VariableManager,
    VariableManagerFactory,
    get_variable_manager,
    cleanup_execution_variables,
)
from .ai_service import AIServiceInterface, get_ai_service
from .execution_service import ExecutionService

__all__ = [
    "VariableManager",
    "VariableManagerFactory", 
    "get_variable_manager",
    "cleanup_execution_variables",
    "AIServiceInterface",
    "get_ai_service",
    "ExecutionService",
]
