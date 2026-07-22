from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "test" / "new_agents_deterministic_e2e.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "new_agents_deterministic_e2e", RUNNER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_runner_executes_each_playwright_adapter_in_a_distinct_pytest_process(
    monkeypatch, capsys
):
    runner = _load_runner()
    commands: list[tuple[str, ...]] = []

    def fake_run(command, **_kwargs):
        commands.append(tuple(command))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="1 passed in 0.01s\n",
            stderr="",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    assert runner.main(["--python", "/venv/python"]) == 0

    assert commands == [
        (
            "/venv/python",
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "tests/e2e/new_agents_browser",
            "-m",
            "e2e and not real_llm",
            "-q",
        ),
        (
            "/venv/python",
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "tests/e2e/new_agents_real/test_deterministic_live_stack.py",
            "-m",
            "e2e and not real_llm",
            "-q",
        ),
    ]
    captured = capsys.readouterr()
    assert captured.out == "2 passed in deterministic adapters\n"
    assert captured.err == ""


def test_runner_fails_closed_when_an_adapter_collects_no_tests(
    monkeypatch,
    capsys,
):
    runner = _load_runner()
    results = iter(
        (
            subprocess.CompletedProcess(
                ("pytest",),
                0,
                stdout="1 passed in 0.01s\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                ("pytest",),
                0,
                stdout="no tests ran in 0.01s\n",
                stderr="",
            ),
        )
    )
    monkeypatch.setattr(
        runner.subprocess, "run", lambda *_args, **_kwargs: next(results)
    )

    assert runner.main(["--python", "/venv/python"]) == 1

    captured = capsys.readouterr()
    assert "deterministic-live-stack collected no tests" in captured.err


def test_runner_stops_before_the_live_adapter_when_browser_adapter_fails(
    monkeypatch,
):
    runner = _load_runner()
    commands: list[tuple[str, ...]] = []

    def fake_run(command, **_kwargs):
        commands.append(tuple(command))
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="1 failed in 0.01s\n",
            stderr="",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    assert runner.main(["--python", "/venv/python"]) == 1

    adapter_targets = [command[7] for command in commands]
    assert adapter_targets == ["tests/e2e/new_agents_browser"]
