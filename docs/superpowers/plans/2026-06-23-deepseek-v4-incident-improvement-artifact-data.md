# DeepSeek V4 INCIDENT_REVIEW/IMPROVEMENT Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend `artifact_data` schema, deterministic renderer, Agent Runtime wiring, tests, and todo updates for `INCIDENT_REVIEW/IMPROVEMENT`.

**Architecture:** Keep the shared New Agents runtime and artifact renderer registry. DeepSeek emits JSON business data only; backend Pydantic models validate references and deterministic renderer produces the Markdown/Mermaid/ai4se-visual artifact consumed by the existing contract, typed SSE, and persistence pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend contracts.

---

## File Structure

- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add IMPROVEMENT data models, dispatch branch, renderer helpers, Mermaid `pie`, and `ai4se-visual action-board`.
- Modify `tools/new-agents/backend/agent_runtime.py`: add IMPROVEMENT structured output instruction and include `INCIDENT_REVIEW/IMPROVEMENT` in artifact_data capability registry.
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add valid fixture, validation negative cases, deterministic contract-valid renderer test.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add parsing, instruction, retry, and raw DeepSeek streaming tests for IMPROVEMENT.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed IMPROVEMENT slice and remaining work.

## Tasks

### Task 1: Write Failing Renderer Tests

- [x] Add `IncidentImprovementArtifactData` import and `VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA` fixture.
- [x] Add negative tests for duplicate `action_id`, inconsistent `report_info.action_count`, inconsistent priority distribution, unknown coverage action IDs, unknown action root-cause references, and covered root causes without action IDs.
- [x] Add deterministic render test asserting the full final-report heading set, `pie title 改进措施优先级分布`, `"type": "action-board"`, all required contract keywords, `stage_action is None`, and contract validation.
- [x] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected before implementation: fail because `IncidentImprovementArtifactData` is not implemented.

### Task 2: Write Failing Runtime Tests

- [x] Import `VALID_INCIDENT_IMPROVEMENT_ARTIFACT_DATA` into `test_agent_runtime.py`.
- [x] Add parse test proving `artifact_data` renders to an IMPROVEMENT artifact.
- [x] Add structured instruction test proving the prompt requests final improvement report data fields without asking for `artifact_update`.
- [x] Add retry prompt test proving validation errors request data repair, not Markdown rewrite.
- [x] Add DeepSeek raw JSON streaming test proving final output contains rendered IMPROVEMENT artifact and system prompt contains IMPROVEMENT schema terms.

### Task 3: Implement Schema And Renderer

- [x] Add IMPROVEMENT Pydantic classes near the other Incident Review artifact data models.
- [x] Validate action count, unique action IDs, priority distribution, coverage action references, action root-cause references, and covered causes with action IDs.
- [x] Add `("INCIDENT_REVIEW", "IMPROVEMENT")` dispatch in `render_agent_turn_from_artifact_data()`.
- [x] Render all required headings, Markdown tables, Mermaid `pie`, `ai4se-visual action-board`, and final stage gate deterministically.
- [x] Use existing escaping/table helpers and add only minimal IMPROVEMENT-specific helper code if needed.

### Task 4: Wire Runtime Instruction

- [x] Add `INCIDENT_IMPROVEMENT_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`.
- [x] Add `("INCIDENT_REVIEW", "IMPROVEMENT")` to `supports_artifact_data_rendering()`.
- [x] Add IMPROVEMENT branch to `build_structured_output_instruction()`.
- [x] Ensure retry prompt continues to use the shared artifact_data repair path.

### Task 5: Update Todo And Verify

- [x] Update DeepSeek todo current progress with the `INCIDENT_REVIEW/IMPROVEMENT` completed slice.
- [x] Run focused renderer/runtime tests.
- [x] Run expanded backend contract/API/SSE tests because runtime and artifact contract behavior changed.
- [x] Run `py_compile` and diff checks.
- [x] Commit with `feat: 支持 DeepSeek 故障改进报告结构化产物数据`.
