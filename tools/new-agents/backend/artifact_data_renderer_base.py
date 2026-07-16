from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

_COMPACT_METADATA_TRANSLATION = str.maketrans(
    {
        "&": "&amp;",
        "\\": "&#92;",
        "`": "&#96;",
        "*": "&#42;",
        "_": "&#95;",
        "~": "&#126;",
        "<": "&lt;",
        ">": "&gt;",
        "[": "&#91;",
        "]": "&#93;",
        "|": "&#124;",
    }
)


class StrictArtifactDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def reject_blank_strings(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            raise ValueError("string fields cannot be blank")
        return value.strip() if isinstance(value, str) else value


def render_compact_metadata(
    heading: str,
    items: Iterable[tuple[str, object]],
) -> str:
    if re.fullmatch(r"#{1,3}\s+\S.*", heading) is None:
        raise ValueError("compact metadata heading must be an H1-H3 Markdown heading")
    rendered_items: list[str] = []
    for raw_label, raw_value in items:
        label = re.sub(r"\s+", " ", raw_label).strip()
        if not label or raw_value is None:
            raise ValueError("compact metadata labels and values cannot be blank")
        value = re.sub(r"\s+", " ", str(raw_value)).strip()
        if not value:
            raise ValueError("compact metadata labels and values cannot be blank")
        value = value.translate(_COMPACT_METADATA_TRANSLATION)
        rendered_items.append(f"{label}：{value}")
    if not rendered_items:
        raise ValueError("compact metadata requires at least one item")
    return f"{heading}\n文档元信息：" + " ｜ ".join(rendered_items)


class DocumentInfo(StrictArtifactDataModel):
    artifact_name: str
    workflow: str
    stage: str
    status: str


class StageGateCheck(StrictArtifactDataModel):
    checked: bool
    item: str
