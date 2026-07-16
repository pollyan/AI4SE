from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Mapping

from pydantic import TypeAdapter, ValidationError

from agent_contracts import validate_artifact_visual_blocks
from artifact_data_renderer_base import StrictArtifactDataModel

ArtifactProjection = SimpleNamespace
ArtifactSectionRenderer = Callable[[ArtifactProjection], str]
ArtifactProjectionValidator = Callable[[ArtifactProjection], None]
ArtifactTitleRenderer = Callable[[ArtifactProjection], str]


@dataclass(frozen=True)
class ArtifactSectionSpec:
    section_id: str
    dependencies: tuple[str, ...]
    render: ArtifactSectionRenderer
    validate_projection: ArtifactProjectionValidator | None = None
    role: str = "business"


@dataclass(frozen=True)
class RenderedArtifact:
    markdown: str
    completed_section_ids: tuple[str, ...]
    normalized_artifact_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class ArtifactRenderPlan:
    model: type[StrictArtifactDataModel]
    title: ArtifactTitleRenderer
    title_dependencies: tuple[str, ...]
    sections: tuple[ArtifactSectionSpec, ...]

    def render_available(
        self,
        raw_artifact_data: Mapping[str, Any],
    ) -> RenderedArtifact | None:
        title_values = self._validate_dependencies(
            raw_artifact_data,
            self.title_dependencies,
        )
        if title_values is None:
            return None

        rendered_sections: list[str] = []
        completed_section_ids: list[str] = []
        completed_business_section = False
        for section in self.sections:
            values = self._validate_dependencies(
                raw_artifact_data,
                section.dependencies,
            )
            if values is None:
                continue
            try:
                projection = ArtifactProjection(**values)
                if section.validate_projection is not None:
                    section.validate_projection(projection)
                markdown = section.render(projection)
                validate_artifact_visual_blocks(markdown)
            except (ValidationError, ValueError):
                continue
            if not markdown.strip():
                raise ValueError(
                    f"artifact section renderer returned blank markdown: "
                    f"{section.section_id}"
                )
            rendered_sections.append(markdown)
            completed_section_ids.append(section.section_id)
            if section.role == "business":
                completed_business_section = True

        if not completed_business_section:
            return None
        title = self.title(ArtifactProjection(**title_values))
        if not title.strip():
            raise ValueError("artifact render plan title cannot be blank")
        return RenderedArtifact(
            markdown="\n\n".join((title, *rendered_sections)),
            completed_section_ids=tuple(completed_section_ids),
        )

    def render_complete(
        self,
        raw_artifact_data: Mapping[str, Any],
    ) -> RenderedArtifact:
        model = self.model.model_validate(raw_artifact_data)
        projection = ArtifactProjection(
            **{
                field_name: getattr(model, field_name)
                for field_name in self.model.model_fields
            }
        )
        title = self.title(projection)
        rendered_sections = []
        for section in self.sections:
            if section.validate_projection is not None:
                section.validate_projection(projection)
            rendered_sections.append(section.render(projection))
        markdown = "\n\n".join((title, *rendered_sections))
        validate_artifact_visual_blocks(markdown)
        return RenderedArtifact(
            markdown=markdown,
            completed_section_ids=tuple(
                section.section_id for section in self.sections
            ),
            normalized_artifact_data=model.model_dump(mode="json"),
        )

    def _validate_dependencies(
        self,
        raw_artifact_data: Mapping[str, Any],
        dependencies: tuple[str, ...],
    ) -> dict[str, Any] | None:
        values: dict[str, Any] = {}
        for field_name in dependencies:
            field = self.model.model_fields.get(field_name)
            if field is None:
                raise ValueError(
                    f"artifact render plan references unknown model field: {field_name}"
                )
            if field_name not in raw_artifact_data:
                if field.is_required():
                    return None
                values[field_name] = field.get_default(call_default_factory=True)
                continue
            try:
                raw_value = self.model.reject_blank_strings(
                    raw_artifact_data[field_name]
                )
                values[field_name] = TypeAdapter(
                    field.rebuild_annotation()
                ).validate_python(raw_value)
            except (ValidationError, ValueError):
                return None
        return values


def validate_model_projection(
    validator: Callable[[Any], Any],
) -> ArtifactProjectionValidator:
    def validate(projection: ArtifactProjection) -> None:
        validator(projection)

    return validate
