from __future__ import annotations

import pytest

from .llm_judge import assert_llm_judges_artifact_quality, is_llm_judge_enabled
from .workflow_runner import (
    StageExpectation,
    WorkflowScenario,
    run_complete_workflow,
)


pytestmark = pytest.mark.e2e


def _lisa_scenario() -> WorkflowScenario:
    return WorkflowScenario(
        agent_name="Lisa",
        workflow_name="测试策略与用例设计",
        initial_heading="测试设计",
        prompt="请为登录和支付联动功能设计完整测试策略与测试用例。",
        stages=(
            StageExpectation(
                stage_tab="需求澄清",
                transition_label="确认进入 策略制定",
                artifact_headings=(
                    "# 需求分析文档",
                    "## 1. 被测系统与边界",
                    "## 4. 隐式需求与非功能性考量",
                ),
                user_turns=(
                    "补充：登录方式包括账号密码、短信验证码和第三方登录；支付只覆盖微信和银行卡。",
                    "确认边界：本次不测第三方渠道底层稳定性，但要测回调超时、重复回调和订单状态一致性。",
                ),
                reject_transition_once_with=(
                    "先暂不进入策略阶段。再补充一个规则：密码连续失败 5 次锁定 30 分钟，"
                    "短信验证码 60 秒内不能重复发送。"
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
                user_turns=(
                    "策略补充：P0 必须覆盖登录成功后发起支付、支付成功回调、订单状态更新。",
                    "风险确认：账号锁定、安全审计、重复支付、回调幂等都按高风险处理。",
                ),
            ),
            StageExpectation(
                stage_tab="用例编写",
                transition_label="确认进入 文档交付",
                artifact_headings=(
                    "# 测试用例集",
                    "## 1. 用例统计",
                    "## 3. 测试点覆盖追溯",
                ),
                user_turns=(
                    "用例补充：请把正向、异常、安全和兼容性分组，不要只有一个大表。",
                    "确认用例粒度：每条用例都要包含前置条件、操作步骤、预期结果和优先级。",
                ),
            ),
            StageExpectation(
                stage_tab="文档交付",
                transition_label=None,
                artifact_headings=(
                    "# 测试设计文档",
                    "## 文档信息",
                    "## 附录：验收标准",
                ),
            ),
        ),
    )


def test_lisa_test_design_workflow_completes_all_stages(new_agents_page):
    run_result = run_complete_workflow(new_agents_page, _lisa_scenario())

    assert "登录支付链路测试设计" in run_result.final_artifact
    assert [snapshot.stage_name for snapshot in run_result.stage_artifacts] == [
        "需求澄清",
        "策略制定",
        "用例编写",
        "文档交付",
    ]
    assert len(run_result.stage_transitions) >= 3
    assert any(
        event.role == "user"
        and "登录和支付联动功能" in event.content
        for event in run_result.conversation_events
    )
    assert any(
        event.role == "assistant"
        and "确认进入策略制定" in event.content
        for event in run_result.conversation_events
    )


def test_lisa_final_artifact_passes_optional_llm_judge(new_agents_page):
    if not is_llm_judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    run_result = run_complete_workflow(new_agents_page, _lisa_scenario())

    assert_llm_judges_artifact_quality("Lisa 测试策略与用例设计", run_result)
