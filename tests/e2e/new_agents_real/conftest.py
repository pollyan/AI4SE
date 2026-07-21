from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path

import pytest

from .config import load_real_llm_config
from .deployed_stack import DeployedStack, DeploymentControl, DeploymentTarget
from .live_stack import LiveStack, LiveStackStartupError
from .matrix import FunctionalCase, selection_from_environment
from .reporting import build_failure_evidence, report_path, write_report

ROOT = Path(__file__).resolve().parents[3]


def _manifest() -> dict:
    return json.loads(
        (ROOT / "tools/new-agents/workflow_manifest.json").read_text(encoding="utf-8")
    )


def build_real_stack(root: Path, config, *, environ: dict[str, str]):
    target_url = environ.get("NEW_AGENTS_REAL_TARGET_URL", "").strip()
    if not target_url:
        return LiveStack(root, config)
    target = DeploymentTarget.parse(target_url)
    control = DeploymentControl.from_environment(root, environ)
    return DeployedStack(root, config, target, control)


def pytest_generate_tests(metafunc) -> None:
    if "real_case" not in metafunc.fixturenames:
        return
    if not os.environ.get("NEW_AGENTS_REAL_SCOPE", "").strip():
        metafunc.parametrize(
            "real_case",
            [pytest.param(None, id="missing-real-scope")],
        )
        return
    selection = selection_from_environment(_manifest(), os.environ)
    metafunc.parametrize(
        "real_case",
        selection.cases,
        ids=[case.test_id for case in selection.cases],
    )


@pytest.fixture(scope="session")
def real_live_stack() -> Generator[LiveStack, None, None]:
    if not os.environ.get("NEW_AGENTS_REAL_SCOPE", "").strip():
        raise pytest.UsageError("NEW_AGENTS_REAL_SCOPE is required")
    config = load_real_llm_config(ROOT, os.environ)
    scope = os.environ["NEW_AGENTS_REAL_SCOPE"]
    stack = build_real_stack(ROOT, config, environ=os.environ)
    try:
        with stack:
            yield stack
    except LiveStackStartupError as error:
        path = report_path(ROOT, scope, "startup")
        write_report(
            path,
            build_failure_evidence(
                error,
                scope=scope,
                workflow_id=None,
                stage_id=None,
            ),
            secrets=stack.redaction_secrets(),
        )
        raise


@pytest.fixture()
def real_case(request) -> FunctionalCase | None:
    return request.param
