from agent_contracts import ArtifactUpdate, StageAction
from sse_schemas import AgentTurnDeltaOutput
from stream_ordering import NaturalChatFirstDeltaSequencer


def _artifact(markdown: str) -> AgentTurnDeltaOutput:
    return AgentTurnDeltaOutput(
        artifact_update=ArtifactUpdate(type="replace", markdown=markdown)
    )


def test_sequencer_buffers_artifact_until_natural_chat_without_synthesizing_chat():
    sequencer = NaturalChatFirstDeltaSequencer()

    assert sequencer.push(_artifact("# 需求分析\n\n第一段")) == []
    assert sequencer.has_emitted_meaningful_chat is False

    outputs = sequencer.push(
        AgentTurnDeltaOutput(chat="我已核对需求边界，接下来请查看右侧分析。")
    )

    assert outputs == [
        AgentTurnDeltaOutput(
            chat="我已核对需求边界，接下来请查看右侧分析。"
        ),
        _artifact("# 需求分析\n\n第一段"),
    ]
    assert sequencer.has_emitted_meaningful_chat is True


def test_sequencer_does_not_unlock_for_progress_placeholder_or_its_prefix():
    sequencer = NaturalChatFirstDeltaSequencer()
    sequencer.push(_artifact("# 需求分析\n\n第一段"))

    assert sequencer.push(AgentTurnDeltaOutput(chat="正在生成")) == []
    assert sequencer.push(
        AgentTurnDeltaOutput(chat="我正在整理当前输入并生成右侧")
    ) == []
    assert sequencer.has_emitted_meaningful_chat is False


def test_sequencer_does_not_unlock_for_incomplete_natural_chat_fragment():
    sequencer = NaturalChatFirstDeltaSequencer()
    sequencer.push(_artifact("# 需求分析\n\n第一段"))

    assert sequencer.push(AgentTurnDeltaOutput(chat="需")) == []
    assert sequencer.has_emitted_meaningful_chat is False

    outputs = sequencer.push(
        AgentTurnDeltaOutput(chat="我已核对需求边界，右侧将展示本轮分析。")
    )

    assert outputs == [
        AgentTurnDeltaOutput(
            chat="我已核对需求边界，右侧将展示本轮分析。"
        ),
        _artifact("# 需求分析\n\n第一段"),
    ]


def test_sequencer_splits_mixed_delta_and_keeps_stage_action_off_chat_frame():
    sequencer = NaturalChatFirstDeltaSequencer()
    stage_action = StageAction(
        type="request_next_stage",
        target_stage_id="STRATEGY",
    )

    outputs = sequencer.push(
        AgentTurnDeltaOutput(
            chat="需求范围已经稳定，可以确认后进入策略阶段。",
            artifact_update=ArtifactUpdate(
                type="replace",
                markdown="# 需求分析\n\n最终内容",
            ),
            stage_action=stage_action,
            warnings=["请复核假设"],
        )
    )

    assert outputs == [
        AgentTurnDeltaOutput(
            chat="需求范围已经稳定，可以确认后进入策略阶段。",
        ),
        AgentTurnDeltaOutput(
            artifact_update=ArtifactUpdate(
                type="replace",
                markdown="# 需求分析\n\n最终内容",
            ),
            stage_action=stage_action,
            warnings=["请复核假设"],
        ),
    ]


def test_sequencer_keeps_only_latest_buffered_artifact_state():
    sequencer = NaturalChatFirstDeltaSequencer()
    sequencer.push(_artifact("# 需求分析\n\n第一段"))
    sequencer.push(_artifact("# 需求分析\n\n第一段\n\n第二段"))

    outputs = sequencer.push(
        AgentTurnDeltaOutput(chat="我已完成关键判断，右侧给出两部分分析。")
    )

    assert outputs[-1] == _artifact("# 需求分析\n\n第一段\n\n第二段")


def test_sequencer_allows_artifact_updates_after_natural_chat():
    sequencer = NaturalChatFirstDeltaSequencer()
    sequencer.push(
        AgentTurnDeltaOutput(
            chat="我先说明本轮关键判断和需要复核的需求边界。"
        )
    )

    assert sequencer.push(_artifact("# 需求分析\n\n第一段")) == [
        _artifact("# 需求分析\n\n第一段")
    ]


def test_sequencer_discard_drops_artifact_buffered_before_error():
    sequencer = NaturalChatFirstDeltaSequencer()
    sequencer.push(_artifact("# 不应泄露的半成品"))

    sequencer.discard()

    assert sequencer.push(
        AgentTurnDeltaOutput(chat="我重新开始核对当前输入。")
    ) == [AgentTurnDeltaOutput(chat="我重新开始核对当前输入。")]
