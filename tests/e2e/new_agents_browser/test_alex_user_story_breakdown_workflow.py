from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from .sse_mock import STAGE_PAYLOADS
from .test_alex_value_discovery_workflow import _alex_scenario
from .workflow_runner import (
    StageExpectation,
    WorkflowScenario,
    run_complete_workflow,
)


pytestmark = pytest.mark.e2e


def _alex_user_story_breakdown_scenario() -> WorkflowScenario:
    return WorkflowScenario(
        agent_name="Alex",
        workflow_name="用户故事拆解",
        initial_heading="用户故事拆解",
        prompt="基于 AI 测试设计助手需求蓝图，拆成用户故事地图和可交接故事卡。",
        stages=(
            StageExpectation(
                stage_tab="校准拆分范围",
                transition_label="确认进入 绘制故事地图",
                artifact_headings=(
                    "# 用户故事拆解文档",
                    "## 1. 拆分范围",
                    "## 2. 需求追溯索引",
                    "REQ-001",
                ),
                user_turns=(
                    "范围确认：MVP 只覆盖需求澄清、测试策略和测试用例生成。",
                    "补充：先不包含团队模板适配和需求系统接入。",
                ),
            ),
            StageExpectation(
                stage_tab="绘制故事地图",
                transition_label="确认进入 编写故事卡片",
                artifact_headings=(
                    "# 用户故事拆解文档",
                    "## 3. 用户故事地图",
                    "## 4. MVP Slice",
                    "US-001",
                ),
                visual_markers=("flowchart TD",),
                user_turns=(
                    "故事地图确认：请把用户活动按输入需求、确认风险、生成资产组织。",
                    "MVP slice 确认：第一版要能形成可评审测试策略和用例。",
                ),
            ),
            StageExpectation(
                stage_tab="编写故事卡片",
                transition_label="确认进入 准备故事交接",
                artifact_headings=(
                    "# 用户故事拆解文档",
                    "## 2. 用户故事卡片",
                    "## 3. Ready Stories",
                    "## 4. Not Ready Stories",
                    "验收标准",
                    "来源需求",
                ),
                user_turns=(
                    "故事卡确认：每张故事都要按垂直业务切片，不要按工程任务拆。",
                    "Ready 判断确认：缺验收标准或依赖不清楚的故事放 Not Ready。",
                ),
            ),
            StageExpectation(
                stage_tab="准备故事交接",
                transition_label=None,
                artifact_headings=(
                    "# 单故事 Handoff 清单",
                    "## 1. Ready Story 总览",
                    "## 2. 单故事需求包",
                    "## 5. AI Coding 输入边界",
                    "storyId",
                    "acceptanceCriteria",
                ),
            ),
        ),
    )


def test_alex_user_story_breakdown_workflow_completes_all_stages(new_agents_page):
    run_result = run_complete_workflow(
        new_agents_page,
        _alex_user_story_breakdown_scenario(),
    )

    assert "单故事 Handoff 清单" in run_result.final_artifact
    assert "实现计划" not in run_result.final_artifact
    assert "文件路径" not in run_result.final_artifact
    assert [snapshot.stage_name for snapshot in run_result.stage_artifacts] == [
        "校准拆分范围",
        "绘制故事地图",
        "编写故事卡片",
        "准备故事交接",
    ]
    assert len(run_result.stage_transitions) == 3


def test_alex_user_story_breakdown_generates_single_story_handoff_packet(new_agents_page):
    run_complete_workflow(
        new_agents_page,
        _alex_user_story_breakdown_scenario(),
    )

    new_agents_page.evaluate(
        """() => {
            Object.defineProperty(navigator, 'clipboard', {
                configurable: true,
                value: {
                    writeText: async (text) => {
                        window.__copiedStoryPacket = text;
                    },
                },
            });
        }"""
    )
    new_agents_page.get_by_title("预览").click()
    packet_button = new_agents_page.get_by_role("button", name="生成 US-001 需求包")
    expect(packet_button).to_be_visible(timeout=10000)
    packet_button.click()

    artifact_pane = new_agents_page.locator("section").nth(1)
    expect(artifact_pane).to_contain_text("US-001 · v1", timeout=10000)
    expect(artifact_pane).not_to_contain_text("实现计划")
    expect(artifact_pane).not_to_contain_text("文件路径")

    new_agents_page.get_by_role("button", name="复制 US-001 需求包").click()
    expect(artifact_pane).to_contain_text("已复制 US-001", timeout=10000)
    copied = new_agents_page.evaluate("() => window.__copiedStoryPacket")
    assert '"storyId": "US-001"' in copied
    assert '"acceptanceCriteria"' in copied
    assert "implementationPlan" not in copied


def test_alex_requirement_blueprint_handoff_to_story_packet_chain(new_agents_page):
    blueprint_result = run_complete_workflow(new_agents_page, _alex_scenario())

    assert "AI 测试设计助手需求蓝图" in blueprint_result.final_artifact
    expect(
        new_agents_page.get_by_role(
            "button",
            name=re.compile("交给 Lisa 做测试设计"),
        )
    ).to_be_visible(timeout=10000)

    story_handoff_button = new_agents_page.get_by_role(
        "button",
        name=re.compile("从需求蓝图继续拆用户故事"),
    )
    expect(story_handoff_button).to_be_visible(timeout=10000)
    story_handoff_button.click()

    expect(new_agents_page).to_have_url(
        re.compile(
            r"/workspace/alex/user-story-breakdown"
            r"\?runId=mock-run-user_story_breakdown-handoff$"
        )
    )
    expect(new_agents_page.locator("section").nth(0)).to_contain_text(
        "请基于 Alex 的需求蓝图继续拆用户故事",
        timeout=10000,
    )
    expect(new_agents_page.locator("section").nth(0)).to_contain_text(
        "AI 测试设计助手需求蓝图",
        timeout=10000,
    )

    story_result = run_complete_workflow(
        new_agents_page,
        _alex_user_story_breakdown_scenario(),
        from_current_workspace=True,
    )

    assert "单故事 Handoff 清单" in story_result.final_artifact
    assert "VALUE_DISCOVERY" in story_result.final_artifact
    assert "BLUEPRINT" in story_result.final_artifact

    new_agents_page.evaluate(
        """() => {
            Object.defineProperty(navigator, 'clipboard', {
                configurable: true,
                value: {
                    writeText: async (text) => {
                        window.__copiedStoryPacket = text;
                    },
                },
            });
        }"""
    )
    new_agents_page.get_by_title("预览").click()
    new_agents_page.get_by_role("button", name="生成 US-001 需求包").click()
    artifact_pane = new_agents_page.locator("section").nth(1)
    expect(artifact_pane).to_contain_text("US-001 · v1", timeout=10000)
    new_agents_page.get_by_role("button", name="复制 US-001 需求包").click()

    copied = new_agents_page.evaluate("() => window.__copiedStoryPacket")
    assert '"storyId": "US-001"' in copied
    assert '"acceptanceCriteria"' in copied
    assert "implementationPlan" not in copied
    assert "filePaths" not in copied
    assert "testCommands" not in copied


def test_alex_user_story_breakdown_mock_fixture_keeps_business_vertical_slices():
    combined = "\n".join(
        STAGE_PAYLOADS[("USER_STORY_BREAKDOWN", stage)].markdown
        for stage in ("SCOPE", "STORY_MAP", "STORIES", "HANDOFF")
    )

    for required_text in (
        "REQ-001",
        "US-001",
        "MVP Slice",
        "Ready Stories",
        "Not Ready Stories",
        "作为",
        "我想要",
        "以便",
        "acceptanceCriteria",
    ):
        assert required_text in combined

    for forbidden_text in ("建表", "写接口", "做页面", "代码修改", "测试命令"):
        assert forbidden_text not in combined
