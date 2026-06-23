# Alex Story Breakdown Mainline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 DeepSeek 主线收口基线上上线 Alex 用户故事拆解 workflow，让用户能从 PRD/需求蓝图生成 Epic、User Story、AC、依赖风险、Sprint 切片和 Lisa handoff 输入。

**Architecture:** 新能力继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、artifact_data renderer、run/artifact persistence 和共享前端 workflow registry。Workflow 差异通过 `workflow_manifest.json`、stage prompt、Pydantic schema、deterministic renderer、handoff 配置和测试表达，不新增 Alex 专属 runtime/API/store/renderer。

**Tech Stack:** Python 3.11、Pydantic、pytest、TypeScript、Vitest、New Agents shared runtime。

---

## 文件结构

- Modify: `tools/new-agents/workflow_manifest.json`
  - 增加 `STORY_BREAKDOWN` workflow、4 个 stage、artifact/visual contract、handoff、onboarding。
- Modify: `tools/new-agents/backend/agent_contracts.py`
  - 增加 story breakdown required headings / visual contract。
- Modify: `tools/new-agents/backend/agent_runtime.py`
  - 增加 story breakdown structured output instructions 和 stage registry。
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
  - 增加 story breakdown Pydantic schema、renderer 和 `ARTIFACT_DATA_RENDERERS` 注册。
- Modify: `tools/new-agents/backend/workflow_handoffs.py`
  - 增加 `STORY_BREAKDOWN/SPRINT_PLAN` 到 Lisa workflows 的 handoff 摘要。
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
  - 覆盖 story breakdown artifact contract。
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  - 覆盖 story breakdown `artifact_data` parse/render/runtime instruction。
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
  - 覆盖 story breakdown renderer 输出和 schema 引用校验。
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
  - 覆盖 manifest/backend workflow sync。
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
  - 覆盖 Lisa handoff 输入。
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
  - 暴露 slug `story-breakdown`。
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`
  - Alex listing 使用在线 workflow，而不是 plan placeholder。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/input_analysis.ts`
  - Story breakdown 输入分析阶段 prompt/template。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/epic_mapping.ts`
  - Story breakdown Epic 映射阶段 prompt/template。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/story_backlog.ts`
  - Story breakdown Story Backlog 阶段 prompt/template。
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/sprint_plan.ts`
  - Story breakdown Sprint 计划阶段 prompt/template 和 story-map 示例。
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
  - 覆盖 frontend registry/listing。
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 补充 workflow slug/type union。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 标记 E13 已消化。
- Modify: `docs/todos/refactor/README.md`
  - 保持当前入口一致，记录 E13 已从 enhancement diagnostic 中消化。

## Task 1: Backend Workflow Contract RED/GREEN

- [x] **Step 1: Write failing backend tests**

Add tests proving `STORY_BREAKDOWN` exists in manifest/backend sync, contract requires stable headings and story-map visual, runtime instruction requests `artifact_data`, and renderer can produce a valid artifact.

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_story_breakdown_artifact_data tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_story_breakdown_artifact_data_outputs_story_package -q
```

Expected RED: unknown workflow/stage, missing renderer, missing contract headings, or missing runtime instruction.

- [x] **Step 2: Implement shared manifest/runtime/contract/renderer**

Port the existing validated story breakdown design into the current DS baseline:

- `workflow_manifest.json`: add `STORY_BREAKDOWN`.
- `agent_contracts.py`: add required heading/visual contract.
- `agent_runtime.py`: add story breakdown structured output instruction.
- `artifact_data_renderers.py`: add schema and renderer.

- [x] **Step 3: Run backend GREEN**

Run the same command. Expected: all selected tests pass.

## Task 2: Handoff RED/GREEN

- [x] **Step 1: Write failing handoff test**

In `test_workflow_handoffs.py`, assert `STORY_BREAKDOWN/SPRINT_PLAN` handoff includes Epics, Stories, AC, dependencies, risks and target Lisa workflow intent.

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected RED: no story breakdown handoff configured.

- [x] **Step 2: Implement handoff**

Update `workflow_handoffs.py` to build a Lisa-ready summary from story breakdown artifact content.

- [x] **Step 3: Run handoff GREEN**

Run same command. Expected: pass.

## Task 3: Frontend Registry and Prompt RED/GREEN

- [x] **Step 1: Write failing frontend tests**

In `workflows.test.ts`, assert:

- `story-breakdown` exists.
- Alex listing includes it as online workflow.
- The old plan placeholder is removed.

In `buildSystemPrompt.test.ts`, assert story breakdown prompt includes story backlog/AC/Sprint instructions and does not inject markdown direct-write requirements for migrated artifact_data stages.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected RED: missing slug/listing/prompt.

- [x] **Step 2: Implement frontend registry and prompt**

Update `workflows.ts`, `agentWorkflows.ts`, `types.ts`, create `prompts/story_breakdown/backlog.ts`, and wire prompt builder.

- [x] **Step 3: Run frontend GREEN**

Run same command. Expected: tests pass.

## Task 4: Todo and Documentation Completion

- [x] **Step 1: Update enhancement diagnostic**

Mark E13 as consumed with completion evidence:

```markdown
| E13 | Alex 用户故事拆解 workflow | 已消化 | 专业内容 | M | P0 | 2026-06-23 已主线化: 共享 Agent Runtime workflow `STORY_BREAKDOWN` ... |
```

- [x] **Step 2: Mark spec completed and add execution record**

Change spec status to `已完成`; append plan execution record with RED/GREEN and validation results.

## Task 5: Verification and Commit

- [x] **Step 1: Run expanded backend tests**

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

- [x] **Step 2: Run frontend tests and lint**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
cd tools/new-agents/frontend && npm run lint
```

- [x] **Step 3: Run static checks**

```bash
.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/workflow_handoffs.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m black --check tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/workflow_handoffs.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py
git diff --check
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-06-23-alex-story-breakdown-mainline.md docs/superpowers/specs/2026-06-23-alex-story-breakdown-mainline-design.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/workflow_manifest.json tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/workflow_handoffs.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts tools/new-agents/frontend/src/core/config/agentWorkflows.ts tools/new-agents/frontend/src/core/prompts/story_breakdown/backlog.ts tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/workflows.ts
git commit -m "feat: 上线 Alex 用户故事拆解 workflow"
```

## 自检

- Spec 覆盖: workflow 入口、runtime、renderer、contract、handoff、frontend listing、docs/todos 均有任务覆盖。
- 占位扫描: 无 TBD/TODO/待补。
- 类型一致性: workflow id 使用 `STORY_BREAKDOWN`，slug 使用 `story-breakdown`，stage id 使用 `INPUT_ANALYSIS`、`EPIC_MAPPING`、`STORY_BACKLOG`、`SPRINT_PLAN`。

## 执行记录

- RED: backend 目标测试最初 4 failed，缺 `STORY_BREAKDOWN` workflow、renderer 和 run persistence stage registry；frontend 目标测试最初 6 failed，缺 `WORKFLOWS.STORY_BREAKDOWN` 和 artifact_data prompt mode。
- GREEN: backend 扩展套件 `274 passed in 0.99s`；frontend Vitest 目标命令实际运行相关 43 个测试文件，`678 passed`。
- Static: `py_compile`、`black --check`、`corepack pnpm --dir tools/new-agents/frontend lint`、`git diff --check` 均通过。
