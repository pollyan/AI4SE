from __future__ import annotations

import ast
import importlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "test" / "new_agents_functional.py"


def _load_runner():
    if not RUNNER_PATH.exists():
        pytest.fail(f"functional runner is missing: {RUNNER_PATH}")
    spec = importlib.util.spec_from_file_location(
        "new_agents_functional",
        RUNNER_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("argv", "scope", "workflow_id", "stage_id"),
    [
        (["inner"], "inner", None, None),
        (["stage", "TEST_DESIGN", "CLARIFY"], "stage", "TEST_DESIGN", "CLARIFY"),
        (["workflow", "VALUE_DISCOVERY"], "workflow", "VALUE_DISCOVERY", None),
        (["pr"], "pr", None, None),
        (["nightly"], "nightly", None, None),
        (["release"], "release", None, None),
    ],
)
def test_cli_scopes(argv, scope, workflow_id, stage_id):
    runner = _load_runner()

    selection = runner.parse_scope(argv)

    assert selection.scope.value == scope
    assert selection.workflow_id == workflow_id
    assert selection.stage_id == stage_id


def test_manifest_scopes_are_complete_and_pr_spans_lisa_and_alex():
    runner = _load_runner()
    manifest = runner.load_workflow_manifest(ROOT)

    nightly = runner.select_cases(runner.FunctionalScope.NIGHTLY, manifest)
    release = runner.select_cases(runner.FunctionalScope.RELEASE, manifest)
    pr_cases = runner.select_cases(runner.FunctionalScope.PR, manifest)

    assert len(nightly) == 25
    assert len({(case.workflow_id, case.stage_id) for case in nightly}) == 25
    assert all(case.kind == "stage" for case in nightly)
    assert len(release) == 7
    assert {case.workflow_id for case in release} == set(manifest["workflows"])
    assert all(case.kind == "workflow" for case in release)
    assert {case.agent_id for case in pr_cases} == {"lisa", "alex"}
    assert {case.workflow_id for case in pr_cases} == {
        "TEST_DESIGN",
        "VALUE_DISCOVERY",
    }


def test_stage_and_workflow_selection_reject_manifest_drift():
    runner = _load_runner()
    manifest = runner.load_workflow_manifest(ROOT)

    with pytest.raises(ValueError, match="unknown workflow"):
        runner.select_cases(
            runner.FunctionalScope.WORKFLOW,
            manifest,
            workflow_id="MISSING",
        )
    with pytest.raises(ValueError, match="unknown stage"):
        runner.select_cases(
            runner.FunctionalScope.STAGE,
            manifest,
            workflow_id="TEST_DESIGN",
            stage_id="MISSING",
        )


def test_missing_real_config_is_not_run_and_fails_closed(tmp_path, monkeypatch):
    runner = _load_runner()
    manifest = runner.load_workflow_manifest(ROOT)
    monkeypatch.setattr(runner, "load_workflow_manifest", lambda _root: manifest)

    execution = runner.plan_execution(
        runner.ScopeSelection(runner.FunctionalScope.PR),
        root=tmp_path,
        environ={},
    )

    assert execution.status == "NOT_RUN"
    assert execution.exit_code != 0
    assert execution.command == ()
    assert "NEW_AGENTS_SMOKE_API_KEY" in execution.reason


def test_release_rejects_partial_deployment_target_configuration():
    runner = _load_runner()
    execution = runner.plan_execution(
        runner.ScopeSelection(runner.FunctionalScope.RELEASE),
        root=ROOT,
        environ={
            "NEW_AGENTS_SMOKE_API_KEY": "sk-qg021-canary",
            "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.example",
            "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
            "NEW_AGENTS_REAL_TARGET_URL": "http://127.0.0.1:18080/new-agents/",
        },
    )

    assert execution.status == "NOT_RUN"
    assert "deployment target configuration" in execution.reason


def test_inner_omits_frontend_backend_and_live_stack_suites_owned_by_pre_push(
    monkeypatch,
):
    runner = _load_runner()
    commands: list[tuple[str, ...]] = []

    class SuccessfulRun:
        returncode = 0

    def capture(command, **_kwargs):
        commands.append(tuple(command))
        return SuccessfulRun()

    monkeypatch.setattr(runner.subprocess, "run", capture)

    assert runner._run_inner(ROOT, {}) == 0

    flattened = "\n".join(" ".join(command) for command in commands)
    assert "tests/test_new_agents_functional_runner.py" in flattened
    assert "tests/e2e/new_agents_real/test_contracts.py" in flattened
    assert "tests/e2e/new_agents_real/test_deterministic_live_stack.py" not in flattened
    assert "scripts/test/test-local.sh" not in flattened


def test_real_config_is_masked_and_removed_from_frontend_environment(tmp_path):
    runner = _load_runner()
    secret = "sk-qg020-canary"
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"NEW_AGENTS_SMOKE_API_KEY={secret}",
                "NEW_AGENTS_SMOKE_BASE_URL=https://api.deepseek.example/v1",
                "NEW_AGENTS_SMOKE_MODEL=deepseek-v4-flash",
                "SAFE_FRONTEND_FLAG=enabled",
            ]
        ),
        encoding="utf-8",
    )

    config = runner.load_real_llm_config(tmp_path, {})
    backend_env, frontend_env = runner.build_child_environments(
        config,
        {
            "PATH": "/usr/bin",
            "HOME": "/tmp/home",
            "TMPDIR": "/tmp",
            "SAFE_FRONTEND_FLAG": "enabled",
            "OTHER_TOKEN": "nope",
            "SESSION_COOKIE": "opaque-cookie",
            "DATABASE_DSN": "postgresql://private",
        },
    )

    assert secret not in repr(config)
    assert backend_env["NEW_AGENTS_DEFAULT_LLM_API_KEY"] == secret
    assert backend_env["NEW_AGENTS_DEFAULT_LLM_BASE_URL"] == config.base_url
    assert backend_env["NEW_AGENTS_DEFAULT_LLM_MODEL"] == config.model
    assert backend_env["FLASK_SKIP_DOTENV"] == "1"
    assert "OTHER_TOKEN" not in backend_env
    assert "SAFE_FRONTEND_FLAG" not in backend_env
    assert "SESSION_COOKIE" not in backend_env
    assert "DATABASE_DSN" not in backend_env
    assert frontend_env == {
        "PATH": "/usr/bin",
        "HOME": "/tmp/home",
        "TMPDIR": "/tmp",
    }
    assert "NEW_AGENTS_SMOKE_API_KEY" not in frontend_env
    assert "NEW_AGENTS_DEFAULT_LLM_API_KEY" not in frontend_env
    assert "OTHER_TOKEN" not in frontend_env
    assert "SAFE_FRONTEND_FLAG" not in frontend_env
    assert "SESSION_COOKIE" not in frontend_env
    assert "DATABASE_DSN" not in frontend_env
    assert secret not in json.dumps(frontend_env)
    assert config.redaction_secrets() == (config.base_url, secret)


def test_secret_free_browser_environment_drops_parent_credentials():
    config_module = importlib.import_module("tests.e2e.new_agents_real.config")
    helper = getattr(config_module, "build_secret_free_browser_environment", None)

    assert callable(helper)

    browser_environment = helper(
        {
            "PATH": "/safe/bin",
            "HOME": "/safe/home",
            "TMPDIR": "/safe/tmp",
            "NEW_AGENTS_SMOKE_API_KEY": "PARENT-API-KEY-CANARY",
            "OTHER_TOKEN": "PARENT-TOKEN-CANARY",
            "SERVICE_PASSWORD": "PARENT-PASSWORD-CANARY",
        }
    )

    assert browser_environment == {
        "PATH": "/safe/bin",
        "HOME": "/safe/home",
        "TMPDIR": "/safe/tmp",
    }


def test_all_functional_chromium_launches_use_shared_secret_free_environment():
    helper_name = "build_secret_free_browser_environment"
    launch_paths = (
        ROOT / "tests/e2e/new_agents_real/live_stack.py",
        ROOT / "tests/e2e/new_agents_real/test_live_stack_contracts.py",
        ROOT / "tests/e2e/new_agents_browser/conftest.py",
    )

    for path in launch_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        launch_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "launch"
        ]
        assert launch_calls, f"expected a Chromium launch in {path}"
        for launch_call in launch_calls:
            environment_keyword = next(
                (keyword for keyword in launch_call.keywords if keyword.arg == "env"),
                None,
            )
            assert environment_keyword is not None, (
                f"Chromium launch inherits the parent environment in {path}:"
                f"{launch_call.lineno}"
            )
            assert isinstance(environment_keyword.value, ast.Call)
            assert isinstance(environment_keyword.value.func, ast.Name)
            assert environment_keyword.value.func.id == helper_name


def test_all_functional_playwright_drivers_use_secret_free_environment():
    helper_names = {
        "secret_free_sync_playwright",
        "start_secret_free_playwright",
    }
    driver_paths = (
        ROOT / "tests/e2e/new_agents_real/live_stack.py",
        ROOT / "tests/e2e/new_agents_real/test_live_stack_contracts.py",
        ROOT / "tests/e2e/new_agents_browser/conftest.py",
    )

    for path in driver_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        unsafe_starts = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sync_playwright"
        ]
        assert not unsafe_starts, (
            f"Playwright driver inherits the parent environment in {path}:"
            f"{unsafe_starts[0].lineno}"
        )
        helper_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in helper_names
        ]
        assert helper_calls, f"expected a secret-free Playwright helper in {path}"
        for helper_call in helper_calls:
            assert len(helper_call.args) == 2
            assert isinstance(helper_call.args[0], ast.Name)
            assert helper_call.args[0].id == "sync_playwright"
            environment = helper_call.args[1]
            assert isinstance(environment, ast.Attribute)
            assert isinstance(environment.value, ast.Name)
            assert environment.value.id == "os"
            assert environment.attr == "environ"


def test_browser_e2e_vite_process_drops_parent_credentials(monkeypatch):
    browser_conftest = importlib.import_module("tests.e2e.new_agents_browser.conftest")
    api_key = "VITE-PARENT-API-KEY-CANARY"
    token = "VITE-PARENT-TOKEN-CANARY"
    password = "VITE-PARENT-PASSWORD-CANARY"
    monkeypatch.setenv("PATH", "/safe/bin")
    monkeypatch.setenv("HOME", "/safe/home")
    monkeypatch.setenv("TMPDIR", "/safe/tmp")
    monkeypatch.setenv("NEW_AGENTS_SMOKE_API_KEY", api_key)
    monkeypatch.setenv("OTHER_TOKEN", token)
    monkeypatch.setenv("SERVICE_PASSWORD", password)
    captured: dict = {}

    class FakeProcess:
        def terminate(self) -> None:
            return None

        def wait(self, timeout=None) -> int:
            return 0

    def capture_popen(*_args, **kwargs):
        captured.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(browser_conftest, "_free_port", lambda: 19003)
    monkeypatch.setattr(browser_conftest, "_wait_for_server", lambda *_args: None)
    monkeypatch.setattr(browser_conftest.subprocess, "Popen", capture_popen)

    fixture_generator = browser_conftest.new_agents_base_url.__wrapped__()
    next(fixture_generator)
    fixture_generator.close()

    vite_environment = captured["env"]
    assert vite_environment["DISABLE_HMR"] == "true"
    assert vite_environment["PATH"] == "/safe/bin"
    assert vite_environment["HOME"] == "/safe/home"
    assert vite_environment["TMPDIR"] == "/safe/tmp"
    assert "NEW_AGENTS_SMOKE_API_KEY" not in vite_environment
    assert "OTHER_TOKEN" not in vite_environment
    assert "SERVICE_PASSWORD" not in vite_environment
    assert api_key not in vite_environment.values()
    assert token not in vite_environment.values()
    assert password not in vite_environment.values()


@pytest.mark.parametrize(
    "configured_base_url",
    [
        "https://user:OpaqueConfigCanary987@api.example/v1",
        "https://api.example/v1?credential=OpaqueConfigCanary987",
        "https://api.example/v1#OpaqueConfigCanary987",
        "https://api.example/v1?",
        "https://api.example/v1#",
        "https://api.example/v1?#",
        "ftp://api.example/v1",
        "https:///missing-host",
    ],
)
def test_real_config_rejects_unsafe_base_url_without_echoing_it(
    configured_base_url,
):
    runner = _load_runner()
    canary = "OpaqueConfigCanary987"

    with pytest.raises(runner.RealLlmConfigurationError) as captured:
        runner.RealLlmConfig(
            api_key=canary,
            base_url=configured_base_url,
            model=canary,
        )

    assert canary not in str(captured.value)
    assert "NEW_AGENTS_SMOKE_BASE_URL" in str(captured.value)


def test_real_config_rejects_remote_plaintext_http_without_echoing_url():
    runner = _load_runner()
    configured_base_url = "http://RemoteHttpCanary987.example/v1"

    with pytest.raises(runner.RealLlmConfigurationError) as captured:
        runner.RealLlmConfig(
            api_key="safe-test-key",
            base_url=configured_base_url,
            model="safe-test-model",
        )

    rendered_error = str(captured.value)
    assert configured_base_url not in rendered_error
    assert "RemoteHttpCanary987" not in rendered_error
    assert "NEW_AGENTS_SMOKE_BASE_URL" in rendered_error


@pytest.mark.parametrize(
    "configured_base_url",
    [
        "http://localhost:8000/v1",
        "http://127.0.0.1:8000/v1",
        "http://[::1]:8000/v1",
    ],
)
def test_real_config_allows_plaintext_http_only_for_loopback(configured_base_url):
    runner = _load_runner()

    config = runner.RealLlmConfig(
        api_key="safe-test-key",
        base_url=configured_base_url,
        model="safe-test-model",
    )

    assert config.base_url == configured_base_url


def test_real_gate_redaction_replaces_overlapping_secrets_longest_first():
    runner = _load_runner()
    api_key = "OverlapCanary987"
    base_url = f"https://{api_key}.example/v1"

    redacted = runner._redact_text(
        f"base={base_url} key={api_key}",
        (api_key, base_url),
    )

    assert redacted == "base=<redacted> key=<redacted>"


def test_complete_config_builds_secret_free_real_command_and_selection_environment():
    runner = _load_runner()
    secret = "sk-qg020-command-canary"

    execution = runner.plan_execution(
        runner.ScopeSelection(runner.FunctionalScope.STAGE, "TEST_DESIGN", "CLARIFY"),
        root=ROOT,
        environ={
            "PATH": "/usr/bin",
            "NEW_AGENTS_SMOKE_API_KEY": secret,
            "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.example/v1",
            "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
        },
    )

    assert execution.status == "READY"
    assert execution.exit_code == 0
    assert "test_real_agent_workflows.py" in " ".join(execution.command)
    assert "real_llm" in execution.command
    assert execution.environment["NEW_AGENTS_REAL_SCOPE"] == "stage"
    assert execution.environment["NEW_AGENTS_REAL_WORKFLOW"] == "TEST_DESIGN"
    assert execution.environment["NEW_AGENTS_REAL_STAGE"] == "CLARIFY"
    assert secret not in " ".join(execution.command)
    assert secret not in execution.reason
    assert secret not in repr(execution)


def test_real_command_routes_playwright_output_to_the_supplied_isolated_directory(
    tmp_path,
):
    runner = _load_runner()
    output_dir = tmp_path / "playwright-artifacts" / "release"

    execution = runner.plan_execution(
        runner.ScopeSelection(runner.FunctionalScope.RELEASE),
        root=ROOT,
        environ={
            "PATH": "/usr/bin",
            "NEW_AGENTS_SMOKE_API_KEY": "sk-qg021-output-canary",
            "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.example/v1",
            "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
            "NEW_AGENTS_REAL_PLAYWRIGHT_OUTPUT_DIR": str(output_dir),
        },
    )

    assert execution.status == "READY"
    assert f"--output={output_dir}" in execution.command


def test_real_gate_output_forwarding_redacts_provider_secret(capsys):
    runner = _load_runner()
    secret = "sk-qg020-output-canary"
    result = subprocess.CompletedProcess(
        args=("pytest",),
        returncode=1,
        stdout=f"provider response mentioned {secret}\n",
        stderr=f"Authorization: Bearer {secret}\n",
    )

    runner.forward_redacted_output(result, secrets=(secret,))

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    assert captured.out == "provider response mentioned <redacted>\n"
    assert captured.err == "Authorization: Bearer <redacted>\n"


def test_real_gate_subprocess_is_captured_before_redacted_forwarding():
    source = RUNNER_PATH.read_text(encoding="utf-8")

    assert "capture_output=True" in source
    assert "forward_redacted_output(" in source


def test_shell_adapter_and_existing_test_runner_use_fail_closed_scopes():
    shell_adapter = ROOT / "scripts/test/new-agents-functional.sh"
    test_local = (ROOT / "scripts/test/test-local.sh").read_text(encoding="utf-8")

    assert shell_adapter.is_file()
    adapter_source = shell_adapter.read_text(encoding="utf-8")
    assert "new_agents_functional.py" in adapter_source
    assert '"$@"' in adapter_source
    deterministic_e2e = (
        ROOT / "scripts/test/new_agents_deterministic_e2e.py"
    ).read_text(encoding="utf-8")
    assert '"e2e and not real_llm"' in deterministic_e2e
    assert 'new-agents-functional.sh" stage TEST_DESIGN CLARIFY' in test_local


def test_deterministic_e2e_runner_collects_browser_and_live_adapters_together():
    test_local = (ROOT / "scripts/test/test-local.sh").read_text(encoding="utf-8")

    assert '--suite-id "new-agents-deterministic-contracts"' in test_local
    assert '--suite-id "new-agents-deterministic-e2e"' in test_local
    assert "new-agents-browser-e2e" not in test_local
    assert "new-agents-deterministic-live-stack" not in test_local
    assert "tests/e2e/new_agents_real/test_contracts.py" in test_local
    assert "tests/e2e/new_agents_real/test_live_stack_contracts.py" in test_local
    assert "scripts/test/new_agents_deterministic_e2e.py" in test_local


def test_legacy_direct_runtime_smoke_is_removed():
    legacy_smoke = ROOT / "tools/new-agents/backend/tests/test_agent_real_smoke.py"

    assert not legacy_smoke.exists()


def test_shell_entrypoint_emits_not_run_and_exits_nonzero_without_credentials():
    environment = dict(os.environ)
    environment.update(
        {
            "NEW_AGENTS_SMOKE_API_KEY": "",
            "NEW_AGENTS_SMOKE_BASE_URL": "",
            "NEW_AGENTS_SMOKE_MODEL": "",
        }
    )
    result = subprocess.run(
        [str(ROOT / "scripts/test/new-agents-functional.sh"), "pr"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["suiteId"] == "new-agents-functional-pr"
    assert payload["status"] == "NOT_RUN"
    assert payload["executed"] == 0
    assert "NEW_AGENTS_SMOKE_API_KEY" in payload["reason"]
    assert "Traceback" not in result.stderr


def test_execution_plan_falls_back_to_active_python_without_local_venv(
    tmp_path,
    monkeypatch,
):
    runner = _load_runner()
    manifest = runner.load_workflow_manifest(ROOT)
    monkeypatch.setattr(runner, "load_workflow_manifest", lambda _root: manifest)

    execution = runner.plan_execution(
        runner.ScopeSelection(
            runner.FunctionalScope.STAGE,
            "TEST_DESIGN",
            "CLARIFY",
        ),
        root=tmp_path,
        environ={
            "PATH": os.environ.get("PATH", ""),
            "NEW_AGENTS_SMOKE_API_KEY": "sk-qg020-python-fallback",
            "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.example/v1",
            "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
        },
    )

    assert execution.command[0] == sys.executable


def test_ci_maps_events_to_real_scopes_and_blocks_production_deploy():
    workflow_path = ROOT / ".github/workflows/deploy.yml"
    source = workflow_path.read_text(encoding="utf-8")
    workflow = yaml.load(source, Loader=yaml.BaseLoader)

    assert "schedule" in workflow["on"]
    real_job = workflow["jobs"]["new-agents-real-functional-test"]
    assert "env" not in real_job
    real_step = next(
        step
        for step in real_job["steps"]
        if step.get("name") == "🤖 Run headless real-model functional gate"
    )
    assert set(real_step["env"]) == {
        "NEW_AGENTS_REAL_SCOPE",
        "NEW_AGENTS_SMOKE_API_KEY",
        "NEW_AGENTS_SMOKE_BASE_URL",
        "NEW_AGENTS_SMOKE_MODEL",
    }
    assert "scripts/test/new_agents_deterministic_e2e.py" in source
    assert "tests/e2e/new_agents_real/test_live_stack_contracts.py" in source
    assert "tests/e2e/new_agents_real/test_contracts.py" in source
    assert "devServerProxy.test.ts" in source
    assert "new-agents-functional.sh" in source
    assert "pull_request) scope=pr" not in source
    assert "schedule) scope=nightly" in source
    assert "push) scope=release" in source
    assert "github.ref_protected == true" in real_job["if"]
    assert "github.event_name == 'pull_request'" not in real_job["if"]
    assert real_job["environment"]["name"]
    assert "test-results/new-agents-real/*.json" in source
    assert "new-agents-functional-deterministic-test" in workflow["jobs"]
    assert (
        "new-agents-real-functional-test"
        in workflow["jobs"]["deploy-to-production"]["needs"]
    )
    assert (
        "inputs.real_scope == 'release'"
        in workflow["jobs"]["deploy-to-production"]["if"]
    )
    assert '-m "not slow"' in source


def test_live_stack_uses_active_python_in_ci_instead_of_local_venv_path():
    source = (ROOT / "tests/e2e/new_agents_real/live_stack.py").read_text(
        encoding="utf-8"
    )

    assert "sys.executable" in source
    assert 'self.root / ".venv/bin/python"' not in source


def test_real_model_module_can_be_deselected_without_scope_configuration(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            f"--output={tmp_path / 'playwright-artifacts'}",
            "tests/e2e/new_agents_real/test_contracts.py",
            "tests/e2e/new_agents_real/test_real_agent_workflows.py",
            "-m",
            "not real_llm",
            "-q",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "passed, 1 deselected" in result.stdout
    assert "1 deselected" in result.stdout


def test_real_model_module_fails_closed_when_selected_without_scope(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            f"--output={tmp_path / 'playwright-artifacts'}",
            "tests/e2e/new_agents_real/test_real_agent_workflows.py",
            "-m",
            "real_llm",
            "-q",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "NEW_AGENTS_SMOKE_API_KEY": "sk-qg020-scope-canary",
            "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.example/v1",
            "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
        },
    )

    output = result.stdout + result.stderr
    assert result.returncode != 0
    assert "NEW_AGENTS_REAL_SCOPE is required" in output
    assert "sk-qg020-scope-canary" not in output
    assert "skipped" not in output.lower()
