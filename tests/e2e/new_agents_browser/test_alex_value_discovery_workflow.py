from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from .llm_judge import (
    assert_llm_judges_artifact_quality,
    assert_llm_judges_handoff_quality,
    is_llm_judge_enabled,
)
from .workflow_runner import (
    StageExpectation,
    WorkflowScenario,
    run_complete_workflow,
)


pytestmark = pytest.mark.e2e


def _alex_scenario() -> WorkflowScenario:
    return WorkflowScenario(
        agent_name="Alex",
        workflow_name="需求蓝图梳理",
        initial_heading="需求蓝图梳理",
        prompt=(
            "我们计划做一个 AI 测试设计助手，帮助测试负责人从需求生成测试策略"
            "和测试用例。"
        ),
        stages=(
            StageExpectation(
                stage_tab="明确价值定位",
                transition_label="确认进入 梳理目标用户",
                artifact_headings=(
                    "# 价值定位分析",
                    "## 产品核心定位",
                    "60 秒电梯演讲",
                ),
                visual_markers=("score-matrix",),
                user_turns=(
                    "价值补充：目标用户是 10 人以上测试团队的测试负责人，痛点是需求变更快、测试设计耗时。",
                    "商业补充：先做 SaaS 订阅，团队愿意为节省测试设计时间和降低漏测风险付费。",
                ),
            ),
            StageExpectation(
                stage_tab="梳理目标用户",
                transition_label="确认进入 梳理用户旅程",
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
                stage_tab="梳理用户旅程",
                transition_label="确认进入 生成需求蓝图",
                artifact_headings=(
                    "# 用户旅程分析",
                    "## 用户旅程地图",
                    "## 核心机会点",
                ),
                visual_markers=("journey-map",),
                user_turns=(
                    "旅程补充：用户从需求评审开始，先识别风险，再设计策略，最后补充用例并组织评审。",
                    "机会补充：最痛的是需求信息不完整和测试点遗漏，产品应优先切入风险识别和用例追溯。",
                ),
            ),
            StageExpectation(
                stage_tab="生成需求蓝图",
                transition_label=None,
                artifact_headings=(
                    "需求蓝图",
                    "## 1. 产品概述",
                    "## 7. 风险评估",
                ),
                visual_markers=("roadmap",),
            ),
        ),
    )


def test_alex_value_discovery_workflow_completes_all_stages(new_agents_page):
    run_result = run_complete_workflow(new_agents_page, _alex_scenario())

    assert "AI 测试设计助手需求蓝图" in run_result.final_artifact
    assert [snapshot.stage_name for snapshot in run_result.stage_artifacts] == [
        "明确价值定位",
        "梳理目标用户",
        "梳理用户旅程",
        "生成需求蓝图",
    ]
    assert len(run_result.stage_transitions) >= 3
    assert any(
        event.role == "user"
        and "AI 测试设计助手" in event.content
        for event in run_result.conversation_events
    )
    assert any(
        event.role == "assistant"
        and "确认进入用户画像" in event.content
        for event in run_result.conversation_events
    )


def test_alex_value_discovery_can_handoff_to_lisa_test_design(new_agents_page):
    run_complete_workflow(new_agents_page, _alex_scenario())

    handoff_button = new_agents_page.get_by_role(
        "button",
        name=re.compile("交给 Lisa 做测试设计"),
    )
    expect(handoff_button).to_be_visible(timeout=10000)
    handoff_button.click()

    expect(new_agents_page).to_have_url(
        re.compile(r"/workspace/lisa/test-design\?runId=mock-run-test_design-handoff$")
    )
    expect(new_agents_page.locator("h3").filter(has_text="测试设计")).to_be_visible(
        timeout=10000
    )
    expect(new_agents_page.locator("section").nth(0)).to_contain_text(
        "请基于 Alex 的价值蓝图",
        timeout=10000,
    )
    expect(new_agents_page.locator("section").nth(0)).to_contain_text(
        "AI 测试设计助手需求蓝图",
        timeout=10000,
    )


def test_alex_final_artifact_passes_optional_llm_judge(new_agents_page):
    if not is_llm_judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    run_result = run_complete_workflow(new_agents_page, _alex_scenario())

    assert_llm_judges_artifact_quality("Alex 需求蓝图梳理", run_result)


def test_alex_to_lisa_handoff_passes_optional_llm_judge(new_agents_page):
    if not is_llm_judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    alex_result = run_complete_workflow(new_agents_page, _alex_scenario())
    handoff_button = new_agents_page.get_by_role(
        "button",
        name=re.compile("交给 Lisa 做测试设计"),
    )
    expect(handoff_button).to_be_visible(timeout=10000)
    handoff_button.click()

    expect(new_agents_page).to_have_url(
        re.compile(r"/workspace/lisa/test-design\?runId=mock-run-test_design-handoff$")
    )
    lisa_result = run_complete_workflow(
        new_agents_page,
        WorkflowScenario(
            agent_name="Lisa",
            workflow_name="测试设计",
            initial_heading="测试设计",
            prompt="请继续基于 Alex 蓝图生成测试设计。",
            stages=(
                StageExpectation(
                    stage_tab="需求澄清",
                    transition_label="确认进入 策略制定",
                    artifact_headings=(
                        "# 需求分析文档",
                        "## 1. 被测系统与边界",
                        "## 4. 隐式需求与非功能性考量",
                    ),
                    visual_markers=("flowchart TD",),
                    user_turns=(
                        "补充：重点检查权限隔离、输出质量和需求追溯。",
                        "确认：请进入策略制定，并保留 Alex 需求蓝图中的风险。",
                    ),
                ),
                StageExpectation(
                    stage_tab="策略制定",
                    transition_label="确认进入 用例编写",
                    artifact_headings=(
                        "# 测试策略蓝图",
                        "## 1. 质量目标",
                        "## 5. 测试点拓扑",
                    ),
                    visual_markers=("risk-board",),
                    user_turns=(
                        "策略补充：P0 先覆盖蓝图中的输出质量和权限隔离。",
                        "确认：请进入用例编写。",
                    ),
                ),
                StageExpectation(
                    stage_tab="用例编写",
                    transition_label=None,
                    artifact_headings=(
                        "# 测试用例集",
                        "## 1. 用例统计",
                        "## 3. 测试点覆盖追溯",
                    ),
                    visual_markers=("traceability-matrix",),
                ),
            ),
        ),
        from_current_workspace=True,
    )

    assert_llm_judges_handoff_quality(
        "Alex 需求蓝图梳理 -> Lisa 测试设计",
        alex_result,
        lisa_result,
    )
