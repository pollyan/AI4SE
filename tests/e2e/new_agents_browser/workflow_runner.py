from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Page, expect


@dataclass(frozen=True)
class StageExpectation:
    stage_tab: str
    transition_label: str | None
    artifact_headings: tuple[str, ...]
    user_turns: tuple[str, ...] = ()
    reject_transition_once_with: str | None = None


@dataclass(frozen=True)
class WorkflowScenario:
    agent_name: str
    workflow_name: str
    prompt: str
    initial_heading: str
    stages: tuple[StageExpectation, ...]


@dataclass(frozen=True)
class ConversationEvent:
    role: str
    stage_name: str
    content: str


@dataclass(frozen=True)
class StageTransitionEvent:
    from_stage: str
    to_stage: str
    action: str


@dataclass(frozen=True)
class StageArtifactSnapshot:
    stage_name: str
    artifact: str


@dataclass(frozen=True)
class WorkflowRunResult:
    final_artifact: str
    stage_artifacts: tuple[StageArtifactSnapshot, ...]
    conversation_events: tuple[ConversationEvent, ...]
    stage_transitions: tuple[StageTransitionEvent, ...]


def _artifact_text(page: Page) -> str:
    return page.locator("section").nth(1).inner_text(timeout=10000)


def _chat_text(page: Page) -> str:
    return page.locator("section").nth(0).inner_text(timeout=10000)


def _append_assistant_delta(
    page: Page,
    previous_chat_text: str,
    events: list[ConversationEvent],
    stage_name: str,
) -> str:
    current_chat_text = _chat_text(page)
    if current_chat_text.startswith(previous_chat_text):
        delta = current_chat_text[len(previous_chat_text) :].strip()
    else:
        delta = current_chat_text.strip()
    if delta:
        events.append(
            ConversationEvent(
                role="assistant",
                stage_name=stage_name,
                content=delta,
            )
        )
    return current_chat_text


def _assert_artifact_contains(page: Page, headings: tuple[str, ...]) -> None:
    artifact_pane = page.locator("section").nth(1)
    for heading in headings:
        expect(artifact_pane).to_contain_text(heading, timeout=10000)


def _assert_chat_does_not_contain_full_artifact(
    page: Page,
    forbidden_headings: tuple[str, ...],
) -> None:
    chat_text = page.locator("section").nth(0).inner_text(timeout=10000)
    matched = [heading for heading in forbidden_headings if heading in chat_text]
    assert len(matched) <= 1, (
        "assistant chat appears to contain artifact headings: "
        + ", ".join(matched)
    )


def _select_agent(page: Page, agent_name: str) -> None:
    page.locator("h2").filter(has_text=agent_name).click()


def _select_workflow(page: Page, workflow_name: str) -> None:
    page.locator("h2").filter(has_text=workflow_name).click()


def _send_message(page: Page, message: str) -> None:
    page.locator("textarea").fill(message)
    page.locator("#send-button").click()


def _assert_no_pending_transition(page: Page) -> None:
    expect(page.get_by_text("等待确认")).not_to_be_visible(timeout=10000)


def _reject_pending_transition(page: Page) -> None:
    reject_button = page.get_by_role("button", name="暂不进入")
    expect(reject_button).to_be_visible(timeout=10000)
    reject_button.click()
    _assert_no_pending_transition(page)


def _open_stage_tab(page: Page, stage_name: str) -> None:
    page.get_by_text(stage_name, exact=True).click()


def _assert_manual_stage_restore(
    page: Page,
    previous_stage: StageExpectation,
    current_stage: StageExpectation,
) -> None:
    _open_stage_tab(page, previous_stage.stage_tab)
    _assert_artifact_contains(page, previous_stage.artifact_headings)
    _open_stage_tab(page, current_stage.stage_tab)
    _assert_artifact_contains(page, current_stage.artifact_headings)


def run_complete_workflow(
    page: Page,
    scenario: WorkflowScenario,
    *,
    from_current_workspace: bool = False,
) -> WorkflowRunResult:
    if not from_current_workspace:
        expect(page.get_by_text("选择你的 AI 助手")).to_be_visible(timeout=10000)
        _select_agent(page, scenario.agent_name)
        expect(page.get_by_text(f"{scenario.agent_name} 的工作流")).to_be_visible(
            timeout=10000
        )
        _select_workflow(page, scenario.workflow_name)
    expect(page.locator("textarea")).to_be_visible(timeout=10000)

    page.get_by_title("代码").click()
    conversation_events: list[ConversationEvent] = [
        ConversationEvent(
            role="user",
            stage_name=scenario.stages[0].stage_tab,
            content=scenario.prompt,
        )
    ]
    stage_artifacts: list[StageArtifactSnapshot] = []
    stage_transitions: list[StageTransitionEvent] = []
    previous_chat_text = _chat_text(page)
    _send_message(page, scenario.prompt)

    all_headings: list[str] = []
    completed_stages: list[StageExpectation] = []
    for stage_index, stage in enumerate(scenario.stages):
        _assert_artifact_contains(page, stage.artifact_headings)
        previous_chat_text = _append_assistant_delta(
            page,
            previous_chat_text,
            conversation_events,
            stage.stage_tab,
        )
        if stage_index > 0:
            _assert_manual_stage_restore(page, completed_stages[-1], stage)

        all_headings.extend(stage.artifact_headings)
        _assert_chat_does_not_contain_full_artifact(page, tuple(all_headings))

        if stage.transition_label:
            _assert_no_pending_transition(page)
            assert len(stage.user_turns) >= 2, (
                "non-final stages must include multiple simulated user turns"
            )

            for message in stage.user_turns[:-1]:
                conversation_events.append(
                    ConversationEvent(
                        role="user",
                        stage_name=stage.stage_tab,
                        content=message,
                    )
                )
                previous_chat_text = _chat_text(page)
                _send_message(page, message)
                _assert_artifact_contains(page, stage.artifact_headings)
                previous_chat_text = _append_assistant_delta(
                    page,
                    previous_chat_text,
                    conversation_events,
                    stage.stage_tab,
                )
                _assert_chat_does_not_contain_full_artifact(page, tuple(all_headings))
                _assert_no_pending_transition(page)

            final_user_turn = stage.user_turns[-1]
            conversation_events.append(
                ConversationEvent(
                    role="user",
                    stage_name=stage.stage_tab,
                    content=final_user_turn,
                )
            )
            previous_chat_text = _chat_text(page)
            _send_message(page, final_user_turn)
            _assert_artifact_contains(page, stage.artifact_headings)
            previous_chat_text = _append_assistant_delta(
                page,
                previous_chat_text,
                conversation_events,
                stage.stage_tab,
            )
            _assert_chat_does_not_contain_full_artifact(page, tuple(all_headings))

            confirm_button = page.get_by_role("button", name=stage.transition_label)
            expect(confirm_button).to_be_visible(timeout=10000)
            stage_artifacts.append(
                StageArtifactSnapshot(
                    stage_name=stage.stage_tab,
                    artifact=_artifact_text(page),
                )
            )

            if stage.reject_transition_once_with:
                next_stage_name = scenario.stages[stage_index + 1].stage_tab
                _reject_pending_transition(page)
                stage_transitions.append(
                    StageTransitionEvent(
                        from_stage=stage.stage_tab,
                        to_stage=next_stage_name,
                        action="reject",
                    )
                )
                conversation_events.append(
                    ConversationEvent(
                        role="user",
                        stage_name=stage.stage_tab,
                        content=stage.reject_transition_once_with,
                    )
                )
                previous_chat_text = _chat_text(page)
                _send_message(page, stage.reject_transition_once_with)
                _assert_artifact_contains(page, stage.artifact_headings)
                previous_chat_text = _append_assistant_delta(
                    page,
                    previous_chat_text,
                    conversation_events,
                    stage.stage_tab,
                )
                confirm_button = page.get_by_role(
                    "button",
                    name=stage.transition_label,
                )
                expect(confirm_button).to_be_visible(timeout=10000)
                stage_artifacts[-1] = StageArtifactSnapshot(
                    stage_name=stage.stage_tab,
                    artifact=_artifact_text(page),
                )

            next_stage_name = scenario.stages[stage_index + 1].stage_tab
            confirm_button.click()
            stage_transitions.append(
                StageTransitionEvent(
                    from_stage=stage.stage_tab,
                    to_stage=next_stage_name,
                    action="confirm",
                )
            )
        else:
            _assert_no_pending_transition(page)
            stage_artifacts.append(
                StageArtifactSnapshot(
                    stage_name=stage.stage_tab,
                    artifact=_artifact_text(page),
                )
            )

        completed_stages.append(stage)

    return WorkflowRunResult(
        final_artifact=_artifact_text(page),
        stage_artifacts=tuple(stage_artifacts),
        conversation_events=tuple(conversation_events),
        stage_transitions=tuple(stage_transitions),
    )
