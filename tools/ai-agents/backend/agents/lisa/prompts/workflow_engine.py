"""
工作流引擎规范 (Workflow Engine Specs)

提供进度同步机制的 Prompt 生成函数。
"""

import json
from typing import List, Dict


def get_plan_sync_instruction(default_stages: List[Dict]) -> str:
    """
    [已废弃] 生成进度同步 Prompt
    
    注意: 进度同步现由后端 get_stream_writer() 主动推送，
    不再依赖 LLM 输出 JSON 代码块。此函数保留为空实现以兼容旧代码调用。
    """
    return ""
