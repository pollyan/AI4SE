# New Agents Artifact 段落级移动自动合并 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Artifact 保存冲突在同一章节内安全的段落移动场景下提供 `自动合并非重叠变更`。

**Architecture:** 继续复用 `ArtifactPane.tsx` 内现有三方 Markdown 解析、冲突卡片、编辑草稿和活动轨迹。新增保守 paragraph movement helper，注册在 section rewrite 之后、section move 之前；只处理同一章节内唯一段落块移动，其他歧义场景继续人工处理。

**Tech Stack:** React 19、TypeScript 5、Zustand、Vitest、Testing Library。

---

### Task 1: 段落级移动自动合并测试

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Add RED tests near existing section merge tests**

Add helper:

```ts
const baseParagraphMoveContent = [
    '# 测试策略蓝图',
    '',
    '## 风险策略',
    '段落A：覆盖支付主链路。',
    '',
    '段落B：覆盖退款逆向链路。',
    '',
    '段落C：覆盖风控拦截链路。',
    '',
    '## 验收口径',
    '旧验收口径',
].join('\n');

const renderParagraphMoveConflict = (
    serverContent: string,
    draftContent: string,
    baseContent = baseParagraphMoveContent,
) => {
    vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
        '产出物已被更新，请刷新后再保存',
        {
            stageId: 'STRATEGY',
            content: serverContent,
            versionNumber: 3,
        },
    ));
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 1,
        currentRunId: 'run-123',
        artifactContent: baseContent,
        stageArtifacts: {
            STRATEGY: baseContent,
        },
        artifactHistory: [
            {
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: baseContent,
                stageId: 'STRATEGY',
            },
        ],
        artifactAuditEvents: [],
    });

    render(<ArtifactPane />);
    fireEvent.click(screen.getByTitle('编辑产出物'));
    fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
        target: {
            value: draftContent,
        },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
};
```

Add tests whose names contain `paragraph movement`:

1. `auto-merges paragraph movement when draft moves one paragraph and server rewrites another paragraph in the same section`
2. `auto-merges paragraph movement when server moves one paragraph and draft rewrites another paragraph in the same section`
3. `auto-merges paragraph movement when both sides move the same paragraph to the same position`
4. `does not auto-merge paragraph movement when the moved paragraph is also rewritten`
5. `does not auto-merge paragraph movement when paragraph blocks repeat`
6. `does not auto-merge paragraph movement when both sides move paragraphs differently`
7. `does not auto-merge paragraph movement across sections`
8. `does not auto-merge paragraph movement for list items`

Positive case expected merge for draft move + server rewrite:

```ts
[
    '# 测试策略蓝图',
    '',
    '## 风险策略',
    '段落C：覆盖风控拦截链路。',
    '',
    '段落A：服务端补充支付主链路观测点。',
    '',
    '段落B：覆盖退款逆向链路。',
    '',
    '## 验收口径',
    '旧验收口径',
].join('\n')
```

Assert:
- positive tests click `自动合并非重叠变更`;
- textarea equals expected merged Markdown;
- `artifactAuditEvents` contains `artifact_auto_merge_applied` with summary `合并轨迹：自动合并服务端与草稿的非重叠段落移动`;
- negative tests wait for `对比服务端版本` and assert no auto-merge button.

- [x] **Step 2: Verify RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "paragraph movement"
```

Expected: positive paragraph movement tests fail because no `自动合并非重叠变更` button appears.

### Task 2: 段落级移动自动合并实现

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add paragraph block parser helpers near section helpers**

Add types and helpers near `buildSectionMap`:

```ts
type ParsedParagraphBlock = {
  baseIndex: number;
  lines: string[];
  key: string;
};

type ParsedSectionParagraphs = {
  heading: string;
  blocks: ParsedParagraphBlock[];
};

type ParagraphMoveChange = {
  heading: string;
  movedBaseIndex: number;
  targetOrder: number[];
};

const isUnsafeParagraphMoveBlock = (lines: string[]): boolean => (
  lines.some(line => (
    /^```/.test(line.trim())
    || /^[-*+]\s+/.test(line.trim())
    || /^\d+\.\s+/.test(line.trim())
    || /^\|.*\|$/.test(line.trim())
  ))
);
```

Implement `parseSectionParagraphBlocks(sectionLines: string[]): ParsedParagraphBlock[] | null`:
- ignore `sectionLines[0]` heading;
- split body into blocks of consecutive non-empty lines;
- return `null` if fewer than 2 blocks;
- return `null` if any block is unsafe by `isUnsafeParagraphMoveBlock`;
- return `null` if any block key repeats within the section.

Implement `findSingleMovedParagraphIndex(baseOrder: number[], targetOrder: number[]): number | null`:
- try every `fromIndex` / `toIndex` pair where `fromIndex !== toIndex`;
- remove the value at `fromIndex`, insert it at `toIndex`, and compare with `targetOrder`;
- return the moved base index value only when exactly one pair matches;
- return `null` when no pair or multiple pairs match.

- [x] **Step 2: Add `findParagraphMoveChange`**

Implement:

```ts
const findParagraphMoveChange = (
  baseSections: ParsedMarkdownSections,
  targetSections: ParsedMarkdownSections
): ParagraphMoveChange | null => {
  if (!hasSameSectionShape(baseSections, targetSections)) return null;
  let move: ParagraphMoveChange | null = null;
  for (const baseSection of baseSections.sections) {
    const targetSection = buildSectionMap(targetSections).get(baseSection.heading);
    if (!targetSection) return null;
    const baseBlocks = parseSectionParagraphBlocks(baseSection.lines);
    const targetBlocks = parseSectionParagraphBlocks(targetSection);
    if (!baseBlocks || !targetBlocks) {
      if (!areLineGroupsEqual(baseSection.lines, targetSection)) return null;
      continue;
    }
    const baseKeys = baseBlocks.map(block => block.key);
    const targetKeys = targetBlocks.map(block => block.key);
    if (baseKeys.length !== targetKeys.length) return null;
    if (new Set(baseKeys).size !== baseKeys.length) return null;
    if (targetKeys.some(key => !baseKeys.includes(key))) {
      if (!areLineGroupsEqual(baseSection.lines, targetSection)) return null;
      return null;
    }
    const targetOrder = targetKeys.map(key => baseKeys.indexOf(key));
    const baseOrder = baseBlocks.map(block => block.baseIndex);
    if (areSectionOrdersEqual(baseOrder.map(String), targetOrder.map(String))) continue;
    const movedBaseIndex = findSingleMovedParagraphIndex(baseOrder, targetOrder);
    if (movedBaseIndex === null) return null;
    if (move) return null;
    move = {
      heading: baseSection.heading,
      movedBaseIndex,
      targetOrder,
    };
  }
  return move;
};
```

If implementation chooses a cleaner way to derive `movedBaseIndex`, keep behavior equivalent and deterministic: moving `段落C` before `段落A` in `[0, 1, 2] -> [2, 0, 1]` must return `2`, not `0`.

- [x] **Step 3: Add `buildAutoMergedParagraphMoveResult`**

Implement after `buildAutoMergedSectionRewriteResult`:
- parse base/server/draft;
- require matching preamble and same section shape for all three;
- compute `serverMove` and `draftMove`;
- return `null` if neither side has a move;
- if both move, require same `heading`, same `movedBaseIndex`, same `targetOrder`, and no extra paragraph rewrite in that moved section;
- if only one side moves, the non-moving side must keep the moved section paragraph order equal to base;
- build merged sections in base order;
- for moved section, use the move side target order; for each base paragraph index in that order:
  - if the non-moving side changed that paragraph and it is not the moved paragraph, use non-moving lines;
  - if the move side changed paragraph content, return `null`;
  - if the non-moving side changed the moved paragraph, return `null`;
  - otherwise use base lines;
- for non-moved sections, reuse existing section rewrite logic: both changed differently returns `null`, otherwise prefer draft, then server, then base;
- require at least one non-move content change or both sides same move;
- return summary `合并轨迹：自动合并服务端与草稿的非重叠段落移动`.

- [x] **Step 4: Register helper**

Update `autoMergedConflict` order:

```ts
const paragraphMoveMerge = buildAutoMergedParagraphMoveResult(
  artifactContent,
  conflictArtifact.content,
  editDraft
);
if (paragraphMoveMerge) return paragraphMoveMerge;
const sectionMoveMerge = buildAutoMergedSectionMoveResult(
  artifactContent,
  conflictArtifact.content,
  editDraft
);
```

Place it after section rewrite and before section move, because it handles same-section changes that section rewrite rejects.

- [x] **Step 5: Verify GREEN**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "paragraph movement"
```

Expected: all paragraph movement tests pass.

### Task 3: 文档记录与完整验证

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`
- Modify: `docs/superpowers/plans/2026-06-20-new-agents-artifact-paragraph-move-merge.md`
- Modify: `docs/superpowers/specs/2026-06-20-new-agents-artifact-paragraph-move-merge-design.md`

- [x] **Step 1: Update todo progress**

Append after the 第四十四块 record:

```markdown
- 2026-06-20：完成第四十五块 CGA「Artifact 段落级移动自动合并」。
  - 保存冲突现在会在章节级合并能力之外，识别同一章节内保守段落移动：当一侧只移动唯一段落块，另一侧只改写同章节或其他章节的非冲突段落时，可使用 `自动合并非重叠变更`。
  - 点击后编辑草稿会保留安全的段落顺序和另一侧非冲突段落改写，并记录 `artifact_auto_merge_applied` 活动轨迹，summary 区分 `非重叠段落移动`。
  - 重复段落、移动段落本身被改写、双方移动不同段落、跨章节移动、列表项/表格行/fenced block 移动等歧义场景不显示自动合并入口，继续交给人工冲突处理。
  - 验证：先运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "paragraph movement"` 观察到缺少自动合并入口失败；实现后同命令通过，并运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。
  - 剩余：更复杂三方 merge 解析、跨章节语义移动和结构化块内部重排仍可作为后续增强切片。
```

- [x] **Step 2: Mark plan checkboxes complete as steps finish**

Only mark `[x]` after each action is actually done.

- [x] **Step 3: Address review veto gap**

Reviewer found that forbidden movement could still auto-merge through `buildAutoMergedSectionRewriteResult` when the other side changed a different section. Added regression tests for:

- cross-section paragraph movement paired with unrelated server section rewrite;
- list item reorder paired with unrelated server section rewrite;
- table row reorder paired with unrelated server section rewrite;
- fenced block movement paired with unrelated server section rewrite;
- paragraph split paired with same-section server rewrite.

Implementation now makes section rewrite auto-merge bypass movement semantics: safe paragraph movement is handled by the paragraph helper, while cross-section movement and unsafe list/table/fenced movement stay manual.

- [x] **Step 4: Run full verification**

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

本轮 worker 指令要求不要 stage、commit、push，因此 Task 4 保留未执行。

**Files:**
- Stage only:
  - `docs/todos/new-agents-ux-professionalization.md`
  - `docs/superpowers/specs/2026-06-20-new-agents-artifact-paragraph-move-merge-design.md`
  - `docs/superpowers/plans/2026-06-20-new-agents-artifact-paragraph-move-merge.md`
  - `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Inspect status and staged files**

Run:

```bash
git status --short --branch
git diff --name-only
git ls-files --others --exclude-standard
```

Expected: only the five files above are changed or untracked.

- [ ] **Step 2: Commit**

Run:

```bash
git add docs/todos/new-agents-ux-professionalization.md \
  docs/superpowers/specs/2026-06-20-new-agents-artifact-paragraph-move-merge-design.md \
  docs/superpowers/plans/2026-06-20-new-agents-artifact-paragraph-move-merge.md \
  tools/new-agents/frontend/src/components/ArtifactPane.tsx \
  tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 支持 Artifact 段落移动自动合并"
```

Expected: focused commit with only planned files.
