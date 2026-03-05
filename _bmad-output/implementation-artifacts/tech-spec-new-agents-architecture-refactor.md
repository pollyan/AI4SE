---
title: 'new-agents 架构重构 - Prompt 整理与配置集中化'
slug: 'new-agents-architecture-refactor'
created: '2026-03-05'
status: 'completed'
stepsCompleted: [1, 2, 3]
tech_stack: [TypeScript, React, Zustand, Python, Flask, SQLAlchemy]
files_to_modify:
  - tools/new-agents/frontend/src/core/prompts/systemPrompt.ts
  - tools/new-agents/frontend/src/core/prompts/alexSystemPrompt.ts
  - tools/new-agents/frontend/src/core/workflows.ts
  - tools/new-agents/frontend/src/core/llm.ts
  - tools/new-agents/frontend/src/core/types.ts
  - tools/new-agents/frontend/src/core/config/agents.ts
  - tools/new-agents/frontend/src/core/config/agentWorkflows.ts
  - tools/new-agents/frontend/src/store.ts
  - tools/new-agents/frontend/src/pages/Workspace.tsx
  - tools/new-agents/frontend/src/components/WorkflowDropdown.tsx
  - tools/new-agents/frontend/src/components/Header.tsx
  - tools/new-agents/frontend/src/services/chatService.ts
  - tools/new-agents/backend/models.py
code_patterns:
  - 工作流 Prompt 提取到独立文件（incident_review/ 和 idea_brainstorm/ 已有先例）
  - AgentConfig 集中式配置（config/agents.ts 已有基础结构）
  - 公共片段组合模式（fragments 拼装为完整 System Prompt）
test_patterns:
  - Vitest 单元测试（frontend，当前 81 tests passing）
  - PyTest 后端测试（backend/tests/test_api.py）
  - TDD 先行：每个重构步骤先写测试再迁移
---

# Tech-Spec: new-agents 架构重构 - Prompt 整理与配置集中化

**Created:** 2026-03-05

## Overview

### Problem Statement

引入 Alex Agent 后，`tools/new-agents` 项目暴露出多项架构和代码质量问题：

1. **System Prompt 70% 重复（DRY 违背）**：`systemPrompt.ts`（Lisa）和 `alexSystemPrompt.ts`（Alex）中的 mark 变更标识规则、阶段推进协议、输出格式约束、Mermaid 渲染约束完全重复，仅角色人设不同。
2. **硬编码 agentId 判断散落 3 处（OCP 违规）**：`llm.ts`、`store.ts`、`WorkflowDropdown.tsx` 均通过 `if (agentId === 'alex')` 做分支，新增 Agent 需改动多处。
3. **阶段 Prompt 存放不一致**：INCIDENT_REVIEW 和 IDEA_BRAINSTORM 已提取到独立文件，但 TEST_DESIGN（~160行）和 REQ_REVIEW（~110行）仍内联在 `workflows.ts` 中，导致其膨胀到 437 行。
4. **Agent 配置碎片化**：同一 Agent 的元数据分散在 agents.ts / agentWorkflows.ts / store.ts / 组件硬编码中。
5. **store.ts barrel re-export** 导致 prompts → store → workflows 循环依赖风险。
6. **Workflow slug 正反映射重复定义**（Workspace.tsx 与 WorkflowDropdown.tsx 各一份）。
7. **零散质量问题**：FENCE 变量多处重复声明、欢迎消息用脆弱的字符串前缀判断、后端每次请求重建 engine。

近期还将新增工作流，若不重构，每次扩展都在累积技术债。

### Solution

分 3 个 Phase 完成纯重构（行为不变）：

- **Phase 1 - Prompt 整理**：提取内联 Prompt、抽取 System Prompt 公共片段、建立统一构建函数
- **Phase 2 - 配置集中化**：扩展 AgentConfig、消除硬编码、统一 slug 映射
- **Phase 3 - 代码质量**：清理 re-export、修复脆弱判断逻辑、后端 engine 复用

全程 TDD，先写新结构的测试再迁移代码。

### Scope

**In Scope:**
- A1: System Prompt 公共片段抽取（mark 规则、阶段推进、输出格式、Mermaid 约束）
- A2: 消除 `agentId === 'alex'` 硬编码（3 处）
- A3: 提取 TEST_DESIGN / REQ_REVIEW 的内联 Prompt 到独立文件
- B1: 清理 store.ts 的 barrel re-export，消除循环依赖风险
- B2: 统一 Workflow slug 映射到单一数据源
- B3: Agent 配置集中化（displayTitle、welcomeTemplate 等字段）
- C1: FENCE 常量统一到公共位置
- C2: 欢迎消息判断逻辑从字符串前缀改为状态标志
- C3: 后端 SQLAlchemy engine/sessionmaker 复用

**Out of Scope:**
- 功能变更（纯重构，所有行为保持不变）
- 新 Agent / 新工作流的开发
- 后端业务逻辑扩展
- UI 组件或视觉设计重构

## Context for Development

### Codebase Patterns

- **已有的 Prompt 提取模式**：`prompts/incident_review/` 和 `prompts/idea_brainstorm/` 已经将阶段 Prompt 提取到独立 `.ts` 文件，每个文件 export 一个 `const XXX_PROMPT` 字符串，在 `workflows.ts` 中 import 后赋值给 `stage.description`。新的 TEST_DESIGN 和 REQ_REVIEW 提取应遵循完全相同的模式。
- **AgentConfig 模式**：`config/agents.ts` 已定义 `AgentConfig` 接口和集中的 Agent 列表。扩展该接口是配置集中化的自然路径。
- **Zustand Store 模式**：`store.ts` 使用 `zustand/middleware` 的 `persist` 中间件，状态变更通过 `set()` 调用。
- **TDD 基线**：当前 81 个 Vitest 测试全部通过，包含 workflows.test.ts（7 tests）验证工作流结构完整性。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `core/prompts/systemPrompt.ts` | Lisa System Prompt（将被拆分为公共片段 + 人设） |
| `core/prompts/alexSystemPrompt.ts` | Alex System Prompt（将被拆分为公共片段 + 人设） |
| `core/workflows.ts` | 工作流定义（437行，含内联 Prompt，将瘦身到 ~100行） |
| `core/llm.ts` | LLM 调用核心（含 agentId 硬编码） |
| `core/config/agents.ts` | Agent 配置（将扩展字段） |
| `core/config/agentWorkflows.ts` | 工作流卡片配置 |
| `store.ts` | Zustand 状态（含 re-export 和欢迎消息） |
| `pages/Workspace.tsx` | Workspace 页面（含 WORKFLOW_ID_MAP） |
| `components/WorkflowDropdown.tsx` | 工作流切换（含 WORKFLOW_SLUG_MAP + 硬编码标题） |
| `components/Header.tsx` | 头部导航 |
| `services/chatService.ts` | 聊天服务（含脆弱的欢迎消息判断） |
| `backend/models.py` | 后端数据模型（engine 复用问题） |
| `core/prompts/incident_review/*.ts` | 参考模式：已提取的 Prompt 文件 |
| `core/prompts/idea_brainstorm/*.ts` | 参考模式：已提取的 Prompt 文件 |

### Technical Decisions

- **纯重构原则**：所有修改必须保证行为不变，现有 81 个测试必须始终通过
- **TDD 先行**：先为新结构编写测试，再执行迁移
- **渐进式迁移**：每个 Phase 独立可交付，Phase 间可部署验证
- **保持向下兼容**：`WORKFLOWS` 对象的外部接口不变，仅内部实现重组

## Implementation Plan

### Phase 概览（Party Mode 修订版）

```
Phase 1: 基础清理 + Prompt 提取 (✔️ Completed)
  1.1 C1: FENCE 常量统一到公共位置 (✔️ Completed)
  1.2 B2: 统一 Workflow slug 映射到单一数据源 (✔️ Completed)
  1.3 A3: 提取 TEST_DESIGN / REQ_REVIEW 内联 Prompt 到独立文件 (✔️ Completed)
  1.4 A1: 抽取 System Prompt 公共片段 + buildSystemPrompt 统一函数 (✔️ Completed)
  验收门：npm test 全量通过 + 本地 Docker 部署验证 (✔️ Passed)

Phase 2: 配置集中化 + 硬编码消除 (✔️ Completed)
  2.1 B3: 扩展 AgentConfig（只加 displayTitle + welcomeTemplate + icon） (✔️ Completed)
  2.2 A2: 消除 3 处 agentId 硬编码（依赖 B3 + A1） (✔️ Completed)
  2.3 C2: 欢迎消息判断改为使用 welcomeTemplate 替换状态标志硬编码 (✔️ Completed)
  验收门：npm test 全量通过 + 本地 Docker 部署验证 (✔️ Passed)

Phase 3: 清理 + 后端 (✔️ Completed)
  3.1 B1: 清理 store.ts 空白气泡 bug （调整判定逻辑，不再只依赖 content，还有 trim 等） (✔️ Completed)
  3.2 C3: 全局移除 Lisa 硬编码展示语句 (✔️ Completed)
  验收门：npm test 全量通过 + 本地 Docker 端到端浏览器自动化验证 (✔️ Passed)
```

### 关键设计决策（Party Mode 共识）

1. **C1 和 B2 提前到 Phase 1 开头**：体量极小但可避免后续 Prompt 提取时产生二次编辑
2. **buildSystemPrompt 统一接口**：
   ```typescript
   buildSystemPrompt(config: {
     agentId: string;
     workflow: WorkflowType;
     stageIndex: number;
     currentArtifact: string;
     stageArtifacts?: Record<string, string>;  // 可选，Alex 用，Lisa 暂不用
   }) => string
   ```
   新增 Agent 只需在 `personas/` 加文件，不改函数签名
3. **AgentConfig 不过度设计**：只加 `displayTitle` 和 `welcomeTemplate`，`personaPrompt` 保持在 `personas/` 目录独立管理
4. **Prompt 提取不需要单独测试**：静态字符串常量，现有 workflows.test.ts 的结构断言自动覆盖
5. **需新增测试的点**：buildSystemPrompt 组装测试、slug 映射一致性测试

### Tasks

(待 Step 2 深度调查后填充)

### Acceptance Criteria

(待 Step 3 生成后填充)

## Additional Context

### Dependencies

- 无外部依赖变更
- 所有改动在 `tools/new-agents/` 目录内完成

### Testing Strategy

- **TDD 先行**：每个任务先写失败测试，再迁移代码使测试通过
- **单元测试**：每个 Phase 完成后 `npm test` 确保 81+ tests 全部通过
- **E2E 回归**：每个 Phase 部署到本地 Docker 后，用浏览器走关键路径（选择 Agent -> 选择工作流 -> 发消息 -> 检查产出物 -> 后退按钮）
- **后端测试**：C3 修改通过 PyTest 验证
- **模板字符串陷阱**：提取 Prompt 时注意保持换行和空白一致，检查 workflows.test.ts 中是否有精确内容匹配的断言（如有则改为模式匹配）

### Notes

- 架构审计报告详见：`architecture_review.md`（artifact）
- 近期将新增工作流，A3 和 B2 的收益会立即体现
- 远期可能新增 Agent，A1 和 A2 的收益会在那时兑现
- Party Mode 参与者：Winston（架构师）、Amelia（开发者）、Quinn（QA） — 共识已纳入上述设计决策
