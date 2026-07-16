from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agent_contracts import ArtifactPatch, AgentTurnOutput, ArtifactUpdate, StageAction


class AgentTurnEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["agent_turn"] = "agent_turn"
    output: AgentTurnOutput


class RunStartedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["run_started"] = "run_started"
    run_id: str | None = Field(default=None, alias="runId")
    warnings: list[str] | None = None


class AgentTurnDeltaOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chat: str | None = None
    artifact_update: ArtifactUpdate | None = None
    artifact_patch: ArtifactPatch | None = None
    stage_action: StageAction | None = None
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_patch_requires_replace_update(self) -> "AgentTurnDeltaOutput":
        if self.artifact_patch is not None and (
            self.artifact_update is None or self.artifact_update.type != "replace"
        ):
            raise ValueError("artifact_patch requires replace artifact_update")
        return self


class AgentTurnDeltaEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["agent_delta"] = "agent_delta"
    output: AgentTurnDeltaOutput


class AgentRetrySignal(BaseModel):
    """Internal runtime boundary before a fresh model output attempt."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    attempt_index: int = Field(ge=2, alias="attemptIndex")


class AgentRetryEvent(BaseModel):
    """Tell stream consumers to reset per-attempt ordering baselines."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["agent_retry"] = "agent_retry"
    attempt_index: int = Field(ge=2, alias="attemptIndex")


class ErrorDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    phase: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1, alias="workflowId")
    stage_id: str = Field(min_length=1, alias="stageId")
    field_path: str = Field(min_length=1, alias="fieldPath")
    validator: str = Field(min_length=1)
    retryable: bool
    public_reason: str = Field(min_length=1, alias="publicReason")

    @field_validator("phase")
    @classmethod
    def validate_phase_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("diagnostic phase cannot be blank")
        return value


class ErrorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["error"] = "error"
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    diagnostic: ErrorDiagnostic | None = None

    @field_validator("code")
    @classmethod
    def validate_code_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("error code cannot be blank")
        return value

    @field_validator("message")
    @classmethod
    def validate_message_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("error message cannot be blank")
        return value


SseEvent = Union[
    RunStartedEvent,
    AgentRetryEvent,
    AgentTurnDeltaEvent,
    AgentTurnEvent,
    ErrorEvent,
]
