# Alex Story Breakdown Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote Alex `story-breakdown` from a plan card to a shared Agent Runtime workflow that generates a deterministic user story package and can hand off to Lisa.

**Status 2026-06-23:** Completed. `STORY_BREAKDOWN/BACKLOG` is implemented as an online shared Agent Runtime workflow with deterministic `artifact_data` rendering, `story-map` visual contract, and Lisa handoffs to `TEST_DESIGN/CLARIFY` and `REQ_REVIEW/REVIEW`.

**Architecture:** Add `STORY_BREAKDOWN/BACKLOG` to the existing workflow manifest, frontend workflow registry, backend contracts, prompt registry, artifact_data schema/renderer, and handoff configuration. Keep the existing `/api/agent/runs/stream`, typed SSE, run persistence, artifact contract validation, and shared UI.

**Tech Stack:** Python 3.11, Pydantic v2, Flask tests, React/TypeScript, Vitest, shared JSON workflow manifest.

---

### Task 1: Shared Workflow Contract RED

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

- [ ] **Step 1: Write failing sync tests**

Add expected prompt file:

```python
("STORY_BREAKDOWN", "BACKLOG"): (
    NEW_AGENTS_ROOT / "frontend" / "src" / "core" / "prompts" / "story_breakdown" / "backlog.ts"
),
```

Add handoff expectation:

```python
("STORY_BREAKDOWN", "BACKLOG", "TEST_DESIGN", "CLARIFY"),
("STORY_BREAKDOWN", "BACKLOG", "REQ_REVIEW", "REVIEW"),
```

Add contract test assertions:

```python
story_fields = REQUIRED_ARTIFACT_HEADINGS[("STORY_BREAKDOWN", "BACKLOG")]
assert "# 用户故事拆解包" in story_fields
assert "## User Story Backlog" in story_fields
assert REQUIRED_ARTIFACT_MERMAID_DIAGRAMS[("STORY_BREAKDOWN", "BACKLOG")] == ["flowchart"]
assert REQUIRED_ARTIFACT_STRUCTURED_VISUALS[("STORY_BREAKDOWN", "BACKLOG")] == ["story-map"]
```

Add frontend workflow test:

```typescript
const wf = WORKFLOWS.STORY_BREAKDOWN;
expect(wf.agentId).toBe('alex');
expect(wf.slug).toBe('story-breakdown');
expect(wf.stages.map(stage => stage.id)).toEqual(['BACKLOG']);
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py::test_required_artifact_headings_cover_every_known_workflow_stage -q
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts
```

Expected: FAIL because `STORY_BREAKDOWN` is not configured.

### Task 2: Manifest, Frontend Registry, Backend Contract GREEN

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/backlog.ts`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

- [ ] **Step 1: Add minimal config**

Add `STORY_BREAKDOWN` to `WorkflowType`, `workflow_manifest.json`, `WORKFLOW_STAGES`, required headings, required Mermaid diagrams, required structured visual contract, and `STAGE_CONTENT_BY_TEMPLATE_ID`.

Prompt file exports:

```typescript
export const BACKLOG_PROMPT = `...`;
export const BACKLOG_TEMPLATE = `...`;
```

Prompt/template must require Story Breakdown output and mention Epic、User Story、AC、依赖、Sprint 切片、Lisa Handoff 输入.

- [ ] **Step 2: Run sync tests**

Run the commands from Task 1 again.

Expected: PASS for sync/config coverage.

### Task 3: Deterministic artifact_data Renderer RED/GREEN

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: Write failing renderer/runtime tests**

Add a sample `STORY_BACKLOG_ARTIFACT_DATA` fixture with one epic, two stories, AC rows, dependency/risk, sprint slice, Lisa handoff input, and checked stage gate.

Assert:

```python
turn = render_agent_turn_from_artifact_data(
    {"chat": "已完成用户故事拆解。", "artifact_data": STORY_BACKLOG_ARTIFACT_DATA},
    workflow_id="STORY_BREAKDOWN",
    current_stage_id="BACKLOG",
)
assert "# 用户故事拆解包" in turn.artifact_update.markdown
assert "```mermaid" in turn.artifact_update.markdown
assert '"type": "story-map"' in turn.artifact_update.markdown
```

Add invalid reference test:

```python
invalid = copy.deepcopy(STORY_BACKLOG_ARTIFACT_DATA)
invalid["acceptance_criteria"][0]["story_id"] = "US-404"
with pytest.raises(ValidationError):
    render_agent_turn_from_artifact_data(...)
```

Add runtime instruction test:

```python
instruction = build_structured_output_instruction("STORY_BREAKDOWN", "BACKLOG")
assert "artifact_data" in instruction
assert "不要输出完整 Markdown" in instruction
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_story_breakdown_backlog_artifact_data_renders_story_package tools/new-agents/backend/tests/test_agent_runtime.py::test_story_breakdown_backlog_structured_output_instruction_requests_artifact_data -q
```

Expected: FAIL because renderer/instruction is not configured.

- [ ] **Step 3: Implement schema, renderer, instruction**

Add Pydantic models for Story Breakdown artifact data, render Markdown with required headings, Mermaid flowchart, `ai4se-visual` `story-map`, and stage gate. Add `("STORY_BREAKDOWN", "BACKLOG")` to `supports_artifact_data_rendering()` and `build_structured_output_instruction()`.

- [ ] **Step 4: Run renderer/runtime tests**

Run the command from Step 2.

Expected: PASS.

### Task 4: Handoff RED/GREEN

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [ ] **Step 1: Write failing handoff test**

Persist a `STORY_BREAKDOWN/BACKLOG` artifact and assert:

```python
result = export_run_handoffs(run.id)
targets = {(item["targetWorkflowId"], item["targetStageId"]) for item in result["handoffs"]}
assert targets == {("TEST_DESIGN", "CLARIFY"), ("REQ_REVIEW", "REVIEW")}
assert "STORY_BREAKDOWN/BACKLOG" in result["handoffs"][0]["prompt"]
```

- [ ] **Step 2: Run to verify RED**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py::test_story_breakdown_backlog_exports_lisa_handoffs -q
```

Expected: FAIL because handoff manifest entries do not exist.

- [ ] **Step 3: Add manifest handoffs**

Add two handoffs from `STORY_BREAKDOWN/BACKLOG` to Lisa `TEST_DESIGN/CLARIFY` and `REQ_REVIEW/REVIEW` using existing `source-artifact-handoff`.

- [ ] **Step 4: Run handoff tests**

Run handoff and sync tests.

Expected: PASS.

### Task 5: Docs, Full Focused Verification, Commit

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`
- Create: `docs/superpowers/specs/2026-06-23-alex-story-breakdown-workflow-design.md`
- Create: `docs/superpowers/plans/2026-06-23-alex-story-breakdown-workflow.md`

- [ ] **Step 1: Update todo**

Mark E13 as consumed and note the single-stage `STORY_BREAKDOWN/BACKLOG` scope, deterministic `artifact_data` renderer, and Lisa handoff support.

- [ ] **Step 2: Run focused verification**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts src/core/__tests__/llm.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all pass.

- [ ] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-alex-story-breakdown-workflow-design.md docs/superpowers/plans/2026-06-23-alex-story-breakdown-workflow.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents/workflow_manifest.json tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/workflows.ts tools/new-agents/frontend/src/core/prompts/story_breakdown/backlog.ts tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts
git commit -m "feat: 上线 Alex 用户故事拆解 workflow"
```

Expected: focused commit created on `codex/alex-story-breakdown-workflow`.
