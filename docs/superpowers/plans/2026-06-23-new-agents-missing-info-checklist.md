# New Agents Missing Info Checklist Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 New Agents 当前阶段 artifact 增加 chat 与 artifact 双区可见的缺失信息清单，标明阻断性和用户下一步。

**Architecture:** 复用 `artifactQuality.ts` 作为共享前端诊断层，在现有质量 item 之上派生 `missingInfoItems`。`ArtifactPane` 和 `ChatPane` 都消费同一个 summary，不新增 API、store、runtime 或 workflow 专属分支。

**Tech Stack:** React 19、Zustand、Vitest、Testing Library、TypeScript。

---

### Task 1: 共享缺失信息模型

**Files:**
- Modify: `tools/new-agents/frontend/src/core/artifactQuality.ts`
- Test: `tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts`

- [ ] **Step 1: 写失败测试**

在 `artifactQuality.test.ts` 增加断言：

```ts
it('builds missing information items with blocking state and next actions', () => {
    const summary = buildArtifactQualitySummary({
        stage: clarifyStage,
        content: '# 草稿\n\n## 8. 阶段门禁\n\n等待确认',
        visualDiagnostics: [],
    });

    expect(summary.missingInfoItems).toEqual(expect.arrayContaining([
        expect.objectContaining({
            title: '缺少标题：# 需求分析文档',
            blocking: true,
            nextAction: expect.stringContaining('补充'),
        }),
        expect.objectContaining({
            title: '阶段门禁缺少决策项',
            blocking: false,
            nextAction: expect.stringContaining('确认'),
        }),
    ]));
});
```

- [ ] **Step 2: 运行 RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts`

Expected: FAIL，原因是 `missingInfoItems` 尚不存在。

- [ ] **Step 3: 最小实现**

在 `ArtifactQualitySummary` 中加入 `missingInfoItems`，从 `items.filter(item.status !== 'pass')` 派生。fail 为阻断，warning 为提醒；为 heading/field/visual/stage-gate/visual-diagnostic 生成明确 `nextAction`。

- [ ] **Step 4: 运行 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts`

Expected: PASS。

### Task 2: ArtifactPane 审阅面板展示

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: 写失败测试**

在 `ArtifactPane.test.tsx` 增加审阅面板断言：打开“审阅”后能看到“缺失信息清单”、“阻断”、“下一步”和缺失标题。

- [ ] **Step 2: 运行 RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: FAIL，原因是面板尚未渲染缺失信息清单。

- [ ] **Step 3: 最小实现**

在质量诊断 section 内，当 `artifactQualitySummary.missingInfoItems.length > 0` 时追加清单区。每项展示 `blocking ? '阻断' : '提醒'`、`reason` 和 `nextAction`；有 `actionDiagnosticId` 时复用现有 `focusArtifactVisualDiagnostic`。

- [ ] **Step 4: 运行 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: PASS。

### Task 3: ChatPane 同步提示

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`

- [ ] **Step 1: 写失败测试**

在 `ChatPane.test.tsx` 增加断言：设置当前阶段 `artifactContent` 为缺少 contract 的草稿后，渲染 ChatPane 能看到“当前阶段缺失信息”、“阻断”和下一步。

- [ ] **Step 2: 运行 RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx`

Expected: FAIL，原因是 ChatPane 尚未计算 artifact quality summary。

- [ ] **Step 3: 最小实现**

ChatPane 读取 `artifactContent`，导入 `buildArtifactQualitySummary`，按当前 stage 和当前阶段 visual diagnostics 计算 summary。非生成中且存在 `missingInfoItems` 时，在 messages 区顶部展示最多 3 条缺失项；存在更多项时显示剩余数量。

- [ ] **Step 4: 运行 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx`

Expected: PASS。

### Task 4: 文档记录与完整验证

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] **Step 1: 更新 todo**

把 E02 标记为已消化，记录 chat/artifact 双区缺失信息清单和验证命令。

- [ ] **Step 2: 运行聚焦验证**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/ChatPane.test.tsx`

Expected: PASS。

- [ ] **Step 3: 运行 lint**

Run: `cd tools/new-agents/frontend && npm run lint`

Expected: PASS。

- [ ] **Step 4: 运行 diff 检查**

Run: `git diff --check`

Expected: 无输出，exit 0。

- [ ] **Step 5: 提交**

```bash
git add docs/superpowers/specs/2026-06-23-new-agents-missing-info-checklist-design.md docs/superpowers/plans/2026-06-23-new-agents-missing-info-checklist.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents/frontend/src/core/artifactQuality.ts tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx tools/new-agents/frontend/src/components/ChatPane.tsx tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx
git commit -m "feat: 增加阶段缺失信息清单"
```
