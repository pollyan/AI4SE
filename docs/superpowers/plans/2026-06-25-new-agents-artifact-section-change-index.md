# New Agents 产出物章节变更索引 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 New Agents 前端在当前 Artifact 更新后记录本轮变化涉及的 Markdown 章节，并在右侧“本轮变更”视图中显示章节摘要。

**Architecture:** `artifactContent` 继续作为唯一事实源；章节变更索引是前端 store 中的非持久化派生状态。新增 `core/artifactSections.ts` 提供纯函数解析和比较，`store.ts` 在集中写入口维护索引，`ArtifactPane.tsx` 只消费索引用于展示。

**Tech Stack:** React 19、TypeScript、Zustand、Vitest、Testing Library。

---

## File Structure

- Create: `tools/new-agents/frontend/src/core/artifactSections.ts`
  - 负责从 Markdown 提取标题章节、忽略 fenced code block 内伪标题、比较前后章节，输出 added / removed / modified 变更。
- Create: `tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts`
  - 覆盖单章节修改、fenced heading 忽略、重复标题 occurrence anchor、结构化内容 safeForPatch 判定。
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 新增 `ArtifactSectionChangeKind` 和 `ArtifactSectionChange`，并在 `ChatState` 中加入 `artifactChangeIndex`。
- Modify: `tools/new-agents/frontend/src/store.ts`
  - 在初始状态和重置路径加入 `artifactChangeIndex: []`；在 `setArtifactContent` 中用旧内容和新内容计算索引；保持 `partialize` 不持久化它。
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
  - 覆盖 `setArtifactContent` 记录索引、stage 切换清空索引、clear history 清空索引。
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 从 store 读取 `artifactChangeIndex`，在当前 diff 卡片头部下方显示“变更章节”摘要。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - 覆盖当前 diff 可见时渲染章节摘要，且无索引时不显示摘要。
- Modify: `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`
  - 记录本切片已完成内容、验证命令和未覆盖的完整 `artifact_patch` 工作。

## Task 1: Core Artifact Section Index

**Files:**
- Create: `tools/new-agents/frontend/src/core/artifactSections.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`

- [ ] **Step 1: Write failing core tests**

Create `tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts` with:

```ts
import { describe, expect, it } from 'vitest';
import {
  buildArtifactSectionChangeIndex,
  extractArtifactSections,
} from '../artifactSections';

describe('artifactSections', () => {
  it('reports only the section whose body changed', () => {
    const changes = buildArtifactSectionChangeIndex(
      '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变',
      '# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
    );

    expect(changes).toEqual([
      expect.objectContaining({
        kind: 'modified',
        title: '范围',
        anchor: 'h2:范围:1',
        safeForPatch: true,
      }),
    ]);
  });

  it('ignores markdown headings inside fenced code blocks', () => {
    const sections = extractArtifactSections(
      '# 文档\n\n```md\n## 伪标题\n```\n\n## 真实标题\n\n正文',
    );

    expect(sections.map(section => section.title)).toEqual(['文档', '真实标题']);
  });

  it('uses occurrence anchors for duplicate headings', () => {
    const sections = extractArtifactSections(
      '# 文档\n\n## 风险\n\n第一处\n\n## 风险\n\n第二处',
    );

    expect(sections.map(section => section.anchor)).toEqual([
      'h1:文档:1',
      'h2:风险:1',
      'h2:风险:2',
    ]);
    expect(sections.map(section => section.displayTitle)).toEqual([
      '文档',
      '风险 #1',
      '风险 #2',
    ]);
  });

  it('marks structured markdown sections as unsafe for automatic patching', () => {
    const changes = buildArtifactSectionChangeIndex(
      '# 文档\n\n## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 旧值 |',
      '# 文档\n\n## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 新值 |',
    );

    expect(changes).toEqual([
      expect.objectContaining({
        kind: 'modified',
        title: '表格',
        safeForPatch: false,
        unsafeReason: 'markdown_table',
      }),
    ]);
  });
});
```

- [ ] **Step 2: Run core tests and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts
```

Expected: FAIL because `../artifactSections` does not exist.

- [ ] **Step 3: Add section change types**

In `tools/new-agents/frontend/src/core/types.ts`, add after `ArtifactVersionInput`:

```ts
export type ArtifactSectionChangeKind = 'added' | 'removed' | 'modified';

export type ArtifactSectionChange = {
    kind: ArtifactSectionChangeKind;
    anchor: string;
    title: string;
    displayTitle: string;
    safeForPatch: boolean;
    unsafeReason?: 'fenced_block' | 'markdown_table' | 'markdown_list' | 'structured_visual';
};
```

- [ ] **Step 4: Implement the core utility**

Create `tools/new-agents/frontend/src/core/artifactSections.ts`:

```ts
import type { ArtifactSectionChange, ArtifactSectionChangeKind } from './types';

export type ArtifactMarkdownSection = {
  level: number;
  heading: string;
  title: string;
  displayTitle: string;
  anchor: string;
  content: string;
};

type UnsafeReason = NonNullable<ArtifactSectionChange['unsafeReason']>;

const normalizeMarkdown = (content: string): string => content.replace(/\r\n/g, '\n');

const isFenceBoundary = (line: string): boolean => /^\s*```/.test(line);

const headingPattern = /^(#{1,6})\s+(.+?)\s*$/;

const detectUnsafeReason = (content: string): UnsafeReason | undefined => {
  const lines = content.split('\n');
  if (lines.some(line => /```\s*ai4se-visual\b/.test(line))) return 'structured_visual';
  if (lines.some(isFenceBoundary)) return 'fenced_block';
  if (lines.some(line => /^\s*\|.*\|\s*$/.test(line))) return 'markdown_table';
  if (lines.some(line => /^[-*+]\s+/.test(line) || /^\d+\.\s+/.test(line))) return 'markdown_list';
  return undefined;
};

export const extractArtifactSections = (content: string): ArtifactMarkdownSection[] => {
  const lines = normalizeMarkdown(content).split('\n');
  const rawSections: Array<Omit<ArtifactMarkdownSection, 'displayTitle' | 'anchor'> & { start: number }> = [];
  let inFence = false;
  let currentStart = -1;
  let currentHeading = '';
  let currentTitle = '';
  let currentLevel = 0;

  lines.forEach((line, index) => {
    if (isFenceBoundary(line)) {
      inFence = !inFence;
      return;
    }
    if (inFence) return;

    const match = line.match(headingPattern);
    if (!match) return;

    if (currentStart >= 0) {
      rawSections.push({
        start: currentStart,
        level: currentLevel,
        heading: currentHeading,
        title: currentTitle,
        content: lines.slice(currentStart, index).join('\n').trim(),
      });
    }

    currentStart = index;
    currentHeading = line.trim();
    currentLevel = match[1].length;
    currentTitle = match[2].trim();
  });

  if (currentStart >= 0) {
    rawSections.push({
      start: currentStart,
      level: currentLevel,
      heading: currentHeading,
      title: currentTitle,
      content: lines.slice(currentStart).join('\n').trim(),
    });
  }

  const duplicateCounts = rawSections.reduce<Record<string, number>>((counts, section) => {
    counts[section.title] = (counts[section.title] ?? 0) + 1;
    return counts;
  }, {});
  const occurrenceCounts: Record<string, number> = {};

  return rawSections.map((section) => {
    const occurrence = (occurrenceCounts[section.title] ?? 0) + 1;
    occurrenceCounts[section.title] = occurrence;
    const isDuplicateTitle = duplicateCounts[section.title] > 1;
    return {
      level: section.level,
      heading: section.heading,
      title: section.title,
      displayTitle: isDuplicateTitle ? `${section.title} #${occurrence}` : section.title,
      anchor: `h${section.level}:${section.title}:${occurrence}`,
      content: section.content,
    };
  });
};

const buildChange = (
  kind: ArtifactSectionChangeKind,
  section: ArtifactMarkdownSection,
): ArtifactSectionChange => {
  const unsafeReason = detectUnsafeReason(section.content);
  return {
    kind,
    anchor: section.anchor,
    title: section.title,
    displayTitle: section.displayTitle,
    safeForPatch: unsafeReason === undefined,
    ...(unsafeReason ? { unsafeReason } : {}),
  };
};

export const buildArtifactSectionChangeIndex = (
  previousContent: string,
  currentContent: string,
): ArtifactSectionChange[] => {
  const previousSections = extractArtifactSections(previousContent);
  const currentSections = extractArtifactSections(currentContent);
  if (previousSections.length === 0 || currentSections.length === 0) return [];

  const previousByAnchor = new Map(previousSections.map(section => [section.anchor, section]));
  const currentByAnchor = new Map(currentSections.map(section => [section.anchor, section]));
  const changes: ArtifactSectionChange[] = [];

  currentSections.forEach((section) => {
    const previous = previousByAnchor.get(section.anchor);
    if (!previous) {
      changes.push(buildChange('added', section));
      return;
    }
    if (previous.content !== section.content) {
      changes.push(buildChange('modified', section));
    }
  });

  previousSections.forEach((section) => {
    if (!currentByAnchor.has(section.anchor)) {
      changes.push(buildChange('removed', section));
    }
  });

  return changes;
};
```

- [ ] **Step 5: Run core tests and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts
```

Expected: PASS.

## Task 2: Store Derived State

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/store.ts`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`

- [ ] **Step 1: Write failing store tests**

Append to `tools/new-agents/frontend/src/__tests__/store.test.ts`:

```ts
    it('records artifact section changes when current artifact content is replaced', () => {
        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变');

        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变');

        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({
                kind: 'modified',
                title: '范围',
                anchor: 'h2:范围:1',
            }),
        ]);
    });

    it('clears artifact section changes when switching stage and clearing history', () => {
        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n旧范围');
        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n新范围');
        expect(useStore.getState().artifactChangeIndex).toHaveLength(1);

        useStore.getState().setStageIndex(1);
        expect(useStore.getState().artifactChangeIndex).toEqual([]);

        useStore.getState().setArtifactContent('# 策略\n\n## 方向\n\n旧方向');
        useStore.getState().setArtifactContent('# 策略\n\n## 方向\n\n新方向');
        expect(useStore.getState().artifactChangeIndex).toHaveLength(1);

        useStore.getState().clearHistory();
        expect(useStore.getState().artifactChangeIndex).toEqual([]);
    });
```

- [ ] **Step 2: Run store tests and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/__tests__/store.test.ts -t "artifact section changes"
```

Expected: FAIL because `artifactChangeIndex` is missing.

- [ ] **Step 3: Add ChatState field**

In `tools/new-agents/frontend/src/core/types.ts`, add this field after `artifactContent: string;`:

```ts
    artifactChangeIndex: ArtifactSectionChange[];
```

- [ ] **Step 4: Maintain derived state in store**

In `tools/new-agents/frontend/src/store.ts`:

1. Import `buildArtifactSectionChangeIndex`:

```ts
import { buildArtifactSectionChangeIndex } from './core/artifactSections';
```

2. Add `artifactChangeIndex: []` to the initial state.
3. Add `artifactChangeIndex: []` to reset paths that replace the active artifact without representing a same-stage update: `sanitizePersistedWorkspaceState`, `setWorkflow`, `setStageIndex`, `transitionToNextStage`, `applyWorkflowHandoff`, `restoreRunSnapshot`, `clearHistory`, and `confirmStageTransition` through `planStageTransitionConfirmation` output handling.
4. Change `setArtifactContent` to compute the index:

```ts
      setArtifactContent: (artifactContent) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
        newStageArtifacts[currentStageId] = artifactContent;
        return {
          artifactContent,
          artifactChangeIndex: buildArtifactSectionChangeIndex(
            state.artifactContent,
            artifactContent
          ),
          stageArtifacts: newStageArtifacts,
          artifactVisualDiagnostics: [],
          artifactVisualDiagnosticFocusRequest: null,
        };
      }),
```

5. Keep `partialize` unchanged so `artifactChangeIndex` is not stored in localStorage.

- [ ] **Step 5: Run store tests and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/__tests__/store.test.ts -t "artifact section changes"
```

Expected: PASS.

## Task 3: ArtifactPane Section Summary

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write failing component tests**

Append near the current artifact diff tests in `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`:

```ts
    it('shows changed section summary inside current artifact change diff', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
            stageArtifacts: {
                CLARIFY: '# 当前产物\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
            },
            artifactHistory: [
                {
                    id: 'version-before',
                    timestamp: 123,
                    content: '# 当前产物\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变',
                    stageId: 'CLARIFY',
                },
                {
                    id: 'version-after',
                    timestamp: 124,
                    content: '# 当前产物\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
                    stageId: 'CLARIFY',
                },
            ],
            artifactChangeIndex: [
                {
                    kind: 'modified',
                    anchor: 'h2:范围:1',
                    title: '范围',
                    displayTitle: '范围',
                    safeForPatch: true,
                },
            ],
        });

        render(<ArtifactPane />);

        const summary = await screen.findByTestId('current-artifact-diff-section-summary');
        expect(summary.textContent).toContain('变更章节：修改 范围');
    });

    it('does not show changed section summary when current artifact change index is empty', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n新结论',
            artifactHistory: [
                {
                    id: 'version-before',
                    timestamp: 123,
                    content: '# 当前产物\n\n旧结论',
                    stageId: 'CLARIFY',
                },
                {
                    id: 'version-after',
                    timestamp: 124,
                    content: '# 当前产物\n\n新结论',
                    stageId: 'CLARIFY',
                },
            ],
            artifactChangeIndex: [],
        });

        render(<ArtifactPane />);

        await screen.findByTestId('current-artifact-diff');
        expect(screen.queryByTestId('current-artifact-diff-section-summary')).toBeNull();
    });
```

- [ ] **Step 2: Run component tests and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx -t "changed section summary"
```

Expected: FAIL because `current-artifact-diff-section-summary` is not rendered.

- [ ] **Step 3: Render the section summary**

In `tools/new-agents/frontend/src/components/ArtifactPane.tsx`:

1. Read the store field:

```ts
  const artifactChangeIndex = useStore((state) => state.artifactChangeIndex);
```

2. Add a display mapping near the current diff memos:

```ts
  const currentArtifactSectionChangeSummary = useMemo(() => {
    const labels = {
      added: '新增',
      removed: '删除',
      modified: '修改',
    } as const;
    return artifactChangeIndex.map(change => `${labels[change.kind]} ${change.displayTitle}`);
  }, [artifactChangeIndex]);
```

3. Render it inside `data-testid="current-artifact-diff"` after the top toolbar:

```tsx
                  {currentArtifactSectionChangeSummary.length > 0 && (
                    <div
                      data-testid="current-artifact-diff-section-summary"
                      className="border-b border-[#1e293b] px-4 py-2 text-[11px] font-semibold text-sky-100"
                    >
                      变更章节：{currentArtifactSectionChangeSummary.join('、')}
                    </div>
                  )}
```

- [ ] **Step 4: Run component tests and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx -t "changed section summary"
```

Expected: PASS.

## Task 4: Records, Focused Verification, and Commit

**Files:**
- Modify: `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`
- Stage only files changed in this plan.

- [ ] **Step 1: Run focused frontend verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx -t "artifactSections|artifact section changes|changed section summary"
```

Expected: PASS.

- [ ] **Step 2: Run expanded relevant frontend verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Run lint**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: PASS.

- [ ] **Step 4: Update active todo progress record**

Append a dated progress section to `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`:

```md
## 2026-06-25 进展：前端章节变更索引

- 已新增 `artifactSections` 纯函数，前端可基于完整 Markdown 提取稳定章节 anchor，并比较本轮 Artifact 内容变化影响的章节。
- 已在 Zustand store 中维护非持久化 `artifactChangeIndex`，`setArtifactContent(...)` 记录同阶段 Artifact 更新范围，stage / workflow / snapshot / history reset 路径清空索引。
- 已在右侧 ArtifactPane 的“本轮变更”视图显示章节摘要，便于用户先从章节层面审阅长文档更新。
- 本切片仍未新增后端 `artifact_patch` / `changed_sections` SSE 契约，也未拆分 ReactMarkdown 为 memoized section rendering；这些仍属于本 todo 的后续工作。
- 验证：
  - `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx -t "artifactSections|artifact section changes|changed section summary"`
  - `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`
  - `cd tools/new-agents/frontend && npm run lint`
```

- [ ] **Step 5: Check status and stage focused files**

Run:

```bash
git status -sb
git add docs/superpowers/specs/2026-06-25-new-agents-artifact-section-change-index-design.md docs/superpowers/plans/2026-06-25-new-agents-artifact-section-change-index.md docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/artifactSections.ts tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts tools/new-agents/frontend/src/store.ts tools/new-agents/frontend/src/__tests__/store.test.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
```

Expected: only the files from this plan are staged; existing unrelated `dist/intent-test-proxy.zip`, `tools/intent-tester/frontend/static/intent-test-proxy.zip`, and `tools/intent-tester/test-results/proxy/junit.xml` remain unstaged.

- [ ] **Step 6: Commit**

Run:

```bash
git commit -m "feat: 记录产出物章节变更索引"
```

Expected: commit succeeds with only the files from this plan.

## Self-Review

- Spec coverage: acceptance criteria 1-4 map to Task 1; criterion 5 maps to Task 2; criterion 6 maps to Task 3; progress recording maps to Task 4.
- Placeholder scan: plan contains concrete paths, test bodies, implementation snippets, commands, and expected results.
- Type consistency: `ArtifactSectionChange`, `artifactChangeIndex`, `extractArtifactSections`, and `buildArtifactSectionChangeIndex` names match across tasks.
