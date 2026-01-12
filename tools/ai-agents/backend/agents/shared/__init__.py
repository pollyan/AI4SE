"""
共享模块

提供智能体间共用的工具函数和基础类型。
"""

from .progress_utils import (
    parse_plan,
    parse_artifact_template,
    parse_all_artifact_templates,
    clean_response_text,
    clean_response_streaming,
    get_current_stage_id,
)

from .progress import get_progress_info

from .state import (
    BaseAgentState,
    get_base_initial_state,
    clear_workflow_state,
)

from .artifact_utils import (
    parse_artifact,
    parse_all_artifacts,
    extract_markdown_block,
)

__all__ = [
    # Progress Utils
    "parse_plan",
    "parse_artifact_template",
    "parse_all_artifact_templates",
    "clean_response_text",
    "clean_response_streaming",
    "get_current_stage_id",
    "get_progress_info",
    # State
    "BaseAgentState",
    "get_base_initial_state",
    "clear_workflow_state",
    # Artifact Utils
    "parse_artifact",
    "parse_all_artifacts",
    "extract_markdown_block",
]

