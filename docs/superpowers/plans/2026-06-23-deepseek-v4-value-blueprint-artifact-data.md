# DeepSeek V4 VALUE_DISCOVERY/BLUEPRINT Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend `artifact_data` schema, deterministic renderer, Agent Runtime wiring, tests, and todo updates for `VALUE_DISCOVERY/BLUEPRINT`.

**Architecture:** Keep the shared New Agents runtime and artifact renderer registry. DeepSeek emits JSON business data only; backend Pydantic models validate references and deterministic renderer produces the Markdown/Mermaid/`ai4se-visual` artifact consumed by the existing contract, typed SSE, and persistence pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend contracts.

---

## File Structure

- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add BLUEPRINT data models, dispatch branch, renderer helpers.
- Modify `tools/new-agents/backend/agent_runtime.py`: add BLUEPRINT structured output instruction and include `VALUE_DISCOVERY/BLUEPRINT` in artifact_data capability registry.
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add valid fixture, validation negative cases, deterministic contract-valid renderer test.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add parsing, instruction, retry, and raw DeepSeek streaming tests for BLUEPRINT.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed BLUEPRINT slice and remaining work.

## Tasks

### Task 1: Write Failing Renderer Tests

- [ ] Add `ValueDiscoveryBlueprintArtifactData` import and `VALID_VALUE_BLUEPRINT_ARTIFACT_DATA` fixture.
- [ ] Add negative tests for unknown requirement references and unknown Lisa Handoff references.
- [ ] Add deterministic render test asserting `需求蓝图`, Mermaid `mindmap`, Mermaid `flowchart TD`, `roadmap`, `Lisa Handoff 输入`, `可测试性等级`, `owner`, `状态`, and contract validation.
- [ ] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: fail because `ValueDiscoveryBlueprintArtifactData` is not implemented.

### Task 2: Write Failing Runtime Tests

- [ ] Import `VALID_VALUE_BLUEPRINT_ARTIFACT_DATA` into `test_agent_runtime.py`.
- [ ] Add parse test proving `artifact_data` renders to a BLUEPRINT artifact.
- [ ] Add structured instruction test proving the prompt requests blueprint data fields and `roadmap` without asking for `artifact_update`.
- [ ] Add retry prompt test proving validation errors request data repair, not Markdown rewrite.
- [ ] Add DeepSeek raw JSON streaming test proving final output contains rendered BLUEPRINT artifact and the system prompt contains BLUEPRINT schema terms.

### Task 3: Implement Schema And Renderer

- [ ] Add BLUEPRINT Pydantic classes after JOURNEY models.
- [ ] Validate unique requirement IDs and acceptance IDs.
- [ ] Validate feature, MVP, acceptance, and Lisa Handoff references.
- [ ] Add `("VALUE_DISCOVERY", "BLUEPRINT")` dispatch in `render_agent_turn_from_artifact_data()`.
- [ ] Render all required headings, Mermaid diagrams, and `roadmap` visual deterministically.

### Task 4: Wire Runtime Instruction

- [ ] Add `VALUE_BLUEPRINT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`.
- [ ] Add `("VALUE_DISCOVERY", "BLUEPRINT")` to `supports_artifact_data_rendering()`.
- [ ] Add BLUEPRINT branch to `build_structured_output_instruction()`.
- [ ] Ensure retry prompt continues to use the shared artifact_data repair path.

### Task 5: Update Todo And Verify

- [ ] Update DeepSeek todo current progress with the tenth completed slice.
- [ ] Run focused renderer/runtime tests.
- [ ] Run expanded backend contract/API/SSE tests because runtime and artifact contract behavior changed.
- [ ] Run `py_compile` and diff checks.
- [ ] Commit with `feat: 支持 DeepSeek 需求蓝图结构化产物数据`.
