# New Agents Workflow 入口专业 Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 New Agents 在线 workflow 选择入口增加配置驱动的专业 preview，让用户进入工作区前判断 workflow 是否适合当前目标。

**Architecture:** 继续以 `workflow_manifest.json` 作为在线 workflow 元数据源。前端类型、`WORKFLOWS` 和 `getAgentWorkflows()` 只做类型化投影，`WorkflowSelect` 只消费共享配置，不新增 runtime、SSE、API、store 或 renderer 分支。

**Tech Stack:** React 19、TypeScript、Vitest、Testing Library、共享 workflow manifest。

---

### Task 1: RED - 配置和入口 UI 测试

**Files:**
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/WorkflowSelect.test.tsx`

- [ ] Step 1: 在 `workflows.test.ts` 增加测试，断言每个在线 workflow card 都包含完整 preview，并与 `WORKFLOWS[workflowId].listing.preview` 同步。

目标断言：

```ts
expect(card?.preview).toEqual(wf.listing.preview);
expect(card?.preview.suitableFor.length).toBeGreaterThanOrEqual(2);
expect(card?.preview.notSuitableFor.length).toBeGreaterThanOrEqual(1);
expect(card?.preview.requiredInputs.length).toBeGreaterThanOrEqual(2);
expect(card?.preview.expectedOutputs.length).toBeGreaterThanOrEqual(2);
expect(card?.preview.sampleInput.trim()).not.toBe('');
```

- [ ] Step 2: 在 `WorkflowSelect.test.tsx` 增加测试，渲染 Lisa 和 Alex 入口后能看到 preview 标签与代表性内容，例如“适合”、“不适合”、“准备输入”、“产出”、“样例输入”。

- [ ] Step 3: 运行聚焦测试并确认 RED。

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/pages/__tests__/WorkflowSelect.test.tsx
```

Expected: FAIL，原因是 `preview` 字段不存在或 UI 未渲染 preview。

### Task 2: GREEN - 增加 preview 配置与类型投影

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`

- [ ] Step 1: 在 `types.ts` 新增 `WorkflowPreviewConfig`，并给 `WorkflowListingConfig` 增加 `preview`。

- [ ] Step 2: 在 `agentWorkflows.ts` 的 `AgentWorkflowConfig` 增加可选 `preview?: WorkflowPreviewConfig`，在线 workflow 投影从 `workflow.listing.preview` 赋值，非运行时 dev/plan 卡片不需要 preview。

- [ ] Step 3: 给 5 个在线 workflow 的 `listing` 添加 preview：
  - Lisa `TEST_DESIGN`
  - Lisa `REQ_REVIEW`
  - Lisa `INCIDENT_REVIEW`
  - Alex `IDEA_BRAINSTORM`
  - Alex `VALUE_DISCOVERY`

- [ ] Step 4: 运行聚焦测试，确认配置同步测试通过，页面测试仍可能因 UI 未渲染失败。

### Task 3: GREEN - 渲染 WorkflowSelect preview

**Files:**
- Modify: `tools/new-agents/frontend/src/pages/WorkflowSelect.tsx`

- [ ] Step 1: 在线 workflow 卡片中，当 `workflow.preview` 存在时渲染 preview 区块。

- [ ] Step 2: 使用现有 lucide 图标和紧凑布局展示四组短列表与样例输入，保持卡片点击行为不变。

- [ ] Step 3: 非在线卡片不渲染 preview，继续显示 `Dev`/`Plan` 标签和“即将推出”。

- [ ] Step 4: 运行聚焦测试，确认全部通过。

### Task 4: Refactor + 文档记录

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] Step 1: 在增强机会清单或首批建议切片处标注 E01 已由本轮入口 preview milestone 消化。

- [ ] Step 2: 检查没有 `TODO`、`TBD` 或未解释占位。

- [ ] Step 3: 运行最终验证。

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/pages/__tests__/WorkflowSelect.test.tsx
cd tools/new-agents/frontend && npm run lint
```

Expected: PASS。

### Commit Boundary

本轮预计形成一个聚焦 commit，包含 workflow preview 配置、前端入口展示、测试、spec/plan 和活跃 todo 消化记录。不 stage 既有 zip 产物或无关 `docs/plans/tech-debt.md`。
