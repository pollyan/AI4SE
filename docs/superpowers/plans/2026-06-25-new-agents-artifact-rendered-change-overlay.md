# New Agents Artifact 正式渲染变更标记 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 New Agents 右侧当前产出物默认保持正式 Markdown 渲染，并在具体表格行、列表项、段落或节点上显示本轮新增/修改和修改前值。

**Architecture:** 不改 Agent Runtime、typed SSE、后端 artifact contract 或 workflow manifest。前端 `ArtifactPane` 基于已有 `artifactHistory`、`artifactContent`、`buildLineDiff()` 和 `artifactChangeIndex` 构建行级渲染注解，再通过共享 ReactMarkdown components 叠加视觉标记；下载、编辑、保存继续使用干净 `artifactContent`。

**Tech Stack:** React 19, TypeScript 5.8, Zustand, ReactMarkdown, remark-gfm, Vitest, Testing Library.

---

## File Structure

- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 负责将当前 raw line diff 面板改为正式预览局部注解。
  - 新增行号注解 helper、摘要 chips、`tr` / `li` / `p` 等 Markdown components 变更样式。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - 更新当前本轮变更相关测试，新增正式预览行级标记和原值展示断言。
- Create/Update: `docs/superpowers/specs/2026-06-25-new-agents-artifact-rendered-change-overlay-design.md`
  - 记录 CGA、需求细化、设计和验收。
- Create/Update: `docs/superpowers/plans/2026-06-25-new-agents-artifact-rendered-change-overlay.md`
  - 记录本实施计划和执行勾选状态。

## Task 1: RED - 当前变更必须正式渲染

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: 更新失败测试**

Replace the old current diff expectations around `shows the current artifact change diff in the main preview by default` with tests that expect formal rendering:

```tsx
it('renders current artifact changes as formal preview annotations instead of raw line diff', async () => {
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        artifactContent: [
            '# 当前产物',
            '',
            '## 2. 被测系统与边界',
            '',
            '| 类型 | 具体内容 | 测试含义 | 状态 |',
            '| --- | --- | --- | --- |',
            '| 用户入口 | 登录页面（Web 端） | 覆盖 Chrome、Firefox、Edge、Safari | 待确认 |',
            '| 成功反馈 | 跳转至首页并设置 JWT Token | 验证 Token 正确生成并存储 | 待确认 |',
        ].join('\n'),
        stageArtifacts: {
            CLARIFY: [
                '# 当前产物',
                '',
                '## 2. 被测系统与边界',
                '',
                '| 类型 | 具体内容 | 测试含义 | 状态 |',
                '| --- | --- | --- | --- |',
                '| 用户入口 | 登录页面（Web 端） | 覆盖 Chrome、Firefox、Edge、Safari | 待确认 |',
                '| 成功反馈 | 跳转至首页并设置 JWT Token | 验证 Token 正确生成并存储 | 待确认 |',
            ].join('\n'),
        },
        artifactHistory: [
            {
                id: 'version-before',
                timestamp: 123,
                content: [
                    '# 当前产物',
                    '',
                    '## 2. 被测系统与边界',
                    '',
                    '| 类型 | 具体内容 | 测试含义 | 状态 |',
                    '| --- | --- | --- | --- |',
                    '| 用户入口 | 登录页面（Web/移动端） | 覆盖不同终端和浏览器 | 待确认 |',
                    '| 成功反馈 | 跳转至首页并设置登录态（Token/Cookie） | 验证登录态正确生成 | 待确认 |',
                ].join('\n'),
                stageId: 'CLARIFY',
            },
            {
                id: 'version-after',
                timestamp: 124,
                content: [
                    '# 当前产物',
                    '',
                    '## 2. 被测系统与边界',
                    '',
                    '| 类型 | 具体内容 | 测试含义 | 状态 |',
                    '| --- | --- | --- | --- |',
                    '| 用户入口 | 登录页面（Web 端） | 覆盖 Chrome、Firefox、Edge、Safari | 待确认 |',
                    '| 成功反馈 | 跳转至首页并设置 JWT Token | 验证 Token 正确生成并存储 | 待确认 |',
                ].join('\n'),
                stageId: 'CLARIFY',
            },
        ],
        artifactChangeIndex: [
            {
                kind: 'modified',
                anchor: 'h2:2. 被测系统与边界:1',
                title: '2. 被测系统与边界',
                displayTitle: '2. 被测系统与边界',
                safeForPatch: false,
                unsafeReason: 'markdown_table',
            },
        ],
    });

    render(<ArtifactPane />);

    expect(await screen.findByTestId('current-artifact-change-summary')).toBeTruthy();
    expect(screen.queryByTestId('current-artifact-diff')).toBeNull();
    expect(screen.getByRole('table')).toBeTruthy();
    expect(screen.getAllByTestId('artifact-change-modified-row')).toHaveLength(2);
    expect(screen.getByText(/原：.*登录页面（Web\/移动端）/)).toBeTruthy();
    expect(screen.getByText(/原：.*登录态（Token\/Cookie）/)).toBeTruthy();
    expect(screen.queryByText('- | 用户入口 | 登录页面（Web/移动端） | 覆盖不同终端和浏览器 | 待确认 |')).toBeNull();
});
```

- [x] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "formal preview annotations"
```

Expected: FAIL because current `ArtifactPane` still renders `current-artifact-diff` raw line diff and does not render `current-artifact-change-summary` or modified row markers.

Actual: FAIL as expected. `current-artifact-change-summary` was not found and the DOM still contained the raw `current-artifact-diff` panel.

## Task 2: GREEN - 渲染注解 helper 和 Markdown components

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add local rendered-change types and helper**

Add near the existing local types:

```tsx
type RenderedChangeKind = 'added' | 'modified';

type RenderedLineChange = {
  kind: RenderedChangeKind;
  previousContent?: string;
};

type RenderedChangeSummary = {
  added: number;
  modified: number;
  removed: number;
};
```

Implement a helper that converts `LineDiffEntry[]` into current-document line annotations. Pair adjacent removed/added runs as modifications; added-only runs are additions; removed-only runs only increment summary and do not render in the formal body.

- [x] **Step 2: Wire annotations into ReactMarkdown components**

Extend `createArtifactMarkdownComponents(...)` with optional `renderedLineChanges?: Map<number, RenderedLineChange>` and `showRenderedChanges?: boolean`.

For `tr`, `li`, `p`, and simple headings:
- Read `node.position.start.line`.
- If `showRenderedChanges` and a line annotation exists, add local highlight class and `data-testid`:
  - `artifact-change-added-row`
  - `artifact-change-modified-row`
  - `artifact-change-added-item`
  - `artifact-change-modified-item`
  - `artifact-change-added-block`
  - `artifact-change-modified-block`
- For `modified`, render a compact line below the row/item/block:

```tsx
<span data-testid="artifact-change-previous-value">原：{annotation.previousContent}</span>
```

For table rows, return a fragment with the highlighted row and a second row using `colSpan={99}` for the previous value.

- [x] **Step 3: Replace raw current diff panel**

In the preview branch:
- Always render `artifact-section-renderer` for `viewMode === 'preview'`.
- If `hasCurrentChangeDiff`, render a compact `current-artifact-change-summary` above the formal body.
- Keep the toolbar `GitCompare` button, but make it toggle rendered annotations instead of swapping to a raw diff panel.
- Do not render `current-artifact-diff` in the main preview path.
- Leave history modal diff and conflict diff unchanged.

- [x] **Step 4: Run GREEN for focused test**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "formal preview annotations"
```

Expected: PASS.

Actual: PASS. Focused Vitest run reported `1 passed | 146 skipped`.

## Task 3: Regression Tests for Toggle and Downloads

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Update existing current-diff tests**

Update old tests so they assert:
- `current-artifact-change-summary` appears when a baseline exists.
- `current-artifact-diff-section-summary` is no longer used in main preview.
- Clicking `隐藏本轮变更` keeps the rendered heading/body but removes `artifact-change-previous-value`.
- Downloaded Markdown does not include `原：` or UI tags.

- [x] **Step 2: Run updated focused current-change tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "current artifact change|formal preview annotations|clean markdown"
```

Expected: PASS.

Actual: PASS. Focused current-change regression run reported `6 passed | 141 skipped`.

## Task 4: Verification and Records

**Files:**
- Modify: `docs/superpowers/plans/2026-06-25-new-agents-artifact-rendered-change-overlay.md`

- [x] **Step 1: Run component regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

Expected: PASS. Existing React `act(...)` warnings may appear only if pre-existing and exit code remains 0.

Actual: PASS. `ArtifactPane.test.tsx` reported `147 passed`. The pre-existing React `act(...)` warning still appears in the artifact comments test.

- [x] **Step 2: Run frontend CI-equivalent checks**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

Expected: all exit 0.

Actual:
- `npm run lint`: PASS (`tsc --noEmit` exit 0).
- `npm run build`: PASS (`vite build` exit 0; existing chunk-size warnings only).
- `git diff --check`: FAIL on unrelated existing `tools/intent-tester/test-results/proxy/junit.xml` trailing whitespace.
- Scoped `git diff --check -- <this-story-files>`: PASS.
- `npm run test`: PASS (`45 passed`, `696 tests passed`) after fixing the new annotation prop to preserve incremental section memoization.

- [x] **Step 3: Goal-mode full verification decision**

Because this changes New Agents frontend main artifact path, run full deterministic local automation unless environment blocks it:

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

Expected: exit 0. If it fails due unrelated existing generated files or external environment, record exact failure and do not claim full verification passed.

Actual: FAIL, not claimed as full pass.
- Intent Tester API: PASS (`294 passed`).
- Code quality check: PASS.
- MidScene Proxy: FAIL before New Agents changes are exercised; `listen EPERM: operation not permitted 0.0.0.0:3002`, plus request tests returning `500` / `AggregateError`.
- Common Frontend lint/build: PASS.
- New Agents Frontend: PASS (`45 passed`, `696 tests passed`).
- New Agents Backend: PASS (`510 passed, 1 deselected`).
- New Agents Browser E2E: FAIL in this sandbox because Playwright Chromium exits with `bootstrap_check_in ... Permission denied (1100)`.

- [x] **Step 4: Commit**

Stage only this user story files:

```bash
git add docs/superpowers/specs/2026-06-25-new-agents-artifact-rendered-change-overlay-design.md docs/superpowers/plans/2026-06-25-new-agents-artifact-rendered-change-overlay.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "fix(new-agents): 正式渲染 artifact 本轮变更"
```

Actual: Staged only this story's implementation, tests, spec, and plan files. Existing intent-tester generated/test-result files and `docs/mockups/` remain unstaged.

Do not stage unrelated existing files:
- `dist/intent-test-proxy.zip`
- `tools/intent-tester/frontend/static/intent-test-proxy.zip`
- `tools/intent-tester/test-results/proxy/junit.xml`
- `docs/mockups/artifact-incremental-rendering-preview.html` unless the user explicitly asks to include the exploratory mockup.

## Self-Review

- Spec coverage: table row marking, item/block marking, old value visibility, no duplicate deletion list, clean downloads, no backend/runtime changes are covered.
- Placeholder scan: no `TODO` / `TBD` placeholders.
- Type consistency: plan uses existing `LineDiffEntry`, `ArtifactPane`, `artifactChangeIndex`, and Testing Library APIs.
