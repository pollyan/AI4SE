# Workflow Handoff Context Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 强化现有 Alex 到 Lisa workflow handoff，让用户在接力前看到来源版本、关键摘要、目标输入和未确认项，并让目标 run 收到结构化上下文 prompt。

**Architecture:** 继续复用共享 workflow manifest、handoff API、run persistence、frontend service、shared store 和 ChatPane。后端从来源 artifact 确定性派生 `context` 并注入 prompt；前端解析并展示该 context，不新增专属 runtime、API path、store 或 renderer。

**Tech Stack:** Python 3.11, Flask, pytest, TypeScript 5.x, React, Vitest, Testing Library.

---

## File Structure

- Modify: `tools/new-agents/backend/workflow_handoffs.py`
  - 构造 `WorkflowHandoff.context`，并把结构化接力上下文注入 prompt。
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
  - RED 覆盖 context 字段、未确认项、prompt 内容、start target run 消息。
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 增加 `WorkflowHandoffContext` 类型，`WorkflowHandoff.context?`。
- Modify: `tools/new-agents/frontend/src/services/workflowHandoffService.ts`
  - 解析并校验可选 `context`。
- Modify: `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`
  - RED 覆盖 context 解析和 malformed context。
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
  - 在跨智能体接力卡片展示来源版本、摘要、目标输入和未确认项。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
  - RED 覆盖 context 展示。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 标记 E07 本轮消化，补验证记录。
- Modify: `docs/todos/refactor/README.md`
  - 更新活动索引摘要。

## Task 1: RED Backend Handoff Context Contract

- [ ] **Step 1: Add failing backend assertions**

在 `tools/new-agents/backend/tests/test_workflow_handoffs.py` 的 `BLUEPRINT_MARKDOWN` 中加入一条待确认输入：

```markdown
| 约束 | NFR-001 | 数据权限边界待确认 | 非功能需求 | 风险分析 / 用例边界 | 待确认 |
```

在 `test_export_run_handoffs_returns_configured_lisa_targets` 中新增断言：

```python
    assert first["context"] == {
        "sourceArtifactTitle": "AI 测试资产管理平台需求蓝图",
        "sourceArtifactSummary": "AI 测试资产管理平台需求蓝图；Lisa handoff 输入 3 项",
        "targetInputSummary": "交给 TEST_DESIGN/CLARIFY 使用：需求 F-001、验收标准 AC-001、约束 NFR-001",
        "unconfirmedItems": ["约束 NFR-001: 数据权限边界待确认"],
    }
    assert "## 接力上下文" in first["prompt"]
    assert "来源版本: v1" in first["prompt"]
    assert "目标输入: 交给 TEST_DESIGN/CLARIFY 使用：需求 F-001、验收标准 AC-001、约束 NFR-001" in first["prompt"]
    assert "- 约束 NFR-001: 数据权限边界待确认" in first["prompt"]
```

在 `test_start_workflow_handoff_creates_target_run_with_handoff_prompt` 中新增：

```python
    assert result["context"]["unconfirmedItems"] == ["约束 NFR-001: 数据权限边界待确认"]
    assert "## 接力上下文" in target_snapshot["messages"][0]["content"]
```

- [ ] **Step 2: Run backend RED**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected: FAIL because `context` is missing from handoff payload.

## Task 2: GREEN Backend Context Extraction

- [ ] **Step 1: Implement minimal backend context**

In `tools/new-agents/backend/workflow_handoffs.py`:

```python
def _build_handoff(handoff: dict, artifact: dict) -> dict:
    context = _build_handoff_context(handoff, artifact)
    return {
        "id": handoff["id"],
        "label": handoff["label"],
        "sourceWorkflowId": handoff["sourceWorkflowId"],
        "sourceStageId": handoff["sourceStageId"],
        "sourceArtifactVersion": artifact["versionNumber"],
        "targetWorkflowId": handoff["targetWorkflowId"],
        "targetStageId": handoff["targetStageId"],
        "targetAgentId": handoff["targetAgentId"],
        "context": context,
        "prompt": _build_handoff_prompt(handoff, artifact, context),
    }
```

Add deterministic helpers:

```python
def _build_handoff_context(handoff: dict, artifact: dict) -> dict:
    content = artifact["content"]
    title = _extract_title(content)
    handoff_inputs = _extract_lisa_handoff_inputs(content)
    item_labels = [f"{item['type']} {item['id']}" for item in handoff_inputs]
    unconfirmed = [
        f"{item['type']} {item['id']}: {item['content']}"
        for item in handoff_inputs
        if _is_unconfirmed_status(item["status"])
    ]
    summary = f"{title}；Lisa handoff 输入 {len(handoff_inputs)} 项"
    return {
        "sourceArtifactTitle": title,
        "sourceArtifactSummary": summary,
        "targetInputSummary": (
            f"交给 {handoff['targetWorkflowId']}/{handoff['targetStageId']} 使用："
            + "、".join(item_labels)
        ),
        "unconfirmedItems": unconfirmed,
    }
```

The helper names and parsing can be adjusted to fit the file, but behavior must match Task 1.

- [ ] **Step 2: Run backend GREEN**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_handoffs.py -q
```

Expected: PASS.

## Task 3: RED Frontend Service And UI

- [ ] **Step 1: Add service RED**

In `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`, add `context` to the successful fetch payload and assert it is returned:

```ts
context: {
    sourceArtifactTitle: 'AI 测试资产管理平台需求蓝图',
    sourceArtifactSummary: 'AI 测试资产管理平台需求蓝图；Lisa handoff 输入 3 项',
    targetInputSummary: '交给 TEST_DESIGN/CLARIFY 使用：需求 F-001、验收标准 AC-001、约束 NFR-001',
    unconfirmedItems: ['约束 NFR-001: 数据权限边界待确认'],
},
```

Add malformed context case:

```ts
it('should fail explicitly when handoff context is malformed', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({
        runId: 'alex-run-123',
        sourceWorkflowId: 'VALUE_DISCOVERY',
        handoffs: [{
            id: 'handoff-1',
            label: '交给 Lisa 做测试设计',
            sourceWorkflowId: 'VALUE_DISCOVERY',
            sourceStageId: 'BLUEPRINT',
            sourceArtifactVersion: 2,
            targetWorkflowId: 'TEST_DESIGN',
            targetStageId: 'CLARIFY',
            targetAgentId: 'lisa',
            prompt: 'prompt',
            context: { sourceArtifactTitle: 42 },
        }],
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }));

    await expect(fetchWorkflowHandoffs('alex-run-123')).rejects.toThrow(
        'Invalid workflow handoff response'
    );
});
```

- [ ] **Step 2: Add ChatPane RED**

In `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`, extend the handoff fixture in `loads workflow handoff actions for the current persisted run` with `context`, then assert:

```ts
expect(await screen.findByText('来源 v2')).toBeDefined();
expect(screen.getByText('AI 测试资产管理平台需求蓝图；Lisa handoff 输入 3 项')).toBeDefined();
expect(screen.getByText('交给 TEST_DESIGN/CLARIFY 使用：需求 F-001、验收标准 AC-001、约束 NFR-001')).toBeDefined();
expect(screen.getByText('未确认 1 项')).toBeDefined();
expect(screen.getByText('约束 NFR-001: 数据权限边界待确认')).toBeDefined();
```

- [ ] **Step 3: Run frontend RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx
```

Expected: FAIL because `WorkflowHandoff.context` parsing and ChatPane rendering are missing.

## Task 4: GREEN Frontend Context Parsing And Rendering

- [ ] **Step 1: Add frontend type and parser**

In `tools/new-agents/frontend/src/core/types.ts`:

```ts
export type WorkflowHandoffContext = {
    sourceArtifactTitle: string;
    sourceArtifactSummary: string;
    targetInputSummary: string;
    unconfirmedItems: string[];
};
```

Add `context?: WorkflowHandoffContext;` to `WorkflowHandoff`.

In `workflowHandoffService.ts`, parse optional context strictly: all string fields must be strings and `unconfirmedItems` must be an array of strings.

- [ ] **Step 2: Render compact handoff details**

In `ChatPane.tsx`, keep the existing card and action buttons, and add a compact context block for each handoff:

```tsx
{handoff.context && (
  <div className="mt-3 rounded-lg border border-cyan-400/15 bg-slate-950/30 p-2 text-[11px] text-cyan-50/80">
    <div className="flex flex-wrap items-center gap-2 font-semibold text-cyan-100">
      <span>来源 v{handoff.sourceArtifactVersion}</span>
      {handoff.context.unconfirmedItems.length > 0 && (
        <span>未确认 {handoff.context.unconfirmedItems.length} 项</span>
      )}
    </div>
    <p className="mt-1">{handoff.context.sourceArtifactSummary}</p>
    <p className="mt-1">{handoff.context.targetInputSummary}</p>
    {handoff.context.unconfirmedItems.length > 0 && (
      <ul className="mt-1 space-y-0.5">
        {handoff.context.unconfirmedItems.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    )}
  </div>
)}
```

Adjust class names to match existing layout if needed, but keep visible text.

- [ ] **Step 3: Run frontend GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx
```

Expected: PASS.

## Task 5: Docs, Full Focused Verification, Commit

- [ ] **Step 1: Update active todo docs**

Update `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`:

- Mark E07 as consumed.
- Add a verification record naming backend handoff tests, frontend service/UI tests, lint, and diff check.
- Keep E05/E06/E08/E09/E10/E11/E12 active.

Update `docs/todos/refactor/README.md` to reflect E07 completion.

- [ ] **Step 2: Run final focused validation**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_handoffs_endpoint_exports_configured_targets tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_handoff_start_endpoint_creates_target_run -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all pass.

- [ ] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-workflow-handoff-context-enhancement-design.md docs/superpowers/plans/2026-06-23-workflow-handoff-context-enhancement.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/backend/workflow_handoffs.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/services/workflowHandoffService.ts tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts tools/new-agents/frontend/src/components/ChatPane.tsx tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx
git commit -m "feat: 增强 workflow handoff 上下文"
```

