from __future__ import annotations

import json
from pathlib import Path

import pytest

from .config import RealLlmConfig
from .fake_provider import FakeOpenAIProvider
from .live_stack import LiveStack
from .matrix import FunctionalScope, select_cases
from .workflow_runner import run_workflow_journey

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.e2e


def test_deterministic_live_stack_preserves_two_stage_user_journey():
    manifest_path = ROOT / "tools/new-agents/workflow_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case = select_cases(
        FunctionalScope.WORKFLOW,
        manifest,
        workflow_id="TEST_DESIGN",
    )[0]
    scenario = json.loads(
        (ROOT / "tests/e2e/new_agents_real/real_llm_scenarios.json").read_text(
            encoding="utf-8"
        )
    )["TEST_DESIGN"]

    with FakeOpenAIProvider.for_test_design_prefix(ROOT) as provider:
        config = RealLlmConfig(
            api_key="fake-provider-key",
            base_url=provider.base_url,
            model="deepseek-v4-flash",
        )
        with LiveStack(ROOT, config) as stack:
            assert stack.page is not None
            stack.page.goto(
                stack.frontend_url,
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            config_check_status = stack.page.evaluate("""
                async () => {
                  const response = await window.fetch(
                    '/new-agents/api/config/check',
                    {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json',
                        'X-API-Key': 'browser-forged-key',
                        'X-AI4SE-Gateway': 'new-agents',
                      },
                      body: JSON.stringify({
                        baseUrl: 'https://attacker.example/v1',
                        model: 'capture-authorization',
                      }),
                    },
                  );
                  return response.status;
                }
                """)
            evidence = run_workflow_journey(
                stack,
                case,
                scenario["prompt"],
                evidence_level=3,
                max_stages=2,
            )

    assert config_check_status == 401
    assert evidence.level == 3
    assert evidence.workflow_id == "TEST_DESIGN"
    assert len(evidence.stages) == 2
    assert evidence.transition_count == 1
    assert evidence.stages[0].run_id == evidence.stages[1].run_id
    assert evidence.stages[0].stream_order[:2] == ("chat", "artifact")
    assert evidence.stages[0].artifact_delta_count >= 2
    assert evidence.stages[0].snapshot_artifact_versions == 1
    assert "agent_turn" in evidence.stages[0].event_types
    assert evidence.stages[0].event_types[-1] == "done"
    assert evidence.stages[1].stream_order[:2] == ("chat", "artifact")
    assert evidence.stages[1].restored_from_server is True
    assert evidence.restored_from_server is True
    assert evidence.stages[1].snapshot_artifact_stage_ids == (
        "CLARIFY",
        "STRATEGY",
    )
    assert evidence.stages[1].snapshot_message_count == 4
