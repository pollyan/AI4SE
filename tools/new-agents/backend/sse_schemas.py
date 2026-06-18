from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_contracts import AgentTurnOutput


class AgentTurnEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["agent_turn"] = "agent_turn"
    output: AgentTurnOutput


class ErrorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["error"] = "error"
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)

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


SseEvent = Union[AgentTurnEvent, ErrorEvent]
