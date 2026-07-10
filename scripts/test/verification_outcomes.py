#!/usr/bin/env python3
"""Emit a machine-readable, fail-closed verdict for a verification gate."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Sequence


NON_PASS_STATUSES = {"FAIL", "NOT_RUN", "BLOCKED", "TIMEOUT", "FLAKY"}
STATUSES = {"PASS", *NON_PASS_STATUSES}


@dataclass(frozen=True)
class VerificationOutcome:
    suiteId: str
    status: str
    collected: int
    executed: int
    skipped: int
    reason: str

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"Unknown verification status {self.status!r}.")
        if min(self.collected, self.executed, self.skipped) < 0:
            raise ValueError("Verification counts must not be negative.")
        if self.executed > self.collected:
            raise ValueError("Executed count must not exceed collected count.")
        if self.executed + self.skipped > self.collected:
            raise ValueError(
                "Executed and skipped counts must not exceed collected count."
            )
        if self.status == "PASS" and (
            self.collected == 0 or self.executed == 0
        ):
            raise ValueError(
                "PASS requires collected and executed counts greater than zero."
            )

    def exit_code(self) -> int:
        return 0 if self.status == "PASS" else 1

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=False)


def _emit(outcome: VerificationOutcome) -> int:
    print(outcome.to_json())
    return outcome.exit_code()


def _parse_jest_counts(output: str) -> tuple[int, int, int] | None:
    summary = re.search(r"^Tests:\s+(.+)$", output, re.MULTILINE)
    if summary is None:
        return None

    def count(label: str) -> int:
        match = re.search(rf"(\d+)\s+{label}", summary.group(1))
        return int(match.group(1)) if match else 0

    failed = count("failed")
    skipped = count("skipped")
    passed = count("passed")
    total = count("total")
    if total == 0:
        return None
    return total, passed + failed, skipped


def _parse_pytest_counts(output: str) -> tuple[int, int, int] | None:
    if "no tests ran" in output:
        return 0, 0, 0

    collected_match = re.search(r"collected\s+(\d+)\s+items?", output)

    def summary_count(label: str) -> int:
        matches = re.findall(rf"(\d+)\s+{label}", output)
        return int(matches[-1]) if matches else 0

    passed = summary_count("passed")
    failed = summary_count("failed")
    errors = summary_count("errors?")
    skipped = summary_count("skipped")
    executed = passed + failed + errors
    if collected_match is None:
        if executed == 0 and skipped == 0:
            return None
        return executed + skipped, executed, skipped
    return int(collected_match.group(1)), executed, skipped


def _parse_vitest_counts(output: str) -> tuple[int, int, int] | None:
    summary = re.search(r"Tests\s+(\d+)\s+passed\s+\((\d+)\)", output)
    if summary is None:
        return None

    passed = int(summary.group(1))
    total = int(summary.group(2))
    return total, passed, 0


def _parsed_counts(parser: str, output: str) -> tuple[int, int, int] | None:
    if parser == "jest":
        return _parse_jest_counts(output)
    if parser == "pytest":
        return _parse_pytest_counts(output)
    if parser == "vitest":
        return _parse_vitest_counts(output)
    return None


def _counts_are_consistent(counts: tuple[int, int, int]) -> bool:
    collected, executed, skipped = counts
    return (
        collected >= 0
        and executed >= 0
        and skipped >= 0
        and executed <= collected
        and skipped <= collected
        and executed + skipped <= collected
    )


def _run_gate(args: argparse.Namespace) -> VerificationOutcome:
    try:
        result = subprocess.run(
            args.command,
            text=True,
            capture_output=True,
            check=False,
            timeout=args.timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="TIMEOUT",
            collected=0,
            executed=0,
            skipped=0,
            reason=f"Timed out after {args.timeout_seconds} seconds.",
        )
    except OSError as error:
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="FAIL",
            collected=0,
            executed=0,
            skipped=0,
            reason=f"Could not start child command: {error}.",
        )

    child_output = result.stdout + result.stderr
    if child_output:
        print(child_output, end="", file=sys.stderr)

    normalized_output = child_output.lower()
    if (
        "no tests found" in normalized_output
        or "no test files found" in normalized_output
        or "no tests ran" in normalized_output
    ):
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="NOT_RUN",
            collected=0,
            executed=0,
            skipped=0,
            reason=(
                "Jest collected no tests."
                if args.parser == "jest"
                else "pytest collected no tests."
            ),
        )

    counts = _parsed_counts(args.parser, child_output)

    if counts is not None and not _counts_are_consistent(counts):
        collected, executed, skipped = counts
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="FAIL",
            collected=0,
            executed=0,
            skipped=0,
            reason=(
                "Parser produced inconsistent counts: "
                f"collected={collected}, executed={executed}, skipped={skipped}."
            ),
        )

    if result.returncode != 0:
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="FAIL",
            collected=counts[0] if counts else 0,
            executed=counts[1] if counts else 0,
            skipped=counts[2] if counts else 0,
            reason=f"Child command exited with code {result.returncode}.",
        )

    if args.parser == "command":
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="PASS",
            collected=1,
            executed=1,
            skipped=0,
            reason="Command completed successfully.",
        )

    if counts is None:
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="NOT_RUN",
            collected=0,
            executed=0,
            skipped=0,
            reason="Command completed without a parsable test summary.",
        )

    collected, executed, skipped = counts
    if executed == 0:
        return VerificationOutcome(
            suiteId=args.suite_id,
            status="NOT_RUN",
            collected=collected,
            executed=executed,
            skipped=skipped,
            reason=f"{args.parser} executed no tests.",
        )

    return VerificationOutcome(
        suiteId=args.suite_id,
        status="PASS",
        collected=collected,
        executed=executed,
        skipped=skipped,
        reason=f"{args.parser} completed successfully.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)

    emit = commands.add_parser("emit")
    emit.add_argument("--suite-id", required=True)
    emit.add_argument("--status", choices=sorted(STATUSES), required=True)
    emit.add_argument("--collected", type=int, required=True)
    emit.add_argument("--executed", type=int, required=True)
    emit.add_argument("--skipped", type=int, required=True)
    emit.add_argument("--reason", required=True)

    run = commands.add_parser("run")
    run.add_argument("--suite-id", required=True)
    run.add_argument(
        "--parser", choices=("command", "jest", "pytest", "vitest"), required=True
    )
    run.add_argument("--timeout-seconds", type=float)
    run.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.action == "emit":
        try:
            outcome = VerificationOutcome(
                suiteId=args.suite_id,
                status=args.status,
                collected=args.collected,
                executed=args.executed,
                skipped=args.skipped,
                reason=args.reason,
            )
        except ValueError as error:
            outcome = VerificationOutcome(
                suiteId=args.suite_id,
                status="FAIL",
                collected=0,
                executed=0,
                skipped=0,
                reason=f"Invalid outcome: {error}",
            )
        return _emit(outcome)

    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if not args.command:
        raise SystemExit("run requires a child command after --")
    return _emit(_run_gate(args))


if __name__ == "__main__":
    raise SystemExit(main())
