# New Agents Artifact 章节重命名自动合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Artifact 保存冲突在安全的 Markdown 章节重命名场景下提供 `自动合并非重叠变更`，继续降低人工校准后的冲突处理成本。

**Architecture:** 继续复用 `ArtifactPane.tsx` 内的三方 Markdown 章节解析、冲突卡片、编辑草稿和活动轨迹。新增保守 rename helper，注册在 section rewrite/move 之后、section add/delete 之前；只有 heading 改名且正文不变时自动合并，其余情况继续人工处理。

**Tech Stack:** React 19、TypeScript 5、Zustand、Vitest、Testing Library。

---

### Task 1: 章节重命名自动合并测试

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Add RED tests near section add/delete and movement tests**

Add tests whose names contain `section rename`:

1. `auto-merges non-overlapping section rename when draft renames and server rewrites another section`
2. `auto-merges non-overlapping section rename when server renames and draft rewrites another section`
3. `auto-merges section rename when both sides rename to the same heading`
4. `does not auto-merge section rename when both sides rename to different headings`
5. `does not auto-merge section rename when renamed section body also changes`
6. `does not auto-merge section rename when the other side changed the renamed section body`
7. `does not auto-merge section rename when the other side also moves and rewrites a section`
8. `does not auto-merge section rename when heading depth changes`

Use the same setup pattern as existing `section add/delete` tests:
- mock `updateRunArtifact` to reject with `ArtifactConflictError`;
- set `workflow: 'TEST_DESIGN'`, `stageIndex: 1`, `currentRunId: 'run-123'`;
- set `artifactContent`, `stageArtifacts.STRATEGY`, and one matching `artifactHistory` entry to the base content;
- render `<ArtifactPane />`, edit the Markdown, click `保存修改`;
- positive tests click `自动合并非重叠变更` and assert textarea value plus `artifact_auto_merge_applied` summary;
- negative tests assert `自动合并非重叠变更` is absent after `对比服务端版本` appears.

Use these base snippets for positive tests:

```ts
const base = [
  '# 测试策略蓝图',
  '',
  '## 风险策略',
  '旧风险策略',
  '',
  '## 验收口径',
  '旧验收口径',
].join('\n');
```

Draft rename positive:
- server content changes `## 风险策略` body to `服务端风险策略：优先覆盖支付链路`;
- draft changes heading `## 验收口径` to `## 质量口径` but keeps body `旧验收口径`;
- expected merged content keeps server risk body and draft heading `## 质量口径`.

Server rename positive:
- server changes heading `## 验收口径` to `## 质量口径` but keeps body;
- draft changes `## 风险策略` body to `用户风险策略：优先覆盖退款链路`;
- expected merged content keeps draft risk body and server heading `## 质量口径`.

Both same rename positive:
- server and draft both rename `## 验收口径` to `## 质量口径`;
- draft also changes `## 风险策略` body;
- expected merged content keeps draft risk body and `## 质量口径`.

Negative cases:
- different headings: server `## 服务验收口径`, draft `## 质量口径`;
- renamed body also changes: draft heading is `## 质量口径` and body is `用户质量口径：增加回滚检查`;
- other side changed renamed section: server changes `## 验收口径` body while draft renames that heading.
- other side moves and rewrites: use a trailing blank base artifact so the renamed section body remains byte-equal, then have the other side move `## 风险策略` and rewrite its body.
- heading depth changes: draft changes `## 验收口径` to `### 质量口径` while the server rewrites another section.

- [x] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section rename"
```

Expected: positive rename tests fail because no `自动合并非重叠变更` button appears.

### Task 2: 章节重命名自动合并实现

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add rename helpers near existing section helpers**

Add small helpers near `getSectionHeadingSet`:

```ts
const getSectionBodyLines = (sectionLines: string[]): string[] => sectionLines.slice(1);

type SectionRenameChange = {
  oldHeading: string;
  newHeading: string;
  newLines: string[];
};

const findSectionRenameChange = (
  baseSections: ParsedMarkdownSections,
  targetSections: ParsedMarkdownSections
): SectionRenameChange | null => {
  const baseHeadingSet = getSectionHeadingSet(baseSections);
  const targetHeadingSet = getSectionHeadingSet(targetSections);
  const deletedHeadings = getSectionOrder(baseSections).filter(heading => !targetHeadingSet.has(heading));
  const addedHeadings = getSectionOrder(targetSections).filter(heading => !baseHeadingSet.has(heading));
  if (deletedHeadings.length !== 1 || addedHeadings.length !== 1) return null;

  const baseSection = buildSectionMap(baseSections).get(deletedHeadings[0]);
  const targetSection = buildSectionMap(targetSections).get(addedHeadings[0]);
  if (!baseSection || !targetSection) return null;
  if (!areLineGroupsEqual(getSectionBodyLines(baseSection), getSectionBodyLines(targetSection))) {
    return null;
  }
  return {
    oldHeading: deletedHeadings[0],
    newHeading: addedHeadings[0],
    newLines: targetSection,
  };
};
```

If the implementation reuses maps for efficiency, keep behavior identical.

- [x] **Step 2: Implement `buildAutoMergedSectionRenameResult`**

Add a helper after `buildAutoMergedSectionMoveResult` and before `buildAutoMergedSectionAddDeleteResult`.

Core rules:
- parse base/server/draft; preamble must match;
- compute `serverRename` and `draftRename` with `findSectionRenameChange`;
- return `null` if neither side has a rename;
- return `null` if one side has a rename and the other side also has unrelated section add/delete;
- if both rename, `oldHeading` and `newHeading` must match;
- the non-renaming side must not modify the renamed old section body;
- the non-renaming side must keep base section order; mixed rename + movement remains manual;
- for every base section, merge in base order, replacing renamed old heading with the new section lines;
- non-renamed sections follow existing section rewrite rules: if both changed differently return `null`; otherwise prefer draft change, then server change, then base;
- require at least one non-rename content change from the opposite side, or both sides same rename, so the result is not just a no-op;
- summary is `合并轨迹：自动合并服务端与草稿的非重叠章节重命名`.

- [x] **Step 3: Register helper and preserve veto**

Update `autoMergedConflict` order:

```ts
const sectionRenameMerge = buildAutoMergedSectionRenameResult(
  artifactContent,
  conflictArtifact.content,
  editDraft
);
if (sectionRenameMerge) return sectionRenameMerge;
const sectionAddDeleteMerge = buildAutoMergedSectionAddDeleteResult(
  artifactContent,
  conflictArtifact.content,
  editDraft
);
if (sectionAddDeleteMerge) return sectionAddDeleteMerge;
if (hasMarkdownSectionSetChangeForAutoMerge(
  artifactContent,
  conflictArtifact.content,
  editDraft
)) return null;
return buildAutoMergedInsertionResult(
  artifactContent,
  conflictArtifact.content,
  editDraft
);
```

Rename helper must run before add/delete helper because rename is represented as one heading deletion plus one heading addition.

- [x] **Step 4: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section rename"
```

Expected: all section rename tests pass.

### Task 3: 文档记录与验证

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Modify: `docs/superpowers/plans/2026-06-20-new-agents-artifact-section-rename-merge.md`

- [x] **Step 1: Update todo progress**

Append after the fourth十三块 record:

```markdown
- 2026-06-20：完成第四十四块 CGA「Artifact 章节重命名自动合并」。
  - 保存冲突现在会在章节增删自动合并之外，识别保守章节重命名：当一侧只修改章节标题且正文不变，另一侧只改写其他章节时，可使用 `自动合并非重叠变更`。
  - 点击后编辑草稿会保留安全的新章节标题、另一侧非冲突章节改写，并记录 `artifact_auto_merge_applied` 活动轨迹，summary 区分 `非重叠章节重命名`。
  - 正文同时变化、双方重命名到不同标题、另一侧改写被重命名章节、重复标题或跨层级重组等歧义场景不显示自动合并入口，继续交给人工冲突处理。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "section rename"` 观察到缺少自动合并入口失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。
  - 剩余：段落级移动和更复杂三方 merge 解析仍可作为后续增强切片。
```

- [x] **Step 2: Mark plan checkboxes complete as steps finish**

Only mark `[x]` after each action is actually done.

- [x] **Step 3: Run full verification**

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

### Task 4: Commit boundary

**Files:**
- Stage only:
  - `docs/todos/new-agents-ux-professionalization.md`
  - `docs/superpowers/specs/2026-06-20-new-agents-artifact-section-rename-merge-design.md`
  - `docs/superpowers/plans/2026-06-20-new-agents-artifact-section-rename-merge.md`
  - `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Inspect status and staged files**

Run:

```bash
git status --short --branch
git diff --name-only
git ls-files --others --exclude-standard
```

Expected: only the files listed above are modified or untracked.

- [ ] **Step 2: Commit after verification**

Run:

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/specs/2026-06-20-new-agents-artifact-section-rename-merge-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-section-rename-merge.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 支持 Artifact 章节重命名自动合并"
```
