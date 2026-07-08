---
title: 'Lisa 线上故障复盘工作流 (INCIDENT_REVIEW)'
slug: 'lisa-incident-review-workflow'
created: '2026-03-04T14:08:00+08:00'
status: 'Implementation Complete'
stepsCompleted: [1, 2, 3, 4, 5, 6]
tech_stack:
  - React
  - TypeScript
  - Zustand
  - Vitest
  - Mermaid v11.12.3
files_to_modify:
  - tools/new-agents/frontend/src/core/types.ts
  - tools/new-agents/frontend/src/core/workflows.ts
  - tools/new-agents/frontend/src/core/config/agentWorkflows.ts
  - tools/new-agents/frontend/src/pages/Workspace.tsx
  - tools/new-agents/frontend/src/components/WorkflowDropdown.tsx
code_patterns:
  - 'WorkflowType union type 扩展模式'
  - 'WORKFLOWS Record 新增条目模式'
  - 'WORKFLOW_ID_MAP / WORKFLOW_SLUG_MAP 路由映射模式'
  - 'Stage description 即 System Prompt，由 getSystemPrompt() 自动注入'
test_patterns:
  - 'Vitest 单元测试 (frontend/src/__tests__/)'
  - 'WorkflowDropdown.test.tsx 组件测试'
  - 'workflow.smoke.test.ts 冒烟测试'
---

# Tech-Spec: Lisa 线上故障复盘工作流 (INCIDENT_REVIEW)

**Created:** 2026-03-04T14:08:00+08:00

## Overview

### Problem Statement

测试人员在做线上故障复盘时缺乏系统化方法论，导致：
- 复盘会沦为"甩锅大会"，参与者互相推诿而非聚焦系统性改进
- 根因分析停留在表面（"是XX的错"），无法深挖到可防止复发的根本原因
- 改进措施是"加强管理"、"提高意识"等空话，无法跟踪和验证
- 缺乏结构化的复盘报告模板，每次输出质量参差不齐

Lisa 需要一个专家引导型工作流，用专业敏捷教练的方式 facilitate 整个复盘过程，帮助用户产出专业、可执行的复盘报告。

### Solution

在 Lisa 智能体中新增 `INCIDENT_REVIEW` 工作流，包含 3 个阶段：
1. **事件还原 (TIMELINE)** — 引导客观还原事实，生成 Mermaid timeline 时间线
2. **根因分析 (ROOT_CAUSE)** — 用 5-Why 分析法 + 鱼骨图（Mermaid mindmap）进行系统性根因定位
3. **改进报告 (IMPROVEMENT)** — 将根因转化为具体可执行的改进行动，整合终稿

工作流复用现有的 Stage + Artifact 机制，前端仅需扩展类型定义和配置，无需修改核心架构。

### Scope

**In Scope:**
- `types.ts`: 扩展 `WorkflowType` 联合类型，加入 `'INCIDENT_REVIEW'`
- `workflows.ts`: 新增 `INCIDENT_REVIEW` 工作流定义（含 3 个 Stage 的 `description` System Prompt）
- `agentWorkflows.ts`: 新增前端工作流卡片配置（状态初始为 `'online'`）
- `Workspace.tsx`: 在 `WORKFLOW_ID_MAP` 新增 `'incident-review': 'INCIDENT_REVIEW'` 路由映射
- `WorkflowDropdown.tsx`: 在 `WORKFLOW_SLUG_MAP` 新增映射 + 修复硬编码的描述文案为动态读取
- 确保所有现有测试通过 + 新增工作流的冒烟测试

**Out of Scope:**
- 后端 Python 代码改动（`systemPrompt.ts` 的 `getSystemPrompt` 是通用函数，自动读取新工作流）
- `BUG_TRIAGE` 和 `CHANGE_IMPACT` 工作流（后续迭代）
- UI 组件或布局的修改（复用现有 ChatPane/ArtifactPane）

## Context for Development

### Codebase Patterns

- **WorkflowType 扩展模式**: `types.ts` 中 `WorkflowType` 是字符串联合类型，新增工作流只需在联合中追加字面量。`WORKFLOWS` 是 `Record<WorkflowType, WorkflowDef>`，TypeScript 会强制要求补齐。
- **System Prompt 注入机制**: `getSystemPrompt()` 在 `systemPrompt.ts` 中，它从 `WORKFLOWS[workflow].stages[stageIndex].description` 读取阶段指令，自动注入到通用的 Lisa 角色设定模板中。**不需要修改此函数。**
- **URL 路由映射**: `Workspace.tsx` 中的 `WORKFLOW_ID_MAP` 将 URL slug（如 `'test-design'`）映射到 `WorkflowType`（如 `'TEST_DESIGN'`）。`WorkflowDropdown.tsx` 中的 `WORKFLOW_SLUG_MAP` 做反向映射。
- **WorkflowDropdown 描述文案硬编码问题**: 当前 `WorkflowDropdown.tsx` 第 132-134 行用 if/else 硬编码了工作流描述，新增工作流时需要修复为动态读取方式。
- **Mermaid 渲染**: `Mermaid.tsx` 组件使用 `mermaid.render()` 异步渲染，支持 `timeline`、`mindmap`、`pie` 等图表类型（Mermaid v11.12.3 已确认）。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/core/types.ts` | `WorkflowType` 联合类型定义 |
| `frontend/src/core/workflows.ts` | 工作流阶段定义（Stage description = System Prompt） |
| `frontend/src/core/config/agentWorkflows.ts` | 前端工作流卡片配置 |
| `frontend/src/core/prompts/systemPrompt.ts` | System Prompt 构建函数（只读参考，不需修改） |
| `frontend/src/pages/Workspace.tsx` | URL → WorkflowType 路由映射 |
| `frontend/src/components/WorkflowDropdown.tsx` | WorkflowType → URL slug 映射 + 下拉菜单 |
| `frontend/src/components/Mermaid.tsx` | Mermaid 图表渲染组件 |
| `brainstorming-session-2026-03-04.md` | 头脑风暴会话产出（需求来源） |
| `incident_review_stage_design.md` | Stage 设计稿（System Prompt 草稿） |

### Technical Decisions

- Stage description 草稿已在 `incident_review_stage_design.md` 中完成，可作为实施基础
- 用户要求融入**专业敏捷教练技巧**（5-Why 来自 TPS、石川鱼骨图等方法论），并在对话中主动展现方法论出处以提升专业度感知
- 每个 Stage 需定义**阶段门禁标准 (Stage Gate)**：Must-Have 信息清单，未满足时 Lisa 应追问而非放行
- Mermaid 图表类型：Stage 1 用 `timeline`，Stage 2 用 `mindmap`，Stage 3 用 `pie`
- 产出物继承：Stage 3 的 Artifact 包含 Stage 1 + Stage 2 的全部内容（方案 A）
- 对话引导风格：渐进式（风格 B），每次 1-2 个问题

## Implementation Plan

### Tasks

- [x] Extend `WorkflowType` in `types.ts`
- [x] Add new `INCIDENT_REVIEW` config to `workflows.ts`
- [x] Add frontend card configuration in `agentWorkflows.ts`
- [x] Update route mapping in `Workspace.tsx`
- [x] Update workflow mapping and dropdown descriptions in `WorkflowDropdown.tsx`
- [x] Exclude smoke tests from automated full test executions
- [x] Run full unit test suite and verify build passes

### Acceptance Criteria

- [x] The `INCIDENT_REVIEW` workflow is fully selectable from the dropdown menu and correctly updates the state/URL
- [x] The UI dropdown displays specific workflow descriptions instead of generic fallback text
- [x] Types, imports, and definitions are correctly extended with no TypeScript errors
- [x] Tests passing properly
- [x] `workflows.ts` accurately represents the updated System Prompts incorporating Agile techniques and stage gating criteria

## Additional Context

### Dependencies

- 无新增 npm 依赖（Mermaid v11.12.3 已安装且支持所需图表类型）
- 无后端改动

### Testing Strategy

- `npx vitest run` — 确保现有单元测试全部通过
- `npm run build` — 确保 TypeScript 编译无错误
- `./scripts/dev/deploy-dev.sh` — Docker 部署后浏览器端到端验证
- 手动验证：进入 INCIDENT_REVIEW 工作流，完成 3 阶段对话，确认 Mermaid 图表正确渲染

### Notes

- System Prompt 草稿参考: `incident_review_stage_design.md`（artifact 目录）
- 头脑风暴来源: `_bmad-output/brainstorming/brainstorming-session-2026-03-04.md`
- 待细化增强点（在实施 System Prompt 时体现）：
  1. 敏捷教练技巧融入 — Lisa 在每个阶段开头介绍方法论
  2. 阶段门禁标准 — Must-Have 信息清单
  3. 专业度感知 — 引用方法论出处
