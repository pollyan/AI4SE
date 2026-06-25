# New Agents 当前产出物本轮 Diff 标识 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在右侧 ArtifactPane 正式阅读区显示本轮新增/删除 diff 标识，并保证导出和状态事实源仍是干净 Markdown。

**Architecture:** 只改前端 ArtifactPane UI：复用当前阶段 `artifactHistory` 和既有 `buildLineDiff(...)` 计算本轮前后差异。Diff 以只读源码行视图呈现，不写入 `artifactContent`，不新增 runtime、SSE、store 或 workflow 分支。

**Tech Stack:** React 19, TypeScript 5.8, Zustand, Vitest, React Testing Library, Tailwind utilities.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Add current diff default display test**

Add a test that seeds two current-stage artifact versions and current content equal to the latest version:

```ts
it('shows the current artifact change diff in the main preview by default', async () => {
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        artifactContent: '# 当前产物\n\n新结论\n保留内容',
        stageArtifacts: {
            CLARIFY: '# 当前产物\n\n新结论\n保留内容',
        },
        artifactHistory: [
            {
                id: 'version-before',
                timestamp: 123,
                content: '# 当前产物\n\n旧结论\n保留内容',
                stageId: 'CLARIFY',
            },
            {
                id: 'version-after',
                timestamp: 124,
                content: '# 当前产物\n\n新结论\n保留内容',
                stageId: 'CLARIFY',
            },
        ],
    });

    render(<ArtifactPane />);

    const diff = await screen.findByTestId('current-artifact-diff');
    expect(diff.textContent).toContain('- 旧结论');
    expect(diff.textContent).toContain('+ 新结论');
    expect(screen.getByTestId('current-artifact-diff-added-line')).toHaveClass('text-emerald-200');
    expect(screen.getByTestId('current-artifact-diff-removed-line')).toHaveClass('line-through');
});
```

- [x] **Step 2: Add hide-current-diff test**

Add a test proving the user can return to the clean Markdown preview:

```ts
it('hides the current artifact change diff and returns to clean preview', async () => {
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        artifactContent: '# 当前产物\n\n新结论\n保留内容',
        stageArtifacts: {
            CLARIFY: '# 当前产物\n\n新结论\n保留内容',
        },
        artifactHistory: [
            {
                id: 'version-before',
                timestamp: 123,
                content: '# 当前产物\n\n旧结论\n保留内容',
                stageId: 'CLARIFY',
            },
            {
                id: 'version-after',
                timestamp: 124,
                content: '# 当前产物\n\n新结论\n保留内容',
                stageId: 'CLARIFY',
            },
        ],
    });

    render(<ArtifactPane />);

    await screen.findByTestId('current-artifact-diff');
    fireEvent.click(screen.getByRole('button', { name: '隐藏本轮变更' }));

    expect(screen.queryByTestId('current-artifact-diff')).toBeNull();
    expect(screen.getByRole('heading', { name: '当前产物' })).toBeTruthy();
    expect(screen.getByText('新结论')).toBeTruthy();
    expect(screen.queryByText('- 旧结论')).toBeNull();
});
```

- [x] **Step 3: Add clean Markdown download regression**

Add a test that keeps the diff visible and downloads Markdown:

```ts
it('downloads clean markdown while the current artifact change diff is visible', async () => {
    const createdAnchors: HTMLAnchorElement[] = [];
    const click = vi.fn();
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:artifact-clean-diff');
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
        const element = originalCreateElement(tagName, options);
        if (tagName.toLowerCase() === 'a') {
            Object.defineProperty(element, 'click', {
                configurable: true,
                value: click,
            });
            createdAnchors.push(element as HTMLAnchorElement);
        }
        return element;
    });
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        artifactContent: '# 当前产物\n\n新结论\n保留内容',
        artifactHistory: [
            {
                id: 'version-before',
                timestamp: 123,
                content: '# 当前产物\n\n旧结论\n保留内容',
                stageId: 'CLARIFY',
            },
            {
                id: 'version-after',
                timestamp: 124,
                content: '# 当前产物\n\n新结论\n保留内容',
                stageId: 'CLARIFY',
            },
        ],
    });

    render(<ArtifactPane />);
    await screen.findByTestId('current-artifact-diff');
    downloadArtifactAs('Markdown');

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const content = await blob.text();
    expect(content).toBe('# 当前产物\n\n新结论\n保留内容');
    expect(content).not.toContain('旧结论');
    expect(content).not.toContain('+ 新结论');
    expect(click).toHaveBeenCalledTimes(1);
});
```

- [x] **Step 4: Add no-baseline guard test**

Add a test for a single current-stage version:

```ts
it('does not show current artifact change diff when no previous baseline exists', () => {
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        artifactContent: '# 当前产物\n\n首版内容',
        artifactHistory: [
            {
                id: 'version-first',
                timestamp: 123,
                content: '# 当前产物\n\n首版内容',
                stageId: 'CLARIFY',
            },
        ],
    });

    render(<ArtifactPane />);

    expect(screen.queryByTestId('current-artifact-diff')).toBeNull();
    expect(screen.queryByRole('button', { name: '显示本轮变更' })).toBeNull();
});
```

- [x] **Step 5: Run red tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx -t "current artifact change diff|clean markdown|no previous baseline"
```

Expected: FAIL because `current-artifact-diff` and the toggle do not exist yet.

Result: FAIL observed. Three new diff-display tests failed because `current-artifact-diff` did not exist; the no-baseline guard passed.

### Task 2: ArtifactPane Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add current diff state**

Add state near the existing view state:

```ts
const [showCurrentChangeDiff, setShowCurrentChangeDiff] = useState(false);
const lastCurrentChangeDiffKeyRef = useRef<string | null>(null);
```

- [x] **Step 2: Compute current change baseline and diff**

Add memoized values after `latestStageArtifactVersion`:

```ts
const currentChangeBaselineVersion = useMemo(() => {
  if (currentStageArtifactHistory.length === 0) return null;
  const latestVersion = currentStageArtifactHistory[currentStageArtifactHistory.length - 1];
  if (latestVersion.content === artifactContent) {
    return currentStageArtifactHistory[currentStageArtifactHistory.length - 2] ?? null;
  }
  return latestVersion;
}, [artifactContent, currentStageArtifactHistory]);

const currentChangeDiff = useMemo(
  () => currentChangeBaselineVersion
    ? buildLineDiff(currentChangeBaselineVersion.content, artifactContent)
    : [],
  [artifactContent, currentChangeBaselineVersion]
);

const hasCurrentChangeDiff = Boolean(
  currentChangeBaselineVersion
  && currentChangeBaselineVersion.content !== artifactContent
  && currentChangeDiff.some(entry => entry.type !== 'unchanged')
);

const currentChangeDiffKey = hasCurrentChangeDiff
  ? `${currentChangeBaselineVersion?.id}->${latestStageArtifactVersion?.content === artifactContent ? latestStageArtifactVersion.id : 'working'}`
  : null;
```

- [x] **Step 3: Auto-open only for new diff keys**

Add an effect:

```ts
useEffect(() => {
  if (!currentChangeDiffKey) {
    lastCurrentChangeDiffKeyRef.current = null;
    setShowCurrentChangeDiff(false);
    return;
  }
  if (lastCurrentChangeDiffKeyRef.current === currentChangeDiffKey) return;
  lastCurrentChangeDiffKeyRef.current = currentChangeDiffKey;
  setShowCurrentChangeDiff(true);
}, [currentChangeDiffKey]);
```

- [x] **Step 4: Add toolbar toggle**

Add a small button near preview/code/history controls when `hasCurrentChangeDiff` is true:

```tsx
{hasCurrentChangeDiff && (
  <button
    type="button"
    onClick={() => setShowCurrentChangeDiff((current) => !current)}
    className={`p-1.5 rounded transition-colors ${showCurrentChangeDiff ? 'bg-emerald-500/10 text-emerald-200' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
    title={showCurrentChangeDiff ? '隐藏本轮变更' : '显示本轮变更'}
    aria-label={showCurrentChangeDiff ? '隐藏本轮变更' : '显示本轮变更'}
  >
    <GitCompare className="w-4 h-4" />
  </button>
)}
```

- [x] **Step 5: Render main diff view**

In the non-editing preview branch, render the diff when `viewMode === 'preview' && showCurrentChangeDiff && hasCurrentChangeDiff`:

```tsx
{viewMode === 'preview' && showCurrentChangeDiff && hasCurrentChangeDiff ? (
  <div data-testid="current-artifact-diff" className="overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] font-mono text-xs">
    <div className="flex items-center justify-between border-b border-[#1e293b] px-4 py-2 text-[11px] font-semibold text-slate-400">
      <span>本轮变更</span>
      <button
        type="button"
        onClick={() => setShowCurrentChangeDiff(false)}
        className="rounded px-2 py-1 text-slate-300 transition-colors hover:bg-white/10 hover:text-white"
        aria-label="隐藏本轮变更"
      >
        隐藏本轮变更
      </button>
    </div>
    {currentChangeDiff.map((entry, index) => {
      const prefix = entry.type === 'added' ? '+ ' : entry.type === 'removed' ? '- ' : '  ';
      return (
        <div
          key={`${entry.type}-${index}-${entry.content}`}
          data-testid={entry.type === 'added' ? 'current-artifact-diff-added-line' : entry.type === 'removed' ? 'current-artifact-diff-removed-line' : undefined}
          className={`whitespace-pre-wrap px-4 py-1.5 ${entry.type === 'added' ? 'bg-emerald-500/10 text-emerald-200' : entry.type === 'removed' ? 'bg-red-500/10 text-red-200 line-through decoration-red-300/70' : 'text-slate-400'}`}
        >
          {prefix}{entry.content || ' '}
        </div>
      );
    })}
  </div>
) : viewMode === 'preview' ? (
  <ReactMarkdown ...>
    {displayContent}
  </ReactMarkdown>
) : (
  <pre ...>{displayContent}</pre>
)}
```

Use the existing `ReactMarkdown`, `remarkGfm`, `rehypeRaw`, `editableMarkdownComponents`, and source `<pre>` exactly as before in their branches.

### Task 3: Verification

**Files:**
- Tests touched above.

- [x] **Step 1: Run focused component tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx -t "current artifact change diff|clean markdown|no previous baseline"
```

Expected: PASS.

Result: PASS, 4 focused tests.

- [x] **Step 2: Run full ArtifactPane test file**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx
```

Expected: PASS.

Result: PASS, 145 tests. Existing `act(...)` warnings appeared in the artifact comment reply test output but did not fail the suite.

- [x] **Step 3: Run diff and parser regressions**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactDiff.test.ts src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts
```

Expected: PASS.

Result: PASS, 133 tests across artifactDiff, llm, and chatService.

- [x] **Step 4: Run frontend lint**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: PASS.

Result: PASS.

- [x] **Step 5: Run frontend full Vitest suite**

Run:

```bash
cd tools/new-agents/frontend && npm run test
```

Result: PASS, 43 files and 671 tests. Existing `act(...)` warnings appeared in the artifact comment reply test output but did not fail the suite.

### Task 4: Todo Record and Commit

**Files:**
- Move/update: `docs/todos/2026-06-25-new-agents-artifact-change-diff-highlighting.md`
- Create/update: `docs/todos/archive/2026-06-25-new-agents-artifact-change-diff-highlighting.md`
- Create: this spec and plan.

- [x] **Step 1: Archive completed todo**

Move the todo to archive with status `已完成`. Record that this closes formal-view current diff highlighting, while full patch/memoized incremental rendering remains in `artifact-incremental-rendering.md`.

Result: PASS. Archived the diff highlighting todo and left the full incremental rendering todo active.

- [x] **Step 2: Run targeted diff and doc checks**

Run:

```bash
git diff --check -- tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx docs/superpowers/specs/2026-06-25-new-agents-current-artifact-diff-design.md docs/superpowers/plans/2026-06-25-new-agents-current-artifact-diff.md docs/todos/archive/2026-06-25-new-agents-artifact-change-diff-highlighting.md
python3 - <<'PY'
from pathlib import Path

paths = [
    Path("docs/superpowers/specs/2026-06-25-new-agents-current-artifact-diff-design.md"),
    Path("docs/superpowers/plans/2026-06-25-new-agents-current-artifact-diff.md"),
    Path("docs/todos/archive/2026-06-25-new-agents-artifact-change-diff-highlighting.md"),
]
tokens = ["TO" + "DO", "TB" + "D", "FIX" + "ME", "待" + "补", "占" + "位", "lor" + "em", "x" + "xx", "X" + "XX"]
matches = [
    f"{path}:{line_number}:{token}"
    for path in paths
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
    for token in tokens
    if token in line
]
if matches:
    raise SystemExit("\n".join(matches))
PY
```

Expected: `git diff --check` exits 0 and the placeholder script exits 0 with no matches.

Result: PASS. Targeted diff check and placeholder script both exited 0.

- [x] **Step 3: Stage only this story**

Stage:

```bash
git add tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx docs/superpowers/specs/2026-06-25-new-agents-current-artifact-diff-design.md docs/superpowers/plans/2026-06-25-new-agents-current-artifact-diff.md docs/todos/archive/2026-06-25-new-agents-artifact-change-diff-highlighting.md
```

Result: PASS. Only this story's UI, tests, spec, plan, and archived todo were staged.

- [x] **Step 4: Commit**

Run:

```bash
git commit -m "feat: 标识当前产出物本轮变更"
```

Result: PASS. The staged change set was committed with this message.
