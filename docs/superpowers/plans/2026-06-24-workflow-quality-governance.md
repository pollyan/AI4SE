# Workflow Quality Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic Artifact/Workflow quality governance view inside the existing New Agents artifact review drawer.

**Architecture:** Add a pure frontend quality model in `src/core/workflowQuality.ts`, typed through existing workflow manifest stage contracts, then render its summary inside `ArtifactPane`'s existing review drawer. No backend API, runtime, SSE, persistence, or agent-specific infrastructure changes.

**Tech Stack:** React 19, TypeScript, Zustand store, Vitest, Testing Library, Tailwind classes already used in `ArtifactPane`.

---

## File Structure

- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - Add optional `artifactContract` and `visualContract` fields to `WorkflowStage`.
- Create: `tools/new-agents/frontend/src/core/workflowQuality.ts`
  - Own all deterministic quality rules and exported summary types.
- Create: `tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts`
  - RED/GREEN coverage for pass, missing heading, missing visual, empty artifact, and current-stage visual diagnostic.
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - Compute summary with `useMemo` and render quality governance section in the existing review drawer.
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
  - Verify the review drawer exposes quality score, issue counts, and action items.
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - Mark E03/E08 as consumed by this milestone.
- Modify: `docs/todos/refactor/README.md`
  - Record this milestone as an active candidate consumed in the current worktree.

## Task 1: Core Quality Model RED

**Files:**
- Test: `tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts`
- Modify later: `tools/new-agents/frontend/src/core/types.ts`
- Create later: `tools/new-agents/frontend/src/core/workflowQuality.ts`

- [ ] **Step 1: Write failing tests**

Create `workflowQuality.test.ts` with tests that import `buildWorkflowQualitySummary` from `../workflowQuality` and use `WORKFLOWS.TEST_DESIGN`.

Required test cases:

```ts
import { describe, expect, it } from 'vitest';
import { WORKFLOWS } from '../workflows';
import { buildWorkflowQualitySummary } from '../workflowQuality';

describe('buildWorkflowQualitySummary', () => {
  it('passes a complete stage artifact with contract evidence', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'STRATEGY',
      artifactMarkdown: [
        '# 测试策略蓝图',
        '## 1. 策略摘要',
        '## 2. 质量目标',
        '## 3. 风险识别与 FMEA',
        '### 3.1 风险矩阵',
        '### 3.2 风险明细',
        '## 4. 测试技术选型',
        '## 5. 测试分层策略',
        '### 5.1 测试金字塔',
        '### 5.2 分层明细',
        '## 6. 测试点拓扑',
        '## 7. 资源与取舍',
        '## 8. 阶段门禁',
        '| 风险 ID | 测试点 ID | 覆盖建议 |',
        '| R1 | TP1 | 覆盖核心链路 |',
        '```mermaid',
        'quadrantChart',
        '```',
        '```mermaid',
        'block-beta',
        '```',
        '```ai4se-visual',
        '{"type":"risk-board","items":[]}',
        '```',
      ].join('\n'),
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('pass');
    expect(summary.score).toBeGreaterThanOrEqual(90);
    expect(summary.failedCount).toBe(0);
    expect(summary.actionItems).toEqual([]);
  });

  it('fails when required headings are missing', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'STRATEGY',
      artifactMarkdown: '# 测试策略蓝图\n\n## 1. 策略摘要\n\n## 8. 阶段门禁',
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('fail');
    expect(summary.failedCount).toBeGreaterThan(0);
    expect(summary.actionItems.some(item => item.includes('补齐必需章节'))).toBe(true);
  });

  it('warns when visual contract evidence is missing', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'STRATEGY',
      artifactMarkdown: [
        '# 测试策略蓝图',
        '## 1. 策略摘要',
        '## 2. 质量目标',
        '## 3. 风险识别与 FMEA',
        '### 3.1 风险矩阵',
        '### 3.2 风险明细',
        '## 4. 测试技术选型',
        '## 5. 测试分层策略',
        '### 5.1 测试金字塔',
        '### 5.2 分层明细',
        '## 6. 测试点拓扑',
        '## 7. 资源与取舍',
        '## 8. 阶段门禁',
        '风险 ID 测试点 ID 覆盖建议',
      ].join('\n'),
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('warning');
    expect(summary.warningCount).toBeGreaterThan(0);
    expect(summary.actionItems.some(item => item.includes('补齐可视化'))).toBe(true);
  });

  it('fails empty artifact content', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'CLARIFY',
      artifactMarkdown: '   ',
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('fail');
    expect(summary.score).toBeLessThan(50);
    expect(summary.actionItems[0]).toContain('生成或恢复当前阶段产出物');
  });

  it('uses only current-stage visual diagnostics as quality issues', () => {
    const summary = buildWorkflowQualitySummary({
      workflow: WORKFLOWS.TEST_DESIGN,
      stageId: 'CLARIFY',
      artifactMarkdown: '# 需求分析文档\n\n## 8. 阶段门禁\n\n```mermaid\nflowchart TD\n```',
      visualDiagnostics: [
        {
          id: 'mermaid:CLARIFY:0',
          stageId: 'CLARIFY',
          kind: 'mermaid',
          title: 'Mermaid 渲染失败',
          message: '第 1 个 Mermaid 图无法渲染',
          createdAt: 1,
        },
        {
          id: 'mermaid:STRATEGY:0',
          stageId: 'STRATEGY',
          kind: 'mermaid',
          title: '其他阶段失败',
          message: '其他阶段问题',
          createdAt: 2,
        },
      ],
    });

    expect(summary.actionItems).toContain('修复当前阶段可视化渲染问题：第 1 个 Mermaid 图无法渲染');
    expect(summary.actionItems).not.toContain('修复当前阶段可视化渲染问题：其他阶段问题');
  });
});
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts
```

Expected: FAIL because `src/core/workflowQuality.ts` does not exist.

## Task 2: Core Quality Model GREEN

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Create: `tools/new-agents/frontend/src/core/workflowQuality.ts`
- Test: `tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts`

- [ ] **Step 1: Add workflow contract types**

Update `WorkflowStage`:

```ts
export interface WorkflowStage {
    id: string;
    name: string;
    description: string;
    template?: string;
    artifactContract?: {
        requiredHeadings?: string[];
    };
    visualContract?: {
        requiredMermaidDiagrams?: string[];
        requiredStructuredVisuals?: string[];
    };
}
```

- [ ] **Step 2: Implement minimal quality model**

Create `workflowQuality.ts` with exported types and `buildWorkflowQualitySummary`.

Implementation requirements:

- Normalize whitespace before matching.
- Treat required heading strings as present if the normalized artifact contains the normalized requirement.
- Detect Mermaid diagram types with fenced ```mermaid blocks and plain body matching the required type.
- Detect structured visuals with fenced ```ai4se-visual blocks and body matching the required type.
- Stage gate passes when artifact contains `阶段门禁`, `Stage Gate`, or `gate`.
- Score starts at 100, subtracts 18 per failed check and 8 per warning, minimum 0; empty artifact content caps the score at 40 because there is no reviewable evidence.
- `status` is `fail` if any failed check, `warning` if any warning and no failures, otherwise `pass`.

- [ ] **Step 3: Run core tests to verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts
```

Expected: PASS.

## Task 3: ArtifactPane Review UI RED

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- Modify later: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Add failing component test**

Add a test near existing review panel tests:

```ts
it('shows workflow quality governance in the artifact review panel', () => {
  useStore.setState({
    workflow: 'TEST_DESIGN',
    stageIndex: 1,
    artifactContent: '# 测试策略蓝图\n\n## 1. 策略摘要\n\n## 8. 阶段门禁',
    artifactVisualDiagnostics: [
      {
        id: 'structured-visual:STRATEGY:0',
        stageId: 'STRATEGY',
        kind: 'structured-visual',
        title: '结构化可视化无效',
        message: 'risk-board JSON 缺 items',
        createdAt: 1,
      },
    ],
  });

  render(<ArtifactPane />);
  fireEvent.click(screen.getByLabelText('更多产物操作'));
  fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));

  expect(screen.getByText('质量治理')).toBeTruthy();
  expect(screen.getByText(/质量分/)).toBeTruthy();
  expect(screen.getByText(/补齐必需章节/)).toBeTruthy();
  expect(screen.getByText(/修复当前阶段可视化渲染问题/)).toBeTruthy();
});
```

- [ ] **Step 2: Run component test to verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "workflow quality governance"
```

Expected: FAIL because `ArtifactPane` does not render the quality governance section yet.

## Task 4: ArtifactPane Review UI GREEN

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Import quality builder**

Add:

```ts
import { buildWorkflowQualitySummary } from '../core/workflowQuality';
```

- [ ] **Step 2: Compute summary**

Near current stage memo values, add:

```ts
  const workflowQualitySummary = useMemo(
    () => buildWorkflowQualitySummary({
      workflow: WORKFLOWS[workflow],
      stageId: currentStageId,
      artifactMarkdown: artifactContent,
      visualDiagnostics: artifactVisualDiagnostics,
    }),
    [artifactContent, artifactVisualDiagnostics, currentStageId, workflow]
  );
```

- [ ] **Step 3: Render quality governance section**

Inside `showReviewPanel`, before unresolved comments, render:

```tsx
<section className="space-y-3 rounded-lg border border-[#1e293b] bg-[#020617] p-3">
  <div className="flex items-start justify-between gap-3">
    <div>
      <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">质量治理</h4>
      <p className="mt-1 text-xs text-slate-500">{workflowQualitySummary.summary}</p>
    </div>
    <div className="text-right">
      <div className="text-lg font-bold text-slate-100">质量分 {workflowQualitySummary.score}</div>
      <div className="text-[10px] font-semibold text-slate-500">{workflowQualitySummary.statusLabel}</div>
    </div>
  </div>
  <div className="grid grid-cols-3 gap-2">
    <div className="rounded border border-emerald-400/20 bg-emerald-400/5 p-2 text-center text-xs text-emerald-200">
      通过 {workflowQualitySummary.passedCount}
    </div>
    <div className="rounded border border-amber-400/20 bg-amber-400/5 p-2 text-center text-xs text-amber-200">
      警告 {workflowQualitySummary.warningCount}
    </div>
    <div className="rounded border border-red-400/20 bg-red-400/5 p-2 text-center text-xs text-red-200">
      失败 {workflowQualitySummary.failedCount}
    </div>
  </div>
  <div className="space-y-2">
    {workflowQualitySummary.checks.slice(0, 6).map((check) => (
      <article key={check.id} className="rounded border border-[#1e293b] bg-black/10 p-2">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-semibold text-slate-200">{check.label}</span>
          <span className="text-[10px] font-bold text-slate-500">{check.statusLabel}</span>
        </div>
        <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{check.evidence}</p>
        <p className="mt-1 text-[11px] leading-relaxed text-slate-400">{check.impact}</p>
      </article>
    ))}
  </div>
  <div className="rounded border border-[#1e293b] bg-black/10 p-2">
    <div className="text-[11px] font-bold uppercase tracking-wide text-slate-500">待处理项</div>
    {workflowQualitySummary.actionItems.length === 0 ? (
      <p className="mt-1 text-xs text-slate-500">当前没有阻断项。</p>
    ) : (
      <ul className="mt-2 space-y-1">
        {workflowQualitySummary.actionItems.map((item) => (
          <li key={item} className="text-xs leading-relaxed text-slate-300">- {item}</li>
        ))}
      </ul>
    )}
  </div>
</section>
```

- [ ] **Step 4: Run component test to verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "workflow quality governance"
```

Expected: PASS.

## Task 5: Docs And Verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/superpowers/plans/2026-06-24-workflow-quality-governance.md`

- [ ] **Step 1: Update todo status**

Mark E03 and E08 as consumed by this milestone and add a short completion note with verification commands.

- [ ] **Step 2: Run focused verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Review changed files**

Run:

```bash
git status --short
git diff --stat
git diff -- docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md
```

Expected: only this milestone's files are modified.

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-24-workflow-quality-governance-design.md docs/superpowers/plans/2026-06-24-workflow-quality-governance.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/workflowQuality.ts tools/new-agents/frontend/src/core/__tests__/workflowQuality.test.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 增加工作流质量治理闭环"
```

Expected: one focused commit on `codex/workflow-quality-governance-current`.

## Self-Review

- Spec coverage: tasks cover quality model, review UI, tests, docs, verification, and commit.
- Placeholder scan: no placeholder work remains; all commands and paths are explicit.
- Type consistency: `WorkflowStage` gains optional contract fields consumed by `workflowQuality.ts`; `ArtifactPane` consumes exported summary only.
