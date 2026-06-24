from agent_contracts import AgentTurnOutput
from stage_readiness import (
    STAGE_READINESS_BLOCKED_WARNING,
    apply_stage_readiness_gate,
    find_blocking_clarify_questions,
)


def _clarify_markdown(question_row: str) -> str:
    return f"""# 需求分析文档

## 5. 待澄清问题
| 问题 ID | 问题描述 | 优先级 | 阻断性 | 影响范围 | 当前假设 | 责任方 | 状态 |
|---|---|---|---|---|---|---|---|
{question_row}
"""


def _turn(markdown: str) -> AgentTurnOutput:
    return AgentTurnOutput.model_validate({
        "chat": "已更新需求分析文档，确认无误后可以进入下一阶段（策略制定）。",
        "artifact_update": {
            "type": "replace",
            "markdown": markdown,
        },
        "stage_action": {
            "type": "request_next_stage",
            "target_stage_id": "STRATEGY",
        },
        "warnings": [],
    })


def test_find_blocking_clarify_questions_detects_open_p0_blocker() -> None:
    markdown = _clarify_markdown(
        "| Q-001 | 账号锁定策略未确认 | P0 | 阻断 | 策略制定 | 暂按常见规则 | 产品 | 待确认 |"
    )

    findings = find_blocking_clarify_questions(markdown)

    assert findings == [
        "Q-001（P0 阻断，状态：待确认）：账号锁定策略未确认"
    ]


def test_apply_stage_readiness_gate_removes_next_stage_action_for_blocker() -> None:
    output = _turn(_clarify_markdown(
        "| Q-001 | 验证码触发条件未确认 | P1 | 阻断 | 风险判断 | 暂按失败三次触发 | 产品 | 待确认 |"
    ))

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated.stage_action is None
    assert STAGE_READINESS_BLOCKED_WARNING in gated.warnings
    assert "还不能进入下一阶段" in gated.chat
    assert "Q-001" in gated.chat


def test_apply_stage_readiness_gate_keeps_action_for_confirmed_blocker() -> None:
    output = _turn(_clarify_markdown(
        "| Q-001 | 验证码触发条件 | P1 | 阻断 | 风险判断 | 已按失败三次触发 | 产品 | 已确认 |"
    ))

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated is output
    assert gated.stage_action is not None


def test_apply_stage_readiness_gate_keeps_action_for_non_blocking_question() -> None:
    output = _turn(_clarify_markdown(
        "| Q-001 | 失败提示文案待确认 | P1 | 非阻断 | 用例细节 | 暂按通用错误提示 | 产品 | 待确认 |"
    ))

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated is output
    assert gated.stage_action is not None


def test_apply_stage_readiness_gate_ignores_other_stages() -> None:
    output = _turn(_clarify_markdown(
        "| Q-001 | 验证码触发条件未确认 | P0 | 阻断 | 风险判断 | 暂按失败三次触发 | 产品 | 待确认 |"
    ))

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    )

    assert gated is output
    assert gated.stage_action is not None
