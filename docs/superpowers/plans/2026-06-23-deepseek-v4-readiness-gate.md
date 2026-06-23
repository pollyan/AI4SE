# DeepSeek V4 Readiness Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为所有在线 New Agents workflow stage 增加本地 DeepSeek V4 `artifact_data` 结构化输出 readiness gate。

**Architecture:** 把 `artifact_data_renderers.py` 中的 stage renderer 支持面暴露为共享 registry，并由后端测试从 manifest 枚举所有 stage 做 fixture、renderer、contract、instruction、DeepSeek raw JSON runtime 的端到端本地验收。不新增 runtime、API、持久化字段或前端协议。

**Tech Stack:** Python 3.11、Pytest、Pydantic、现有 New Agents backend Agent Runtime、workflow manifest、artifact contract。

---

### Task 1: 写 DeepSeek readiness RED 测试

**Files:**
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`

- [ ] **Step 1: 写失败测试**

测试应导入尚未存在的 `get_artifact_data_renderer_stage_keys`，并覆盖全部 manifest stage：

```python
import json
from pathlib import Path

import pytest

from agent_contracts import validate_agent_turn
from agent_runtime import (
    PydanticAgentRuntime,
    RawStreamingConfig,
    build_structured_output_instruction,
)
from artifact_data_renderers import (
    get_artifact_data_renderer_stage_keys,
    render_agent_turn_from_artifact_data,
)
from sse_schemas import AgentTurnDeltaOutput
from test_artifact_data_renderers import (
    VALID_CASES_ARTIFACT_DATA,
    VALID_CLARIFY_ARTIFACT_DATA,
    VALID_DELIVERY_ARTIFACT_DATA,
    VALID_IDEA_CONCEPT_ARTIFACT_DATA,
    VALID_IDEA_CONVERGE_ARTIFACT_DATA,
    VALID_IDEA_DEFINE_ARTIFACT_DATA,
    VALID_IDEA_DIVERGE_ARTIFACT_DATA,
    VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
    VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
    VALID_REQ_REVIEW_ARTIFACT_DATA,
    VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
    VALID_STRATEGY_ARTIFACT_DATA,
    VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
    VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
    VALID_VALUE_JOURNEY_ARTIFACT_DATA,
    VALID_VALUE_PERSONA_ARTIFACT_DATA,
)

ARTIFACT_DATA_FIXTURES = {
    ("TEST_DESIGN", "CLARIFY"): VALID_CLARIFY_ARTIFACT_DATA,
    ("TEST_DESIGN", "STRATEGY"): VALID_STRATEGY_ARTIFACT_DATA,
    ("TEST_DESIGN", "CASES"): VALID_CASES_ARTIFACT_DATA,
    ("TEST_DESIGN", "DELIVERY"): VALID_DELIVERY_ARTIFACT_DATA,
    ("REQ_REVIEW", "REVIEW"): VALID_REQ_REVIEW_ARTIFACT_DATA,
    ("REQ_REVIEW", "REPORT"): VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "TIMELINE"): VALID_INCIDENT_TIMELINE_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA,
    ("INCIDENT_REVIEW", "IMPROVEMENT"): VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "DEFINE"): VALID_IDEA_DEFINE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "DIVERGE"): VALID_IDEA_DIVERGE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "CONVERGE"): VALID_IDEA_CONVERGE_ARTIFACT_DATA,
    ("IDEA_BRAINSTORM", "CONCEPT"): VALID_IDEA_CONCEPT_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "ELEVATOR"): VALID_VALUE_ELEVATOR_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "PERSONA"): VALID_VALUE_PERSONA_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "JOURNEY"): VALID_VALUE_JOURNEY_ARTIFACT_DATA,
    ("VALUE_DISCOVERY", "BLUEPRINT"): VALID_VALUE_BLUEPRINT_ARTIFACT_DATA,
}

class FakeAgent:
    def __init__(self, output):
        self.output = output

    def run_sync(self, prompt, *, deps=None, model_settings=None):
        raise AssertionError("readiness tests use raw streaming, not PydanticAI")

def manifest_stage_keys():
    manifest = json.loads(Path("tools/new-agents/workflow_manifest.json").read_text(encoding="utf-8"))
    return {
        (workflow_id, stage["id"])
        for workflow_id, workflow in manifest["workflows"].items()
        for stage in workflow["stages"]
    }

def test_deepseek_readiness_covers_every_manifest_stage():
    expected = manifest_stage_keys()

    assert set(get_artifact_data_renderer_stage_keys()) == expected
    assert set(ARTIFACT_DATA_FIXTURES) == expected

@pytest.mark.parametrize("workflow_id, stage_id", sorted(ARTIFACT_DATA_FIXTURES))
def test_deepseek_readiness_renderer_output_passes_contract(workflow_id, stage_id):
    output = render_agent_turn_from_artifact_data(
        {
            "chat": "已生成结构化产物数据。",
            "artifact_data": ARTIFACT_DATA_FIXTURES[(workflow_id, stage_id)],
            "stage_action": None,
            "warnings": [],
        },
        workflow_id=workflow_id,
        current_stage_id=stage_id,
    )

    assert output is not None
    validate_agent_turn(output, workflow_id=workflow_id, current_stage_id=stage_id)

@pytest.mark.parametrize("workflow_id, stage_id", sorted(ARTIFACT_DATA_FIXTURES))
def test_deepseek_readiness_instruction_requests_artifact_data(workflow_id, stage_id):
    instruction = build_structured_output_instruction(workflow_id, stage_id)

    assert "artifact_data" in instruction
    assert "artifact_update.markdown" not in instruction

@pytest.mark.parametrize("workflow_id, stage_id", sorted(ARTIFACT_DATA_FIXTURES))
def test_deepseek_readiness_raw_json_streaming_uses_json_object_mode(monkeypatch, workflow_id, stage_id):
    final_json = json.dumps(
        {
            "chat": "已生成结构化产物数据。",
            "artifact_data": ARTIFACT_DATA_FIXTURES[(workflow_id, stage_id)],
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield final_json[:12]
        yield final_json[12:]

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model_name="deepseek-v4-flash",
            system_prompt="system prompt",
        ),
    )

    outputs = list(runtime.stream_turn("用户输入", workflow_id=workflow_id, current_stage_id=stage_id))

    assert isinstance(outputs[0], AgentTurnDeltaOutput)
    assert outputs[-1].artifact_update.markdown
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
```

- [ ] **Step 2: 运行测试确认 RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q`

Expected: FAIL，导入 `get_artifact_data_renderer_stage_keys` 失败。

### Task 2: 暴露 renderer registry

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: 最小实现**

将 `render_agent_turn_from_artifact_data` 的 if/elif stage 分支收束为 registry：

```python
ArtifactDataRendererConfig = tuple[type[StrictArtifactDataModel], Any]

ARTIFACT_DATA_RENDERERS: dict[tuple[str, str], ArtifactDataRendererConfig] = {
    ("TEST_DESIGN", "CLARIFY"): (ClarifyArtifactData, render_test_design_clarify_markdown),
    ...
}

def get_artifact_data_renderer_stage_keys() -> tuple[tuple[str, str], ...]:
    return tuple(sorted(ARTIFACT_DATA_RENDERERS))
```

`render_agent_turn_from_artifact_data` 查 registry，缺失时仍抛 `ValueError("artifact_data renderer is not configured for ...")`。

- [ ] **Step 2: 运行 readiness 测试确认 GREEN**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q`

Expected: PASS。

### Task 3: 文档记录和扩大验证

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] **Step 1: 更新 todo**

在“当前进展”追加本地 readiness gate 已完成，并在“进入实现前需要补的设计问题”中保留真实 smoke 和 raw data persistence 作为后续候选。

- [ ] **Step 2: 运行完整相关验证**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_contract_registry.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
git diff --check
```

Expected: all commands exit 0。

- [ ] **Step 3: 提交**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-readiness-gate-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-readiness-gate.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_deepseek_v4_readiness.py
git commit -m "test: 增加 DeepSeek 结构化输出就绪门禁"
```

Expected: commit succeeds on branch `codex/deepseek-readiness-gate`。
