# DeepSeek V4 Format Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 DeepSeek V4 artifact_data 迁移补上覆盖门禁，防止在线 workflow stage 静默回退到模型拼 Markdown/Mermaid/表格。

**Architecture:** 继续复用共享 New Agents Runtime、现有 artifact_data renderer 和现有 typed SSE 输出。把 runtime instruction 映射和 renderer stage key 显式暴露并交叉校验，所有在线 manifest stage 必须同时具备 renderer 与 artifact_data instruction。

**Tech Stack:** Python 3.11, Flask/PydanticAI backend, Pydantic models, pytest, black.

**Status:** 已完成。因本轮范围集中在共享后端 runtime/renderer 和对应测试，未派发可写子智能体，主线程按 TDD 串行执行。

---

## File Structure

- Modify: `tools/new-agents/backend/agent_runtime.py`
  - 新增 `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` 字典。
  - 让 `supports_artifact_data_rendering()` 基于 instruction keys 与 renderer keys 的交集判断。
  - 让 `build_structured_output_instruction()` 从字典读取 instruction。
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
  - 新增 `ARTIFACT_DATA_RENDERER_STAGE_KEYS` 与 `get_artifact_data_renderer_stage_keys()`。
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  - 新增 manifest 全 stage artifact_data 覆盖、instruction 不回退 Markdown、retry prompt 不回退 Markdown 的测试。
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
  - 新增 renderer key 与 runtime instruction key 同步测试。
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - 记录本轮已补迁移后防回退门禁。

## Task 1: RED DeepSeek Format Guard Tests

- [x] **Step 1: Add failing runtime coverage tests**

In `tools/new-agents/backend/tests/test_agent_runtime.py`, import the new instruction registry and renderer key helper:

```python
from agent_runtime import (
    ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS,
    build_model_settings,
    build_raw_json_retry_prompt,
    build_structured_output_instruction,
    build_system_prompt,
    parse_agent_turn_output_text,
    supports_artifact_data_rendering,
)
from artifact_data_renderers import get_artifact_data_renderer_stage_keys
from workflow_contract_registry import get_workflow_stages
```

Add these tests near the existing artifact_data instruction tests:

```python
def test_all_manifest_stages_use_artifact_data_instructions_without_markdown_fallback():
    stage_keys = {
        (workflow_id, stage_id)
        for workflow_id, stages in get_workflow_stages().items()
        for stage_id in stages
    }

    assert stage_keys
    assert stage_keys == set(ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS)
    assert stage_keys == get_artifact_data_renderer_stage_keys()

    for workflow_id, stage_id in sorted(stage_keys):
        assert supports_artifact_data_rendering(workflow_id, stage_id)
        instruction = build_structured_output_instruction(workflow_id, stage_id)
        assert "artifact_data" in instruction
        assert "artifact_update.markdown" not in instruction
        assert "完整 Markdown 文档" not in instruction
        assert "后端会负责确定性渲染" in instruction
```

```python
def test_all_manifest_stage_retry_prompts_repair_artifact_data_not_markdown():
    for workflow_id, stages in get_workflow_stages().items():
        for stage_id in stages:
            prompt = build_raw_json_retry_prompt(
                "原始提示",
                ValueError("artifact_data.requirements.0.title missing"),
                workflow_id=workflow_id,
                current_stage_id=stage_id,
            )
            assert "artifact_data" in prompt
            assert "不要输出 Markdown 文档" in prompt
            assert "artifact_update.type 必须为 replace" not in prompt
```

- [x] **Step 2: Add failing renderer/runtime key sync test**

In `tools/new-agents/backend/tests/test_artifact_data_renderers.py`, import the runtime registry:

```python
from agent_runtime import ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS
```

Add:

```python
def test_artifact_data_renderer_stage_keys_match_runtime_instruction_registry():
    assert get_artifact_data_renderer_stage_keys() == set(
        ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS
    )
```

- [x] **Step 3: Run RED tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stages_use_artifact_data_instructions_without_markdown_fallback tools/new-agents/backend/tests/test_agent_runtime.py::test_all_manifest_stage_retry_prompts_repair_artifact_data_not_markdown tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_artifact_data_renderer_stage_keys_match_runtime_instruction_registry -q
```

Expected: FAIL because `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` and `get_artifact_data_renderer_stage_keys()` do not exist yet.

Actual RED: failed during collection with `ImportError: cannot import name 'ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS' from 'agent_runtime'`, matching the missing guard interface.

## Task 2: GREEN Registry And Guard Implementation

- [x] **Step 1: Add renderer stage key registry**

In `tools/new-agents/backend/artifact_data_renderers.py`, add this near the imports / shared helpers:

```python
ARTIFACT_DATA_RENDERER_STAGE_KEYS: frozenset[tuple[str, str]] = frozenset(
    {
        ("IDEA_BRAINSTORM", "DEFINE"),
        ("IDEA_BRAINSTORM", "DIVERGE"),
        ("IDEA_BRAINSTORM", "CONVERGE"),
        ("IDEA_BRAINSTORM", "CONCEPT"),
        ("INCIDENT_REVIEW", "TIMELINE"),
        ("INCIDENT_REVIEW", "ROOT_CAUSE"),
        ("INCIDENT_REVIEW", "IMPROVEMENT"),
        ("TEST_DESIGN", "CLARIFY"),
        ("TEST_DESIGN", "STRATEGY"),
        ("TEST_DESIGN", "CASES"),
        ("TEST_DESIGN", "DELIVERY"),
        ("REQ_REVIEW", "REVIEW"),
        ("REQ_REVIEW", "REPORT"),
        ("VALUE_DISCOVERY", "ELEVATOR"),
        ("VALUE_DISCOVERY", "PERSONA"),
        ("VALUE_DISCOVERY", "JOURNEY"),
        ("VALUE_DISCOVERY", "BLUEPRINT"),
    }
)


def get_artifact_data_renderer_stage_keys() -> set[tuple[str, str]]:
    return set(ARTIFACT_DATA_RENDERER_STAGE_KEYS)
```

- [x] **Step 2: Add runtime instruction registry**

In `tools/new-agents/backend/agent_runtime.py`, import the renderer key helper:

```python
from artifact_data_renderers import (
    get_artifact_data_renderer_stage_keys,
    render_agent_turn_from_artifact_data,
)
```

Add `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` after all artifact_data instruction constants:

```python
ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS: dict[tuple[str, str], str] = {
    ("IDEA_BRAINSTORM", "DEFINE"): IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("IDEA_BRAINSTORM", "DIVERGE"): IDEA_DIVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("IDEA_BRAINSTORM", "CONVERGE"): IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("IDEA_BRAINSTORM", "CONCEPT"): IDEA_CONCEPT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "CLARIFY"): ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "STRATEGY"): STRATEGY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "CASES"): CASES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("TEST_DESIGN", "DELIVERY"): DELIVERY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("REQ_REVIEW", "REVIEW"): REQ_REVIEW_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("REQ_REVIEW", "REPORT"): REQ_REVIEW_REPORT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "ELEVATOR"): VALUE_ELEVATOR_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "PERSONA"): VALUE_PERSONA_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "JOURNEY"): VALUE_JOURNEY_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("VALUE_DISCOVERY", "BLUEPRINT"): VALUE_BLUEPRINT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("INCIDENT_REVIEW", "TIMELINE"): INCIDENT_TIMELINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): INCIDENT_ROOT_CAUSE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
    ("INCIDENT_REVIEW", "IMPROVEMENT"): INCIDENT_IMPROVEMENT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION,
}
```

- [x] **Step 3: Use registries in runtime helpers**

Replace `supports_artifact_data_rendering()` with:

```python
def supports_artifact_data_rendering(workflow_id: str, current_stage_id: str) -> bool:
    stage_key = (workflow_id, current_stage_id)
    return (
        stage_key in ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS
        and stage_key in get_artifact_data_renderer_stage_keys()
    )
```

Replace `build_structured_output_instruction()` with:

```python
def build_structured_output_instruction(
    workflow_id: str,
    current_stage_id: str,
) -> str:
    return ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS.get(
        (workflow_id, current_stage_id),
        TEXT_STRUCTURED_OUTPUT_INSTRUCTION,
    )
```

- [x] **Step 4: Run GREEN tests**

Run the RED command again. Expected: PASS.

Actual GREEN: the three new focused tests passed after registry implementation.

## Task 3: Docs And Final Verification

- [x] **Step 1: Update DeepSeek todo**

In `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`, add a current progress bullet:

```markdown
- 2026-06-23 已补迁移后防回退门禁: runtime instruction registry、renderer stage key registry 和 manifest coverage tests 会保证所有在线 workflow stage 同时具备 `artifact_data` instruction 与后端 renderer；未来新增 stage 若漏配任一侧，后端测试会失败，避免 DeepSeek V4 路径静默回退到完整 Markdown/Mermaid/表格输出职责。
```

Update the acceptance section to state that all current online stages have a regression guard, while real smoke still needs credentials.

- [x] **Step 2: Run focused validation**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m black --check tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py
git diff --check
```

Actual results:

- `test_agent_runtime.py` + `test_artifact_data_renderers.py`: `163 passed in 0.33s`
- `py_compile`: passed
- `black --check`: 4 files left unchanged
- `git diff --check`: passed

- [x] **Step 3: Commit**

Stage only this milestone:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-v4-format-guard-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-format-guard.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py
git commit -m "test: 增加 DeepSeek 格式输出防回退门禁"
```
