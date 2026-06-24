# Workflow Handoff Context Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reviewable Alex-to-Lisa workflow handoff context so users can inspect source version, summary, unconfirmed items, and target input checklist before starting the target workflow.

**Architecture:** Extend the existing manifest-driven handoff path instead of adding a new runtime or API path. The backend builds a conservative structured context from the source artifact, returns it with the existing handoff response, and uses the same context in the target run prompt. The frontend strictly parses the new fields and renders a compact review card inside the existing ChatPane handoff action surface.

**Tech Stack:** Python 3.11, Flask tests with pytest, React 19, TypeScript, Zustand, Vitest, existing New Agents workflow manifest and run persistence.

---

## File Structure

- Modify: `tools/new-agents/backend/workflow_handoffs.py`
  - Responsibility: construct handoff candidates, structured context, and target run prompt.
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
  - Responsibility: backend RED/PASS coverage for context extraction and persisted target prompt.
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - Responsibility: API-level coverage that handoff endpoints expose the structured fields.
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - Responsibility: `WorkflowHandoff` response contract.
- Modify: `tools/new-agents/frontend/src/services/workflowHandoffService.ts`
  - Responsibility: strict parser for handoff payloads.
- Modify: `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`
  - Responsibility: frontend service RED/PASS coverage for required fields and start response.
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
  - Responsibility: compact handoff context review UI.
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
  - Responsibility: visible handoff context and apply behavior tests.
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
  - Responsibility: store keeps enhanced prompt when applying handoff.
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - Responsibility: mark E07 as consumed in this milestone and preserve remaining candidate list.
- Modify: `docs/todos/refactor/README.md`
  - Responsibility: summarize current active candidate state after E07.

## Commit Boundary

One focused milestone commit:

```bash
git commit -m "feat(new-agents): 增强 workflow handoff 上下文审阅"
```

The commit includes code, tests, spec, plan, and todo updates because they describe one completed user-visible handoff capability.

## Task 1: Backend RED Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: Add failing handoff context assertions**

In `test_export_run_handoffs_returns_configured_lisa_targets`, assert the first handoff includes structured context:

```python
    assert first["sourceSummary"].startswith("AI 测试资产管理平台需求蓝图")
    assert first["unconfirmedItems"] == []
    assert first["targetInputChecklist"] == [
        "复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1",
        "确认目标阶段 TEST_DESIGN/CLARIFY 所需的需求、验收标准和约束均已覆盖",
        "确认没有遗留未确认项后进入目标产物生成",
    ]
    assert "来源版本: VALUE_DISCOVERY/BLUEPRINT v1" in first["prompt"]
    assert "关键摘要:" in first["prompt"]
    assert "未确认项:" in first["prompt"]
    assert "目标工作流输入:" in first["prompt"]
```

- [ ] **Step 2: Add failing unconfirmed extraction test**

Append a test to `test_workflow_handoffs.py`:

```python
def test_export_run_handoffs_extracts_unconfirmed_items_for_review(app):
    markdown = BLUEPRINT_MARKDOWN.replace(
        "| 需求 | F-001 | 自动生成测试策略和用例 | P0 需求 | 需求评审 / 测试设计 | 已确认 |",
        "| 需求 | F-001 | 自动生成测试策略和用例 | P0 需求 | 需求评审 / 测试设计 | 待确认 |",
    )
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(run.id, "BLUEPRINT", markdown)

        result = export_run_handoffs(run.id)

    first = result["handoffs"][0]
    assert first["unconfirmedItems"] == ["需求 F-001: 自动生成测试策略和用例"]
    assert "处理 1 个未确认项后再进入目标产物生成" in first["targetInputChecklist"]
    assert "- 需求 F-001: 自动生成测试策略和用例" in first["prompt"]
```

- [ ] **Step 3: Add endpoint-level failing assertions**

In the existing handoff endpoint test that reads `/handoffs` or `/start`, assert:

```python
    handoff = payload["handoffs"][0]
    assert handoff["sourceSummary"]
    assert isinstance(handoff["unconfirmedItems"], list)
    assert handoff["targetInputChecklist"]
```

If the endpoint file only covers the start route, assert the same fields on the start response.

- [ ] **Step 4: Run backend RED tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
```

Expected: fails because `sourceSummary`, `unconfirmedItems`, and `targetInputChecklist` are not present.

## Task 2: Backend Implementation

**Files:**
- Modify: `tools/new-agents/backend/workflow_handoffs.py`

- [ ] **Step 1: Add context helpers**

Add constants and helper functions:

```python
UNCONFIRMED_MARKERS = ("待确认", "未确认", "待澄清", "未验证", "开放问题")

def _build_source_summary(source_artifact: str) -> str:
    title = _first_markdown_heading(source_artifact)
    body_line = _first_summary_body_line(source_artifact)
    if title and body_line:
        return f"{title}: {body_line}"
    if title:
        return title
    if body_line:
        return body_line
    return "源产物未提供可提取摘要"
```

Also add `_first_markdown_heading()`, `_first_summary_body_line()`, `_extract_unconfirmed_items()`, `_format_unconfirmed_item()`, `_is_table_separator()`, `_build_target_input_checklist()`, and `_format_bullets()` using conservative line/table parsing.

- [ ] **Step 2: Return structured fields**

Update `_build_handoff()` to compute and return:

```python
    source_summary = _build_source_summary(artifact["content"])
    unconfirmed_items = _extract_unconfirmed_items(artifact["content"])
    target_input_checklist = _build_target_input_checklist(
        handoff,
        artifact["versionNumber"],
        unconfirmed_items,
    )
```

Then include `sourceSummary`, `unconfirmedItems`, and `targetInputChecklist` in the returned dict.

- [ ] **Step 3: Enrich prompt**

Change `_build_handoff_prompt()` to accept `source_artifact_version`, `source_summary`, `unconfirmed_items`, and `target_input_checklist`, then join:

```python
[
    template.format(**handoff),
    f"来源版本: {source_version}",
    "关键摘要:\n" + _format_bullets([source_summary]),
    "未确认项:\n" + _format_bullets(unconfirmed_items or ["无"]),
    "目标工作流输入:\n" + _format_bullets(target_input_checklist),
    "源产物内容:",
    bounded_artifact,
]
```

- [ ] **Step 4: Run backend PASS tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
```

Expected: all selected backend tests pass.

## Task 3: Frontend RED Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`

- [ ] **Step 1: Ensure frontend dependencies exist in this worktree**

If `tools/new-agents/frontend/node_modules` is absent, create a local symlink only for verification:

```bash
ln -s /Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules tools/new-agents/frontend/node_modules
```

Do not stage the symlink.

- [ ] **Step 2: Add service fixture fields**

In handoff service tests, add:

```ts
sourceSummary: 'AI 测试资产管理平台需求蓝图: AI 测试资产管理平台。',
unconfirmedItems: ['需求 F-001: 自动生成测试策略和用例'],
targetInputChecklist: ['复核来源版本 VALUE_DISCOVERY/BLUEPRINT v2'],
```

Assert parsed handoffs include these fields.

- [ ] **Step 3: Add malformed payload assertion**

Add a service test where payload omits `sourceSummary`:

```ts
await expect(fetchWorkflowHandoffs('alex-run-123')).rejects.toThrow(
    'Invalid workflow handoff response'
);
```

- [ ] **Step 4: Add ChatPane visible context assertions**

In the existing `loads workflow handoff actions` test fixture, add the new fields and assert:

```ts
expect(await screen.findByText('来源 VALUE_DISCOVERY/BLUEPRINT v2')).toBeDefined();
expect(screen.getByText(/AI 测试资产管理平台需求蓝图/)).toBeDefined();
expect(screen.getByText('需求 F-001: 自动生成测试策略和用例')).toBeDefined();
expect(screen.getByText('复核来源版本 VALUE_DISCOVERY/BLUEPRINT v2')).toBeDefined();
```

- [ ] **Step 5: Add store prompt assertion**

In `store.test.ts`, apply a handoff with enhanced prompt:

```ts
prompt: '来源版本: VALUE_DISCOVERY/BLUEPRINT v2\n\n关键摘要:\n- AI 测试资产管理平台需求蓝图',
```

Assert the new chat message content equals the enhanced prompt.

- [ ] **Step 6: Run frontend RED tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts
```

Expected: fails because the type/parser/UI do not support the new fields yet.

## Task 4: Frontend Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/workflowHandoffService.ts`
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`

- [ ] **Step 1: Extend `WorkflowHandoff` type**

Add required fields:

```ts
sourceSummary: string;
unconfirmedItems: string[];
targetInputChecklist: string[];
```

- [ ] **Step 2: Parse string arrays strictly**

Add helper:

```ts
const parseStringArray = (value: unknown): string[] => {
    if (!Array.isArray(value) || value.some((item) => typeof item !== 'string')) {
        throw new Error('Invalid workflow handoff response');
    }
    return value;
};
```

Require `sourceSummary` to be a string and parse both arrays before returning `WorkflowHandoff`.

- [ ] **Step 3: Render compact review context**

In the handoff card button area, render each handoff as a compact panel containing:

```tsx
<p>来源 {handoff.sourceWorkflowId}/{handoff.sourceStageId} v{handoff.sourceArtifactVersion}</p>
<p>{handoff.sourceSummary}</p>
{handoff.unconfirmedItems.length > 0 ? ... : <p>未确认项: 无</p>}
{handoff.targetInputChecklist.slice(0, 3).map(...)}
```

Keep the existing button label and `ArrowRight` action.

- [ ] **Step 4: Run frontend PASS tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts
```

Expected: all selected frontend tests pass.

## Task 5: Todo Records and Verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update active todo record**

Record that E07 is consumed by this milestone, with branch, commit placeholder before commit, and verification commands. Keep remaining candidates visible and do not claim unrelated branches are merged into `master`.

- [ ] **Step 2: Run CI-equivalent verification**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/workflowHandoffService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all pass.

- [ ] **Step 3: Inspect diff and status**

Run:

```bash
git diff --stat
git status --short
```

Expected: only handoff code/tests/spec/plan/todo files changed, plus an untracked local `node_modules` symlink if it was created for verification.

- [ ] **Step 4: Remove local symlink if present**

Run:

```bash
rm tools/new-agents/frontend/node_modules
```

Only run this if `node_modules` is a symlink created in Task 3.

- [ ] **Step 5: Commit**

Stage only this milestone's files and commit:

```bash
git add docs/superpowers/specs/2026-06-24-workflow-handoff-context-review-design.md docs/superpowers/plans/2026-06-24-workflow-handoff-context-review.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/backend/workflow_handoffs.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/services/workflowHandoffService.ts tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts tools/new-agents/frontend/src/components/ChatPane.tsx tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx tools/new-agents/frontend/src/__tests__/store.test.ts
git commit -m "feat(new-agents): 增强 workflow handoff 上下文审阅"
```

## Plan Self-Review

- Spec coverage: Tasks cover backend context extraction, API exposure, target prompt persistence, frontend strict parsing, ChatPane visibility, store handoff application, todo records, and verification.
- Placeholder scan: No placeholder steps remain; each task lists exact files, commands, and expected outcomes.
- Type consistency: Field names are consistently `sourceSummary`, `unconfirmedItems`, and `targetInputChecklist` across backend JSON, TypeScript type, service parser, UI, tests, and prompt expectations.
