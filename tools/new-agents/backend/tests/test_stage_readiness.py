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


def _turn(
    markdown: str,
    *,
    artifact_data: dict[str, object] | None = None,
) -> AgentTurnOutput:
    payload: dict[str, object] = {
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
    }
    if artifact_data is not None:
        payload["artifact_data"] = artifact_data
    return AgentTurnOutput.model_validate(payload)


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


def test_apply_stage_readiness_gate_keeps_action_for_user_authorized_assumption() -> None:
    output = _turn(_clarify_markdown(
        "| Q-001 | 密码错误次数限制和锁定时间 | P1 | 阻断 | 策略制定 | 密码错误 3 次后锁定 12 小时 | 用户 | 已假设 |"
    ))

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated is output
    assert gated.stage_action is not None
    assert STAGE_READINESS_BLOCKED_WARNING not in gated.warnings


def test_apply_stage_readiness_gate_blocks_legacy_closed_status_without_authorization() -> None:
    output = _turn(_clarify_markdown(
        "| Q-001 | 密码错误次数限制和锁定时间 | P1 | 阻断 | 策略制定 | 密码错误 3 次后锁定 12 小时 | 产品 | 已关闭 |"
    ))

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated.stage_action is None
    assert STAGE_READINESS_BLOCKED_WARNING in gated.warnings


def test_apply_stage_readiness_gate_uses_structured_questions_before_markdown() -> None:
    artifact_data = {
        "clarification_questions": [
            {
                "question_id": "Q-001",
                "question": "密码错误次数限制和锁定时间",
                "priority": "P1",
                "blocking": "阻断",
                "impact": "策略制定",
                "assumption": "密码错误 3 次后锁定 12 小时",
                "owner": "用户",
                "status": "已假设",
            }
        ]
    }
    output = _turn(
        _clarify_markdown(
            "| Q-001 | 密码错误次数限制和锁定时间 | P1 | 阻断 | 策略制定 | 密码错误 3 次后锁定 12 小时 | 用户 | 待确认 |"
        ),
        artifact_data=artifact_data,
    )

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated is output
    assert gated.stage_action is not None


def test_apply_stage_readiness_gate_uses_markdown_when_structured_questions_are_absent() -> None:
    artifact_data = {
        "document_info": {
            "artifact_name": "测试需求分析与澄清基线",
        }
    }
    output = _turn(
        _clarify_markdown(
            "| Q-001 | 锁定策略是否存在 | P1 | 阻断 | 策略制定 | 暂按 5 次失败锁定 | 产品 | 待确认 |"
        ),
        artifact_data=artifact_data,
    )

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated.stage_action is None
    assert STAGE_READINESS_BLOCKED_WARNING in gated.warnings
    assert gated.artifact_data == artifact_data


def test_apply_stage_readiness_gate_uses_markdown_when_structured_questions_are_empty() -> None:
    artifact_data = {"clarification_questions": []}
    output = _turn(
        _clarify_markdown(
            "| Q-001 | 锁定策略是否存在 | P1 | 阻断 | 策略制定 | 暂按 5 次失败锁定 | 产品 | 待确认 |"
        ),
        artifact_data=artifact_data,
    )

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated.stage_action is None
    assert STAGE_READINESS_BLOCKED_WARNING in gated.warnings
    assert gated.artifact_data == artifact_data


def test_apply_stage_readiness_gate_uses_markdown_when_structured_question_is_malformed() -> None:
    artifact_data = {"clarification_questions": [{"question_id": "Q-001"}]}
    output = _turn(
        _clarify_markdown(
            "| Q-001 | 锁定策略是否存在 | P1 | 阻断 | 策略制定 | 暂按 5 次失败锁定 | 产品 | 待确认 |"
        ),
        artifact_data=artifact_data,
    )

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated.stage_action is None
    assert STAGE_READINESS_BLOCKED_WARNING in gated.warnings
    assert gated.artifact_data == artifact_data


def test_apply_stage_readiness_gate_keeps_artifact_data_when_ai_assumption_blocks() -> None:
    artifact_data = {
        "clarification_questions": [
            {
                "question_id": "Q-001",
                "question": "锁定策略是否存在",
                "priority": "P1",
                "blocking": "阻断",
                "impact": "策略制定",
                "assumption": "暂按 5 次失败锁定",
                "owner": "产品",
                "status": "AI 假设",
            }
        ]
    }
    output = _turn(
        _clarify_markdown(
            "| Q-001 | 锁定策略是否存在 | P1 | 阻断 | 策略制定 | 暂按 5 次失败锁定 | 产品 | AI 假设 |"
        ),
        artifact_data=artifact_data,
    )

    gated = apply_stage_readiness_gate(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert gated.stage_action is None
    assert STAGE_READINESS_BLOCKED_WARNING in gated.warnings
    assert gated.artifact_data == artifact_data


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
