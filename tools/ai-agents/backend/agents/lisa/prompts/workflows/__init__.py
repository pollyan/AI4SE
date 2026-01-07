"""
Lisa Prompts Workflows 模块

包含各工作流的专属 Prompt。
"""

from .test_design import (
    WORKFLOW_TEST_DESIGN_SYSTEM,
    STAGE_CLARIFY_PROMPT,
    STAGE_STRATEGY_PROMPT,
    STAGE_CASES_PROMPT,
    STAGE_DELIVERY_PROMPT,
    build_workflow_prompt,
)

__all__ = [
    "WORKFLOW_TEST_DESIGN_SYSTEM",
    "STAGE_CLARIFY_PROMPT",
    "STAGE_STRATEGY_PROMPT",
    "STAGE_CASES_PROMPT",
    "STAGE_DELIVERY_PROMPT",
    "build_workflow_prompt",
]
