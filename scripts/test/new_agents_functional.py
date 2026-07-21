#!/usr/bin/env python3
"""Run New Agents functional gates with fail-closed real-model scopes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.e2e.new_agents_real.config import (
    RealLlmConfigurationError,
    RealLlmConfig,
    build_child_environments,
    load_real_llm_config,
)
from tests.e2e.new_agents_real.matrix import (
    FunctionalCase,
    FunctionalScope,
    select_cases,
)

DEPLOYMENT_TARGET_ENV_NAMES = (
    "NEW_AGENTS_REAL_TARGET_URL",
    "NEW_AGENTS_REAL_EVIDENCE_DIR",
    "NEW_AGENTS_REAL_DEPLOYMENT_CONTROL_FILE",
)


class ScopeSelection(NamedTuple):
    scope: FunctionalScope
    workflow_id: str | None = None
    stage_id: str | None = None


class ExecutionPlan(NamedTuple):
    status: str
    exit_code: int
    reason: str
    command: tuple[str, ...]
    cases: tuple[FunctionalCase, ...]
    config: RealLlmConfig | None
    environment: dict[str, str]

    def __repr__(self) -> str:
        return (
            "ExecutionPlan("
            f"status={self.status!r}, exit_code={self.exit_code!r}, "
            f"reason={self.reason!r}, command={self.command!r}, "
            f"cases={self.cases!r}, config={self.config!r}, "
            "environment='<redacted>')"
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="scope", required=True)
    subcommands.add_parser("inner")
    stage = subcommands.add_parser("stage")
    stage.add_argument("workflow_id")
    stage.add_argument("stage_id")
    workflow = subcommands.add_parser("workflow")
    workflow.add_argument("workflow_id")
    subcommands.add_parser("pr")
    subcommands.add_parser("nightly")
    subcommands.add_parser("release")
    return parser


def parse_scope(argv: Sequence[str]) -> ScopeSelection:
    arguments = _parser().parse_args(list(argv))
    return ScopeSelection(
        scope=FunctionalScope(arguments.scope),
        workflow_id=getattr(arguments, "workflow_id", None),
        stage_id=getattr(arguments, "stage_id", None),
    )


def load_workflow_manifest(root: Path) -> dict:
    return json.loads(
        (root / "tools" / "new-agents" / "workflow_manifest.json").read_text(
            encoding="utf-8"
        )
    )


def plan_execution(
    selection: ScopeSelection,
    *,
    root: Path = ROOT,
    environ: Mapping[str, str] = os.environ,
) -> ExecutionPlan:
    manifest = load_workflow_manifest(root)
    cases = select_cases(
        selection.scope,
        manifest,
        workflow_id=selection.workflow_id,
        stage_id=selection.stage_id,
    )
    if selection.scope is FunctionalScope.INNER:
        return ExecutionPlan(
            status="READY",
            exit_code=0,
            reason="deterministic inner loop does not require model credentials",
            command=(),
            cases=cases,
            config=None,
            environment=dict(environ),
        )
    try:
        config = load_real_llm_config(root, environ)
    except RealLlmConfigurationError as error:
        return ExecutionPlan(
            status="NOT_RUN",
            exit_code=1,
            reason=str(error),
            command=(),
            cases=cases,
            config=None,
            environment=dict(environ),
        )
    test_environment = {
        **dict(environ),
        **config.real_test_environment(),
        "NEW_AGENTS_REAL_SCOPE": selection.scope.value,
    }
    deployment_values = {
        name: str(environ.get(name, "")).strip() for name in DEPLOYMENT_TARGET_ENV_NAMES
    }
    has_deployment_target = any(deployment_values.values())
    if has_deployment_target and not all(deployment_values.values()):
        return ExecutionPlan(
            status="NOT_RUN",
            exit_code=1,
            reason="partial deployment target configuration is not allowed",
            command=(),
            cases=cases,
            config=None,
            environment=dict(environ),
        )
    if has_deployment_target and selection.scope is not FunctionalScope.RELEASE:
        return ExecutionPlan(
            status="NOT_RUN",
            exit_code=1,
            reason="deployment target configuration is only valid for release",
            command=(),
            cases=cases,
            config=None,
            environment=dict(environ),
        )
    if has_deployment_target:
        test_environment.update(deployment_values)
    if selection.workflow_id:
        test_environment["NEW_AGENTS_REAL_WORKFLOW"] = selection.workflow_id
    if selection.stage_id:
        test_environment["NEW_AGENTS_REAL_STAGE"] = selection.stage_id
    python = root / ".venv/bin/python"
    if not python.is_file():
        python = Path(sys.executable)
    playwright_output_dir = str(
        environ.get("NEW_AGENTS_REAL_PLAYWRIGHT_OUTPUT_DIR", "")
    ).strip()
    playwright_output_option = (
        (f"--output={playwright_output_dir}",) if playwright_output_dir else ()
    )
    command = (
        str(python),
        "-m",
        "pytest",
        "-o",
        "addopts=",
        *playwright_output_option,
        str(root / "tests/e2e/new_agents_real/test_real_agent_workflows.py"),
        "-m",
        "real_llm",
        "-q",
    )
    return ExecutionPlan(
        status="READY",
        exit_code=0,
        reason="real-model configuration is available",
        command=command,
        cases=cases,
        config=config,
        environment=test_environment,
    )


def _outcome_payload(
    *,
    suite_id: str,
    status: str,
    collected: int,
    executed: int,
    reason: str,
) -> str:
    return json.dumps(
        {
            "suiteId": suite_id,
            "status": status,
            "collected": collected,
            "executed": executed,
            "skipped": 0,
            "reason": reason,
        },
        ensure_ascii=False,
    )


def _redact_text(value: str, secrets: Sequence[str]) -> str:
    redacted = value
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def forward_redacted_output(
    result: subprocess.CompletedProcess[str],
    *,
    secrets: Sequence[str],
) -> None:
    if result.stdout:
        sys.stdout.write(_redact_text(result.stdout, secrets))
    if result.stderr:
        sys.stderr.write(_redact_text(result.stderr, secrets))


def _run_inner(root: Path, environ: Mapping[str, str]) -> int:
    python = root / ".venv/bin/python"
    if not python.is_file():
        python = Path(sys.executable)
    commands = (
        (
            str(python),
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "tests/test_new_agents_functional_runner.py",
            "tests/e2e/new_agents_real/test_contracts.py",
            "-q",
        ),
    )
    for command in commands:
        result = subprocess.run(
            command,
            cwd=root,
            env=dict(environ),
            check=False,
        )
        if result.returncode != 0:
            return result.returncode
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    selection = parse_scope(argv if argv is not None else sys.argv[1:])
    plan = plan_execution(selection)
    suite_id = f"new-agents-functional-{selection.scope.value}"
    if selection.scope is FunctionalScope.INNER:
        return _run_inner(ROOT, os.environ)
    if plan.status != "READY":
        print(
            _outcome_payload(
                suite_id=suite_id,
                status=plan.status,
                collected=len(plan.cases),
                executed=0,
                reason=plan.reason,
            )
        )
        return plan.exit_code

    python = ROOT / ".venv/bin/python"
    if not python.is_file():
        python = Path(sys.executable)
    gate_command = (
        str(python),
        str(ROOT / "scripts/test/verification_outcomes.py"),
        "run",
        "--suite-id",
        suite_id,
        "--parser",
        "pytest",
        "--",
        *plan.command,
    )
    result = subprocess.run(
        gate_command,
        cwd=ROOT,
        env=plan.environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if plan.config is None:
        raise RuntimeError("ready real-model execution requires configuration")
    forward_redacted_output(
        result,
        secrets=plan.config.redaction_secrets(),
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
