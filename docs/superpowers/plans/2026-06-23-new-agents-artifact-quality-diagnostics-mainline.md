# New Agents Artifact 质量诊断面板实施计划

> **给 agentic worker 的要求:** 必须使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按任务执行。本文使用 checkbox（`- [ ]`）追踪步骤。

**目标:** 在右侧 ArtifactPane 中增加共享产物质量诊断面板，让用户能看到当前 stage artifact 是否满足标题、可视化、阶段门禁、专业字段和运行时 visual 诊断要求。

**架构:** 新增前端纯函数模块 `tools/new-agents/frontend/src/core/artifactQuality.ts` 负责诊断计算，`ArtifactPane` 只负责展示。诊断完全派生自现有 workflow 配置、当前 Markdown artifact 和已有 visual diagnostics，不新增 backend endpoint、持久化模型、runtime 分支或 agent 专属 renderer。

**技术栈:** React 19、TypeScript、Zustand store、Vitest、Testing Library、现有 New Agents workflow config。

---

## 文件职责

- 新建 `tools/new-agents/frontend/src/core/artifactQuality.ts`：定义质量诊断类型和 `buildArtifactQualityDiagnostics()` 纯函数。
- 新建 `tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts`：覆盖完整产物通过、缺标题/缺可视化失败、visual runtime warning 合并、空 artifact 不展示。
- 修改 `tools/new-agents/frontend/src/components/ArtifactPane.tsx`：读取当前 workflow/stage/artifact/visual diagnostics，渲染质量诊断摘要和分组结果。
- 修改 `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`：覆盖面板可见性、失败项展示、warning 展示、空 artifact 不展示。
- 修改 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`：把 E03 标记为已消化并记录验证证据。

## Task 1: 纯函数质量诊断

**文件:**
- 新建: `tools/new-agents/frontend/src/core/artifactQuality.ts`
- 新建: `tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts`

- [ ] **Step 1: 先写失败单元测试**

在 `artifactQuality.test.ts` 写入以下测试，先表达目标行为：

```typescript
import { describe, expect, it } from 'vitest';
import { buildArtifactQualityDiagnostics } from '../artifactQuality';

describe('buildArtifactQualityDiagnostics', () => {
    it('marks a complete TEST_DESIGN CLARIFY artifact as passed', () => {
        const result = buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: [
                '# 需求分析',
                '## 核心业务规则',
                '## 待澄清问题',
                '## 阶段门禁',
                '```mermaid',
                'flowchart TD',
                'A[输入] --> B[澄清]',
                '```',
                '```ai4se-visual',
                '{"type":"requirement-map","title":"需求地图"}',
                '```',
            ].join('\\n'),
            visualDiagnostics: [],
        });

        expect(result?.status).toBe('pass');
        expect(result?.summary.failed).toBe(0);
        expect(result?.summary.warning).toBe(0);
        expect(result?.groups.some(group => group.id === 'contract')).toBe(true);
    });

    it('reports failed heading and visual checks for an incomplete artifact', () => {
        const result = buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: '# 需求分析\\n\\n只有摘要。',
            visualDiagnostics: [],
        });

        expect(result?.status).toBe('fail');
        expect(result?.summary.failed).toBeGreaterThanOrEqual(2);
        expect(result?.groups.flatMap(group => group.items).map(item => item.title)).toContain('必需标题');
        expect(result?.groups.flatMap(group => group.items).map(item => item.title)).toContain('必需可视化');
    });

    it('converts current-stage visual diagnostics into warnings', () => {
        const result = buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: [
                '# 需求分析',
                '## 核心业务规则',
                '## 待澄清问题',
                '## 阶段门禁',
                '```mermaid',
                'flowchart TD',
                'A --> B',
                '```',
                '```ai4se-visual',
                '{"type":"requirement-map","title":"需求地图"}',
                '```',
            ].join('\\n'),
            visualDiagnostics: [{
                id: 'structured-visual:CLARIFY:0',
                stageId: 'CLARIFY',
                kind: 'structured-visual',
                title: '结构化可视化渲染失败',
                message: 'JSON 缺少 title 字段。',
                blockIndex: 0,
                createdAt: 1710000000000,
            }],
        });

        expect(result?.status).toBe('warning');
        expect(result?.summary.warning).toBe(1);
        expect(result?.groups.flatMap(group => group.items).some(item => item.message.includes('JSON 缺少 title 字段'))).toBe(true);
    });

    it('returns null for blank artifacts', () => {
        expect(buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: '   ',
            visualDiagnostics: [],
        })).toBeNull();
    });
});
```

- [ ] **Step 2: 运行 RED 单元测试**

命令:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts
```

预期: 失败，原因是 `../artifactQuality` 尚不存在。

- [ ] **Step 3: 实现最小诊断模块**

创建 `artifactQuality.ts`，导出：

- `ArtifactQualityStatus = 'pass' | 'warning' | 'fail'`
- `ArtifactQualityItem`
- `ArtifactQualityGroup`
- `ArtifactQualityDiagnostics`
- `buildArtifactQualityDiagnostics(input)`

实现要求：

- 空白 artifact 返回 `null`。
- `contract` 分组检查至少一个 `#` 标题和至少一个 `##` 标题。
- `visual` 分组检查 Mermaid fence 和 `ai4se-visual` fence。
- `stage-gate` 分组检查至少一个专业关键词：`阶段门禁`、`验收`、`风险`、`开放问题`、`待澄清`、`handoff`、`checklist`。
- `runtime` 分组只合并当前 stage 的 visual diagnostics，并生成 warning 项。
- 状态优先级为 `fail > warning > pass`，summary 统计三类项数量。

- [ ] **Step 4: 运行 GREEN 单元测试**

命令:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts
```

预期: 通过。

## Task 2: ArtifactPane 质量面板

**文件:**
- 修改: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- 修改: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: 先写失败组件测试**

在 `ArtifactPane.test.tsx` 增加测试：

- 当前 `TEST_DESIGN/CLARIFY` artifact 缺 visual 时，页面展示 `产物质量诊断`、`需处理` 和 `必需可视化`。
- 当前 stage 有 visual diagnostic 时，页面展示 warning 诊断消息。
- 空 artifact 时不展示质量诊断面板。

- [ ] **Step 2: 运行 RED 组件测试**

命令:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

预期: 失败，原因是 ArtifactPane 尚未渲染质量面板。

- [ ] **Step 3: 实现面板展示**

在 `ArtifactPane.tsx` 中：

- import `buildArtifactQualityDiagnostics`。
- 用 `useMemo` 基于 `workflow`、`currentStageId`、`artifactContent`、`artifactVisualDiagnostics` 计算诊断。
- 仅在当前 artifact 非空且非编辑模式时展示面板。
- 面板展示标题 `产物质量诊断`、整体状态、通过/警告/失败计数。
- 分组展示 `contract`、`visual`、`stage-gate`、`runtime` 的诊断项。
- 保持现有 visual diagnostic focus anchor 和 read-only history preview 行为不变。

- [ ] **Step 4: 运行 GREEN 组件测试**

命令:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
```

预期: 通过。

## Task 3: Todo 记录与最终验证

**文件:**
- 修改: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] **Step 1: 更新 E03 消化记录**

把 E03 从活动候选更新为已消化，记录：

- 新增共享前端诊断模块。
- ArtifactPane 面板展示。
- 验证命令。
- 非目标：无 backend endpoint、无 runtime/SSE/persistence 变更、无自动修复。

- [ ] **Step 2: 运行聚焦验证**

命令:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

预期: 所有命令 exit 0。

- [ ] **Step 3: 聚焦提交**

命令:

```bash
git add docs/superpowers/specs/2026-06-23-new-agents-artifact-quality-diagnostics-mainline-design.md docs/superpowers/plans/2026-06-23-new-agents-artifact-quality-diagnostics-mainline.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents/frontend/src/core/artifactQuality.ts tools/new-agents/frontend/src/core/__tests__/artifactQuality.test.ts tools/new-agents/frontend/src/components/ArtifactPane.tsx tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx
git commit -m "feat: 增加产物质量诊断面板"
```

## 自检

- Spec 覆盖：Task 1 覆盖诊断计算，Task 2 覆盖用户可见面板，Task 3 覆盖 todo 记录和验证。
- 占位扫描：无 TBD、TODO、implement later 或未定义步骤。
- 类型一致性：`buildArtifactQualityDiagnostics` 是测试和 `ArtifactPane` 共用的唯一入口。
