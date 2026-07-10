from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class StrictArtifactDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def reject_blank_strings(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            raise ValueError("string fields cannot be blank")
        return value.strip() if isinstance(value, str) else value

class DocumentInfo(StrictArtifactDataModel):
    artifact_name: str
    workflow: str
    stage: str
    status: str

class StageGateCheck(StrictArtifactDataModel):
    checked: bool
    item: str
