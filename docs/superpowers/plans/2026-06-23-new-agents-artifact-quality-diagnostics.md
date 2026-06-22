# New Agents Artifact 质量诊断面板 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在共享 ArtifactPane 审阅侧栏中显示当前阶段 artifact contract / visual contract / 阶段门禁 / 渲染错误质量诊断。

**Architecture:** 新增 `artifactQuality.ts` 纯函数模块，从 `WorkflowStage` 合同、artifact Markdown 和现有 visual diagnostics 派生诊断摘要。ArtifactPane 只负责渲染摘要和调用已有 `focusArtifactVisualDiagnostic`，不新增 runtime、API、store 或专属 renderer。

**Tech Stack:** React 19、TypeScript 5、Vitest、Testing Library、现有 `workflow_manifest.json`、现有 Zustand store。

---

### Task 1: 建立质量诊断纯函数合同

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Create: `tools/new-agents/frontend/src/core/artifactQuality.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts`

- [ ] **Step 1: 写失败测试**

在 `artifactQuality.test.ts` 覆盖：

```ts
import { describe, expect, it } from 'vitest';
import { buildArtifactQualitySummary } from '../artifactQuality';
import type { ArtifactVisualDiagnostic, WorkflowStage } from '../types';

const clarifyStage: WorkflowStage = {
  id: 'CLARIFY',
  name: '需求澄清',
  description: '需求澄清',
  artifactContract: {
    requiredHeadings: [
      '# 需求分析文档',
      '## 8. 阶段门禁',
      '事实 ID',
      '状态',
    ],
  },
  visualContract: {
    requiredMermaidDiagrams: ['flowchart'],
    requiredStructuredVisuals: ['risk-board'],
  },
};

describe('buildArtifactQualitySummary', () => {
  it('reports missing headings, fields, visuals, and stage gate decisions', () => {
    const summary = buildArtifactQualitySummary({
      stage: clarifyStage,
      content: '# 草稿\n\n## 8. 阶段门禁\n\n等待确认',
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('fail');
    expect(summary.failedCount).toBe(5);
    expect(summary.warningCount).toBe(1);
    expect(summary.items).toEqual(expect.arrayContaining([
      expect.objectContaining({ category: 'heading', status: 'fail', title: '缺少标题：# 需求分析文档' }),
      expect.objectContaining({ category: 'field', status: 'fail', title: '缺少专业字段：事实 ID' }),
      expect.objectContaining({ category: 'field', status: 'fail', title: '缺少专业字段：状态' }),
      expect.objectContaining({ category: 'visual', status: 'fail', title: '缺少 Mermaid 图：flowchart' }),
      expect.objectContaining({ category: 'visual', status: 'fail', title: '缺少结构化可视化：risk-board' }),
      expect.objectContaining({ category: 'stage-gate', status: 'warning', title: '阶段门禁缺少决策项' }),
    ]));
  });

  it('passes when required headings, fields, visuals, and stage gate decisions exist', () => {
    const summary = buildArtifactQualitySummary({
      stage: clarifyStage,
      content: [
        '# 需求分析文档',
        '',
        '| 事实 ID | 状态 |',
        '| --- | --- |',
        '| F-1 | 已确认 |',
        '',
        '```mermaid',
        'flowchart TD',
        'A --> B',
        '```',
        '',
        '```ai4se-visual',
        '{"type":"risk-board","title":"风险看板","columns":["风险"],"rows":[{"风险":"R1"}]}',
        '```',
        '',
        '## 8. 阶段门禁',
        '- [x] 关键事实已确认',
      ].join('\n'),
      visualDiagnostics: [],
    });

    expect(summary.status).toBe('pass');
    expect(summary.failedCount).toBe(0);
    expect(summary.warningCount).toBe(0);
  });

  it('includes current-stage visual diagnostics as actionable failures', () => {
    const visualDiagnostic: ArtifactVisualDiagnostic = {
      id: 'structured-visual:CLARIFY:0',
      stageId: 'CLARIFY',
      kind: 'structured-visual',
      title: '结构化可视化格式错误',
      message: '结构化可视化必须是合法 JSON。',
      blockIndex: 0,
      createdAt: 1710000000000,
    };

    const summary = buildArtifactQualitySummary({
      stage: clarifyStage,
      content: '',
      visualDiagnostics: [visualDiagnostic],
    });

    expect(summary.items).toContainEqual(expect.objectContaining({
      category: 'visual-diagnostic',
      status: 'fail',
      actionDiagnosticId: 'structured-visual:CLARIFY:0',
    }));
  });
});
```

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts`

Expected: FAIL，因为 `artifactQuality.ts` 和 `buildArtifactQualitySummary` 尚不存在。

- [ ] **Step 3: 最小实现**

实现 `ArtifactContract`、`VisualContract`、`ArtifactQualityItem`、`ArtifactQualitySummary` 类型，并实现 `buildArtifactQualitySummary`。解析 Markdown fence 时只识别 fenced code block，不在 prose 中猜测图表。

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts`

Expected: PASS。

### Task 2: 在 ArtifactPane 审阅面板展示诊断

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: 写失败测试**

新增测试：

```ts
it('shows artifact quality diagnostics in the review panel', () => {
  useStore.setState({
    workflow: 'TEST_DESIGN',
    stageIndex: 0,
    artifactContent: '# 草稿\n\n## 8. 阶段门禁\n\n等待确认',
  });

  render(<ArtifactPane />);
  clickArtifactToolbarMenuItem('审阅');

  expect(screen.getByText('质量诊断')).toBeTruthy();
  expect(screen.getByText('缺少标题：# 需求分析文档')).toBeTruthy();
  expect(screen.getByText('缺少专业字段：事实 ID')).toBeTruthy();
  expect(screen.getByText('缺少 Mermaid 图：flowchart')).toBeTruthy();
  expect(screen.getByText('阶段门禁缺少决策项')).toBeTruthy();
});
```

新增定位测试：

```ts
it('focuses a visual diagnostic from the artifact quality panel', async () => {
  const scrollIntoView = vi.fn();
  window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
  useStore.setState({
    workflow: 'TEST_DESIGN',
    stageIndex: 0,
    artifactContent: ['```ai4se-visual', '{ broken', '```'].join('\n'),
    artifactVisualDiagnostics: [],
  });

  const { container } = render(<ArtifactPane />);
  await waitFor(() => {
    expect(screen.getByText('结构化可视化格式错误')).toBeTruthy();
  });

  clickArtifactToolbarMenuItem('审阅');
  fireEvent.click(screen.getByRole('button', { name: '定位质量诊断：结构化可视化格式错误' }));

  await waitFor(() => expect(scrollIntoView).toHaveBeenCalled());
  expect(container.querySelector('[data-artifact-visual-focused="true"]')).toBeTruthy();
});
```

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: FAIL，因为审阅面板还没有质量诊断区。

- [ ] **Step 3: 最小实现**

在 ArtifactPane 中：

- 读取 `currentStage = WORKFLOWS[workflow].stages[stageIndex]`。
- 用 `useMemo` 调用 `buildArtifactQualitySummary({ stage: currentStage, content: artifactContent, visualDiagnostics: currentStageVisualDiagnostics })`。
- 在“产物审阅”侧栏顶部渲染质量诊断 summary 和 items。
- 对带 `actionDiagnosticId` 的 item 渲染按钮，点击调用 `useStore.getState().focusArtifactVisualDiagnostic(actionDiagnosticId)`。

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactQuality.test.ts`

Expected: PASS。

### Task 3: 文档待办消化记录与验证

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] **Step 1: 更新 todo**

在 E03 章节记录本轮已消化：共享 ArtifactPane 审阅面板新增 artifact quality diagnostics，覆盖 headings、professional fields、visual contracts、stage gate checkbox 和 existing visual diagnostics。

- [ ] **Step 2: 扩大验证**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: all commands exit 0。

- [ ] **Step 3: 检查 diff 并提交**

Run:

```bash
git status --short
git diff --stat
git add docs/superpowers/specs/2026-06-23-new-agents-artifact-quality-diagnostics-design.md docs/superpowers/plans/2026-06-23-new-agents-artifact-quality-diagnostics.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/artifactQuality.ts tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat: 增加产物质量诊断面板"
```

Expected: commit succeeds on branch `codex/artifact-quality-diagnostics`。

