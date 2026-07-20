from __future__ import annotations

from enum import Enum
from collections.abc import Mapping
from typing import Any, NamedTuple


class FunctionalScope(str, Enum):
    INNER = "inner"
    STAGE = "stage"
    WORKFLOW = "workflow"
    PR = "pr"
    NIGHTLY = "nightly"
    RELEASE = "release"


class FunctionalCase(NamedTuple):
    kind: str
    workflow_id: str
    stage_id: str | None
    agent_id: str
    slug: str

    @property
    def test_id(self) -> str:
        suffix = f"-{self.stage_id}" if self.stage_id else ""
        return f"{self.kind}-{self.workflow_id}{suffix}"


class FunctionalSelection(NamedTuple):
    scope: FunctionalScope
    cases: tuple[FunctionalCase, ...]


def _workflows(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    workflows = manifest.get("workflows")
    if not isinstance(workflows, dict) or not workflows:
        raise ValueError("workflow manifest must contain a non-empty workflows map")
    return workflows


def _workflow_case(workflow_id: str, workflow: dict[str, Any]) -> FunctionalCase:
    return FunctionalCase(
        kind="workflow",
        workflow_id=workflow_id,
        stage_id=None,
        agent_id=str(workflow["agentId"]),
        slug=str(workflow["slug"]),
    )


def _stage_cases(
    workflow_id: str,
    workflow: dict[str, Any],
) -> tuple[FunctionalCase, ...]:
    return tuple(
        FunctionalCase(
            kind="stage",
            workflow_id=workflow_id,
            stage_id=str(stage["id"]),
            agent_id=str(workflow["agentId"]),
            slug=str(workflow["slug"]),
        )
        for stage in workflow["stages"]
    )


def select_cases(
    scope: FunctionalScope,
    manifest: dict[str, Any],
    *,
    workflow_id: str | None = None,
    stage_id: str | None = None,
    scenarios: dict[str, Any] | None = None,
) -> tuple[FunctionalCase, ...]:
    workflows = _workflows(manifest)

    if scope is FunctionalScope.INNER:
        return ()
    if scope is FunctionalScope.PR:
        if scenarios is None:
            import json
            from pathlib import Path

            scenarios = json.loads(
                Path(__file__)
                .with_name("real_llm_scenarios.json")
                .read_text(encoding="utf-8")
            )
        workflow_ids = tuple(
            identifier
            for identifier in workflows
            if scenarios.get(identifier, {}).get("prCritical") is True
        )
        if len(workflow_ids) < 2:
            raise ValueError("PR scope requires at least two critical workflows")
        return tuple(
            _workflow_case(identifier, workflows[identifier])
            for identifier in workflow_ids
        )
    if scope is FunctionalScope.NIGHTLY:
        return tuple(
            case
            for identifier, workflow in workflows.items()
            for case in _stage_cases(identifier, workflow)
        )
    if scope is FunctionalScope.RELEASE:
        return tuple(
            _workflow_case(identifier, workflow)
            for identifier, workflow in workflows.items()
        )

    if not workflow_id or workflow_id not in workflows:
        raise ValueError(f"unknown workflow: {workflow_id or '<missing>'}")
    workflow = workflows[workflow_id]
    if scope is FunctionalScope.WORKFLOW:
        return (_workflow_case(workflow_id, workflow),)
    if scope is FunctionalScope.STAGE:
        stages = {str(stage["id"]): stage for stage in workflow["stages"]}
        if not stage_id or stage_id not in stages:
            raise ValueError(
                f"unknown stage for {workflow_id}: {stage_id or '<missing>'}"
            )
        return tuple(
            case
            for case in _stage_cases(workflow_id, workflow)
            if case.stage_id == stage_id
        )
    raise ValueError(f"unsupported functional scope: {scope}")


def selection_from_environment(
    manifest: dict[str, Any],
    environ: Mapping[str, str],
) -> FunctionalSelection:
    raw_scope = str(environ.get("NEW_AGENTS_REAL_SCOPE", "")).strip()
    if not raw_scope:
        raise ValueError("NEW_AGENTS_REAL_SCOPE is required")
    try:
        scope = FunctionalScope(raw_scope)
    except ValueError as error:
        raise ValueError(f"unknown real-agent scope: {raw_scope}") from error
    if scope is FunctionalScope.INNER:
        raise ValueError("inner scope does not collect real-model tests")
    cases = select_cases(
        scope,
        manifest,
        workflow_id=(str(environ.get("NEW_AGENTS_REAL_WORKFLOW", "")).strip() or None),
        stage_id=(str(environ.get("NEW_AGENTS_REAL_STAGE", "")).strip() or None),
    )
    return FunctionalSelection(scope=scope, cases=cases)
