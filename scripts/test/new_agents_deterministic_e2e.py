#!/usr/bin/env python3
"""Run two deterministic New Agents E2E adapters as one fail-closed gate."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class PytestAdapter:
    suite_id: str
    targets: tuple[str, ...]


ADAPTERS = (
    PytestAdapter("browser", ("tests/e2e/new_agents_browser",)),
    PytestAdapter(
        "deterministic-live-stack",
        ("tests/e2e/new_agents_real/test_deterministic_live_stack.py",),
    ),
)


def _executed_count(output: str) -> int | None:
    if "no tests ran" in output.lower():
        return None
    passed = re.findall(r"(\d+)\s+passed", output)
    failed = re.findall(r"(\d+)\s+failed", output)
    errors = re.findall(r"(\d+)\s+errors?", output)
    count = sum(int(value) for value in (*passed, *failed, *errors))
    return count or None


def _command(python: str, adapter: PytestAdapter) -> tuple[str, ...]:
    return (
        python,
        "-m",
        "pytest",
        "-o",
        "addopts=",
        "-p",
        "no:cacheprovider",
        *adapter.targets,
        "-m",
        "e2e and not real_llm",
        "-q",
    )


def _run_adapter(
    root: Path,
    python: str,
    adapter: PytestAdapter,
) -> int | None:
    command = _command(python, adapter)
    result = subprocess.run(
        command,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    count = _executed_count(output)
    if result.returncode != 0:
        if output:
            print(output, end="", file=sys.stderr)
        print(
            f"{adapter.suite_id} exited with code {result.returncode}",
            file=sys.stderr,
        )
        return None
    if count is None:
        if output:
            print(output, end="", file=sys.stderr)
        print(f"{adapter.suite_id} collected no tests", file=sys.stderr)
        return None
    return count


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    counts: list[int] = []
    for adapter in ADAPTERS:
        count = _run_adapter(args.root, args.python, adapter)
        if count is None:
            return 1
        counts.append(count)
    print(f"{sum(counts)} passed in deterministic adapters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
