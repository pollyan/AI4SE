from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError

from .matrix import FunctionalCase
from .assertions import FunctionalAssertionError
from .reporting import build_failure_evidence, report_path, write_report
from .stream_observer import latest_trace_summary
from .workflow_runner import run_stage_probe, run_workflow_journey

ROOT = Path(__file__).resolve().parents[3]
pytestmark = [pytest.mark.e2e, pytest.mark.slow, pytest.mark.real_llm]


def _scenarios() -> dict:
    return json.loads(
        (ROOT / "tests/e2e/new_agents_real/real_llm_scenarios.json").read_text(
            encoding="utf-8"
        )
    )


def _scope() -> str:
    return os.environ["NEW_AGENTS_REAL_SCOPE"]


def test_real_agent_functional_scope(
    real_live_stack,
    real_case: FunctionalCase | None,
) -> None:
    if real_case is None:
        pytest.fail("NEW_AGENTS_REAL_SCOPE is required")
    scenario = _scenarios()[real_case.workflow_id]
    path = report_path(ROOT, _scope(), real_case.test_id)
    redaction_secrets = real_live_stack.redaction_secrets()
    safe_error: FunctionalAssertionError | None = None
    try:
        if real_case.kind == "stage":
            evidence = run_stage_probe(
                real_live_stack,
                real_case,
                scenario["prompt"],
            )
        else:
            evidence = run_workflow_journey(
                real_live_stack,
                real_case,
                scenario["prompt"],
            )
    except (
        FunctionalAssertionError,
        PlaywrightError,
        AssertionError,
        RuntimeError,
        ValueError,
        OSError,
    ) as error:
        if isinstance(error, FunctionalAssertionError):
            safe_error = error
        elif isinstance(error, (PlaywrightError, AssertionError)):
            safe_error = FunctionalAssertionError(
                "BROWSER_ASSERTION_FAILED",
                "browser functional assertion failed",
            )
        else:
            safe_error = FunctionalAssertionError(
                "AGENT_RUNTIME_UNAVAILABLE",
                "real agent functional execution failed",
            )
    if safe_error is not None:
        report_error: FunctionalAssertionError | None = None
        try:
            write_report(
                path,
                build_failure_evidence(
                    safe_error,
                    scope=_scope(),
                    workflow_id=real_case.workflow_id,
                    stage_id=real_case.stage_id,
                    trace_summary=latest_trace_summary(real_live_stack.page),
                ),
                secrets=redaction_secrets,
            )
        except (
            FunctionalAssertionError,
            PlaywrightError,
            AssertionError,
            RuntimeError,
            TypeError,
            ValueError,
            OSError,
        ):
            report_error = FunctionalAssertionError(
                "REPORT_WRITE_FAILED",
                "functional evidence report could not be written",
            )
        if report_error is not None:
            raise report_error from None
        raise safe_error from None

    write_report(
        path,
        {
            "scope": _scope(),
            "workflowId": real_case.workflow_id,
            "stageId": real_case.stage_id,
            "status": "PASS",
            "evidenceLevel": 4,
            "evidence": asdict(evidence),
        },
        secrets=redaction_secrets,
    )
