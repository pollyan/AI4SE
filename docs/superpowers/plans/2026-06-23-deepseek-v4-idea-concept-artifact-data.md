# DeepSeek V4 IDEA_BRAINSTORM/CONCEPT Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend `artifact_data` schema, deterministic renderer, Agent Runtime wiring, tests, and todo updates for `IDEA_BRAINSTORM/CONCEPT`.

**Architecture:** Keep the shared New Agents runtime and artifact renderer registry. DeepSeek emits JSON business data only; backend Pydantic models validate product concept references and completeness, then a deterministic renderer produces the Markdown/Mermaid/`ai4se-visual` artifact consumed by the existing contract, typed SSE, and persistence pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend contracts and manifest sync tests.

---

## File Structure

- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add CONCEPT data models, dispatch branch, renderer helpers, Mermaid `pie`/`flowchart`, and `ai4se-visual` `mvp-map`.
- Modify `tools/new-agents/backend/agent_runtime.py`: add CONCEPT structured output instruction and include `IDEA_BRAINSTORM/CONCEPT` in artifact_data capability registry.
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add valid fixture, validation negative cases, deterministic contract-valid renderer test.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add parsing, instruction, retry, and raw DeepSeek streaming tests for CONCEPT.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed CONCEPT slice and close the IDEA_BRAINSTORM migration gap.

## Tasks

### Task 1: Write Failing Renderer Tests

- [x] Add `IdeaConceptArtifactData` import and `VALID_IDEA_CONCEPT_ARTIFACT_DATA` fixture.
- [x] Add negative tests for duplicate assumption IDs, duplicate validation IDs, duplicate action IDs, missing Lean Canvas cells, missing growth funnel stages, unknown MVP feature assumption reference, unknown validation roadmap assumption reference, unknown next action reference, and stage gate with no checked item.
- [x] Add deterministic render test asserting `# 产品概念简报`, all CONCEPT required headings, Mermaid `pie`, Mermaid `flowchart`, `ai4se-visual` `mvp-map`, `owner`, `状态`, `stage_action is None`, and contract validation.
- [x] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected before implementation: fail because `IdeaConceptArtifactData` is not implemented.

### Task 2: Write Failing Runtime Tests

- [x] Import `VALID_IDEA_CONCEPT_ARTIFACT_DATA` into `test_agent_runtime.py`.
- [x] Add parse test proving `artifact_data` renders to a CONCEPT artifact.
- [x] Add structured instruction test proving the prompt requests concept data fields without asking for `artifact_update`.
- [x] Add retry prompt test proving validation errors request data repair, not Markdown rewrite.
- [x] Add DeepSeek raw JSON streaming test proving final output contains rendered CONCEPT artifact and system prompt contains CONCEPT schema terms.

### Task 3: Implement Schema And Renderer

- [x] Add CONCEPT Pydantic classes near the other IDEA artifact data models.
- [x] Validate unique IDs, Lean Canvas coverage, growth funnel coverage, cross references, and checked stage gate.
- [x] Add `("IDEA_BRAINSTORM", "CONCEPT")` dispatch in `render_agent_turn_from_artifact_data()`.
- [x] Render all required headings, Markdown tables, Mermaid `pie`, Mermaid `flowchart`, `ai4se-visual` `mvp-map`, and stage gate deterministically.
- [x] Reuse existing escaping/table/visual helpers and avoid agent-specific runtime or renderer infrastructure.

### Task 4: Wire Runtime Instruction

- [x] Add `IDEA_CONCEPT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`.
- [x] Add `("IDEA_BRAINSTORM", "CONCEPT")` to `supports_artifact_data_rendering()`.
- [x] Add CONCEPT branch to `build_structured_output_instruction()`.
- [x] Ensure retry prompt continues to use the shared artifact_data repair path.

### Task 5: Update Todo And Verify

- [x] Update DeepSeek todo current progress with the `IDEA_BRAINSTORM/CONCEPT` completed slice.
- [x] Run focused renderer/runtime/contract tests.
- [x] Run expanded backend contract/API/SSE/workflow tests because runtime and artifact/visual contract behavior changed.
- [x] Run `py_compile` and diff checks.
- [x] Commit with `feat: 支持 DeepSeek 创意概念结构化产物数据`.
