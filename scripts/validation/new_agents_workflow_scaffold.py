from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WORKFLOW_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
STAGE_ID_RE = WORKFLOW_ID_RE
SLUG_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
PROMPT_TEMPLATE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


class WorkflowScaffoldError(ValueError):
    pass


@dataclass(frozen=True)
class WorkflowScaffoldStage:
    id: str
    name: str
    prompt_template_id: str
    artifact_title: str


@dataclass(frozen=True)
class WorkflowScaffoldSpec:
    workflow_id: str
    agent_id: str
    slug: str
    name: str
    description: str
    welcome_message: str
    starter_prompts: list[str]
    stages: list[WorkflowScaffoldStage]


@dataclass(frozen=True)
class ScaffoldWrite:
    relative_path: str
    path: Path
    content: str
    overwrite: bool = False


@dataclass(frozen=True)
class WorkflowScaffoldPlan:
    repo_root: Path
    spec: WorkflowScaffoldSpec
    summary: str
    writes: list[ScaffoldWrite]
    next_command: str


def load_workflow_scaffold_spec(path: Path) -> WorkflowScaffoldSpec:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise WorkflowScaffoldError("workflow scaffold spec must be a JSON object")

    workflow_id = _required_string(raw, "workflowId")
    _validate_identifier("workflowId", workflow_id, WORKFLOW_ID_RE)
    agent_id = _required_string(raw, "agentId")
    slug = _required_string(raw, "slug")
    _validate_identifier("slug", slug, SLUG_RE)
    name = _required_string(raw, "name")
    description = _required_string(raw, "description")
    welcome_message = _required_string(raw, "welcomeMessage")
    starter_prompts = _required_string_list(raw, "starterPrompts")
    raw_stages = raw.get("stages")
    if not isinstance(raw_stages, list) or not raw_stages:
        raise WorkflowScaffoldError("stages must be a non-empty list")

    stages: list[WorkflowScaffoldStage] = []
    seen_stage_ids: set[str] = set()
    seen_template_ids: set[str] = set()
    for index, raw_stage in enumerate(raw_stages):
        if not isinstance(raw_stage, dict):
            raise WorkflowScaffoldError(f"stages[{index}] must be a JSON object")
        stage_id = _required_string(raw_stage, "id")
        _validate_identifier(f"stages[{index}].id", stage_id, STAGE_ID_RE)
        if stage_id in seen_stage_ids:
            raise WorkflowScaffoldError(f"duplicate stage id: {stage_id}")
        seen_stage_ids.add(stage_id)

        stage_name = _required_string(raw_stage, "name")
        prompt_template_id = _required_string(raw_stage, "promptTemplateId")
        _validate_identifier(
            f"stages[{index}].promptTemplateId",
            prompt_template_id,
            PROMPT_TEMPLATE_ID_RE,
        )
        if prompt_template_id in seen_template_ids:
            raise WorkflowScaffoldError(
                f"duplicate promptTemplateId: {prompt_template_id}"
            )
        seen_template_ids.add(prompt_template_id)

        artifact_title = raw_stage.get("artifactTitle", f"# {stage_name}产出物")
        if not isinstance(artifact_title, str) or not artifact_title.strip():
            raise WorkflowScaffoldError(
                f"stages[{index}].artifactTitle must be a non-empty string"
            )
        stages.append(
            WorkflowScaffoldStage(
                id=stage_id,
                name=stage_name,
                prompt_template_id=prompt_template_id,
                artifact_title=artifact_title.strip(),
            )
        )

    return WorkflowScaffoldSpec(
        workflow_id=workflow_id,
        agent_id=agent_id,
        slug=slug,
        name=name,
        description=description,
        welcome_message=welcome_message,
        starter_prompts=starter_prompts,
        stages=stages,
    )


def build_scaffold_plan(repo_root: Path, spec: WorkflowScaffoldSpec) -> WorkflowScaffoldPlan:
    repo_root = repo_root.resolve()
    manifest_path = repo_root / "tools/new-agents/workflow_manifest.json"
    manifest = _load_manifest(manifest_path)
    workflows = manifest.setdefault("workflows", {})
    if not isinstance(workflows, dict):
        raise WorkflowScaffoldError("workflow_manifest.json workflows must be an object")
    if spec.workflow_id in workflows:
        raise WorkflowScaffoldError(f"workflow already exists: {spec.workflow_id}")

    next_manifest = dict(manifest)
    next_workflows = dict(workflows)
    next_workflows[spec.workflow_id] = _build_manifest_workflow(spec)
    next_manifest["workflows"] = next_workflows

    writes = [
        ScaffoldWrite(
            relative_path="tools/new-agents/workflow_manifest.json",
            path=manifest_path,
            content=json.dumps(next_manifest, ensure_ascii=False, indent=2) + "\n",
            overwrite=True,
        )
    ]
    for stage in spec.stages:
        prompt_path = _prompt_file_path(repo_root, stage.prompt_template_id)
        writes.append(
            ScaffoldWrite(
                relative_path=_relative_to_repo(repo_root, prompt_path),
                path=prompt_path,
                content=_build_prompt_skeleton(spec, stage),
            )
        )

    return WorkflowScaffoldPlan(
        repo_root=repo_root,
        spec=spec,
        summary=(
            f"Workflow scaffold plan for {spec.workflow_id}: "
            f"{len(spec.stages)} stage(s), {len(writes)} planned write(s)."
        ),
        writes=writes,
        next_command=(
            "python3 scripts/validation/new_agents_workflow_dry_run.py "
            f"{repo_root}"
        ),
    )


def apply_scaffold_plan(plan: WorkflowScaffoldPlan) -> None:
    for write in plan.writes:
        if write.path.exists() and not write.overwrite:
            raise WorkflowScaffoldError(f"target file already exists: {write.path}")

    for write in plan.writes:
        write.path.parent.mkdir(parents=True, exist_ok=True)
        write.path.write_text(write.content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview or write New Agents workflow scaffold files."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[2]),
        help="Repository root. Defaults to the current AI4SE checkout.",
    )
    parser.add_argument("--spec", required=True, help="Workflow scaffold spec JSON.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write scaffold files. Defaults to preview mode.",
    )
    args = parser.parse_args(argv)

    try:
        spec = load_workflow_scaffold_spec(Path(args.spec))
        plan = build_scaffold_plan(Path(args.repo_root), spec)
        if args.write:
            apply_scaffold_plan(plan)
            print("Workflow scaffold written.")
        else:
            print("Preview only; no files written.")
        print(plan.summary)
        print("Planned writes:")
        for write in plan.writes:
            action = "overwrite" if write.overwrite else "create"
            print(f"- {action}: {write.relative_path}")
        print("Next validation:")
        print(f"- {plan.next_command}")
        return 0
    except (OSError, json.JSONDecodeError, WorkflowScaffoldError) as exc:
        print(f"Workflow scaffold failed: {exc}", file=sys.stderr)
        return 1


def _required_string(raw: dict[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value.strip():
        raise WorkflowScaffoldError(f"{field} must be a non-empty string")
    return value.strip()


def _required_string_list(raw: dict[str, Any], field: str) -> list[str]:
    value = raw.get(field)
    if not isinstance(value, list) or not value:
        raise WorkflowScaffoldError(f"{field} must be a non-empty string list")
    normalized: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise WorkflowScaffoldError(f"{field}[{index}] must be a non-empty string")
        normalized.append(item.strip())
    return normalized


def _validate_identifier(field: str, value: str, pattern: re.Pattern[str]) -> None:
    if not pattern.fullmatch(value):
        raise WorkflowScaffoldError(f"invalid {field}: {value!r}")


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {"handoffs": [], "workflows": {}}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise WorkflowScaffoldError("workflow_manifest.json must be a JSON object")
    return manifest


def _build_manifest_workflow(spec: WorkflowScaffoldSpec) -> dict[str, Any]:
    return {
        "id": spec.workflow_id,
        "agentId": spec.agent_id,
        "slug": spec.slug,
        "name": spec.name,
        "description": spec.description,
        "listing": {
            "name": spec.name,
            "description": spec.description,
            "icon": "Workflow",
            "preview": {
                "suitableFor": [],
                "notSuitableFor": [],
                "requiredInputs": [],
                "expectedOutputs": [stage.artifact_title for stage in spec.stages],
                "sampleInput": spec.starter_prompts[0],
            },
        },
        "stages": [
            {
                "id": stage.id,
                "name": stage.name,
                "promptTemplateId": stage.prompt_template_id,
                "artifactContract": {
                    "requiredHeadings": [
                        stage.artifact_title,
                        "## 1. 输入事实",
                        "## 2. 结构化输出",
                        "## 3. 阶段门禁",
                    ]
                },
            }
            for stage in spec.stages
        ],
        "onboarding": {
            "welcomeMessage": spec.welcome_message,
            "starterPrompts": spec.starter_prompts,
            "inputPlaceholder": "描述你的目标、输入材料或约束...",
        },
    }


def _prompt_file_path(repo_root: Path, prompt_template_id: str) -> Path:
    folder, file_name = prompt_template_id.split(".", maxsplit=1)
    return (
        repo_root
        / "tools/new-agents/frontend/src/core/prompts"
        / folder
        / f"{file_name}.ts"
    )


def _relative_to_repo(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _build_prompt_skeleton(
    spec: WorkflowScaffoldSpec,
    stage: WorkflowScaffoldStage,
) -> str:
    export_prefix = f"{spec.workflow_id}_{stage.id}"
    return f"""export const {export_prefix}_PROMPT = `你正在执行 {spec.name} / {stage.name} 阶段。
请基于用户输入生成右侧产物，并明确区分已确认事实、AI 假设、待确认问题和阶段门禁。
此文件由 workflow scaffold 生成，只提供最小骨架；上线前必须补齐专业方法、artifact contract 示例和 dry-run 报告中的剩余缺口。
`;

export const {export_prefix}_TEMPLATE = `{stage.artifact_title}

## 1. 输入事实

| 类型 | 内容 | 来源 | 状态 |
|---|---|---|---|
| 用户输入 | [记录用户提供的核心事实] | 用户描述 | 已确认 / 待确认 / AI 假设 |

## 2. 结构化输出

| 项目 | 内容 | 依据 | 后续用途 |
|---|---|---|---|
| [输出项] | [结构化结论] | [事实或假设] | [下一阶段用途] |

## 3. 阶段门禁

- [ ] 已列出关键输入事实。
- [ ] 已标记待确认问题和可推进假设。
- [ ] 已说明下一阶段需要消费的结构化信息。`;
"""


if __name__ == "__main__":
    raise SystemExit(main())
