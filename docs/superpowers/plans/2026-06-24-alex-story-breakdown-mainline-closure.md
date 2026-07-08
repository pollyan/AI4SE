# Alex 用户故事拆解 Workflow 主线化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Alex `story-breakdown` 从计划卡片升级为当前主线可运行的共享 Agent Runtime workflow。

**Current Baseline:** 本计划在隔离 worktree `.worktrees/alex-story-breakdown-goal-current` 执行，分支为 `codex/alex-story-breakdown-goal-current`，基线为 `e35c9643 docs(goal): 明确 Superpowers 头脑风暴细化规则`。主工作区存在既有未提交改动，本轮不触碰。实现移植前已用 Node 只读验收检查确认当前 manifest 缺 `STORY_BREAKDOWN` 并得到预期失败。

**Architecture:** 以 `workflow_manifest.json` 为共享 workflow 配置入口，同步前端 `WORKFLOWS`、prompt registry、后端 `WORKFLOW_STAGES`、artifact contract、renderer 和 handoff。所有运行继续走共享 `/api/agent/runs/stream`、typed SSE、artifact persistence 和共享 UI，不新增 Alex 专属 runtime、API path、store 或 renderer。

**Tech Stack:** Python 3.11, Flask/Pydantic/Pytest, React/TypeScript/Vitest, New Agents shared workflow manifest.

---

## 文件结构

- Create: `docs/superpowers/specs/2026-06-24-alex-story-breakdown-mainline-closure-design.md`
- Create: `docs/superpowers/plans/2026-06-24-alex-story-breakdown-mainline-closure.md`
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/input_analysis.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/epic_mapping.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/story_backlog.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/sprint_plan.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`

## Task 1: RED - 写当前主线缺失 workflow 的验收测试

- [x] **Step 1: Add frontend workflow RED**

Update `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts` with assertions that:

- `WORKFLOWS.STORY_BREAKDOWN` exists.
- `WORKFLOWS.STORY_BREAKDOWN.agentId === "alex"`.
- `WORKFLOWS.STORY_BREAKDOWN.stages` has `INPUT_ANALYSIS`, `EPIC_MAPPING`, `STORY_BACKLOG`, `SPRINT_PLAN`.
- Alex workflow listing exposes `story-breakdown` as online with `/workspace/alex/story-breakdown`.

- [x] **Step 2: Add backend sync RED**

Update `tools/new-agents/backend/tests/test_workflow_contract_sync.py` with `STORY_BREAKDOWN` stage and contract sync expectations:

- manifest stages match backend `WORKFLOW_STAGES`.
- manifest prompt templates are registered.
- manifest required headings match backend contract.
- final stage handoff includes Lisa `TEST_DESIGN/CLARIFY` and `REQ_REVIEW/REVIEW`.

- [x] **Step 3: Add runtime / renderer RED**

Update `tools/new-agents/backend/tests/test_artifact_data_renderers.py` and `tools/new-agents/backend/tests/test_agent_runtime.py` with a valid `STORY_BREAKDOWN` fixture. Assert `parse_agent_turn_output_text()` renders artifact Markdown with `# 用户故事拆解包` and passes `validate_agent_turn()`.

- [x] **Step 4: Add handoff RED**

Update `tools/new-agents/backend/tests/test_workflow_handoffs.py` with a Story Breakdown final-stage run. Assert available handoffs target Lisa `TEST_DESIGN/CLARIFY` and `REQ_REVIEW/REVIEW`, and generated prompt includes `STORY_BREAKDOWN/SPRINT_PLAN`.

- [x] **Step 5: Run RED**

```bash
node -e "const fs=require('fs'); const m=JSON.parse(fs.readFileSync('tools/new-agents/workflow_manifest.json','utf8')); if (!m.workflows.STORY_BREAKDOWN) throw new Error('STORY_BREAKDOWN missing from workflow manifest')"
```

Expected: FAIL with `STORY_BREAKDOWN missing from workflow manifest`, because current `master` does not register `STORY_BREAKDOWN` as runtime workflow.

## Task 2: GREEN - 同步共享 workflow 和 prompt 配置

- [x] **Step 1: Add manifest workflow**

Update `tools/new-agents/workflow_manifest.json` with `STORY_BREAKDOWN`, slug `story-breakdown`, agent `alex`, four stages, artifact contract, visual contract, onboarding, starter prompts and final-stage handoff entries.

- [x] **Step 2: Add frontend workflow config**

Update:

- `tools/new-agents/frontend/src/core/workflows.ts`
- `tools/new-agents/frontend/src/core/types.ts`
- `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`

`story-breakdown` must move from plan card to online workflow entry.

- [x] **Step 3: Add prompt templates**

Create:

- `tools/new-agents/frontend/src/core/prompts/story_breakdown/input_analysis.ts`
- `tools/new-agents/frontend/src/core/prompts/story_breakdown/epic_mapping.ts`
- `tools/new-agents/frontend/src/core/prompts/story_breakdown/story_backlog.ts`
- `tools/new-agents/frontend/src/core/prompts/story_breakdown/sprint_plan.ts`

Register these templates in `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`.

## Task 3: GREEN - 同步后端 contract、renderer 和 handoff

- [x] **Step 1: Add backend stage and artifact contract**

Update `tools/new-agents/backend/agent_contracts.py` with:

- `WORKFLOW_STAGES["STORY_BREAKDOWN"] = ["INPUT_ANALYSIS", "EPIC_MAPPING", "STORY_BACKLOG", "SPRINT_PLAN"]`
- required headings for all four stages
- required Mermaid / structured visual requirements for stages that render visuals

- [x] **Step 2: Add structured output instructions**

Update `tools/new-agents/backend/agent_runtime.py` so `STORY_BREAKDOWN` stages receive `artifact_data` instructions and continue through the shared raw JSON runtime path.

- [x] **Step 3: Add deterministic renderer**

Update `tools/new-agents/backend/artifact_data_renderers.py` so valid Story Breakdown `artifact_data` renders deterministic Markdown, Mermaid and `ai4se-visual` blocks.

- [x] **Step 4: Add handoff support**

Update handoff configuration or prompt behavior so final Story Breakdown artifacts can be handed to Lisa `TEST_DESIGN/CLARIFY` and `REQ_REVIEW/REVIEW`.

## Task 4: 验证、文档和提交

- [x] **Step 1: Run focused backend verification**

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected: PASS.

- [x] **Step 2: Run focused frontend verification**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: PASS.

- [x] **Step 3: Run syntax and diff hygiene checks**

```bash
python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/workflow_handoffs.py
git diff --check
```

Expected: PASS.

- [x] **Step 4: Update todo records**

Update `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` and `docs/todos/refactor/README.md`:

- Record E13 as completed in this branch.
- Keep E03, E04, E14 and mainline coordination items as next candidates.
- Do not claim unrelated feature branches are complete on `master`.

- [ ] **Step 5: Commit**

```bash
git status --short
git add docs/superpowers/specs/2026-06-24-alex-story-breakdown-mainline-closure-design.md \
  docs/superpowers/plans/2026-06-24-alex-story-breakdown-mainline-closure.md \
  docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md \
  docs/todos/refactor/README.md \
  tools/new-agents/workflow_manifest.json \
  tools/new-agents/backend/agent_contracts.py \
  tools/new-agents/backend/agent_runtime.py \
  tools/new-agents/backend/artifact_data_renderers.py \
  tools/new-agents/backend/tests/test_agent_contracts.py \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/backend/tests/test_artifact_data_renderers.py \
  tools/new-agents/backend/tests/test_workflow_contract_sync.py \
  tools/new-agents/backend/tests/test_workflow_handoffs.py \
  tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts \
  tools/new-agents/frontend/src/core/config/agentWorkflows.ts \
  tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts \
  tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts \
  tools/new-agents/frontend/src/core/prompts/story_breakdown/input_analysis.ts \
  tools/new-agents/frontend/src/core/prompts/story_breakdown/epic_mapping.ts \
  tools/new-agents/frontend/src/core/prompts/story_breakdown/story_backlog.ts \
  tools/new-agents/frontend/src/core/prompts/story_breakdown/sprint_plan.ts \
  tools/new-agents/frontend/src/core/types.ts \
  tools/new-agents/frontend/src/core/workflows.ts
git commit -m "feat(new-agents): 上线 Alex 用户故事拆解 workflow"
```

Expected: focused commit on isolated worktree.

## Plan Self-Review

- Spec coverage: 覆盖 workflow 入口、manifest、prompt、backend contract、renderer、runtime、handoff、验证和 todo 更新。
- Placeholder scan: no `TBD`, `TODO`, or unresolved placeholders.
- Type consistency: workflow id `STORY_BREAKDOWN`; slug `story-breakdown`; stages `INPUT_ANALYSIS`, `EPIC_MAPPING`, `STORY_BACKLOG`, `SPRINT_PLAN`.
