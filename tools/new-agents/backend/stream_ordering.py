from agent_contracts import is_meaningful_agent_chat
from sse_schemas import AgentTurnDeltaOutput


class NaturalChatFirstDeltaSequencer:
    """Keep visible artifact deltas behind the first natural model chat."""

    def __init__(self) -> None:
        self._has_emitted_meaningful_chat = False
        self._last_emitted_chat: str | None = None
        self._pending_output: AgentTurnDeltaOutput | None = None

    @property
    def has_emitted_meaningful_chat(self) -> bool:
        return self._has_emitted_meaningful_chat

    def push(
        self,
        output: AgentTurnDeltaOutput,
        *,
        is_final: bool = False,
    ) -> list[AgentTurnDeltaOutput]:
        chat_is_meaningful = is_meaningful_agent_chat(
            output.chat,
            allow_partial=not is_final,
        )
        output_without_chat = self._without_chat(output)

        if not self._has_emitted_meaningful_chat:
            if self._has_payload(output_without_chat):
                self._pending_output = self._merge_pending(output_without_chat)
            if not chat_is_meaningful:
                return []

            self._has_emitted_meaningful_chat = True
            self._last_emitted_chat = output.chat
            emitted = [AgentTurnDeltaOutput(chat=output.chat)]
            if self._pending_output is not None:
                emitted.append(self._pending_output)
                self._pending_output = None
            return emitted

        emitted: list[AgentTurnDeltaOutput] = []
        if chat_is_meaningful and output.chat != self._last_emitted_chat:
            emitted.append(AgentTurnDeltaOutput(chat=output.chat))
            self._last_emitted_chat = output.chat
        if self._has_payload(output_without_chat):
            emitted.append(output_without_chat)
        return emitted

    def discard(self) -> None:
        self._pending_output = None

    def reset_attempt(self) -> None:
        """Start a new model attempt with a fresh chat-first boundary."""

        self._has_emitted_meaningful_chat = False
        self._last_emitted_chat = None
        self._pending_output = None

    @staticmethod
    def _without_chat(
        output: AgentTurnDeltaOutput,
    ) -> AgentTurnDeltaOutput:
        artifact_update = output.artifact_update
        if artifact_update is not None and artifact_update.type == "none":
            artifact_update = None
        return AgentTurnDeltaOutput(
            artifact_update=artifact_update,
            artifact_patch=output.artifact_patch,
            stage_action=output.stage_action,
            warnings=output.warnings,
        )

    @staticmethod
    def _has_payload(output: AgentTurnDeltaOutput) -> bool:
        return any(
            (
                output.artifact_update is not None,
                output.artifact_patch is not None,
                output.stage_action is not None,
                bool(output.warnings),
            )
        )

    def _merge_pending(
        self,
        output: AgentTurnDeltaOutput,
    ) -> AgentTurnDeltaOutput:
        if self._pending_output is None:
            return output
        pending = self._pending_output
        warnings = list(dict.fromkeys([*pending.warnings, *output.warnings]))
        return AgentTurnDeltaOutput(
            artifact_update=output.artifact_update or pending.artifact_update,
            artifact_patch=output.artifact_patch or pending.artifact_patch,
            stage_action=output.stage_action or pending.stage_action,
            warnings=warnings,
        )
