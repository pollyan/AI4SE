from __future__ import annotations

import pytest

from .llm_judge import assert_llm_judges_artifact_quality, is_llm_judge_enabled
from .workflow_runner import (
    StageExpectation,
    WorkflowScenario,
    run_complete_workflow,
)


pytestmark = pytest.mark.e2e


def _alex_scenario() -> WorkflowScenario:
    return WorkflowScenario(
        agent_name="Alex",
        workflow_name="价值发现",
        initial_heading="价值发现",
        prompt=(
            "我们计划做一个 AI 测试设计助手，帮助测试负责人从需求生成测试策略"
            "和测试用例。"
        ),
        stages=(
            StageExpectation(
                stage_tab="价值定位",
                transition_label="确认进入 用户画像",
                artifact_headings=(
                    "# 价值定位分析",
                    "## 产品核心定位",
                    "60 秒电梯演讲",
                ),
                user_turns=(
                    "价值补充：目标用户是 10 人以上测试团队的测试负责人，痛点是需求变更快、测试设计耗时。",
                    "商业补充：先做 SaaS 订阅，团队愿意为节省测试设计时间和降低漏测风险付费。",
                ),
            ),
            StageExpectation(
                stage_tab="用户画像",
                transition_label="确认进入 用户旅程",
                artifact_headings=(
                    "# 用户画像分析",
                    "## 主要用户画像",
                    "## 用户优先级排序",
                ),
                user_turns=(
                    "画像补充：核心用户每天参加需求评审，每周要交付测试计划和用例评审材料。",
                    "决策补充：购买决策看重可控性、输出质量、权限隔离和能否接入现有需求系统。",
                ),
            ),
            StageExpectation(
                stage_tab="用户旅程",
                transition_label="确认进入 需求蓝图",
                artifact_headings=(
                    "# 用户旅程分析",
                    "## 用户旅程地图",
                    "## 核心机会点",
                ),
                user_turns=(
                    "旅程补充：用户从需求评审开始，先识别风险，再设计策略，最后补充用例并组织评审。",
                    "机会补充：最痛的是需求信息不完整和测试点遗漏，产品应优先切入风险识别和用例追溯。",
                ),
            ),
            StageExpectation(
                stage_tab="需求蓝图",
                transition_label=None,
                artifact_headings=(
                    "需求蓝图",
                    "## 1. 产品概述",
                    "## 7. 风险评估",
                ),
            ),
        ),
    )


def test_alex_value_discovery_workflow_completes_all_stages(new_agents_page):
    final_artifact = run_complete_workflow(new_agents_page, _alex_scenario())

    assert "AI 测试设计助手需求蓝图" in final_artifact


def test_alex_final_artifact_passes_optional_llm_judge(new_agents_page):
    if not is_llm_judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    final_artifact = run_complete_workflow(new_agents_page, _alex_scenario())

    assert_llm_judges_artifact_quality("Alex 价值发现", final_artifact)
