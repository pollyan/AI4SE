# New Agents Artifact 工具条收敛 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ArtifactPane 右侧产物工具条从七个等权重图标收敛为高频一级操作 + `更多产物操作` 菜单。

**Architecture:** 只修改 `ArtifactPane.tsx` 的本地 UI 状态和工具条 JSX，不改变 store、后端 API 或 Artifact 协作数据结构。现有批注、章节锁定和下载 handler 继续复用，只移动入口层级。

**Tech Stack:** React 19、TypeScript 5、Zustand、Vitest、Testing Library、lucide-react。

---

### Task 1: 工具条菜单行为测试

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Add RED tests**

Add tests whose names contain `artifact toolbar`:

```ts
it('keeps secondary artifact actions behind the artifact toolbar menu', () => {
    useStore.setState({ artifactContent: '# 当前产出物' });
    render(<ArtifactPane />);

    expect(screen.queryByTitle('批注')).toBeNull();
    expect(screen.queryByTitle('章节锁定')).toBeNull();
    expect(screen.queryByTitle('下载')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));

    expect(screen.getByRole('button', { name: '批注' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '章节锁定' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '下载 Markdown' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '下载 Word' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '下载 PDF' })).toBeTruthy();
});
```

Add a second test:

```ts
it('opens comments from the artifact toolbar menu', () => {
    useStore.setState({ artifactContent: '# 当前产物\n\n需要批注的内容' });
    render(<ArtifactPane />);

    fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));
    fireEvent.click(screen.getByRole('button', { name: '批注' }));

    expect(screen.getByText('产出物批注')).toBeTruthy();
    expect(screen.queryByRole('button', { name: '下载 Markdown' })).toBeNull();
});
```

- [x] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact toolbar"
```

Expected: tests fail because `更多产物操作` does not exist and direct secondary buttons are still visible.

### Task 2: Implement ArtifactPane overflow menu

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add menu state and More icon import**

Import `MoreHorizontal` from `lucide-react` and add:

```ts
const [showArtifactActionsMenu, setShowArtifactActionsMenu] = useState(false);
```

- [x] **Step 2: Move secondary actions into menu**

Keep direct buttons for preview, code, history, edit. Replace direct `批注`、`章节锁定`、`下载` buttons with one button:

```tsx
<button
  type="button"
  onClick={() => {
    setShowArtifactActionsMenu((current) => !current);
    setShowExportMenu(false);
  }}
  aria-label="更多产物操作"
  title="更多产物操作"
  className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
>
  <MoreHorizontal className="w-4 h-4" />
</button>
```

Render menu items for comments, section locks, and three download formats. Use existing handlers and close the menu after each action.

- [x] **Step 3: Remove old export submenu dependency**

Remove toolbar usage of `showExportMenu` if it is no longer needed. If no other code references it, remove the state entirely.

- [x] **Step 4: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact toolbar"
```

Expected: toolbar tests pass.

### Task 3: Regression and documentation

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Modify: `docs/superpowers/plans/2026-06-20-new-agents-artifact-toolbar-overflow.md`

- [x] **Step 1: Update todo progress**

Append under P0 工作区顶部操作收敛 progress:

```markdown
- 2026-06-20：完成第二块 CGA「Artifact 工具条二级操作收敛」。
  - ArtifactPane 顶部一级操作保留预览、代码、历史和编辑；批注、章节锁定和 Markdown/Word/PDF 下载收敛到 `更多产物操作`。
  - 右侧产物协作和导出能力仍保留原行为，但不再作为一排等权重图标挤占阅读区顶部。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact toolbar"` 观察到缺少菜单失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。
```

- [x] **Step 2: Run full verification**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
npm run lint
npm run build
cd ../../..
git diff --check
```

Expected: all commands exit 0.

### Task 4: Commit

**Files:**
- Stage:
  - `docs/todos/new-agents-ux-professionalization.md`
  - `docs/superpowers/specs/2026-06-20-new-agents-artifact-toolbar-overflow-design.md`
  - `docs/superpowers/plans/2026-06-20-new-agents-artifact-toolbar-overflow.md`
  - `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Inspect status**

Run:

```bash
git status --short --branch
git diff --name-only
git ls-files --others --exclude-standard
```

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/specs/2026-06-20-new-agents-artifact-toolbar-overflow-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-toolbar-overflow.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 收敛 Artifact 工具条二级操作"
```
