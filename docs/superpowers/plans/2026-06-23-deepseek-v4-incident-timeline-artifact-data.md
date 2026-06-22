# DeepSeek V4 INCIDENT_REVIEW/TIMELINE Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend `artifact_data` schema, deterministic renderer, Agent Runtime wiring, tests, and todo updates for `INCIDENT_REVIEW/TIMELINE`.

**Architecture:** Keep the shared New Agents runtime and artifact renderer registry. DeepSeek emits JSON business data only; backend Pydantic models validate references and deterministic renderer produces the Markdown/Mermaid artifact consumed by the existing contract, typed SSE, and persistence pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend contracts.

---

## File Structure

- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add TIMELINE data models, dispatch branch, renderer helpers.
- Modify `tools/new-agents/backend/agent_runtime.py`: add TIMELINE structured output instruction and include `INCIDENT_REVIEW/TIMELINE` in artifact_data capability registry.
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add valid fixture, validation negative cases, deterministic contract-valid renderer test.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add parsing, instruction, retry, and raw DeepSeek streaming tests for TIMELINE.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed TIMELINE slice and remaining work.

## Tasks

### Task 1: Write Failing Renderer Tests

- [x] Add `IncidentTimelineArtifactData` import and `VALID_INCIDENT_TIMELINE_ARTIFACT_DATA` fixture.
- [x] Add negative tests for duplicate `fact_id` and timeline events referencing unknown facts.
- [x] Add deterministic render test asserting `# 故障复盘报告`, `timeline`, no `14:30 :` Mermaid time token, all required headings, and contract validation.
- [x] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Observed before implementation: fail because `IncidentTimelineArtifactData` is not implemented.

### Task 2: Write Failing Runtime Tests

- [x] Import `VALID_INCIDENT_TIMELINE_ARTIFACT_DATA` into `test_agent_runtime.py`.
- [x] Add parse test proving `artifact_data` renders to a TIMELINE artifact.
- [x] Add structured instruction test proving the prompt requests incident timeline data fields without asking for `artifact_update`.
- [x] Add retry prompt test proving validation errors request data repair, not Markdown rewrite.
- [x] Add DeepSeek raw JSON streaming test proving final output contains rendered TIMELINE artifact and system prompt contains TIMELINE schema terms.

### Task 3: Implement Schema And Renderer

- [x] Add TIMELINE Pydantic classes near the other artifact data models.
- [x] Validate unique fact IDs and timeline fact references.
- [x] Add `("INCIDENT_REVIEW", "TIMELINE")` dispatch in `render_agent_turn_from_artifact_data()`.
- [x] Render all required headings and Mermaid `timeline` deterministically.
- [x] Escape Mermaid timeline time labels by replacing half-width `:` with full-width `：`.

### Task 4: Wire Runtime Instruction

- [x] Add `INCIDENT_TIMELINE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`.
- [x] Add `("INCIDENT_REVIEW", "TIMELINE")` to `supports_artifact_data_rendering()`.
- [x] Add TIMELINE branch to `build_structured_output_instruction()`.
- [x] Ensure retry prompt continues to use the shared artifact_data repair path.

### Task 5: Update Todo And Verify

- [x] Update DeepSeek todo current progress with the INCIDENT_REVIEW/TIMELINE completed slice.
- [x] Run focused renderer/runtime tests.
- [x] Run expanded backend contract/API/SSE tests because runtime and artifact contract behavior changed.
- [x] Run `py_compile` and diff checks.
- [ ] Commit with `feat: 支持 DeepSeek 故障时间线结构化产物数据`.
