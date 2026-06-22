# DeepSeek V4 INCIDENT_REVIEW/ROOT_CAUSE Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend `artifact_data` schema, deterministic renderer, Agent Runtime wiring, tests, and todo updates for `INCIDENT_REVIEW/ROOT_CAUSE`.

**Architecture:** Keep the shared New Agents runtime and artifact renderer registry. DeepSeek emits JSON business data only; backend Pydantic models validate references and deterministic renderer produces the Markdown/Mermaid/ai4se-visual artifact consumed by the existing contract, typed SSE, and persistence pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend contracts.

---

## File Structure

- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add ROOT_CAUSE data models, dispatch branch, renderer helpers, and Mermaid/visual escaping where needed.
- Modify `tools/new-agents/backend/agent_runtime.py`: add ROOT_CAUSE structured output instruction and include `INCIDENT_REVIEW/ROOT_CAUSE` in artifact_data capability registry.
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add valid fixture, validation negative cases, deterministic contract-valid renderer test.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add parsing, instruction, retry, and raw DeepSeek streaming tests for ROOT_CAUSE.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed ROOT_CAUSE slice and remaining work.

## Tasks

### Task 1: Write Failing Renderer Tests

- [x] Add `IncidentRootCauseArtifactData` import and `VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA` fixture.
- [x] Add negative tests for fewer than 3 Why rows, duplicate `cause_id`, unknown `fishbone_categories.cause_ids`, unknown `root_cause_conclusions.related_cause_id`, and missing root-cause conclusion.
- [x] Add deterministic render test asserting `# 故障复盘报告`, all `6.x` headings, `mindmap`, `"type": "cause-map"`, `证据强度`, `置信度`, `可行动性`, `stage_action.target_stage_id == "IMPROVEMENT"`, and contract validation.
- [x] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Observed before implementation: fail because `IncidentRootCauseArtifactData` is not implemented.

### Task 2: Write Failing Runtime Tests

- [x] Import `VALID_INCIDENT_ROOT_CAUSE_ARTIFACT_DATA` into `test_agent_runtime.py`.
- [x] Add parse test proving `artifact_data` renders to a ROOT_CAUSE artifact.
- [x] Add structured instruction test proving the prompt requests root cause data fields without asking for `artifact_update`.
- [x] Add retry prompt test proving validation errors request data repair, not Markdown rewrite.
- [x] Add DeepSeek raw JSON streaming test proving final output contains rendered ROOT_CAUSE artifact and system prompt contains ROOT_CAUSE schema terms.

### Task 3: Implement Schema And Renderer

- [x] Add ROOT_CAUSE Pydantic classes near the other artifact data models.
- [x] Validate Why depth, unique cause IDs, fishbone references, conclusion references, and root-cause conclusion presence.
- [x] Add `("INCIDENT_REVIEW", "ROOT_CAUSE")` dispatch in `render_agent_turn_from_artifact_data()`.
- [x] Render all required headings, Markdown tables, `ai4se-visual cause-map`, and Mermaid `mindmap` deterministically.
- [x] Use existing escaping/table helpers and add only minimal ROOT_CAUSE-specific escaping helpers if needed.

### Task 4: Wire Runtime Instruction

- [x] Add `INCIDENT_ROOT_CAUSE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`.
- [x] Add `("INCIDENT_REVIEW", "ROOT_CAUSE")` to `supports_artifact_data_rendering()`.
- [x] Add ROOT_CAUSE branch to `build_structured_output_instruction()`.
- [x] Ensure retry prompt continues to use the shared artifact_data repair path.

### Task 5: Update Todo And Verify

- [x] Update DeepSeek todo current progress with the `INCIDENT_REVIEW/ROOT_CAUSE` completed slice.
- [x] Run focused renderer/runtime tests.
- [x] Run expanded backend contract/API/SSE tests because runtime and artifact contract behavior changed.
- [x] Run `py_compile` and diff checks.
- [x] Commit with `feat: 支持 DeepSeek 故障根因结构化产物数据`.
