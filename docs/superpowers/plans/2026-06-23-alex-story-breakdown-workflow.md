# Alex Story Breakdown Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Alex `story-breakdown` 从 plan 卡片升级为共享 Agent Runtime 上的在线 `STORY_BREAKDOWN` workflow。

**Architecture:** 使用 `tools/new-agents/workflow_manifest.json` 作为 workflow 单一配置入口，前端 `WORKFLOWS` 继续由 manifest 派生。后端增加 `StoryBreakdownArtifactData` 和确定性 renderer，但仍通过共享 `AgentTurnOutput`、artifact contract、typed SSE 和 persistence 交付。

**Tech Stack:** Python 3.11、Pydantic、Flask/PydanticAI shared Agent Runtime、React 19、TypeScript 5.x、Vitest、pytest。

---

## File Structure

- Modify `tools/new-agents/workflow_manifest.json`: 新增 `STORY_BREAKDOWN` workflow、listing、onboarding、4 个 stages、artifact/visual contract。
- Modify `tools/new-agents/frontend/src/core/types.ts`: 扩展 `WorkflowType`。
- Modify `tools/new-agents/frontend/src/core/workflows.ts`: 注册 `story_breakdown.*` prompt/template。
- Create `tools/new-agents/frontend/src/core/prompts/story_breakdown/input_analysis.ts`
- Create `tools/new-agents/frontend/src/core/prompts/story_breakdown/epic_mapping.ts`
- Create `tools/new-agents/frontend/src/core/prompts/story_breakdown/story_writing.ts`
- Create `tools/new-agents/frontend/src/core/prompts/story_breakdown/sprint_slicing.ts`
- Modify `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`: 删除 `story-breakdown` plan 卡片，避免在线卡片重复。
- Modify `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`: 增加在线 workflow 验收。
- Modify `tools/new-agents/backend/agent_contracts.py`: 增加 stage order、required headings、structured visual contract。
- Modify `tools/new-agents/backend/agent_runtime.py`: 增加 readiness stages 和 structured output instruction。
- Modify `tools/new-agents/backend/artifact_data_renderers.py`: 增加 Pydantic schema、校验器、renderer、dispatch。
- Modify `tools/new-agents/backend/tests/test_workflow_contract_sync.py`: 增加 frontend prompt file 映射。
- Modify `tools/new-agents/backend/tests/test_artifact_data_renderers.py`: 增加 valid fixture、负例、确定性渲染测试。
- Modify `tools/new-agents/backend/tests/test_agent_runtime.py`: 增加 parse 和 instruction 测试。
- Modify `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`: 标记 E13 已消化。
- Modify `docs/todos/refactor/README.md`: 更新当前入口摘要。

## Task 1: RED Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Add frontend workflow test**

Add a Vitest case expecting `WORKFLOWS.STORY_BREAKDOWN`, slug `story-breakdown`, agent `alex`, stages `INPUT_ANALYSIS`, `EPIC_MAPPING`, `STORY_WRITING`, `SPRINT_SLICING`, online card link `/workspace/alex/story-breakdown`, and no duplicate non-runtime `story-breakdown` card.

- [ ] **Step 2: Add backend sync test mapping**

Add `FRONTEND_PROMPT_FILES` entries for:
- `("STORY_BREAKDOWN", "INPUT_ANALYSIS")`
- `("STORY_BREAKDOWN", "EPIC_MAPPING")`
- `("STORY_BREAKDOWN", "STORY_WRITING")`
- `("STORY_BREAKDOWN", "SPRINT_SLICING")`

- [ ] **Step 3: Add renderer fixture and tests**

Add `VALID_STORY_BREAKDOWN_ARTIFACT_DATA` with one Epic, two Stories, two AC rows, one dependency, one Sprint slice, one handoff input, and checked stage gate. Add tests that unknown Epic/Story references raise `ValidationError`, and `SPRINT_SLICING` renders Markdown containing `# Sprint 切片计划` and `priority-board`.

- [ ] **Step 4: Add runtime tests**

Add tests that `parse_agent_turn_output_text(... workflow_id="STORY_BREAKDOWN", current_stage_id="SPRINT_SLICING")` renders artifact_data, and `build_structured_output_instruction("STORY_BREAKDOWN", "STORY_WRITING")` includes `artifact_data`, `stories`, `acceptance_criteria`, and excludes `artifact_update.markdown`.

- [ ] **Step 5: Run RED checks**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_story_breakdown_artifact_data_is_deterministic_and_contract_valid tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_story_breakdown_artifact_data tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_shared_workflow_manifest_stage_keys_match_frontend_prompt_templates -q
```

Expected: fail because `StoryBreakdownArtifactData` / `STORY_BREAKDOWN` is not implemented.

Run frontend test if dependencies are available:

```bash
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
```

Expected: fail because `WORKFLOWS.STORY_BREAKDOWN` is missing or duplicate card state is wrong.

## Task 2: Shared Workflow Config

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/*.ts`

- [ ] **Step 1: Add manifest workflow**

Add `STORY_BREAKDOWN` with `agentId: "alex"`, `slug: "story-breakdown"`, listing preview, onboarding starter prompts, and four stages.

- [ ] **Step 2: Add prompt files**

Create four prompt/template files. Each template must be longer than 100 chars and include `ai4se-visual` examples for stages with structured visual contracts using `${FENCE}`.

- [ ] **Step 3: Register frontend workflow**

Add `STORY_BREAKDOWN` to `WorkflowType`, import prompt modules in `workflows.ts`, and add template id mappings for `story_breakdown.input_analysis`, `story_breakdown.epic_mapping`, `story_breakdown.story_writing`, `story_breakdown.sprint_slicing`.

- [ ] **Step 4: Remove plan card**

Remove the hard-coded `story-breakdown` entry from `NON_RUNTIME_AGENT_WORKFLOWS`; the online card will now be derived from `WORKFLOWS`.

## Task 3: Backend Contract And Renderer

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] **Step 1: Add backend contract**

Add `STORY_BREAKDOWN` stage order, required headings for all stages, and structured visuals:
- `EPIC_MAPPING`: `roadmap`
- `STORY_WRITING`: `traceability-matrix`
- `SPRINT_SLICING`: `priority-board`

- [ ] **Step 2: Add artifact_data models**

Add strict Pydantic models for input insights, epics, stories, AC, dependencies, sprint slices, handoff inputs, and `StoryBreakdownArtifactData`.

- [ ] **Step 3: Add cross-field validation**

Validate unique IDs and references:
- stories reference known epics
- AC reference known stories
- dependencies reference known stories and are not self-dependencies
- sprint slices and handoff inputs reference known stories
- stage gate includes checked item

- [ ] **Step 4: Add deterministic renderer**

Add `render_story_breakdown_markdown(data, stage_id)` and helpers to render current-stage headings, Markdown tables, and required `ai4se-visual` JSON.

- [ ] **Step 5: Add runtime readiness**

Add all four stages to `ARTIFACT_DATA_READY_STAGES`. Add `STORY_BREAKDOWN_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION`, and return it from `build_structured_output_instruction()` for `STORY_BREAKDOWN` stages.

## Task 4: Verification And Documentation

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update todo records**

Mark E13 as consumed with a Goal Mode record explaining that `STORY_BREAKDOWN` now uses shared runtime, manifest, artifact contract, DeepSeek artifact_data readiness, deterministic renderer, and frontend/backend tests.

- [ ] **Step 2: Run backend verification**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py -q
```

Expected: all pass.

- [ ] **Step 3: Run frontend verification**

Run:

```bash
cd tools/new-agents/frontend && corepack pnpm test src/core/config/__tests__/workflows.test.ts
cd tools/new-agents/frontend && corepack pnpm run lint
```

Expected: all pass.

- [ ] **Step 4: Run final checks**

Run:

```bash
python3 -m json.tool tools/new-agents/workflow_manifest.json
git diff --check
git status --short
```

Expected: JSON parses, diff check has no output, status contains only this milestone files.

- [ ] **Step 5: Commit**

Stage only this milestone files and commit:

```bash
git commit -m "feat(new-agents): 上线 Alex 用户故事拆解 workflow"
```
