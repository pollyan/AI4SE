"""
Utils Package - 工具函数模块
从app_enhanced.py中提取的工具函数
"""

from .execution_utils import basic_variable_resolve
from .mock_ai_utils import (
    mock_ai_query_result,
    mock_ai_query_result_from_schema,
    mock_ai_string_result,
    mock_ai_ask_result,
    mock_javascript_result
)

__all__ = [
    'basic_variable_resolve',
    'mock_ai_query_result',
    'mock_ai_query_result_from_schema', 
    'mock_ai_string_result',
    'mock_ai_ask_result',
    'mock_javascript_result'
]