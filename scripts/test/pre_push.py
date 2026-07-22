#!/usr/bin/env python3
"""Run the fixed, fail-closed local verification gate before a Git push."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

NON_PASS = frozenset({"FAIL", "NOT_RUN", "BLOCKED", "TIMEOUT", "FLAKY"})
STATUSES = frozenset({"PASS", *NON_PASS})
PHASES = (
    "preflight",
    "static",
    "deterministic",
    "deployment",
    "real_e2e",
    "finalization",
)
REQUIRED_NPM_LOCKFILES = (
    "tools/frontend/package-lock.json",
    "tools/intent-tester/package-lock.json",
    "tools/new-agents/frontend/package-lock.json",
)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class GateOutcome:
    phase: str
    suite_id: str
    status: str
    collected: int
    executed: int
    reason: str

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unsupported gate status: {self.status}")
        if min(self.collected, self.executed) < 0:
            raise ValueError("gate counts must not be negative")
        if self.executed > self.collected:
            raise ValueError("executed count must not exceed collected count")


@dataclass(frozen=True)
class SuiteSpec:
    phase: str
    suite_id: str
    parser: str
    command: tuple[str, ...]
    cwd: Path
    invariants: tuple[str, ...]
    evidence_level: int
    external_dependency: str
    canonical_owner: str
    disposition: str
    timeout_seconds: float = 900.0

    def __post_init__(self) -> None:
        if self.phase not in {"static", "deterministic", "real_e2e"}:
            raise ValueError(f"unsupported fixed suite phase: {self.phase}")
        if self.parser not in {"command", "pytest", "jest", "vitest"}:
            raise ValueError(f"unsupported fixed suite parser: {self.parser}")
        if self.disposition not in {"KEEP", "MOVE", "MERGE", "DELETE"}:
            raise ValueError(f"unsupported suite disposition: {self.disposition}")
        if not self.invariants:
            raise ValueError("a fixed suite must own at least one invariant")
        if self.evidence_level < 1:
            raise ValueError("evidence level must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("suite timeout must be positive")


def git_head(root: Path) -> str:
    result = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("could not resolve the current Git HEAD")
    head = result.stdout.strip()
    if len(head) != 40:
        raise RuntimeError("current Git HEAD is not a full object identifier")
    return head


def git_status(root: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ("git", "status", "--porcelain=v1", "-uall"),
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("could not read Git worktree status")
    return tuple(line for line in result.stdout.splitlines() if line)


@dataclass(frozen=True)
class PrePushContext:
    root: Path
    head: str
    output_dir: Path
    initial_status: tuple[str, ...]
    workspace_dir: Path | None = field(default=None, repr=False, compare=False)
    environment: Mapping[str, str] = field(
        default_factory=dict,
        repr=False,
        compare=False,
    )

    @classmethod
    def create(cls, root: Path, _environ: Mapping[str, str]) -> "PrePushContext":
        head = git_head(root)
        output_dir = root / "test-results" / "pre-push" / head
        if output_dir.is_symlink():
            output_dir.unlink()
        elif output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=False)
        workspace_dir = Path(tempfile.mkdtemp(prefix=f"ai4se-pre-push-{head[:12]}-"))
        return cls(
            root=root,
            head=head,
            output_dir=output_dir,
            initial_status=git_status(root),
            workspace_dir=workspace_dir,
            environment=dict(_environ),
        )

    @property
    def child_workspace(self) -> Path:
        return self.workspace_dir or self.output_dir


@dataclass
class PrePushState:
    llm_config: Any | None = None
    deployment: Any | None = None


def _suite(
    *,
    phase: str,
    suite_id: str,
    parser: str,
    command: tuple[str, ...],
    cwd: Path,
    invariants: tuple[str, ...],
    evidence_level: int,
    external_dependency: str,
    disposition: str,
) -> SuiteSpec:
    return SuiteSpec(
        phase=phase,
        suite_id=suite_id,
        parser=parser,
        command=command,
        cwd=cwd,
        invariants=invariants,
        evidence_level=evidence_level,
        external_dependency=external_dependency,
        canonical_owner="scripts/test/pre_push.py",
        disposition=disposition,
    )


def fixed_suites(context: PrePushContext) -> tuple[SuiteSpec, ...]:
    python = str(context.root / ".venv" / "bin" / "python")
    output = context.child_workspace
    coverage_root = context.root.resolve()
    return (
        _suite(
            phase="static",
            suite_id="docs-links",
            parser="command",
            command=("bash", str(context.root / "scripts/test/check-docs.sh")),
            cwd=context.root,
            invariants=("document links resolve",),
            evidence_level=1,
            external_dependency="none",
            disposition="KEEP",
        ),
        _suite(
            phase="static",
            suite_id="intent-tester-critical-lint",
            parser="command",
            command=(
                python,
                "-m",
                "flake8",
                "tools/intent-tester/backend",
                "--select=E9,F63,F7,F82",
            ),
            cwd=context.root,
            invariants=("critical Python syntax and name errors fail",),
            evidence_level=1,
            external_dependency="none",
            disposition="KEEP",
        ),
        _suite(
            phase="static",
            suite_id="intent-tester-api",
            parser="pytest",
            command=(
                python,
                "-m",
                "pytest",
                "tools/intent-tester/tests",
                "-q",
                f"--cov={coverage_root / 'tools' / 'intent-tester' / 'backend'}",
                f"--cov-config={coverage_root / 'scripts' / 'test' / 'intent_tester_pre_push.coveragerc'}",
                "--cov-fail-under=50",
                "--cov-report=term",
            ),
            cwd=context.root,
            invariants=("Intent API contract and CI coverage threshold",),
            evidence_level=1,
            external_dependency="provider mocks only",
            disposition="MERGE",
        ),
        _suite(
            phase="static",
            suite_id="intent-proxy",
            parser="jest",
            command=("npx", "jest", "tests/proxy", "--runInBand"),
            cwd=context.root / "tools/intent-tester",
            invariants=("Intent proxy protocol",),
            evidence_level=1,
            external_dependency="Playwright adapter replacement",
            disposition="KEEP",
        ),
        _suite(
            phase="static",
            suite_id="common-frontend-lint",
            parser="command",
            command=("npm", "run", "lint"),
            cwd=context.root / "tools/frontend",
            invariants=("common frontend type and lint safety",),
            evidence_level=1,
            external_dependency="none",
            disposition="KEEP",
        ),
        _suite(
            phase="static",
            suite_id="common-frontend-build",
            parser="command",
            command=(
                "npm",
                "run",
                "build",
                "--",
                "--outDir",
                str(output / "common-frontend-dist"),
            ),
            cwd=context.root / "tools/frontend",
            invariants=("common frontend production build",),
            evidence_level=1,
            external_dependency="none",
            disposition="MOVE",
        ),
        _suite(
            phase="static",
            suite_id="new-agents-frontend-lint",
            parser="command",
            command=("npm", "run", "lint"),
            cwd=context.root / "tools/new-agents/frontend",
            invariants=("New Agents frontend type safety",),
            evidence_level=1,
            external_dependency="none",
            disposition="MOVE",
        ),
        _suite(
            phase="static",
            suite_id="new-agents-frontend-test",
            parser="vitest",
            command=("npm", "run", "test"),
            cwd=context.root / "tools/new-agents/frontend",
            invariants=("frontend stream parsing and state behavior",),
            evidence_level=1,
            external_dependency="controlled browser and API seams",
            disposition="MERGE",
        ),
        _suite(
            phase="static",
            suite_id="new-agents-frontend-build",
            parser="command",
            command=(
                "npm",
                "run",
                "build",
                "--",
                "--outDir",
                str(output / "new-agents-frontend-dist"),
            ),
            cwd=context.root / "tools/new-agents/frontend",
            invariants=("New Agents production frontend build",),
            evidence_level=1,
            external_dependency="none",
            disposition="MOVE",
        ),
        _suite(
            phase="static",
            suite_id="new-agents-backend",
            parser="pytest",
            command=(python, "-m", "pytest", "-m", "not slow", "-q"),
            cwd=context.root / "tools/new-agents/backend",
            invariants=("backend contracts, persistence and typed SSE",),
            evidence_level=1,
            external_dependency="provider mocks only",
            disposition="MERGE",
        ),
        _suite(
            phase="deterministic",
            suite_id="new-agents-runner-contracts",
            parser="pytest",
            command=(
                python,
                "-m",
                "pytest",
                "tests/test_new_agents_functional_runner.py",
                "-q",
            ),
            cwd=context.root,
            invariants=("real-model runner scope and secret boundary",),
            evidence_level=2,
            external_dependency="none",
            disposition="KEEP",
        ),
        _suite(
            phase="deterministic",
            suite_id="verification-outcomes",
            parser="pytest",
            command=(
                python,
                "-m",
                "pytest",
                "tests/test_verification_outcomes.py",
                "-q",
            ),
            cwd=context.root,
            invariants=("zero collection and non-PASS outcome closure",),
            evidence_level=2,
            external_dependency="none",
            disposition="KEEP",
        ),
        _suite(
            phase="deterministic",
            suite_id="ci-deploy-hardening",
            parser="pytest",
            command=(python, "-m", "pytest", "tests/test_ci_deploy_hardening.py", "-q"),
            cwd=context.root,
            invariants=("CI and deployment configuration contracts",),
            evidence_level=2,
            external_dependency="none",
            disposition="KEEP",
        ),
        _suite(
            phase="deterministic",
            suite_id="new-agents-real-contracts",
            parser="pytest",
            command=(
                python,
                "-m",
                "pytest",
                "tests/e2e/new_agents_real/test_contracts.py",
                "tests/e2e/new_agents_real/test_live_stack_contracts.py",
                "-q",
            ),
            cwd=context.root,
            invariants=(
                "real-model evidence, stream and persistence assertions",
                "stream observer and startup diagnostics remain fail-closed",
            ),
            evidence_level=2,
            external_dependency="none",
            disposition="KEEP",
        ),
        _suite(
            phase="deterministic",
            suite_id="new-agents-deterministic-e2e",
            parser="pytest",
            command=(
                python,
                str(context.root / "scripts/test/new_agents_deterministic_e2e.py"),
            ),
            cwd=context.root,
            invariants=(
                "browser-visible stream order and artifact rendering",
                "real frontend/backend/SSE/SQLite two-stage journey",
            ),
            evidence_level=3,
            external_dependency=(
                "controlled Agent Runtime seam and deterministic provider seam"
            ),
            disposition="MERGE",
        ),
    )


def _duration_class(suite: SuiteSpec) -> str:
    """Classify expected cost from the fixed evidence level, not a second list."""
    return {1: "短", 2: "中", 3: "长"}[suite.evidence_level]


def render_suite_ownership(suites: Sequence[SuiteSpec]) -> str:
    """Render the checked-in ownership view from the canonical suite registry."""
    lines = [
        "# QG-021 固定 Pre-push Suite 所有权",
        "",
        "本文件由 `scripts/test/pre_push.py:fixed_suites()` 渲染；修改门禁时必须更新 registry，并由同步测试阻止此视图漂移。",
        "",
        "| Suite | 保护的不变量 | 证据层 | 外部边界 | Canonical owner | 耗时 | 处置 |",
        "| --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for suite in suites:
        lines.append(
            "| "
            f"`{suite.suite_id}` | {'<br>'.join(suite.invariants)} | "
            f"{suite.evidence_level} | {suite.external_dependency} | "
            f"`{suite.canonical_owner}` | {_duration_class(suite)} | "
            f"{suite.disposition} |"
        )
    lines.extend(
        (
            "| `new-agents-deployed-real-release` | deployed real-model release covers every manifest workflow, stage and transition | 4 | isolated production Compose and real configured provider | `scripts/test/pre_push.py` | 很长 | MOVE |",
            "| `new-agents-real-nightly-stage-probes` | independent per-stage real-model diagnostic coverage | 4 | GitHub scheduled runner and real configured provider | `.github/workflows/deploy.yml` | 很长 | KEEP |",
        )
    )
    return "\n".join(lines) + "\n"


def passing_outcome(phase: str) -> GateOutcome:
    return GateOutcome(
        phase=phase,
        suite_id=f"{phase}-contract",
        status="PASS",
        collected=1,
        executed=1,
        reason="contract passed",
    )


def _write_outcome_journal(context: PrePushContext, outcome: GateOutcome) -> None:
    """Persist only the normalized verdict, never a child process transcript."""
    journal_dir = context.output_dir / "outcomes"
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal = journal_dir / f"{outcome.phase}-{outcome.suite_id}.json"
    journal.write_text(
        json.dumps(asdict(outcome), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )


def _outcome_from_verification_output(
    spec: SuiteSpec,
    result: subprocess.CompletedProcess[str],
) -> GateOutcome:
    """Translate the verification utility's sole JSON stdout payload safely."""
    try:
        payload = json.loads(result.stdout)
        suite_id = payload["suiteId"]
        status = payload["status"]
        collected = payload["collected"]
        executed = payload["executed"]
        reason = payload["reason"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return GateOutcome(
            phase=spec.phase,
            suite_id=spec.suite_id,
            status="FAIL",
            collected=0,
            executed=0,
            reason="verification outcome could not be parsed",
        )

    if suite_id != spec.suite_id:
        return GateOutcome(
            phase=spec.phase,
            suite_id=spec.suite_id,
            status="FAIL",
            collected=0,
            executed=0,
            reason="verification outcome suite identifier did not match",
        )
    if not isinstance(collected, int) or not isinstance(executed, int):
        return GateOutcome(
            phase=spec.phase,
            suite_id=spec.suite_id,
            status="FAIL",
            collected=0,
            executed=0,
            reason="verification outcome counts were invalid",
        )
    if not isinstance(status, str) or not isinstance(reason, str):
        return GateOutcome(
            phase=spec.phase,
            suite_id=spec.suite_id,
            status="FAIL",
            collected=0,
            executed=0,
            reason="verification outcome fields were invalid",
        )
    return GateOutcome(
        phase=spec.phase,
        suite_id=spec.suite_id,
        status=status,
        collected=collected,
        executed=executed,
        reason=reason,
    )


def run_suite(
    spec: SuiteSpec,
    context: PrePushContext,
    *,
    extra_environment: Mapping[str, str] = {},
) -> GateOutcome:
    """Run one fixed suite through the fail-closed outcome normalizer."""
    coverage_dir = context.child_workspace / "coverage"
    junit_dir = context.child_workspace / "intent-proxy" / "junit"
    playwright_dir = context.child_workspace / "playwright-artifacts" / spec.suite_id
    coverage_dir.mkdir(parents=True, exist_ok=True)
    junit_dir.mkdir(parents=True, exist_ok=True)
    playwright_dir.mkdir(parents=True, exist_ok=True)
    suite_command = spec.command
    if (
        spec.parser == "pytest"
        and len(spec.command) >= 3
        and spec.command[1:3] == ("-m", "pytest")
    ):
        suite_command = (
            *spec.command[:3],
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            f"--output={playwright_dir}",
            *spec.command[3:],
        )
    command = (
        str(context.root / ".venv" / "bin" / "python"),
        str(context.root / "scripts" / "test" / "verification_outcomes.py"),
        "run",
        "--suite-id",
        spec.suite_id,
        "--parser",
        spec.parser,
        "--timeout-seconds",
        str(spec.timeout_seconds),
        "--",
        *suite_command,
    )
    with tempfile.TemporaryDirectory(prefix="ai4se-pre-push-coverage-") as directory:
        environment = dict(context.environment)
        environment.update(extra_environment)
        environment.update(
            {
                "COVERAGE_FILE": str(Path(directory) / ".coverage"),
                "JEST_JUNIT_OUTPUT_DIR": str(junit_dir),
                "PYTEST_ADDOPTS": f"--output={playwright_dir}",
            }
        )
        try:
            result = subprocess.run(
                command,
                cwd=spec.cwd,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError:
            outcome = GateOutcome(
                phase=spec.phase,
                suite_id=spec.suite_id,
                status="FAIL",
                collected=0,
                executed=0,
                reason="verification outcome runner could not be started",
            )
        else:
            outcome = _outcome_from_verification_output(spec, result)
    _write_outcome_journal(context, outcome)
    return outcome


def has_new_worktree_entries(context: PrePushContext) -> bool:
    return git_status(context.root) != context.initial_status


def finalize(context: PrePushContext, outcomes: Sequence[GateOutcome]) -> int:
    if git_head(context.root) != context.head:
        return 1
    if has_new_worktree_entries(context):
        return 1
    return int(any(outcome.status in NON_PASS for outcome in outcomes))


def _write_summary(context: PrePushContext, outcomes: Sequence[GateOutcome]) -> None:
    context.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "head": context.head,
        "outcomes": [asdict(outcome) for outcome in outcomes],
    }
    (context.output_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _phase_outcome(phase: str, status: str, reason: str) -> GateOutcome:
    return GateOutcome(
        phase=phase,
        suite_id=f"pre-push-{phase}",
        status=status,
        collected=1 if status == "PASS" else 0,
        executed=1 if status == "PASS" else 0,
        reason=reason,
    )


def _load_real_llm_config(root: Path, environ: Mapping[str, str]) -> Any:
    from tests.e2e.new_agents_real.config import load_real_llm_config

    return load_real_llm_config(root, environ)


def _chromium_is_available(python: Path) -> bool:
    """Verify the browser binary used by the Python Playwright suites exists."""
    probe = (
        "from pathlib import Path; "
        "from playwright.sync_api import sync_playwright; "
        "playwright = sync_playwright().start(); "
        "executable = playwright.chromium.executable_path; "
        "playwright.stop(); "
        "raise SystemExit(0 if Path(executable).is_file() else 1)"
    )
    try:
        result = subprocess.run(
            (str(python), "-c", probe),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _command_version(command: tuple[str, ...], *, cwd: Path) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("could not record preflight tool version") from error
    version = (result.stdout or result.stderr).strip().splitlines()
    if result.returncode != 0 or not version:
        raise RuntimeError("could not record preflight tool version")
    return version[0]


def _optional_git_reference(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ("git", *arguments),
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _record_preflight_evidence(context: PrePushContext, python: Path) -> None:
    tools = {
        "python": _command_version((str(python), "--version"), cwd=context.root),
        "node": _command_version(("node", "--version"), cwd=context.root),
        "npm": _command_version(("npm", "--version"), cwd=context.root),
        "docker": _command_version(("docker", "--version"), cwd=context.root),
        "dockerCompose": _command_version(
            ("docker", "compose", "version", "--short"), cwd=context.root
        ),
        "chromium": "available",
    }
    payload = {
        "head": context.head,
        "branch": _optional_git_reference(
            context.root, "rev-parse", "--abbrev-ref", "HEAD"
        ),
        "upstream": _optional_git_reference(
            context.root,
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
        ),
        "lockfiles": list(REQUIRED_NPM_LOCKFILES),
        "tools": tools,
    }
    context.output_dir.mkdir(parents=True, exist_ok=True)
    (context.output_dir / "preflight.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_workflow_manifest(root: Path) -> Mapping[str, Any]:
    manifest = json.loads(
        (root / "tools" / "new-agents" / "workflow_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(manifest, Mapping):
        raise ValueError("workflow manifest must be an object")
    return manifest


def validate_deployed_release_evidence(context: PrePushContext) -> str:
    manifest = load_workflow_manifest(context.root)
    workflows = manifest.get("workflows")
    if not isinstance(workflows, Mapping) or not workflows:
        raise ValueError("workflow manifest has no workflows")
    expected_transitions: dict[str, int] = {}
    expected_stage_count = 0
    for workflow_id, workflow in workflows.items():
        stages = workflow.get("stages") if isinstance(workflow, Mapping) else None
        if (
            not isinstance(workflow_id, str)
            or not isinstance(stages, list)
            or not stages
        ):
            raise ValueError("workflow manifest has invalid stages")
        expected_transitions[workflow_id] = len(stages) - 1
        expected_stage_count += len(stages)

    reports: dict[str, Mapping[str, Any]] = {}
    for path in sorted((context.output_dir / "real-e2e").glob("release-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("release evidence could not be read") from error
        if not isinstance(payload, Mapping):
            raise ValueError("release evidence report is invalid")
        workflow_id = payload.get("workflowId")
        evidence = payload.get("evidence")
        if (
            payload.get("scope") != "release"
            or payload.get("status") != "PASS"
            or not isinstance(workflow_id, str)
            or not isinstance(evidence, Mapping)
            or workflow_id in reports
        ):
            raise ValueError("release evidence report is invalid")
        reports[workflow_id] = evidence

    if set(reports) != set(expected_transitions):
        raise ValueError("release evidence does not cover every workflow")
    for workflow_id, expected_transition_count in expected_transitions.items():
        if reports[workflow_id].get("transition_count") != expected_transition_count:
            raise ValueError("release evidence transition count is invalid")

    transition_count = sum(expected_transitions.values())
    return (
        f"release evidence covered {len(expected_transitions)} workflows, "
        f"{expected_stage_count} stages, {transition_count} transitions"
    )


def _run_preflight(
    context: PrePushContext,
    state: PrePushState,
) -> list[GateOutcome]:
    if context.initial_status:
        return [_phase_outcome("preflight", "BLOCKED", "working tree is not clean")]
    python = context.root / ".venv" / "bin" / "python"
    if not python.is_file():
        return [
            _phase_outcome(
                "preflight", "BLOCKED", "project virtual environment is missing"
            )
        ]
    if shutil.which("docker") is None:
        return [_phase_outcome("preflight", "BLOCKED", "Docker is unavailable")]
    try:
        docker_info = subprocess.run(
            ("docker", "info"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        docker_info = None
    if docker_info is None or docker_info.returncode != 0:
        return [_phase_outcome("preflight", "BLOCKED", "Docker daemon is unavailable")]
    if shutil.which("node") is None:
        return [_phase_outcome("preflight", "BLOCKED", "Node.js is unavailable")]
    if shutil.which("npm") is None:
        return [_phase_outcome("preflight", "BLOCKED", "npm is unavailable")]
    if any(
        not (context.root / lockfile).is_file() for lockfile in REQUIRED_NPM_LOCKFILES
    ):
        return [
            _phase_outcome("preflight", "BLOCKED", "required npm lockfile is missing")
        ]
    if not _chromium_is_available(python):
        return [_phase_outcome("preflight", "BLOCKED", "Chromium is unavailable")]
    try:
        state.llm_config = _load_real_llm_config(context.root, context.environment)
    except ValueError:
        return [
            _phase_outcome(
                "preflight",
                "BLOCKED",
                "real-model configuration is unavailable or invalid",
            )
        ]
    try:
        _record_preflight_evidence(context, python)
    except (OSError, RuntimeError):
        return [
            _phase_outcome(
                "preflight", "FAIL", "preflight evidence could not be recorded"
            )
        ]
    return [
        _phase_outcome(
            "preflight", "PASS", "fixed pre-push prerequisites are available"
        )
    ]


def _run_deployment(
    context: PrePushContext,
    state: PrePushState,
) -> list[GateOutcome]:
    if state.llm_config is None:
        return [
            _phase_outcome(
                "deployment", "BLOCKED", "real-model configuration is unavailable"
            )
        ]
    common_frontend_dist = context.child_workspace / "common-frontend-dist"
    if not common_frontend_dist.is_dir():
        return [
            _phase_outcome(
                "deployment",
                "BLOCKED",
                "isolated common frontend build output is unavailable",
            )
        ]
    try:
        from scripts.test.pre_push_deployment import DeploymentConfig, ProductionHarness

        deployment = DeploymentConfig.create(
            root=context.root,
            output_dir=context.output_dir,
            llm_config=state.llm_config,
            common_frontend_dist=common_frontend_dist,
        )
        state.deployment = ProductionHarness(deployment)
        state.deployment.start()
    except (OSError, RuntimeError, ValueError, ImportError):
        return [
            _phase_outcome(
                "deployment",
                "FAIL",
                "isolated production-shaped deployment did not become ready",
            )
        ]
    return [
        _phase_outcome(
            "deployment", "PASS", "isolated production-shaped deployment is ready"
        )
    ]


def _run_real_e2e(
    context: PrePushContext,
    state: PrePushState,
) -> list[GateOutcome]:
    if state.llm_config is None or state.deployment is None:
        return [
            _phase_outcome(
                "real_e2e", "BLOCKED", "deployed real-model target is unavailable"
            )
        ]
    deployment = state.deployment.config
    suite = SuiteSpec(
        phase="real_e2e",
        suite_id="new-agents-deployed-real-release",
        parser="command",
        command=(
            str(context.root / ".venv" / "bin" / "python"),
            str(context.root / "scripts" / "test" / "new_agents_functional.py"),
            "release",
        ),
        cwd=context.root,
        invariants=(
            "deployed real-model release traverses every manifest workflow and stage",
        ),
        evidence_level=4,
        external_dependency="real configured provider",
        canonical_owner="scripts/test/pre_push.py",
        disposition="MOVE",
        timeout_seconds=2_700,
    )
    outcome = run_suite(
        suite,
        context,
        extra_environment={
            **state.llm_config.real_test_environment(),
            "NEW_AGENTS_REAL_TARGET_URL": deployment.frontend_url,
            "NEW_AGENTS_REAL_EVIDENCE_DIR": str(deployment.evidence_dir),
            "NEW_AGENTS_REAL_DEPLOYMENT_CONTROL_FILE": str(deployment.control_path),
            "NEW_AGENTS_REAL_VERIFY_RESTART": "1",
            "NEW_AGENTS_REAL_PLAYWRIGHT_OUTPUT_DIR": str(
                context.child_workspace / "playwright-artifacts" / suite.suite_id
            ),
        },
    )
    if outcome.status != "PASS":
        return [outcome]
    try:
        coverage = validate_deployed_release_evidence(context)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return [
            replace(
                outcome,
                status="FAIL",
                reason="deployed release evidence did not satisfy manifest coverage",
            )
        ]
    return [replace(outcome, reason=coverage)]


def _scan_evidence(context: PrePushContext, state: PrePushState) -> GateOutcome:
    paths = context.output_dir.rglob("*.json")
    secrets: list[str] = []
    if state.llm_config is not None:
        secrets.extend(state.llm_config.redaction_secrets())
    deployment = getattr(state.deployment, "config", None)
    deployment_environment = getattr(deployment, "environment", {})
    if isinstance(deployment_environment, Mapping):
        for key, value in deployment_environment.items():
            normalized_key = str(key).lower().replace("_", "").replace("-", "")
            if any(
                token in normalized_key
                for token in ("apikey", "authorization", "secret", "token", "password")
            ):
                secrets.append(str(value))
    for path in paths:
        if not path.is_file():
            continue
        try:
            value = path.read_text(encoding="utf-8")
            payload = json.loads(value)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return _phase_outcome(
                "finalization", "FAIL", "evidence could not be scanned"
            )
        if any(secret and secret in value for secret in secrets):
            return _phase_outcome(
                "finalization", "FAIL", "evidence contained a configured secret"
            )
        if _contains_sensitive_key(payload):
            return _phase_outcome(
                "finalization", "FAIL", "evidence contained a sensitive key"
            )
    return _phase_outcome("finalization", "PASS", "evidence is sanitized and isolated")


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).lower().replace("_", "").replace("-", "")
            if any(
                token in normalized
                for token in ("apikey", "authorization", "secret", "token", "password")
            ):
                return True
            if _contains_sensitive_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _run_finalization(
    context: PrePushContext, state: PrePushState
) -> list[GateOutcome]:
    if state.deployment is not None:
        try:
            state.deployment.close()
        except (OSError, RuntimeError, ValueError):
            return [
                _phase_outcome(
                    "finalization", "FAIL", "isolated deployment cleanup failed"
                )
            ]
    outcome = _scan_evidence(context, state)
    if context.workspace_dir is not None:
        try:
            shutil.rmtree(context.workspace_dir)
        except OSError:
            return [
                _phase_outcome(
                    "finalization", "FAIL", "isolated child workspace cleanup failed"
                )
            ]
    return [outcome]


def run_phase(
    phase: str,
    context: PrePushContext,
    state: PrePushState,
) -> list[GateOutcome]:
    if phase == "preflight":
        return _run_preflight(context, state)
    if phase in {"static", "deterministic"}:
        return [
            run_suite(spec, context)
            for spec in fixed_suites(context)
            if spec.phase == phase
        ]
    if phase == "deployment":
        return _run_deployment(context, state)
    if phase == "real_e2e":
        return _run_real_e2e(context, state)
    if phase == "finalization":
        return _run_finalization(context, state)
    raise ValueError(f"unknown fixed pre-push phase: {phase}")


def run_pre_push(root: Path, environ: Mapping[str, str]) -> int:
    context = PrePushContext.create(root, environ)
    state = PrePushState()
    outcomes: list[GateOutcome] = []
    halted = False
    for phase in PHASES:
        if phase == "finalization":
            for outcome in outcomes:
                _write_outcome_journal(context, outcome)
            _write_summary(context, outcomes)
            outcomes.extend(run_phase(phase, context, state))
            continue
        if halted:
            outcomes.append(
                _phase_outcome(
                    phase,
                    "NOT_RUN",
                    "an earlier fixed pre-push phase did not pass",
                )
            )
            continue
        try:
            phase_outcomes = run_phase(phase, context, state)
        except (ImportError, OSError, RuntimeError, ValueError):
            phase_outcomes = [
                _phase_outcome(
                    phase,
                    "FAIL",
                    "fixed pre-push phase did not complete safely",
                )
            ]
        outcomes.extend(phase_outcomes)
        halted = any(outcome.status in NON_PASS for outcome in phase_outcomes)
    for outcome in outcomes:
        _write_outcome_journal(context, outcome)
    _write_summary(context, outcomes)
    return finalize(context, outcomes)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    parse_args(() if argv is None else argv)
    return run_pre_push(Path(__file__).resolve().parents[2], os.environ)


if __name__ == "__main__":
    raise SystemExit(main())
