# DeepSeek V4 IDEA_BRAINSTORM/DEFINE Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend `artifact_data` schema, deterministic renderer, Agent Runtime wiring, tests, and todo updates for `IDEA_BRAINSTORM/DEFINE`.

**Architecture:** Keep the shared New Agents runtime and artifact renderer registry. DeepSeek emits JSON business data only; backend Pydantic models validate references and deterministic renderer produces the Markdown/Mermaid artifact consumed by the existing contract, typed SSE, and persistence pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend contracts.

---

## File Structure

- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add DEFINE data models, dispatch branch, renderer helpers, and Mermaid `mindmap`.
- Modify `tools/new-agents/backend/agent_runtime.py`: add DEFINE structured output instruction and include `IDEA_BRAINSTORM/DEFINE` in artifact_data capability registry.
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add valid fixture, validation negative cases, deterministic contract-valid renderer test.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add parsing, instruction, retry, and raw DeepSeek streaming tests for DEFINE.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed DEFINE slice and remaining IDEA_BRAINSTORM work.

## Tasks

### Task 1: Write Failing Renderer Tests

- [x] Add `IdeaDefineArtifactData` import and `VALID_IDEA_DEFINE_ARTIFACT_DATA` fixture.
- [x] Add negative tests for duplicate evidence IDs, duplicate problem IDs, unknown fit evidence references, root problem without evidence or fit coverage, and stage gate with no checked item.
- [x] Add deterministic render test asserting `# 问题域分析`, all DEFINE required headings, `mindmap`, `证据等级`, `验证动作`, `验证状态`, `stage_action.target_stage_id == "DIVERGE"`, and contract validation.
- [x] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected before implementation: fail because `IdeaDefineArtifactData` is not implemented.

### Task 2: Write Failing Runtime Tests

- [x] Import `VALID_IDEA_DEFINE_ARTIFACT_DATA` into `test_agent_runtime.py`.
- [x] Add parse test proving `artifact_data` renders to a DEFINE artifact.
- [x] Add structured instruction test proving the prompt requests problem-domain data fields without asking for `artifact_update`.
- [x] Add retry prompt test proving validation errors request data repair, not Markdown rewrite.
- [x] Add DeepSeek raw JSON streaming test proving final output contains rendered DEFINE artifact and system prompt contains DEFINE schema terms.

### Task 3: Implement Schema And Renderer

- [x] Add DEFINE Pydantic classes near the other artifact data models.
- [x] Validate unique evidence IDs, unique problem IDs, fit evidence references, root problem coverage, and checked stage gate.
- [x] Add `("IDEA_BRAINSTORM", "DEFINE")` dispatch in `render_agent_turn_from_artifact_data()`.
- [x] Render all required headings, Markdown tables, Mermaid `mindmap`, and stage gate deterministically.
- [x] Use existing escaping/table helpers and add only minimal DEFINE-specific helper code if needed.

### Task 4: Wire Runtime Instruction

- [x] Add `IDEA_DEFINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`.
- [x] Add `("IDEA_BRAINSTORM", "DEFINE")` to `supports_artifact_data_rendering()`.
- [x] Add DEFINE branch to `build_structured_output_instruction()`.
- [x] Ensure retry prompt continues to use the shared artifact_data repair path.

### Task 5: Update Todo And Verify

- [x] Update DeepSeek todo current progress with the `IDEA_BRAINSTORM/DEFINE` completed slice.
- [x] Run focused renderer/runtime tests.
- [x] Run expanded backend contract/API/SSE tests because runtime and artifact contract behavior changed.
- [x] Run `py_compile` and diff checks.
- [x] Commit with `feat: 支持 DeepSeek 创意问题域结构化产物数据`.
