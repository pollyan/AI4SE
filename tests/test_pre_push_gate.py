from __future__ import annotations

import importlib.util
import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "test" / "pre_push.py"


def _load_runner():
    if not RUNNER_PATH.exists():
        pytest.fail(f"pre-push runner is missing: {RUNNER_PATH}")
    spec = importlib.util.spec_from_file_location("pre_push", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pre_push_rejects_scope_arguments_and_records_the_starting_head(
    tmp_path, monkeypatch
):
    runner = _load_runner()
    monkeypatch.setattr(runner, "git_head", lambda _root: "a" * 40)
    monkeypatch.setattr(runner, "git_status", lambda _root: (" M known-file",))

    context = runner.PrePushContext.create(tmp_path, {"PATH": "/bin"})

    assert context.head == "a" * 40
    assert context.output_dir == tmp_path / "test-results" / "pre-push" / ("a" * 40)
    assert context.initial_status == (" M known-file",)
    with pytest.raises(SystemExit):
        runner.parse_args(["--scope", "frontend"])


def test_pre_push_context_replaces_only_its_own_prior_head_artifacts(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    head = "a" * 40
    output = tmp_path / "test-results" / "pre-push" / head
    output.mkdir(parents=True)
    (output / "stale.json").write_text("stale", encoding="utf-8")
    monkeypatch.setattr(runner, "git_head", lambda _root: head)
    monkeypatch.setattr(runner, "git_status", lambda _root: ())

    context = runner.PrePushContext.create(tmp_path, {})

    assert context.output_dir == output
    assert not (output / "stale.json").exists()


def test_non_pass_or_head_change_makes_the_final_verdict_nonzero(tmp_path, monkeypatch):
    runner = _load_runner()
    heads = iter(("a" * 40, "b" * 40))
    monkeypatch.setattr(runner, "git_head", lambda _root: next(heads))
    monkeypatch.setattr(runner, "git_status", lambda _root: ())
    context = runner.PrePushContext.create(tmp_path, {"PATH": "/bin"})
    outcome = runner.GateOutcome(
        phase="static",
        suite_id="static-contract",
        status="PASS",
        collected=1,
        executed=1,
        reason="contract passed",
    )

    assert runner.finalize(context, [outcome]) == 1


def test_shell_wrapper_requires_the_project_virtual_environment():
    wrapper = ROOT / "scripts" / "test" / "pre-push.sh"

    assert wrapper.is_file()
    source = wrapper.read_text(encoding="utf-8")
    assert ".venv/bin/python" in source
    assert "python3" not in source


def test_pre_push_artifacts_are_git_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "test-results/pre-push/" in gitignore


def test_fixed_suite_registry_has_one_owner_and_full_required_coverage(tmp_path):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )

    suites = runner.fixed_suites(context)

    assert [suite.phase for suite in suites] == [
        "static",
        "static",
        "static",
        "static",
        "static",
        "static",
        "static",
        "static",
        "static",
        "static",
        "deterministic",
        "deterministic",
        "deterministic",
        "deterministic",
        "deterministic",
        "deterministic",
    ]
    assert len({suite.suite_id for suite in suites}) == len(suites)
    assert {suite.suite_id for suite in suites} >= {
        "docs-links",
        "intent-tester-critical-lint",
        "intent-tester-api",
        "intent-proxy",
        "common-frontend-lint",
        "common-frontend-build",
        "new-agents-frontend-lint",
        "new-agents-frontend-test",
        "new-agents-frontend-build",
        "new-agents-backend",
        "new-agents-runner-contracts",
        "verification-outcomes",
        "ci-deploy-hardening",
        "new-agents-real-contracts",
        "new-agents-live-stack",
        "new-agents-browser-e2e",
    }
    assert all(suite.invariants and suite.canonical_owner for suite in suites)
    assert {suite.disposition for suite in suites} >= {"KEEP", "MOVE", "MERGE"}


def test_fixed_build_outputs_use_the_child_isolated_workspace(tmp_path):
    runner = _load_runner()
    workspace = tmp_path / "child-workspace"
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
        workspace_dir=workspace,
    )

    suites = {suite.suite_id: suite for suite in runner.fixed_suites(context)}

    assert (
        str(workspace / "common-frontend-dist")
        in suites["common-frontend-build"].command
    )
    assert (
        str(workspace / "new-agents-frontend-dist")
        in suites["new-agents-frontend-build"].command
    )


def test_intent_api_coverage_source_is_anchored_to_the_checked_out_repository(tmp_path):
    runner = _load_runner()
    checkout = tmp_path / "clean-checkout"
    checkout.mkdir()
    root = tmp_path / "checkout-alias"
    root.symlink_to(checkout, target_is_directory=True)
    context = runner.PrePushContext(
        root=root,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )

    suites = {suite.suite_id: suite for suite in runner.fixed_suites(context)}

    assert (
        f"--cov={checkout / 'tools' / 'intent-tester' / 'backend'}"
        in suites["intent-tester-api"].command
    )
    assert (
        f"--cov-config={checkout / 'scripts' / 'test' / 'intent_tester_pre_push.coveragerc'}"
        in suites["intent-tester-api"].command
    )


def test_jest_junit_output_is_taken_from_the_pre_push_artifact_directory():
    source = (ROOT / "tools/intent-tester/jest.config.js").read_text(encoding="utf-8")

    assert "JEST_JUNIT_OUTPUT_DIR" in source


def test_run_suite_preserves_not_run_and_writes_an_isolated_journal(tmp_path):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    suite = runner.SuiteSpec(
        phase="static",
        suite_id="empty-pytest",
        parser="pytest",
        command=(sys.executable, "-c", "print('no tests ran')"),
        cwd=ROOT,
        invariants=("zero collection fails closed",),
        evidence_level=1,
        external_dependency="none",
        canonical_owner="scripts/test/pre_push.py",
        disposition="KEEP",
    )

    outcome = runner.run_suite(suite, context)

    assert outcome.status == "NOT_RUN"
    journal = context.output_dir / "outcomes" / "static-empty-pytest.json"
    assert json.loads(journal.read_text(encoding="utf-8"))["status"] == "NOT_RUN"


def test_run_suite_prepares_isolated_coverage_and_junit_directories(tmp_path):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    suite = runner.SuiteSpec(
        phase="static",
        suite_id="isolated-output",
        parser="command",
        command=(sys.executable, "-c", "pass"),
        cwd=ROOT,
        invariants=("isolated test output directories exist",),
        evidence_level=1,
        external_dependency="none",
        canonical_owner="scripts/test/pre_push.py",
        disposition="KEEP",
    )

    runner.run_suite(suite, context)

    assert (context.output_dir / "coverage").is_dir()
    assert (context.output_dir / "intent-proxy" / "junit").is_dir()


def test_run_suite_keeps_coverage_database_outside_a_suite_that_cleans_test_results(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    suite = runner.SuiteSpec(
        phase="static",
        suite_id="ephemeral-coverage",
        parser="command",
        command=(sys.executable, "-c", "pass"),
        cwd=ROOT,
        invariants=("coverage database does not depend on a child-managed path",),
        evidence_level=1,
        external_dependency="none",
        canonical_owner="scripts/test/pre_push.py",
        disposition="KEEP",
    )
    captured: dict[str, str] = {}

    def fake_run(command, **kwargs):
        captured["command"] = tuple(command)
        captured.update(kwargs["env"])
        return runner.subprocess.CompletedProcess(
            args=(),
            returncode=0,
            stdout=(
                '{"suiteId":"ephemeral-coverage","status":"PASS",'
                '"collected":1,"executed":1,"skipped":0,"reason":"ok"}'
            ),
            stderr="",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    runner.run_suite(suite, context)

    assert not Path(captured["COVERAGE_FILE"]).is_relative_to(context.output_dir)


def test_run_suite_routes_pytest_playwright_output_to_the_child_workspace(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    workspace = tmp_path / "child-workspace"
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
        workspace_dir=workspace,
    )
    suite = runner.SuiteSpec(
        phase="deterministic",
        suite_id="isolated-playwright-output",
        parser="pytest",
        command=(sys.executable, "-m", "pytest", "-q"),
        cwd=ROOT,
        invariants=("pytest-playwright cannot delete pre-push evidence",),
        evidence_level=2,
        external_dependency="none",
        canonical_owner="scripts/test/pre_push.py",
        disposition="KEEP",
    )
    captured: dict[str, str] = {}

    def fake_run(command, **kwargs):
        captured["command"] = tuple(command)
        captured.update(kwargs["env"])
        return runner.subprocess.CompletedProcess(
            args=(),
            returncode=0,
            stdout=(
                '{"suiteId":"isolated-playwright-output","status":"PASS",'
                '"collected":1,"executed":1,"skipped":0,"reason":"ok"}'
            ),
            stderr="",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    runner.run_suite(suite, context)

    assert captured["PYTEST_ADDOPTS"] == (
        f"--output={workspace / 'playwright-artifacts' / suite.suite_id}"
    )
    assert (
        f"--output={workspace / 'playwright-artifacts' / suite.suite_id}"
        in captured["command"]
    )


def test_run_suite_keeps_existing_journals_when_pytest_playwright_is_loaded(tmp_path):
    """The real plugin defaults to ``test-results`` and must not erase evidence."""
    runner = _load_runner()
    output_dir = tmp_path / "test-results" / "pre-push" / ("a" * 40)
    journal = output_dir / "outcomes" / "static-earlier-suite.json"
    journal.parent.mkdir(parents=True)
    journal.write_text('{"status": "PASS"}', encoding="utf-8")
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=output_dir,
        initial_status=(),
        workspace_dir=tmp_path / "child-workspace",
    )
    suite = runner.SuiteSpec(
        phase="static",
        suite_id="real-pytest-playwright-output",
        parser="pytest",
        command=(
            str(ROOT / ".venv" / "bin" / "python"),
            "-m",
            "pytest",
            str(ROOT / "tests" / "test_verification_outcomes.py"),
            "-q",
        ),
        cwd=tmp_path,
        invariants=("pytest-playwright cannot delete prior pre-push evidence",),
        evidence_level=1,
        external_dependency="none",
        canonical_owner="scripts/test/pre_push.py",
        disposition="KEEP",
    )

    outcome = runner.run_suite(suite, context)

    assert outcome.status == "PASS"
    assert json.loads(journal.read_text(encoding="utf-8")) == {"status": "PASS"}


def test_run_suite_keeps_existing_journals_when_a_child_starts_pytest(tmp_path):
    runner = _load_runner()
    output_dir = tmp_path / "test-results" / "pre-push" / ("a" * 40)
    journal = output_dir / "outcomes" / "static-earlier-suite.json"
    journal.parent.mkdir(parents=True)
    journal.write_text('{"status": "PASS"}', encoding="utf-8")
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=output_dir,
        initial_status=(),
        workspace_dir=tmp_path / "child-workspace",
    )
    nested_pytest = (
        "import subprocess, sys; "
        "raise SystemExit(subprocess.run((sys.executable, '-m', 'pytest', "
        f"'{ROOT / 'tests' / 'test_verification_outcomes.py'}', '-q')).returncode)"
    )
    suite = runner.SuiteSpec(
        phase="static",
        suite_id="nested-pytest-playwright-output",
        parser="command",
        command=(str(ROOT / ".venv" / "bin" / "python"), "-c", nested_pytest),
        cwd=tmp_path,
        invariants=("nested pytest cannot delete prior pre-push evidence",),
        evidence_level=1,
        external_dependency="none",
        canonical_owner="scripts/test/pre_push.py",
        disposition="KEEP",
    )

    outcome = runner.run_suite(suite, context)

    assert outcome.status == "PASS"
    assert json.loads(journal.read_text(encoding="utf-8")) == {"status": "PASS"}


def test_canonical_run_orders_all_phases_and_never_runs_real_e2e_before_deployment(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=tmp_path,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    observed: list[str] = []
    monkeypatch.setattr(runner.PrePushContext, "create", lambda *_args: context)
    monkeypatch.setattr(
        runner,
        "run_phase",
        lambda phase, *_args: observed.append(phase) or [runner.passing_outcome(phase)],
    )
    monkeypatch.setattr(runner, "finalize", lambda *_args: 0)

    assert runner.run_pre_push(tmp_path, {"PATH": "/bin"}) == 0
    assert observed == [
        "preflight",
        "static",
        "deterministic",
        "deployment",
        "real_e2e",
        "finalization",
    ]


def test_real_e2e_is_a_supported_fixed_suite_phase():
    runner = _load_runner()

    suite = runner.SuiteSpec(
        phase="real_e2e",
        suite_id="deployed-real-release",
        parser="command",
        command=(sys.executable, "-c", "pass"),
        cwd=ROOT,
        invariants=("deployed release journey",),
        evidence_level=4,
        external_dependency="isolated production stack and real model",
        canonical_owner="scripts/test/pre_push.py",
        disposition="KEEP",
    )

    assert suite.phase == "real_e2e"


def test_controlled_phase_error_still_runs_finalization_and_fails_closed(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=tmp_path,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    context.output_dir.mkdir(parents=True)
    observed: list[str] = []
    finalized: list[runner.GateOutcome] = []
    monkeypatch.setattr(runner.PrePushContext, "create", lambda *_args: context)

    def run_phase(phase, *_args):
        observed.append(phase)
        if phase == "real_e2e":
            raise ValueError("phase setup failed")
        return [runner.passing_outcome(phase)]

    monkeypatch.setattr(runner, "run_phase", run_phase)
    monkeypatch.setattr(
        runner,
        "finalize",
        lambda _context, outcomes: finalized.extend(outcomes) or 1,
    )

    assert runner.run_pre_push(tmp_path, {}) == 1
    assert observed[-1] == "finalization"
    assert any(
        outcome.phase == "real_e2e" and outcome.status == "FAIL"
        for outcome in finalized
    )


def test_preflight_blocks_before_running_suites_when_docker_is_unavailable(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    monkeypatch.setattr(runner.shutil, "which", lambda _name: None)

    outcomes = runner.run_phase("preflight", context, runner.PrePushState())

    assert outcomes[0].status == "BLOCKED"
    assert "Docker" in outcomes[0].reason


@pytest.mark.parametrize(
    ("missing_tool", "expected_name"),
    (("node", "Node"), ("npm", "npm")),
)
def test_preflight_blocks_before_running_suites_when_node_tooling_is_unavailable(
    tmp_path,
    monkeypatch,
    missing_tool,
    expected_name,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    monkeypatch.setattr(
        runner.shutil,
        "which",
        lambda name: None if name == missing_tool else f"/usr/local/bin/{name}",
    )
    monkeypatch.setattr(runner, "_load_real_llm_config", lambda *_args: object())
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: runner.subprocess.CompletedProcess(
            args=(), returncode=0, stdout="", stderr=""
        ),
    )

    outcomes = runner.run_phase("preflight", context, runner.PrePushState())

    assert outcomes[0].status == "BLOCKED"
    assert expected_name in outcomes[0].reason


def test_preflight_blocks_before_running_suites_when_chromium_is_unavailable(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/local/bin/tool")
    monkeypatch.setattr(runner, "_chromium_is_available", lambda _python: False)
    monkeypatch.setattr(runner, "_load_real_llm_config", lambda *_args: object())
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: runner.subprocess.CompletedProcess(
            args=(), returncode=0, stdout="", stderr=""
        ),
    )

    outcomes = runner.run_phase("preflight", context, runner.PrePushState())

    assert outcomes[0].status == "BLOCKED"
    assert "Chromium" in outcomes[0].reason


def test_preflight_records_safe_head_and_tooling_evidence(tmp_path, monkeypatch):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    context.output_dir.mkdir(parents=True)
    monkeypatch.setattr(runner.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    monkeypatch.setattr(runner, "_chromium_is_available", lambda _python: True)
    monkeypatch.setattr(runner, "_load_real_llm_config", lambda *_args: object())

    def fake_run(command, **_kwargs):
        if command[-1:] == ("@{upstream}",):
            return runner.subprocess.CompletedProcess(
                args=command, returncode=0, stdout="origin/master\n", stderr=""
            )
        if command[:3] == ("git", "rev-parse", "--abbrev-ref"):
            return runner.subprocess.CompletedProcess(
                args=command, returncode=0, stdout="master\n", stderr=""
            )
        return runner.subprocess.CompletedProcess(
            args=command, returncode=0, stdout="v1.2.3\n", stderr=""
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    outcomes = runner.run_phase("preflight", context, runner.PrePushState())

    assert outcomes[0].status == "PASS"
    evidence = json.loads((context.output_dir / "preflight.json").read_text())
    assert evidence["head"] == "a" * 40
    assert evidence["branch"] == "master"
    assert evidence["upstream"] == "origin/master"
    assert evidence["lockfiles"] == list(runner.REQUIRED_NPM_LOCKFILES)
    assert evidence["tools"] == {
        "chromium": "available",
        "docker": "v1.2.3",
        "dockerCompose": "v1.2.3",
        "node": "v1.2.3",
        "npm": "v1.2.3",
        "python": "v1.2.3",
    }


def test_preflight_blocks_when_the_starting_worktree_is_not_clean(tmp_path):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(" M user-owned-file",),
    )

    outcomes = runner.run_phase("preflight", context, runner.PrePushState())

    assert outcomes[0].status == "BLOCKED"
    assert outcomes[0].reason == "working tree is not clean"


def test_preflight_blocks_before_running_suites_when_docker_daemon_is_unreachable(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/local/bin/docker")
    monkeypatch.setattr(runner, "_load_real_llm_config", lambda *_args: object())
    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *_args, **_kwargs: runner.subprocess.CompletedProcess(
            args=(), returncode=1, stdout="", stderr=""
        ),
    )

    outcomes = runner.run_phase("preflight", context, runner.PrePushState())

    assert outcomes[0].status == "BLOCKED"
    assert outcomes[0].reason == "Docker daemon is unavailable"


def test_deployment_does_not_create_credentials_before_checking_required_build_output(
    monkeypatch,
    tmp_path,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
        workspace_dir=tmp_path / "child-workspace",
    )
    state = runner.PrePushState(llm_config=object())
    from scripts.test import pre_push_deployment

    def unexpected_create(**_kwargs):
        raise AssertionError("deployment credentials must not be created")

    monkeypatch.setattr(
        pre_push_deployment.DeploymentConfig,
        "create",
        unexpected_create,
    )

    outcomes = runner._run_deployment(context, state)

    assert outcomes[0].status == "BLOCKED"
    assert state.deployment is None


def test_real_e2e_routes_nested_pytest_playwright_output_to_the_child_workspace(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    workspace = tmp_path / "child-workspace"
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
        workspace_dir=workspace,
    )
    state = runner.PrePushState(
        llm_config=SimpleNamespace(real_test_environment=lambda: {}),
        deployment=SimpleNamespace(
            config=SimpleNamespace(
                frontend_url="http://127.0.0.1:18080/new-agents/",
                evidence_dir=context.output_dir / "real-e2e",
                control_path=context.output_dir / "real-e2e" / "control.json",
            )
        ),
    )
    captured: dict[str, str] = {}

    def fake_run_suite(_suite, _context, *, extra_environment):
        captured.update(extra_environment)
        return runner.GateOutcome(
            phase="real_e2e",
            suite_id="new-agents-deployed-real-release",
            status="PASS",
            collected=1,
            executed=1,
            reason="ok",
        )

    monkeypatch.setattr(runner, "run_suite", fake_run_suite)
    monkeypatch.setattr(
        runner, "validate_deployed_release_evidence", lambda _context: "ok"
    )

    outcomes = runner._run_real_e2e(context, state)

    assert outcomes[0].status == "PASS"
    assert captured["NEW_AGENTS_REAL_PLAYWRIGHT_OUTPUT_DIR"] == str(
        workspace / "playwright-artifacts" / "new-agents-deployed-real-release"
    )


def test_deployed_release_evidence_must_cover_every_manifest_workflow_stage_and_transition(
    tmp_path,
):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    evidence_dir = context.output_dir / "real-e2e"
    evidence_dir.mkdir(parents=True)
    manifest = runner.load_workflow_manifest(ROOT)
    for workflow_id, workflow in manifest["workflows"].items():
        (evidence_dir / f"release-{workflow_id}.json").write_text(
            json.dumps(
                {
                    "scope": "release",
                    "workflowId": workflow_id,
                    "status": "PASS",
                    "evidence": {"transition_count": len(workflow["stages"]) - 1},
                }
            ),
            encoding="utf-8",
        )

    coverage = runner.validate_deployed_release_evidence(context)

    assert coverage == "release evidence covered 7 workflows, 25 stages, 18 transitions"


def test_deployed_release_evidence_rejects_a_missing_workflow_report(tmp_path):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    evidence_dir = context.output_dir / "real-e2e"
    evidence_dir.mkdir(parents=True)

    with pytest.raises(
        ValueError, match="release evidence does not cover every workflow"
    ):
        runner.validate_deployed_release_evidence(context)


def test_evidence_scan_recursively_rejects_runtime_deployment_credentials(tmp_path):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )
    nested_evidence = context.output_dir / "real-e2e" / "nested" / "report.json"
    nested_evidence.parent.mkdir(parents=True)
    nested_evidence.write_text(
        json.dumps({"observed": "runtime-proxy-canary"}), encoding="utf-8"
    )
    state = runner.PrePushState(
        llm_config=SimpleNamespace(redaction_secrets=lambda: ()),
        deployment=SimpleNamespace(
            config=SimpleNamespace(
                environment={"PROXY_API_KEY": "runtime-proxy-canary"}
            )
        ),
    )

    outcome = runner._scan_evidence(context, state)

    assert outcome.status == "FAIL"
    assert outcome.reason == "evidence contained a configured secret"


def test_versioned_git_hook_executes_only_the_canonical_runner():
    hook = ROOT / ".githooks/pre-push"

    source = hook.read_text(encoding="utf-8")
    assert "scripts/test/pre-push.sh" in source
    assert "git push" not in source
    assert "--scope" not in source


def test_suite_ownership_document_is_rendered_from_the_fixed_registry(tmp_path):
    runner = _load_runner()
    context = runner.PrePushContext(
        root=ROOT,
        head="a" * 40,
        output_dir=tmp_path / "test-results" / "pre-push" / ("a" * 40),
        initial_status=(),
    )

    expected = runner.render_suite_ownership(runner.fixed_suites(context))
    document = ROOT / "docs/test_requirements/2026-07-21-qg021-suite-ownership.md"

    assert document.read_text(encoding="utf-8") == expected
