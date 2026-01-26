
import pytest
from backend.agents.lisa.prompts.artifacts import (
    ARTIFACT_CLARIFY_REQUIREMENTS,
    ARTIFACT_UPDATE_PROMPT
)
from backend.agents.lisa.schemas import ArtifactType

def test_clarify_requirements_template_has_pending_clarifications_section():
    """Verify that the clarify requirements template includes the 'Pending Clarifications' section."""
    assert "## 5. 待澄清问题" in ARTIFACT_CLARIFY_REQUIREMENTS
    assert "| ID | 问题描述 | 状态 | 结论 |" in ARTIFACT_CLARIFY_REQUIREMENTS
    assert "| Q1 | [问题描述] | 待确认 | - |" in ARTIFACT_CLARIFY_REQUIREMENTS

def test_artifact_update_prompt_is_chinese_and_strict():
    """Verify that the artifact update prompt is in Chinese and enforces strict structure."""
    assert "系统内部指令" in ARTIFACT_UPDATE_PROMPT
    assert "严禁" in ARTIFACT_UPDATE_PROMPT or "严重警告" in ARTIFACT_UPDATE_PROMPT
    assert "{template_outline}" in ARTIFACT_UPDATE_PROMPT
    assert "UpdateStructuredArtifact" in ARTIFACT_UPDATE_PROMPT
    assert "{artifact_key}" in ARTIFACT_UPDATE_PROMPT

def test_clarify_requirements_template_has_other_required_sections():
    """Verify other mandatory sections exist."""
    assert "## 1. 需求全景图" in ARTIFACT_CLARIFY_REQUIREMENTS
    assert "## 2. 功能详细规格" in ARTIFACT_CLARIFY_REQUIREMENTS
    assert "## 3. 业务流程图" in ARTIFACT_CLARIFY_REQUIREMENTS
    assert "## 4. 非功能需求 (NFR)" in ARTIFACT_CLARIFY_REQUIREMENTS
