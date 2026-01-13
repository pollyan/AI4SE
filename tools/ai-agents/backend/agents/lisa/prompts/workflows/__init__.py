"""
Lisa Prompts Workflows 模块

包含各工作流的专属 Prompt。
"""

from .test_design import build_test_design_prompt
from .requirement_review import build_requirement_review_prompt

def build_workflow_prompt(
    workflow_type: str,
    stage: str,
    artifacts_summary: str,
    pending_clarifications: str,
    consensus_count: int,
    plan_context: str = "(无进度计划)"
) -> str:
    """
    构建工作流 Prompt (统一入口)
    
    根据 workflow_type 分发到对应的工作流 Prompt 构建函数。
    """
    if workflow_type == "requirement_review":
        return build_requirement_review_prompt(
            stage, artifacts_summary, pending_clarifications, consensus_count, plan_context
        )
    else:
        # 默认为测试设计
        return build_test_design_prompt(
            stage, artifacts_summary, pending_clarifications, consensus_count, plan_context
        )

__all__ = [
    "build_workflow_prompt",
]
