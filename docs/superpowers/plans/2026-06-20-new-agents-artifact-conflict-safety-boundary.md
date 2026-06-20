# New Agents Artifact 冲突安全边界收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 让 Artifact 保存冲突在无法证明自动合并安全时显示可读的人工处理原因，并保留用户草稿和对比路径。

**Architecture:** 继续复用 `ArtifactPane.tsx` 现有冲突卡片、自动合并结果、拒绝原因渲染和编辑草稿状态。本轮只补齐 `autoMergeRejectionReason` 的安全边界，不改服务端 API，不新增 Lisa/Alex 或 workflow 专属分支。

**Tech Stack:** React 19, TypeScript, Zustand, Vitest, Testing Library.

---

## File Structure

- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - 新增复杂冲突转人工的 RED 测试。
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - 在 `autoMergeRejectionReason` 中增加通用人工处理 fallback。
- Modify: `docs/todos/new-agents-ux-professionalization.md`
  - 记录本轮完成项和剩余边界。
- Create: `docs/superpowers/specs/2026-06-20-new-agents-artifact-conflict-safety-boundary-design.md`
- Create: `docs/superpowers/plans/2026-06-20-new-agents-artifact-conflict-safety-boundary.md`

## Commit Boundary

一个 commit：`feat(new-agents): 收口 Artifact 冲突安全边界`

该 commit 覆盖一个完整用户能力包：复杂保存冲突无法安全自动合并时，系统明确转人工、保留草稿、保留对比路径。

---

### Task 1: RED 测试覆盖复杂冲突转人工

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Write the failing test**

在同章节段落冲突测试附近新增用例：

```tsx
it('shows a manual merge reason when overlapping section edits cannot be proven safe', async () => {
    vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
        '产出物已被更新，请刷新后再保存',
        {
            stageId: 'STRATEGY',
            content: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：服务端补充支付失败后的回归策略。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：服务端新增风控拦截链路。',
            ].join('\n'),
            versionNumber: 3,
        },
    ));
    const baseContent = [
        '# 测试策略蓝图',
        '',
        '## 风险策略',
        '段落A：覆盖支付主链路。',
        '',
        '段落B：覆盖退款逆向链路。',
    ].join('\n');
    const draftContent = [
        '# 测试策略蓝图',
        '',
        '## 风险策略',
        '段落A：用户补充支付失败后的降级策略。',
        '',
        '段落B：用户补充退款失败后的人工复核。',
    ].join('\n');
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

    await screen.findByRole('button', { name: '对比服务端版本' });
    expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    expect(screen.getByText('自动合并暂不可用')).not.toBeNull();
    expect(screen.getByText('双方改动存在重叠或顺序无法证明安全，已保留你的草稿，请打开对比服务端版本后手工确认。')).not.toBeNull();
    expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(draftContent);
});
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "manual merge reason"
```

Expected: FAIL because `自动合并暂不可用` or the new generic description is not rendered for this conflict.

---

### Task 2: GREEN 实现通用人工处理原因

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Add fallback rejection reason**

在 `autoMergeRejectionReason` 中保留现有优先级：

```tsx
const autoMergeRejectionReason = useMemo(() => {
  if (!conflictArtifact || autoMergedConflict) return null;
  if (hasUnsafeSameSectionParagraphInsertRewriteForAutoMerge(
    artifactContent,
    conflictArtifact.content,
    editDraft
  )) {
    return {
      title: '自动合并暂不可用',
      description: '双方改动涉及同一章节的多处段落，已保留你的草稿，请手工确认后重试保存。',
    };
  }
  if (hasStructuredBlockReorderForAutoMerge(
    artifactContent,
    conflictArtifact.content,
    editDraft
  )) {
    return {
      title: '结构化块重排需人工处理',
      description: '检测到列表项、表格行或代码块位置调整，为避免误合并，请打开对比服务端版本手动确认。',
    };
  }
  return {
    title: '自动合并暂不可用',
    description: '双方改动存在重叠或顺序无法证明安全，已保留你的草稿，请打开对比服务端版本后手工确认。',
  };
}, [artifactContent, autoMergedConflict, conflictArtifact, editDraft]);
```

- [x] **Step 2: Run focused GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "manual merge reason|auto-merge unavailable|structured block"
```

Expected: PASS. Existing specific rejection reasons remain specific.

---

### Task 3: 回归安全自动合并不被覆盖

**Files:**
- No production edits unless test fails.

- [x] **Step 1: Run focused automatic merge regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges same-section paragraph insertion|table row|list item|fenced block line reordering|paragraph movement|section"
```

Expected: PASS. If any safe auto-merge test fails, inspect `autoMergedConflict` ordering before touching logic.

---

### Task 4: 更新 todo 记录

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [x] **Step 1: Append progress record**

在 Artifact 协作体验深化进展末尾追加：

```markdown
- 2026-06-20：完成第六十块 CGA「Artifact 冲突安全边界收口」。
  - 保存冲突无法证明自动合并安全时，冲突卡片会显示 `自动合并暂不可用` 和手工处理路径，明确草稿已保留并引导打开 `对比服务端版本`。
  - 已有可证明安全的 `自动合并非重叠变更` 继续保留；结构化块重排和同章节多段插入/改写等已有具体拒绝原因优先显示。
  - 本轮不新增复杂三方 merge 算法分支；后续只有出现完整、可证明安全的用户冲突场景时，才按 Artifact 冲突处理能力包继续推进。
  - 验证：`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "manual merge reason|auto-merge unavailable|structured block"`；`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "auto-merges same-section paragraph insertion|table row|list item|fenced block line reordering|paragraph movement|section"`；`npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`；`npm run lint`；`npm run build`；`npm run test`；`git diff --check`。
  - 剩余：更复杂三方 merge 解析不再按单算法分支拆薄；歧义场景保持人工处理。
```

- [x] **Step 2: Check docs**

Run:

```bash
git diff -- docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-conflict-safety-boundary-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-conflict-safety-boundary.md
```

Expected: docs state the intended verification commands explicitly and do not include fill-in placeholder markers.

---

### Task 5: 扩展验证与提交

**Files:**
- All files above.

- [x] **Step 1: Run full ArtifactPane test**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

Expected: PASS.

- [x] **Step 2: Run lint**

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: PASS.

- [x] **Step 3: Run build**

```bash
cd tools/new-agents/frontend && npm run build
```

Expected: PASS.

- [x] **Step 4: Run full frontend tests**

```bash
cd tools/new-agents/frontend && npm run test
```

Expected: PASS.

- [x] **Step 5: Run diff check**

```bash
git diff --check
```

Expected: no output.

- [x] **Step 6: Commit**

```bash
git status --short --branch
git diff --stat
git add docs/todos/new-agents-ux-professionalization.md docs/superpowers/specs/2026-06-20-new-agents-artifact-conflict-safety-boundary-design.md docs/superpowers/plans/2026-06-20-new-agents-artifact-conflict-safety-boundary.md tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 收口 Artifact 冲突安全边界"
```

Expected: one focused commit.

## Self-Review

- Spec coverage: user story, scope, non-goals, scenarios, acceptance, risk, verification all map to tasks.
- Placeholder scan: no fill-in placeholder markers remain.
- Type consistency: no new exported types or APIs are introduced.
