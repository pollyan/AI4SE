"""
Execution Utils - 执行相关工具函数
从app_enhanced.py中提取的执行相关工具函数
"""

import re
import logging

logger = logging.getLogger(__name__)

def basic_variable_resolve(params, variable_manager):
    """
    基础变量解析辅助函数
    从app_enhanced.py中提取的变量解析逻辑
    """
    
    def resolve_value(value):
        if isinstance(value, str):
            # 查找${variable}模式
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            
            resolved_value = value
            for match in matches:
                try:
                    # 尝试从变量管理器获取值
                    var_value = variable_manager.get_variable(match)
                    if var_value is not None:
                        resolved_value = resolved_value.replace(f'${{{match}}}', str(var_value))
                except Exception as e:
                    # 如果获取失败，保留原始引用
                    logger.warning(f"变量解析失败: {match}, 错误: {e}")
                    pass
                    
            return resolved_value
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        else:
            return value
    
    return resolve_value(params)
