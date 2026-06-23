# Alex 用户故事拆解 Workflow 主线落地 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Alex `story-breakdown` 从 plan 卡片升级为共享 Agent Runtime 在线 workflow。

**Architecture:** 以 `workflow_manifest.json` 为单一 workflow 入口，同步前端 `WORKFLOWS`、prompt registry、后端 `WORKFLOW_STAGES`、artifact contract、renderer 和 handoff。所有运行继续走共享 `/api/agent/runs/stream`、typed SSE、artifact persistence 和共享 UI。

**Tech Stack:** Flask/Pydantic/Pytest、React/TypeScript/Vitest、共享 New Agents workflow manifest。

---

### Task 1: 写 RED 测试证明 story-breakdown 尚未成为 runtime workflow

**Files:**
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`

- [ ] **Step 1: Frontend RED**

新增测试断言 Alex 的 `story-breakdown` 卡片为 online，link 为 `/workspace/alex/story-breakdown`，并且 `WORKFLOWS.STORY_BREAKDOWN` 存在 4 个阶段。

- [ ] **Step 2: Backend sync RED**

新增测试断言 manifest、backend stage registry、prompt file registry、artifact contract registry 都包含 `STORY_BREAKDOWN`。

- [ ] **Step 3: Runtime RED**

新增测试断言 `parse_agent_turn_output_text()` 能把 `STORY_BREAKDOWN/INPUT_ANALYSIS` 的 `artifact_data` 渲染为完整 artifact。

- [ ] **Step 4: Handoff RED**

新增测试断言 `STORY_BREAKDOWN/SPRINT_PLAN` 声明到 Lisa `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW` 的 handoff。

- [ ] **Step 5: Run RED commands**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts
```

Expected: FAIL because `STORY_BREAKDOWN` is not registered as runtime workflow.

### Task 2: 实现共享 workflow 配置和 prompt

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/input_analysis.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/epic_mapping.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/story_backlog.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/story_breakdown/sprint_plan.ts`

- [ ] **Step 1: Add manifest workflow**

新增 `STORY_BREAKDOWN`，包含 4 个 stage、listing preview、onboarding 和 handoff。

- [ ] **Step 2: Add frontend workflow**

在 `WORKFLOWS` 中新增 `STORY_BREAKDOWN`，slug 为 `story-breakdown`，并从 plan cards 移除同名非 runtime 卡片。

- [ ] **Step 3: Add prompt templates**

新增 4 个 prompt template，并在 `buildSystemPrompt.ts` registry 中注册。

### Task 3: 实现 backend contract、renderer 和 handoff

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/workflow_handoffs.py`

- [ ] **Step 1: Add backend stage and artifact contract**

同步 `WORKFLOW_STAGES`、required headings、required Mermaid diagrams 和 structured visual types。

- [ ] **Step 2: Add structured output instructions**

为 4 个 stage 增加 `artifact_data` 输出指令，要求模型不要直接输出完整 Markdown/Mermaid。

- [ ] **Step 3: Add deterministic renderer**

新增 story breakdown 的 data validation 和 renderer，输出固定 headings、Markdown 表格、Mermaid 和 `ai4se-visual`。

- [ ] **Step 4: Add handoff template**

扩展 handoff prompt，让 Lisa 能识别来源为 Story 包。

### Task 4: GREEN 验证与清理

**Files:**
- Modify tests listed above
- Modify todo docs after code green

- [ ] **Step 1: Run focused backend tests**

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected: PASS.

- [ ] **Step 2: Run focused frontend tests**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: PASS.

- [ ] **Step 3: Run syntax and diff checks**

```bash
python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/workflow_handoffs.py
git diff --check
```

Expected: PASS.

- [ ] **Step 4: Update todo records**

在 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 记录 E13 已完成主线 runtime workflow 落地，保留 E14、DeepSeek smoke/evidence、质量产品化为后续候选。

- [ ] **Step 5: Commit**

```bash
git add <本轮相关文件>
git commit -m "feat(new-agents): 上线 Alex 用户故事拆解 workflow"
```
