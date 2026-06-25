# New Agents 产出物章节 Patch 应用 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让前端 store 能安全应用同 base 的单章节 replace patch，并在失败时返回明确降级原因。

**Architecture:** `artifactSections.ts` 提供纯函数 patch 应用与安全判断；`store.ts` 暴露 action 并在成功时同步完整 artifact 事实源和 `artifactChangeIndex`。后端 SSE、`chatService.ts` 和 UI 渲染拆分不在本切片内变更。

**Tech Stack:** TypeScript、Zustand、Vitest。

---

## File Structure

- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 新增 `ArtifactSectionPatch`、`ArtifactSectionPatchResult` 和 fallback reason 类型，并扩展 `ChatState` action。
- Modify: `tools/new-agents/frontend/src/core/artifactSections.ts`
  - 给 extracted section 增加 line range；导出安全原因检测；新增 `applyArtifactSectionPatch(...)`。
- Modify: `tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts`
  - 覆盖成功 replace、base mismatch、section missing、unsafe section。
- Modify: `tools/new-agents/frontend/src/store.ts`
  - 新增 `applyArtifactSectionPatch(...)` action，成功时更新当前 artifact 和派生索引，失败不改 state。
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
  - 覆盖 store action 成功更新和失败不变。
- Modify: `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`
  - 记录本切片进展和验证。

## Task 1: Core Section Patch Function

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/artifactSections.ts`
- Modify: `tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts`

- [ ] **Step 1: Write failing core tests**

Append to `tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts`:

```ts
  it('applies a same-base section replace patch and reports the changed section', () => {
    const base = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变';
    const result = applyArtifactSectionPatch(base, {
      operation: 'replace',
      sectionAnchor: 'h2:范围:1',
      replacementMarkdown: '## 范围\n\n新范围',
      baseContent: base,
    });

    expect(result).toEqual(expect.objectContaining({
      applied: true,
      content: '# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
    }));
    expect(result.changes).toEqual([
      expect.objectContaining({
        kind: 'modified',
        anchor: 'h2:范围:1',
      }),
    ]);
  });

  it('rejects section patches when the current content no longer matches the base', () => {
    const base = '# 文档\n\n## 范围\n\n旧范围';
    const current = '# 文档\n\n## 范围\n\n用户已手动修改';

    const result = applyArtifactSectionPatch(current, {
      operation: 'replace',
      sectionAnchor: 'h2:范围:1',
      replacementMarkdown: '## 范围\n\n新范围',
      baseContent: base,
    });

    expect(result).toEqual({
      applied: false,
      content: current,
      changes: [],
      fallbackReason: 'base_mismatch',
    });
  });

  it('rejects section patches when the anchor cannot be found', () => {
    const current = '# 文档\n\n## 范围\n\n旧范围';

    const result = applyArtifactSectionPatch(current, {
      operation: 'replace',
      sectionAnchor: 'h2:不存在:1',
      replacementMarkdown: '## 不存在\n\n新范围',
      baseContent: current,
    });

    expect(result.fallbackReason).toBe('section_not_found');
    expect(result.content).toBe(current);
  });

  it('rejects section patches for unsafe structured markdown sections', () => {
    const current = '# 文档\n\n## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 旧值 |';

    const result = applyArtifactSectionPatch(current, {
      operation: 'replace',
      sectionAnchor: 'h2:表格:1',
      replacementMarkdown: '## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 新值 |',
      baseContent: current,
    });

    expect(result).toEqual({
      applied: false,
      content: current,
      changes: [],
      fallbackReason: 'unsafe_section',
    });
  });
```

Also update the import:

```ts
import {
  applyArtifactSectionPatch,
  buildArtifactSectionChangeIndex,
  extractArtifactSections,
} from '../artifactSections';
```

- [ ] **Step 2: Run core tests and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts -t "section patch"
```

Expected: FAIL because `applyArtifactSectionPatch` does not exist.

- [ ] **Step 3: Add patch types**

Add to `tools/new-agents/frontend/src/core/types.ts` after `ArtifactSectionChange`:

```ts
export type ArtifactSectionPatchOperation = 'replace';

export type ArtifactSectionPatchFallbackReason =
    | 'base_mismatch'
    | 'section_not_found'
    | 'unsafe_section'
    | 'invalid_patch';

export type ArtifactSectionPatch = {
    operation: ArtifactSectionPatchOperation;
    sectionAnchor: string;
    replacementMarkdown: string;
    baseContent?: string;
};

export type ArtifactSectionPatchResult = {
    applied: boolean;
    content: string;
    changes: ArtifactSectionChange[];
    fallbackReason?: ArtifactSectionPatchFallbackReason;
};
```

- [ ] **Step 4: Implement minimal core patch function**

In `tools/new-agents/frontend/src/core/artifactSections.ts`:

- Import patch types.
- Add `startLine` and `endLine` to `ArtifactMarkdownSection`.
- Replace `detectUnsafeReason(...)` with exported `getArtifactSectionUnsafeReason(...)`.
- Add:

```ts
const buildFallback = (
  content: string,
  fallbackReason: ArtifactSectionPatchFallbackReason,
): ArtifactSectionPatchResult => ({
  applied: false,
  content,
  changes: [],
  fallbackReason,
});

export const applyArtifactSectionPatch = (
  currentContent: string,
  patch: ArtifactSectionPatch,
): ArtifactSectionPatchResult => {
  if (patch.operation !== 'replace' || !patch.sectionAnchor.trim() || !patch.replacementMarkdown.trim()) {
    return buildFallback(currentContent, 'invalid_patch');
  }
  if (patch.baseContent !== undefined && patch.baseContent !== currentContent) {
    return buildFallback(currentContent, 'base_mismatch');
  }

  const sections = extractArtifactSections(currentContent);
  const targetSection = sections.find(section => section.anchor === patch.sectionAnchor);
  if (!targetSection) {
    return buildFallback(currentContent, 'section_not_found');
  }

  const replacementSections = extractArtifactSections(patch.replacementMarkdown);
  if (replacementSections.length !== 1) {
    return buildFallback(currentContent, 'invalid_patch');
  }
  if (
    getArtifactSectionUnsafeReason(targetSection.content)
    || getArtifactSectionUnsafeReason(replacementSections[0].content)
  ) {
    return buildFallback(currentContent, 'unsafe_section');
  }

  const lines = currentContent.replace(/\r\n/g, '\n').split('\n');
  const nextContent = [
    ...lines.slice(0, targetSection.startLine),
    ...patch.replacementMarkdown.replace(/\r\n/g, '\n').split('\n'),
    ...lines.slice(targetSection.endLine),
  ].join('\n');

  return {
    applied: true,
    content: nextContent,
    changes: buildArtifactSectionChangeIndex(currentContent, nextContent),
  };
};
```

- [ ] **Step 5: Run core tests and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts -t "section patch"
```

Expected: PASS.

## Task 2: Store Patch Action

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/store.ts`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`

- [ ] **Step 1: Write failing store tests**

Append to `tools/new-agents/frontend/src/__tests__/store.test.ts`:

```ts
    it('applies artifact section patches to the active stage artifact', () => {
        const base = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变';
        useStore.getState().setArtifactContent(base);

        const result = useStore.getState().applyArtifactSectionPatch({
            operation: 'replace',
            sectionAnchor: 'h2:范围:1',
            replacementMarkdown: '## 范围\n\n新范围',
            baseContent: base,
        });

        expect(result.applied).toBe(true);
        expect(useStore.getState().artifactContent).toBe('# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变');
        expect(useStore.getState().stageArtifacts.CLARIFY).toBe(useStore.getState().artifactContent);
        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({
                kind: 'modified',
                anchor: 'h2:范围:1',
            }),
        ]);
    });

    it('does not mutate artifact state when section patch application falls back', () => {
        const base = '# 文档\n\n## 范围\n\n旧范围';
        useStore.getState().setArtifactContent(base);

        const result = useStore.getState().applyArtifactSectionPatch({
            operation: 'replace',
            sectionAnchor: 'h2:不存在:1',
            replacementMarkdown: '## 不存在\n\n新范围',
            baseContent: base,
        });

        expect(result).toEqual({
            applied: false,
            content: base,
            changes: [],
            fallbackReason: 'section_not_found',
        });
        expect(useStore.getState().artifactContent).toBe(base);
        expect(useStore.getState().stageArtifacts.CLARIFY).toBe(base);
    });
```

- [ ] **Step 2: Run store tests and verify red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/__tests__/store.test.ts -t "section patch"
```

Expected: FAIL because `applyArtifactSectionPatch` is missing on `ChatState`.

- [ ] **Step 3: Add store action type**

In `tools/new-agents/frontend/src/core/types.ts`, add action:

```ts
    applyArtifactSectionPatch: (patch: ArtifactSectionPatch) => ArtifactSectionPatchResult;
```

- [ ] **Step 4: Implement store action**

In `tools/new-agents/frontend/src/store.ts`:

- Import `applyArtifactSectionPatch` with an alias to avoid action name conflict.
- Add action after `setArtifactContent`:

```ts
      applyArtifactSectionPatch: (patch) => {
        const result = applyArtifactSectionPatchToContent(
          useStore.getState().artifactContent,
          patch
        );
        if (!result.applied) return result;

        set((state) => {
          const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
          return {
            artifactContent: result.content,
            artifactChangeIndex: result.changes,
            stageArtifacts: {
              ...state.stageArtifacts,
              [currentStageId]: result.content,
            },
            artifactVisualDiagnostics: [],
            artifactVisualDiagnosticFocusRequest: null,
          };
        });
        return result;
      },
```

- [ ] **Step 5: Run store tests and verify green**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/__tests__/store.test.ts -t "section patch"
```

Expected: PASS.

## Task 3: Records, Verification, and Commit

**Files:**
- Modify: `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`
- Stage only this slice files.

- [ ] **Step 1: Run focused verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts -t "section patch"
```

Expected: PASS.

- [ ] **Step 2: Run expanded frontend verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts
cd tools/new-agents/frontend && npm run lint
```

Expected: both commands PASS.

- [ ] **Step 3: Update active todo**

Append a progress section for “前端章节 patch 应用与显式降级” with completed behavior, verification commands, and remaining backend SSE / memoized rendering work.

- [ ] **Step 4: Run diff checks and stage files**

Run:

```bash
git diff --check -- docs/superpowers/specs/2026-06-25-new-agents-artifact-section-patch-application-design.md docs/superpowers/plans/2026-06-25-new-agents-artifact-section-patch-application.md docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/artifactSections.ts tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts tools/new-agents/frontend/src/store.ts tools/new-agents/frontend/src/__tests__/store.test.ts
git add docs/superpowers/specs/2026-06-25-new-agents-artifact-section-patch-application-design.md docs/superpowers/plans/2026-06-25-new-agents-artifact-section-patch-application.md docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/artifactSections.ts tools/new-agents/frontend/src/core/__tests__/artifactSections.test.ts tools/new-agents/frontend/src/store.ts tools/new-agents/frontend/src/__tests__/store.test.ts
git diff --cached --check
```

Expected: checks pass and only this slice files are staged.

- [ ] **Step 5: Commit**

Run:

```bash
git commit -m "feat: 支持前端章节 patch 应用降级"
```

Expected: commit succeeds.

## Self-Review

- Spec coverage: acceptance criteria 1-4 map to Task 1; criterion 5 maps to Task 2; records and verification map to Task 3.
- Placeholder scan: plan uses concrete files, tests, implementation snippets, commands, and expected results.
- Type consistency: `ArtifactSectionPatch`, `ArtifactSectionPatchResult`, `applyArtifactSectionPatch`, and store action names are consistent across tasks.
