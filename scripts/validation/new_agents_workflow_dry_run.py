from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


StageKey = tuple[str, str]


@dataclass(frozen=True)
class WorkflowDryRunIssue:
    code: str
    message: str
    workflow_id: str | None = None
    stage_id: str | None = None


@dataclass(frozen=True)
class WorkflowDryRunReport:
    issues: list[WorkflowDryRunIssue]
    checks: int

    @property
    def passed(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class WorkflowDryRunInputs:
    manifest: dict[str, Any]
    manifest_stage_keys: set[StageKey]
    manifest_stage_order: dict[str, list[str]]
    prompt_template_ids_by_stage: dict[StageKey, str]
    prompt_files_by_stage: dict[StageKey, Path]
    frontend_stage_content_template_ids: set[str]
    backend_workflow_stages: dict[str, list[str]]
    required_artifact_heading_keys: set[StageKey]
    required_mermaid_diagrams: dict[StageKey, set[str]]
    required_structured_visuals: dict[StageKey, set[str]]
    artifact_data_ready_stage_keys: set[StageKey]
    artifact_data_renderer_stage_keys: set[StageKey]
    handoff_template_ids: set[str]
    packaging_files: dict[str, str]


def load_workflow_dry_run_inputs(repo_root: Path) -> WorkflowDryRunInputs:
    repo_root = repo_root.resolve()
    new_agents_root = repo_root / "tools" / "new-agents"
    backend_root = new_agents_root / "backend"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from agent_contracts import (  # pylint: disable=import-outside-toplevel
        REQUIRED_ARTIFACT_HEADINGS,
        REQUIRED_ARTIFACT_MERMAID_DIAGRAMS,
        REQUIRED_ARTIFACT_STRUCTURED_VISUALS,
        WORKFLOW_STAGES,
    )
    from agent_runtime import (  # pylint: disable=import-outside-toplevel
        get_artifact_data_ready_stages,
    )
    from artifact_data_renderers import (  # pylint: disable=import-outside-toplevel
        get_artifact_data_renderer_stage_keys,
    )
    from workflow_handoffs import (  # pylint: disable=import-outside-toplevel
        HANDOFF_PROMPT_TEMPLATES,
    )

    manifest_path = new_agents_root / "workflow_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_stage_order = {
        workflow_id: [stage["id"] for stage in workflow["stages"]]
        for workflow_id, workflow in manifest["workflows"].items()
    }
    manifest_stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stage_ids in manifest_stage_order.items()
        for stage_id in stage_ids
    }
    prompt_template_ids_by_stage = {
        (workflow_id, stage["id"]): stage.get("promptTemplateId", "")
        for workflow_id, workflow in manifest["workflows"].items()
        for stage in workflow["stages"]
    }

    return WorkflowDryRunInputs(
        manifest=manifest,
        manifest_stage_keys=manifest_stage_keys,
        manifest_stage_order=manifest_stage_order,
        prompt_template_ids_by_stage=prompt_template_ids_by_stage,
        prompt_files_by_stage=_prompt_files_by_stage(
            new_agents_root,
            prompt_template_ids_by_stage,
        ),
        frontend_stage_content_template_ids=_frontend_stage_content_template_ids(
            new_agents_root
        ),
        backend_workflow_stages={
            workflow_id: list(stage_ids)
            for workflow_id, stage_ids in WORKFLOW_STAGES.items()
        },
        required_artifact_heading_keys=set(REQUIRED_ARTIFACT_HEADINGS),
        required_mermaid_diagrams={
            key: set(value)
            for key, value in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.items()
        },
        required_structured_visuals={
            key: set(value)
            for key, value in REQUIRED_ARTIFACT_STRUCTURED_VISUALS.items()
        },
        artifact_data_ready_stage_keys=get_artifact_data_ready_stages(),
        artifact_data_renderer_stage_keys=get_artifact_data_renderer_stage_keys(),
        handoff_template_ids=set(HANDOFF_PROMPT_TEMPLATES),
        packaging_files={
            "backend Dockerfile": (
                new_agents_root / "backend" / "docker" / "Dockerfile"
            ).read_text(encoding="utf-8"),
            "frontend Dockerfile": (
                new_agents_root / "docker" / "Dockerfile"
            ).read_text(encoding="utf-8"),
            "docker-compose.dev.yml": (
                repo_root / "docker-compose.dev.yml"
            ).read_text(encoding="utf-8"),
            "docker-compose.dev-cn.yml": (
                repo_root / "docker-compose.dev-cn.yml"
            ).read_text(encoding="utf-8"),
        },
    )


def build_workflow_dry_run_report(
    inputs: WorkflowDryRunInputs,
) -> WorkflowDryRunReport:
    issues: list[WorkflowDryRunIssue] = []
    checks = 0

    def add_issue(
        code: str,
        message: str,
        stage_key: StageKey | None = None,
    ) -> None:
        workflow_id = stage_key[0] if stage_key else None
        stage_id = stage_key[1] if stage_key else None
        issues.append(
            WorkflowDryRunIssue(
                code=code,
                message=message,
                workflow_id=workflow_id,
                stage_id=stage_id,
            )
        )

    checks += 1
    if inputs.manifest_stage_order != inputs.backend_workflow_stages:
        add_issue(
            "BACKEND_STAGE_MISMATCH",
            "workflow_manifest.json stages must match backend WORKFLOW_STAGES.",
        )

    checks += 1
    _check_missing_stage_keys(
        issues,
        "ARTIFACT_CONTRACT_MISSING",
        "stage missing from REQUIRED_ARTIFACT_HEADINGS",
        inputs.manifest_stage_keys,
        inputs.required_artifact_heading_keys,
    )

    checks += 1
    _check_missing_stage_keys(
        issues,
        "ARTIFACT_DATA_READY_MISSING",
        "stage missing from DeepSeek artifact_data readiness set",
        inputs.manifest_stage_keys,
        inputs.artifact_data_ready_stage_keys,
    )

    checks += 1
    _check_missing_stage_keys(
        issues,
        "ARTIFACT_DATA_RENDERER_MISSING",
        "stage missing from artifact_data renderer registry",
        inputs.manifest_stage_keys,
        inputs.artifact_data_renderer_stage_keys,
    )

    for stage_key in sorted(inputs.manifest_stage_keys):
        checks += 1
        template_id = inputs.prompt_template_ids_by_stage.get(stage_key, "")
        if not _valid_prompt_template_id(template_id):
            add_issue(
                "PROMPT_TEMPLATE_ID_INVALID",
                f"invalid promptTemplateId: {template_id!r}",
                stage_key,
            )
            continue

        if template_id not in inputs.frontend_stage_content_template_ids:
            add_issue(
                "FRONTEND_TEMPLATE_MAPPING_MISSING",
                f"workflows.ts does not map promptTemplateId {template_id!r}",
                stage_key,
            )

        prompt_file = inputs.prompt_files_by_stage[stage_key]
        if not prompt_file.exists():
            add_issue(
                "PROMPT_FILE_MISSING",
                f"prompt file does not exist: {prompt_file}",
                stage_key,
            )
        else:
            prompt_text = prompt_file.read_text(encoding="utf-8")
            if "_PROMPT" not in prompt_text or "_TEMPLATE" not in prompt_text:
                add_issue(
                    "PROMPT_FILE_EXPORT_MISSING",
                    "prompt file must export both *_PROMPT and *_TEMPLATE content",
                    stage_key,
                )

    manifest_template_ids = set(inputs.prompt_template_ids_by_stage.values())
    for template_id in sorted(
        inputs.frontend_stage_content_template_ids - manifest_template_ids
    ):
        checks += 1
        issues.append(
            WorkflowDryRunIssue(
                code="FRONTEND_TEMPLATE_MAPPING_ORPHANED",
                message=(
                    "workflows.ts maps promptTemplateId not used by manifest: "
                    f"{template_id!r}"
                ),
            )
        )

    for stage_key, visual_types in sorted(inputs.required_structured_visuals.items()):
        checks += 1
        prompt_text = _read_prompt_text(inputs.prompt_files_by_stage, stage_key)
        if prompt_text is None:
            continue
        rendered_template_section = prompt_text.split("TEMPLATE = ", maxsplit=1)[-1]
        for visual_type in visual_types:
            if "```ai4se-visual" not in prompt_text and "${FENCE}ai4se-visual" not in prompt_text:
                add_issue(
                    "STRUCTURED_VISUAL_EXAMPLE_MISSING",
                    "prompt/template must include an ai4se-visual fenced example",
                    stage_key,
                )
            if f'"type": "{visual_type}"' not in prompt_text:
                add_issue(
                    "STRUCTURED_VISUAL_TYPE_MISSING",
                    f"prompt/template missing ai4se-visual type {visual_type!r}",
                    stage_key,
                )
            if '"columns"' not in prompt_text or '"rows"' not in prompt_text:
                add_issue(
                    "STRUCTURED_VISUAL_TABLE_SHAPE_MISSING",
                    "prompt/template must include ai4se-visual columns and rows",
                    stage_key,
                )
            if "fenced:ai4se-visual" in rendered_template_section:
                add_issue(
                    "STRUCTURED_VISUAL_LEGACY_FENCE",
                    "rendered template must not contain legacy fenced:ai4se-visual",
                    stage_key,
                )
            if '"data"' in rendered_template_section or '"matrix"' in rendered_template_section:
                add_issue(
                    "STRUCTURED_VISUAL_LEGACY_SHAPE",
                    "rendered template must not use legacy data/matrix wrappers",
                    stage_key,
                )

    for stage_key, diagram_types in sorted(inputs.required_mermaid_diagrams.items()):
        checks += 1
        prompt_text = _read_prompt_text(inputs.prompt_files_by_stage, stage_key)
        if prompt_text is None:
            continue
        if "mermaid" not in prompt_text:
            add_issue(
                "MERMAID_EXAMPLE_MISSING",
                "prompt/template must include a Mermaid example",
                stage_key,
            )
        for diagram_type in diagram_types:
            if diagram_type not in prompt_text:
                add_issue(
                    "MERMAID_TYPE_MISSING",
                    f"prompt/template missing Mermaid diagram type {diagram_type!r}",
                    stage_key,
                )

    checks += _check_handoffs(inputs, issues)
    checks += _check_manifest_packaging(inputs, issues)

    return WorkflowDryRunReport(issues=issues, checks=checks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run New Agents workflow schema dry-run checks."
    )
    parser.add_argument(
        "repo_root",
        nargs="?",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root. Defaults to the current AI4SE checkout.",
    )
    args = parser.parse_args(argv)
    inputs = load_workflow_dry_run_inputs(Path(args.repo_root))
    report = build_workflow_dry_run_report(inputs)

    if report.passed:
        print(f"New Agents workflow dry-run passed ({report.checks} checks).")
        return 0

    print(
        f"New Agents workflow dry-run failed "
        f"({len(report.issues)} issues, {report.checks} checks)."
    )
    for issue in report.issues:
        scope = (
            f" {issue.workflow_id}/{issue.stage_id}"
            if issue.workflow_id and issue.stage_id
            else ""
        )
        print(f"[{issue.code}]{scope} {issue.message}")
    return 1


def _prompt_files_by_stage(
    new_agents_root: Path,
    prompt_template_ids_by_stage: dict[StageKey, str],
) -> dict[StageKey, Path]:
    prompt_root = new_agents_root / "frontend" / "src" / "core" / "prompts"
    return {
        stage_key: _prompt_file_from_template_id(prompt_root, template_id)
        for stage_key, template_id in prompt_template_ids_by_stage.items()
    }


def _prompt_file_from_template_id(prompt_root: Path, template_id: str) -> Path:
    parts = template_id.split(".")
    if len(parts) != 2:
        return prompt_root / "__invalid__" / f"{template_id}.ts"
    folder, file_name = parts
    return prompt_root / folder / f"{file_name}.ts"


def _frontend_stage_content_template_ids(new_agents_root: Path) -> set[str]:
    workflows_ts = (
        new_agents_root / "frontend" / "src" / "core" / "workflows.ts"
    ).read_text(encoding="utf-8")
    match = re.search(
        r"const\s+STAGE_CONTENT_BY_TEMPLATE_ID[^=]*=\s*\{(?P<body>.*?)\n\};",
        workflows_ts,
        flags=re.DOTALL,
    )
    if not match:
        return set()
    return set(re.findall(r"['\"]([^'\"]+)['\"]\s*:", match.group("body")))


def _valid_prompt_template_id(template_id: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", template_id))


def _check_missing_stage_keys(
    issues: list[WorkflowDryRunIssue],
    code: str,
    message: str,
    expected: set[StageKey],
    actual: set[StageKey],
) -> None:
    for workflow_id, stage_id in sorted(expected - actual):
        issues.append(
            WorkflowDryRunIssue(
                code=code,
                message=message,
                workflow_id=workflow_id,
                stage_id=stage_id,
            )
        )


def _read_prompt_text(
    prompt_files_by_stage: dict[StageKey, Path],
    stage_key: StageKey,
) -> str | None:
    prompt_file = prompt_files_by_stage.get(stage_key)
    if prompt_file is None or not prompt_file.exists():
        return None
    return prompt_file.read_text(encoding="utf-8")


def _check_handoffs(
    inputs: WorkflowDryRunInputs,
    issues: list[WorkflowDryRunIssue],
) -> int:
    checks = 0
    workflows = inputs.manifest["workflows"]
    for handoff in inputs.manifest.get("handoffs", []):
        checks += 1
        source_workflow = handoff.get("sourceWorkflowId")
        source_stage = handoff.get("sourceStageId")
        target_workflow = handoff.get("targetWorkflowId")
        target_stage = handoff.get("targetStageId")
        target_agent = handoff.get("targetAgentId")
        if (source_workflow, source_stage) not in inputs.manifest_stage_keys:
            issues.append(
                WorkflowDryRunIssue(
                    code="HANDOFF_SOURCE_INVALID",
                    message="handoff source must reference a manifest workflow/stage",
                    workflow_id=source_workflow,
                    stage_id=source_stage,
                )
            )
        if (target_workflow, target_stage) not in inputs.manifest_stage_keys:
            issues.append(
                WorkflowDryRunIssue(
                    code="HANDOFF_TARGET_INVALID",
                    message="handoff target must reference a manifest workflow/stage",
                    workflow_id=target_workflow,
                    stage_id=target_stage,
                )
            )
        elif target_agent != workflows[target_workflow]["agentId"]:
            issues.append(
                WorkflowDryRunIssue(
                    code="HANDOFF_TARGET_AGENT_MISMATCH",
                    message="handoff targetAgentId must match target workflow agentId",
                    workflow_id=target_workflow,
                    stage_id=target_stage,
                )
            )
        if handoff.get("promptTemplateId") not in inputs.handoff_template_ids:
            issues.append(
                WorkflowDryRunIssue(
                    code="HANDOFF_TEMPLATE_MISSING",
                    message="handoff promptTemplateId must exist in HANDOFF_PROMPT_TEMPLATES",
                    workflow_id=source_workflow,
                    stage_id=source_stage,
                )
            )
    return checks


def _check_manifest_packaging(
    inputs: WorkflowDryRunInputs,
    issues: list[WorkflowDryRunIssue],
) -> int:
    required_snippets = {
        "backend Dockerfile": "COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json",
        "frontend Dockerfile": "COPY tools/new-agents/workflow_manifest.json /workflow_manifest.json",
        "docker-compose.dev.yml": "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro",
        "docker-compose.dev-cn.yml": "./tools/new-agents/workflow_manifest.json:/workflow_manifest.json:ro",
    }
    checks = 0
    for file_label, snippet in required_snippets.items():
        checks += 1
        if snippet not in inputs.packaging_files.get(file_label, ""):
            issues.append(
                WorkflowDryRunIssue(
                    code="MANIFEST_PACKAGING_MISSING",
                    message=f"{file_label} must include {snippet!r}",
                )
            )
    return checks


if __name__ == "__main__":
    raise SystemExit(main())
