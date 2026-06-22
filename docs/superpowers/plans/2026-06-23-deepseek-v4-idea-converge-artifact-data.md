# DeepSeek V4 IDEA_BRAINSTORM/CONVERGE Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backend `artifact_data` schema, deterministic renderer, Agent Runtime wiring, tests, and todo updates for `IDEA_BRAINSTORM/CONVERGE`.

**Architecture:** Keep the shared New Agents runtime and artifact renderer registry. DeepSeek emits JSON business data only; backend Pydantic models validate references and scoring consistency, then a deterministic renderer produces the Markdown/Mermaid artifact consumed by the existing contract, typed SSE, and persistence pipeline.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, existing New Agents backend contracts and manifest sync tests.

---

## File Structure

- Modify `tools/new-agents/backend/artifact_data_renderers.py`: add CONVERGE data models, dispatch branch, renderer helpers, and Mermaid `quadrantChart`.
- Modify `tools/new-agents/backend/agent_runtime.py`: add CONVERGE structured output instruction and include `IDEA_BRAINSTORM/CONVERGE` in artifact_data capability registry.
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: add valid fixture, validation negative cases, deterministic contract-valid renderer test.
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: add parsing, instruction, retry, and raw DeepSeek streaming tests for CONVERGE.
- Modify `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record the completed CONVERGE slice and remaining IDEA_BRAINSTORM work.

## Tasks

### Task 1: Write Failing Renderer Tests

- [x] Add `IdeaConvergeArtifactData` import and `VALID_IDEA_CONVERGE_ARTIFACT_DATA` fixture.
- [x] Add negative tests for duplicate idea IDs, duplicate ranks, invalid ICE score, unknown recommended idea, unknown validation experiment idea reference, unknown merge path idea reference, no recommended idea, and stage gate with no checked item.
- [x] Add deterministic render test asserting `# 收敛聚焦`, all CONVERGE required headings, `quadrantChart`, `评分口径`, `影响力`, `信心`, `实现难度`, `ICE得分`, `淘汰理由`, `推荐方案`, `下一步验证`, `合并逻辑`, `证据来源`, `用户确认状态`, `stage_action.target_stage_id == "CONCEPT"`, and contract validation.
- [x] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected before implementation: fail because `IdeaConvergeArtifactData` is not implemented.

### Task 2: Write Failing Runtime Tests

- [x] Import `VALID_IDEA_CONVERGE_ARTIFACT_DATA` into `test_agent_runtime.py`.
- [x] Add parse test proving `artifact_data` renders to a CONVERGE artifact.
- [x] Add structured instruction test proving the prompt requests convergence data fields without asking for `artifact_update`.
- [x] Add retry prompt test proving validation errors request data repair, not Markdown rewrite.
- [x] Add DeepSeek raw JSON streaming test proving final output contains rendered CONVERGE artifact and system prompt contains CONVERGE schema terms.

### Task 3: Implement Schema And Renderer

- [x] Add CONVERGE Pydantic classes near the other IDEA artifact data models.
- [x] Validate unique idea IDs, unique ranks, ICE score consistency, recommended idea existence, validation/merge references, at least one recommended item, and checked stage gate.
- [x] Add `("IDEA_BRAINSTORM", "CONVERGE")` dispatch in `render_agent_turn_from_artifact_data()`.
- [x] Render all required headings, Markdown tables, Mermaid `quadrantChart`, and stage gate deterministically.
- [x] Reuse existing escaping/table helpers and avoid agent-specific runtime or renderer infrastructure.

### Task 4: Wire Runtime Instruction

- [x] Add `IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`.
- [x] Add `("IDEA_BRAINSTORM", "CONVERGE")` to `supports_artifact_data_rendering()`.
- [x] Add CONVERGE branch to `build_structured_output_instruction()`.
- [x] Ensure retry prompt continues to use the shared artifact_data repair path.

### Task 5: Update Todo And Verify

- [x] Update DeepSeek todo current progress with the `IDEA_BRAINSTORM/CONVERGE` completed slice.
- [x] Run focused renderer/runtime/contract tests.
- [x] Run expanded backend contract/API/SSE/workflow tests because runtime and artifact/visual contract behavior changed.
- [x] Run `py_compile` and diff checks.
- [x] Commit with `feat: 支持 DeepSeek 创意收敛结构化产物数据`.
