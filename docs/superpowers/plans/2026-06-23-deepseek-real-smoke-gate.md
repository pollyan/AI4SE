# DeepSeek V4 Real Smoke Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the real DeepSeek V4 smoke gate with the current `artifact_data -> deterministic renderer -> artifact contract` runtime path.

**Architecture:** Reuse the existing `test_agent_real_smoke.py` pytest entry and `build_pydantic_agent_runtime()` raw streaming path. Add deterministic tests that monkeypatch raw streaming so the smoke gate can be validated without network, while preserving the existing `NEW_AGENTS_SMOKE_*` env-gated real model test.

**Tech Stack:** Python 3.11, pytest, Pydantic models, OpenAI-compatible raw streaming, existing New Agents Agent Runtime.

---

## File Map

- Modify `tools/new-agents/backend/tests/test_agent_real_smoke.py`: replace old Markdown-output smoke prompt with artifact_data smoke contract, add deterministic mock streaming tests, keep env-gated real smoke.
- Modify `docs/TESTING.md`: update the real smoke layer description from generic `artifact_update.markdown` to current artifact_data renderer semantics.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record that the smoke gate has been aligned while real external evidence still depends on credentials/network/quota.
- Modify `docs/todos/refactor/README.md`: update current entrance summary if needed.

## Task 1: RED Smoke Gate Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_real_smoke.py`

- [ ] **Step 1: Add tests that describe the new smoke contract**

Append tests that currently fail because `SMOKE_SYSTEM_PROMPT` still asks for `artifact_update.markdown` and the file has no deterministic raw-streaming smoke test:

```python
def test_smoke_system_prompt_requests_artifact_data_not_markdown_protocol():
    assert "artifact_data" in SMOKE_SYSTEM_PROMPT
    assert "artifact_update" not in SMOKE_SYSTEM_PROMPT
    assert "不要输出完整 Markdown" in SMOKE_SYSTEM_PROMPT


def test_deepseek_smoke_gate_uses_artifact_data_renderer_and_json_object_mode(monkeypatch):
    emitted_calls = []

    def fake_stream_chat_completion_content(**kwargs):
        emitted_calls.append(kwargs)
        yield json.dumps(
            {
                "chat": "已完成登录需求澄清，右侧产物由结构化数据渲染。",
                "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
                "stage_action": None,
                "warnings": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )
    runtime = build_pydantic_agent_runtime(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model_name="deepseek-v4-flash",
        system_prompt=SMOKE_SYSTEM_PROMPT,
    )

    output = _run_smoke_turn(runtime)

    assert emitted_calls[0]["response_format"] == {"type": "json_object"}
    assert emitted_calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in emitted_calls[0]["messages"][0]["content"]
    assert output.artifact_update.markdown is not None
    assert "# 需求分析文档" in output.artifact_update.markdown
    assert "flowchart" in output.artifact_update.markdown
    assert not _contains_artifact_markdown(output.chat)
```

- [ ] **Step 2: Run RED tests**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_real_smoke.py::test_smoke_system_prompt_requests_artifact_data_not_markdown_protocol tests/test_agent_real_smoke.py::test_deepseek_smoke_gate_uses_artifact_data_renderer_and_json_object_mode -q
```

Expected: at least the prompt contract test fails because `SMOKE_SYSTEM_PROMPT` does not contain `artifact_data` and still contains `artifact_update`.

## Task 2: GREEN Smoke Gate Implementation

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_real_smoke.py`

- [ ] **Step 1: Import deterministic fixture and add helper**

Add imports:

```python
import json

from agent_contracts import validate_agent_turn
from test_artifact_data_renderers import VALID_CLARIFY_ARTIFACT_DATA
```

Add helper:

```python
def _run_smoke_turn(runtime):
    output = runtime.run_turn(
        SMOKE_USER_PROMPT,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )
    return validate_agent_turn(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )
```

- [ ] **Step 2: Replace the smoke system prompt**

Change `SMOKE_SYSTEM_PROMPT` so it asks for:

```text
你是 Lisa 测试专家。请严格输出一个 JSON object，用于验证 TEST_DESIGN/CLARIFY 的 artifact_data 结构化产物链路。
本次只验证 TEST_DESIGN/CLARIFY 阶段，不要请求进入下一阶段。
chat 只返回给用户看的简短说明，禁止包含 Markdown 标题、表格、代码块、Mermaid 或完整文档正文。
必须输出 artifact_data，不要输出 artifact_update，不要输出完整 Markdown、Mermaid、表格或 ai4se-visual；后端会负责确定性渲染右侧 artifact。
artifact_data 必须包含 document_info、requirement_facts、system_boundaries、business_rules、flow_links、clarification_questions、quality_requirements、downstream_inputs 和 stage_gate。
stage_action 必须为 null，warnings 可以为空数组。
```

- [ ] **Step 3: Update real smoke assertions**

Refactor `test_real_pydantic_ai_runtime_returns_valid_clarify_artifact()` to call `_run_smoke_turn(runtime)` and keep the existing artifact title/heading/chat assertions. The test name can stay unchanged or become `test_real_deepseek_smoke_returns_artifact_data_rendered_clarify_artifact`.

- [ ] **Step 4: Run GREEN tests**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_real_smoke.py -q
```

Expected without env: deterministic tests pass and the real smoke test is skipped because required env vars are missing. With env: all tests pass or expose a real provider/schema/contract failure.

## Task 3: Documentation and Todo Recording

**Files:**
- Modify: `docs/TESTING.md`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update TESTING.md**

In the `真实模型冒烟层` section, change the coverage bullets to state:

```markdown
- 真实模型能在当前 workflow/stage 下返回合法 JSON object，并由后端 `artifact_data` renderer 生成合法 `AgentTurnOutput`。
- renderer 输出的 `artifact_update.markdown` 包含阶段必需标题和可视化 contract。
- `chat` 不包含 artifact Markdown 结构。
- DeepSeek V4 smoke 必须验证 JSON object mode 和 thinking disabled；仅在显式提供 `NEW_AGENTS_SMOKE_*` 环境变量时运行。
```

- [ ] **Step 2: Update DeepSeek todo**

Add a dated progress bullet stating the smoke gate now targets the current DeepSeek artifact_data path, and adjust the remaining real-smoke note to say external execution evidence still requires credentials, network and quota.

- [ ] **Step 3: Update refactor README**

Update the current entrance summary so it says the smoke gate/evidence mechanism is aligned, while actual external DeepSeek evidence remains optional and environment-dependent.

- [ ] **Step 4: Run doc checks**

Run:

```bash
rg -n "真实模型冒烟层|artifact_data renderer|真实 DeepSeek|smoke gate|NEW_AGENTS_SMOKE" docs/TESTING.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/README.md
git diff --check
```

Expected: references appear in the three documents and diff check passes.

## Task 4: Final Verification and Commit

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run focused backend verification**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_real_smoke.py tests/test_deepseek_v4_readiness.py -q
```

Expected: deterministic tests pass; real smoke is skipped without env or passes with env.

- [ ] **Step 2: Run syntax verification**

Run:

```bash
python3 -m py_compile tools/new-agents/backend/tests/test_agent_real_smoke.py
```

Expected: command exits 0.

- [ ] **Step 3: Inspect status and diff**

Run:

```bash
git status --short
git diff --stat
git diff --check
```

Expected: only the smoke test, spec, plan, TESTING doc and todo docs are modified; diff check passes.

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-real-smoke-gate-design.md docs/superpowers/plans/2026-06-23-deepseek-real-smoke-gate.md docs/TESTING.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/README.md tools/new-agents/backend/tests/test_agent_real_smoke.py
git commit -m "test(new-agents): 对齐 DeepSeek 真实 smoke 结构化链路"
```

Expected: one focused commit.

## Self-Review

- Spec coverage: Tasks cover smoke prompt, deterministic gate, real env skip, docs/todo recording and verification.
- Placeholder scan: no unresolved placeholders or unspecified implementation steps.
- Type consistency: tests use existing `build_pydantic_agent_runtime()`, `validate_agent_turn()` and `VALID_CLARIFY_ARTIFACT_DATA`.
