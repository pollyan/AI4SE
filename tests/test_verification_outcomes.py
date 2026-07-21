import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTCOME_TOOL = ROOT / "scripts" / "test" / "verification_outcomes.py"
LOCAL_RUNNER = ROOT / "scripts" / "test" / "test-local.sh"
DOCS_CHECK = ROOT / "scripts" / "test" / "check-docs.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"


def run_outcome_tool(*args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
    result = subprocess.run(
        [sys.executable, str(OUTCOME_TOOL), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, json.loads(result.stdout)


def test_jest_zero_collection_is_not_run_even_when_child_exits_zero():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "intent-proxy",
        "--parser",
        "jest",
        "--",
        sys.executable,
        "-c",
        "print('No tests found, exiting with code 0')",
    )

    assert result.returncode == 1
    assert outcome == {
        "suiteId": "intent-proxy",
        "status": "NOT_RUN",
        "collected": 0,
        "executed": 0,
        "skipped": 0,
        "reason": "Jest collected no tests.",
    }


def test_jest_skip_only_summary_preserves_collection_and_skip_counts():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "intent-proxy",
        "--parser",
        "jest",
        "--",
        sys.executable,
        "-c",
        "print('Tests: 1 skipped, 1 total')",
    )

    assert result.returncode == 1
    assert outcome == {
        "suiteId": "intent-proxy",
        "status": "NOT_RUN",
        "collected": 1,
        "executed": 0,
        "skipped": 1,
        "reason": "jest executed no tests.",
    }


def test_child_tool_failure_is_not_reported_as_pass():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "docs-links",
        "--parser",
        "command",
        "--",
        sys.executable,
        "-c",
        "import sys; sys.exit(9)",
    )

    assert result.returncode == 1
    assert outcome["status"] == "FAIL"
    assert outcome["reason"] == "Child command exited with code 9."


def test_missing_child_executable_is_a_machine_readable_failure():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "missing-tool",
        "--parser",
        "command",
        "--",
        "definitely-not-an-executable",
    )

    assert result.returncode == 1
    assert outcome["status"] == "FAIL"
    assert outcome["reason"].startswith("Could not start child command:")


def test_skip_only_pytest_result_is_not_pass():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "intent-api",
        "--parser",
        "pytest",
        "--",
        sys.executable,
        "-c",
        "print('collected 3 items'); print('3 skipped in 0.01s')",
    )

    assert result.returncode == 1
    assert outcome == {
        "suiteId": "intent-api",
        "status": "NOT_RUN",
        "collected": 3,
        "executed": 0,
        "skipped": 3,
        "reason": "pytest executed no tests.",
    }


def test_pytest_summary_without_verbose_collection_count_is_a_pass():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "new-agents-backend",
        "--parser",
        "pytest",
        "--",
        sys.executable,
        "-c",
        "print('910 passed, 1 skipped in 1.00s')",
    )

    assert result.returncode == 0
    assert outcome == {
        "suiteId": "new-agents-backend",
        "status": "PASS",
        "collected": 911,
        "executed": 910,
        "skipped": 1,
        "reason": "pytest completed successfully.",
    }


def test_inconsistent_parser_counts_are_machine_readable_failure_not_traceback():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "inconsistent-pytest",
        "--parser",
        "pytest",
        "--",
        sys.executable,
        "-c",
        "print('collected 1 item'); print('1 passed, 1 skipped in 0.01s')",
    )

    assert result.returncode == 1
    assert outcome == {
        "suiteId": "inconsistent-pytest",
        "status": "FAIL",
        "collected": 0,
        "executed": 0,
        "skipped": 0,
        "reason": "Parser produced inconsistent counts: collected=1, executed=1, skipped=1.",
    }


def test_vitest_summary_records_the_actual_test_count():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "new-agents-frontend",
        "--parser",
        "vitest",
        "--",
        sys.executable,
        "-c",
        "print('Test Files  2 passed (2)'); print('Tests  872 passed (872)')",
    )

    assert result.returncode == 0
    assert outcome == {
        "suiteId": "new-agents-frontend",
        "status": "PASS",
        "collected": 872,
        "executed": 872,
        "skipped": 0,
        "reason": "vitest completed successfully.",
    }


def test_successful_command_gate_is_a_pass_with_one_executed_gate():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "critical-lint",
        "--parser",
        "command",
        "--",
        sys.executable,
        "-c",
        "pass",
    )

    assert result.returncode == 0
    assert outcome == {
        "suiteId": "critical-lint",
        "status": "PASS",
        "collected": 1,
        "executed": 1,
        "skipped": 0,
        "reason": "Command completed successfully.",
    }


def test_no_test_files_output_is_not_a_successful_command_gate():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "new-agents-frontend",
        "--parser",
        "command",
        "--",
        sys.executable,
        "-c",
        "print('No test files found, exiting with code 0')",
    )

    assert result.returncode == 1
    assert outcome["status"] == "NOT_RUN"
    assert outcome["collected"] == 0
    assert outcome["executed"] == 0


def test_timed_out_gate_reports_timeout():
    result, outcome = run_outcome_tool(
        "run",
        "--suite-id",
        "bounded-command",
        "--parser",
        "command",
        "--timeout-seconds",
        "0.01",
        "--",
        sys.executable,
        "-c",
        "import time; time.sleep(1)",
    )

    assert result.returncode == 1
    assert outcome["status"] == "TIMEOUT"
    assert outcome["reason"] == "Timed out after 0.01 seconds."


def test_explicit_not_run_outcome_is_not_success():
    result, outcome = run_outcome_tool(
        "emit",
        "--suite-id",
        "new-agents-real-llm-smoke",
        "--status",
        "NOT_RUN",
        "--collected",
        "0",
        "--executed",
        "0",
        "--skipped",
        "0",
        "--reason",
        "Missing required smoke configuration.",
    )

    assert result.returncode == 1
    assert outcome["status"] == "NOT_RUN"
    assert outcome["skipped"] == 0


def test_emit_rejects_pass_without_collected_and_executed_work():
    result, outcome = run_outcome_tool(
        "emit",
        "--suite-id",
        "invalid-pass",
        "--status",
        "PASS",
        "--collected",
        "0",
        "--executed",
        "0",
        "--skipped",
        "0",
        "--reason",
        "This must not be accepted.",
    )

    assert result.returncode == 1
    assert outcome["status"] == "FAIL"
    assert (
        "PASS requires collected and executed counts greater than zero"
        in outcome["reason"]
    )


def test_local_smoke_runner_reports_missing_configuration_as_not_run():
    environment = os.environ.copy()
    for name in (
        "NEW_AGENTS_SMOKE_API_KEY",
        "NEW_AGENTS_SMOKE_BASE_URL",
        "NEW_AGENTS_SMOKE_MODEL",
    ):
        environment[name] = ""

    result = subprocess.run(
        ["bash", str(LOCAL_RUNNER), "smoke"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 1
    outcomes = [
        json.loads(line)
        for line in result.stdout.splitlines()
        if line.startswith('{"suiteId"')
    ]
    assert outcomes == [
        {
            "suiteId": "new-agents-functional-stage",
            "status": "NOT_RUN",
            "collected": 1,
            "executed": 0,
            "skipped": 0,
            "reason": (
                "missing required real-model configuration: "
                "NEW_AGENTS_SMOKE_API_KEY, NEW_AGENTS_SMOKE_BASE_URL, "
                "NEW_AGENTS_SMOKE_MODEL"
            ),
        }
    ]


def test_proxy_gates_reject_zero_collection_in_local_runner_and_ci():
    local_runner = LOCAL_RUNNER.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "--passWithNoTests" not in local_runner
    assert "--passWithNoTests" not in workflow
    assert '--testPathPattern="tests/proxy"' in local_runner
    assert '--testPathPattern="tests/proxy"' in workflow
    assert (
        'OUTCOME_TOOL="$PROJECT_ROOT/scripts/test/verification_outcomes.py"'
        in local_runner
    )
    assert '"$PROJECT_PYTHON" "$OUTCOME_TOOL" run' in local_runner
    assert "verification_outcomes.py run" in workflow


def test_docs_gate_does_not_silence_child_tool_errors():
    docs_check = DOCS_CHECK.read_text(encoding="utf-8")

    assert "set -e -o pipefail" in docs_check
    assert 'GREP_BIN="${GREP_BIN:-grep}"' in docs_check
    assert 'if links=$("$GREP_BIN" -oE' in docs_check
    assert "sed -E" in docs_check
    assert 'if [ "$status" -eq 1 ]; then' in docs_check
    assert 'return "$status"' in docs_check


def test_docs_gate_emits_machine_readable_failure_for_a_child_tool_error(
    tmp_path: Path,
):
    fake_grep = tmp_path / "grep-that-fails"
    fake_grep.write_text("#!/bin/sh\nexit 2\n", encoding="utf-8")
    fake_grep.chmod(0o755)
    environment = os.environ.copy()
    environment["GREP_BIN"] = str(fake_grep)

    result = subprocess.run(
        ["bash", str(DOCS_CHECK)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode != 0
    outcomes = [
        json.loads(line)
        for line in result.stdout.splitlines()
        if line.startswith('{"suiteId"')
    ]
    assert outcomes == [
        {
            "suiteId": "docs-links",
            "status": "FAIL",
            "collected": 1,
            "executed": 1,
            "skipped": 0,
            "reason": f"Documentation link check failed with exit code {result.returncode}.",
        }
    ]
