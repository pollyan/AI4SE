# Artifact 审阅诊断中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 New Agents ArtifactPane 中展示当前阶段 artifact 是否满足 workflow manifest 的 artifact/visual/stage gate 质量契约，并聚合正文暴露的待补信息、阻断项和下一步。

**Architecture:** 新增前端纯函数 `artifactDiagnostics.ts` 负责从 manifest contract、当前 Markdown 和 visual runtime diagnostics 计算诊断结果与缺失信息清单；`ArtifactPane.tsx` 只负责展示。继续复用共享 workflow manifest、Zustand store、ArtifactPane 和现有 visual diagnostic 机制，不新增 API 或 agent-specific 分支。

**Tech Stack:** React 19、TypeScript、Vitest、Testing Library、Zustand、现有 workflow manifest。

---

## 当前执行状态

本 plan 对应的代码切片在隔离 worktree `/Users/anhui/Documents/myProgram/AI4SE/.worktrees/artifact-quality-diagnostics-goal-mainline` 中收束，分支为 `codex/artifact-quality-diagnostics-goal-mainline`。当前主工作区存在 intent-tester zip、`docs/plans/tech-debt.md` 和两个 todo 文件的既有未提交改动，本切片不在主工作区写入，避免覆盖用户改动。

本轮采用的能力包边界是 Artifact 审阅诊断中心：合并 E02 当前 artifact 审阅侧缺失信息清单和 E03 Artifact 质量诊断面板。Alex `STORY_BREAKDOWN`、Alex `PRD_REVIEW`、Lisa 测试资产质量闭环和 handoff 上下文强化不纳入本 commit。

TDD 记录口径：本切片先新增 `artifactReview.test.ts` 和 `ArtifactPane.test.tsx` 中的审阅诊断断言，再实现 `artifactDiagnostics.ts` 与 UI 展示。当前 worktree 已把该 TDD 切片整理到基于 `master` 的干净分支，并重新运行 GREEN 与 CI 等价验证。

## 验证结果

- `npm run test -- --run src/core/__tests__/artifactReview.test.ts src/components/__tests__/ArtifactPane.test.tsx src/core/config/__tests__/workflows.test.ts src/__tests__/testHygiene.test.ts`: 4 个测试文件通过，166 个测试通过。
- `npm run lint`: 通过，`tsc --noEmit` 无错误。
- `git diff --check`: 通过，无空白错误。
- `git status -sb`: commit 后 worktree 干净。

### Task 1: Manifest Contract 类型、诊断核心和缺失信息提取

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflowRegistry.ts`
- Create: `tools/new-agents/frontend/src/core/artifactDiagnostics.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/artifactReview.test.ts`

- [x] **Step 1: 写 RED 测试**

新增 `artifactReview.test.ts`，覆盖：

```ts
import { describe, expect, it } from 'vitest';
import { buildArtifactQualityDiagnostics } from '../artifactDiagnostics';

describe('buildArtifactQualityDiagnostics', () => {
  it('reports missing required headings and required visuals for the current stage', () => {
    const result = buildArtifactQualityDiagnostics({
      workflowId: 'TEST_DESIGN',
      stageId: 'STRATEGY',
      artifactContent: '# 测试策略蓝图\n\n## 1. 策略摘要\n\n## 8. 阶段门禁\n\n- checked=true',
      visualDiagnostics: [],
    });

    expect(result.status).toBe('fail');
    expect(result.items).toEqual(expect.arrayContaining([
      expect.objectContaining({
        category: 'heading',
        status: 'fail',
        title: '缺少必填标题',
      }),
      expect.objectContaining({
        category: 'mermaid',
        status: 'fail',
        title: '缺少 Mermaid 图表',
      }),
      expect.objectContaining({
        category: 'structured-visual',
        status: 'fail',
        title: '缺少结构化可视化',
      }),
    ]));
  });

  it('passes when the artifact satisfies the stage contract', () => {
    const result = buildArtifactQualityDiagnostics({
      workflowId: 'TEST_DESIGN',
      stageId: 'STRATEGY',
      artifactContent: [
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
        '```mermaid',
        'quadrantChart',
        '```',
        '```mermaid',
        'block-beta',
        '```',
        '```ai4se-visual',
        '{"type":"risk-board","title":"风险板","columns":[]}',
        '```',
      ].join('\n'),
      visualDiagnostics: [],
    });

    expect(result.status).toBe('pass');
    expect(result.summary.fail).toBe(0);
  });

  it('adds current-stage runtime visual diagnostics as warnings', () => {
    const result = buildArtifactQualityDiagnostics({
      workflowId: 'TEST_DESIGN',
      stageId: 'CLARIFY',
      artifactContent: '# 需求分析文档\n\n## 8. 阶段门禁\n\n```mermaid\nflowchart TD\n```',
      visualDiagnostics: [{
        id: 'mermaid:CLARIFY:0',
        stageId: 'CLARIFY',
        kind: 'mermaid',
        title: 'Mermaid 图表渲染失败',
        message: 'syntax error',
        createdAt: 1,
      }],
    });

    expect(result.items).toEqual(expect.arrayContaining([
      expect.objectContaining({
        category: 'runtime-visual',
        status: 'warn',
        detail: 'syntax error',
      }),
    ]));
  });

  it('extracts blocking missing information from artifact sections', () => {
    const result = buildArtifactQualityDiagnostics({
      workflowId: 'TEST_DESIGN',
      stageId: 'CLARIFY',
      artifactContent: [
        '# 需求分析文档',
        '## 5. 待澄清问题',
        '- 阻断：支付失败重试次数缺失，必须由 PM 确认。',
        '- 待确认：优惠券叠加规则需要补充样例。',
        '## 8. 阶段门禁',
        '- checked=false：核心异常链路未确认，无法进入策略制定。',
      ].join('\n'),
      visualDiagnostics: [],
    });

    expect(result.summary.openQuestions).toBe(3);
    expect(result.openQuestions).toEqual(expect.arrayContaining([
      expect.objectContaining({
        blocking: true,
        title: '支付失败重试次数缺失',
        nextAction: '补充输入或手工修订后重新生成当前阶段产物。',
      }),
      expect.objectContaining({
        blocking: false,
        title: '优惠券叠加规则需要补充样例',
      }),
    ]));
  });
});
```

- [x] **Step 2: 运行 RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactReview.test.ts`

Expected: FAIL，原因是 `artifactDiagnostics.ts` 不存在。

- [x] **Step 3: 最小实现**

补充 contract 类型，新增 `buildArtifactQualityDiagnostics()`，用正则扫描 Markdown heading、fenced mermaid、fenced `ai4se-visual` JSON 类型、阶段门禁关键词和缺失信息章节。缺失信息最多返回 6 条，每条包含标题、阻断性、详情和下一步。

- [x] **Step 4: 运行 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactReview.test.ts`

Expected: PASS。

### Task 2: ArtifactPane 审阅诊断 UI

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: 写 RED 组件测试**

在 `ArtifactPane.test.tsx` 新增测试：打开“产物审阅”后能看到“审阅诊断”、失败数、缺少标题、缺少 Mermaid、缺少结构化可视化；另一个测试证明 runtime visual diagnostic 会显示在诊断面板；第三个测试证明待澄清/阻断信息会显示为缺失信息清单。

- [x] **Step 2: 运行 RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "审阅诊断"`

Expected: FAIL，原因是 UI 尚未展示诊断面板。

- [x] **Step 3: 最小 UI 实现**

在 `ArtifactPane` 中用 `useMemo` 调用 `buildArtifactQualityDiagnostics()`，在审阅面板顶部增加紧凑诊断区。失败项用红色，警告项用琥珀色，通过项用绿色；缺失信息用待处理列表展示阻断性和下一步；空 artifact 展示“暂无产物可诊断”。

- [x] **Step 4: 运行 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "审阅诊断"`

Expected: PASS。

### Task 3: 回归验证和记录

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/superpowers/specs/2026-06-23-artifact-quality-diagnostics-panel-design.md`
- Modify: `docs/superpowers/plans/2026-06-23-artifact-quality-diagnostics-panel.md`

- [x] **Step 1: 运行前端聚焦验证**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactReview.test.ts src/components/__tests__/ArtifactPane.test.tsx src/core/config/__tests__/workflows.test.ts src/__tests__/testHygiene.test.ts
```

Expected: PASS。

- [x] **Step 2: 运行 TypeScript / lint 等价验证**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: PASS。该命令覆盖本轮新增 TypeScript 类型、`ArtifactPane` UI 接线和 workflow registry 类型变更。

- [x] **Step 3: 更新 todo 消化记录**

记录 E02 当前 artifact 审阅缺失信息清单和 E03 Artifact 质量诊断面板已合并完成，说明未纳入自动修复、LLM judge、跨 run 趋势和 Lisa 资产闭环。

- [x] **Step 4: 运行 diff 检查**

Run: `git diff --check`

Expected: 无输出，退出码 0。

- [x] **Step 5: 提交**

Run:

```bash
git status -sb
git add docs/superpowers/specs/2026-06-23-artifact-quality-diagnostics-panel-design.md docs/superpowers/plans/2026-06-23-artifact-quality-diagnostics-panel.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/workflowRegistry.ts tools/new-agents/frontend/src/core/artifactDiagnostics.ts tools/new-agents/frontend/src/core/__tests__/artifactReview.test.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat(new-agents): 增加 Artifact 审阅诊断中心"
```
