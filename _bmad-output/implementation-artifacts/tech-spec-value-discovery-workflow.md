---
title: 'VALUE_DISCOVERY 工作流实现'
slug: 'value-discovery-workflow'
created: '2026-03-05'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['TypeScript', 'Vitest']
files_to_modify:
  - 'prompts/value_discovery/elevator.ts (新建)'
  - 'prompts/value_discovery/persona.ts (新建)'
  - 'prompts/value_discovery/journey.ts (新建)'
  - 'prompts/value_discovery/blueprint.ts (新建)'
  - 'core/types.ts (修改)'
  - 'core/workflows.ts (修改)'
  - 'core/config/agentWorkflows.ts (修改)'
  - 'core/config/__tests__/workflows.test.ts (修改)'
  - 'pages/WorkflowSelect.tsx (修改 - 图标映射)'
  - 'core/prompts/buildSystemPrompt.ts (修改 - 通用化文案)'
code_patterns:
  - 'Stage 文件导出 XXX_PROMPT + XXX_TEMPLATE'
  - '有 Mermaid 时 import FENCE from utils/constants'
  - '无 Mermaid 时不需要 import'
  - '模板字符串用 \\${FENCE} 插值包裹 Mermaid 代码块'
test_patterns:
  - 'Vitest describe/it/expect'
  - '校验工作流 stages 数量、id、name'
  - '校验 description 长度 > 100'
---

# Tech-Spec: VALUE_DISCOVERY 工作流实现

**Created:** 2026-03-05

## Overview

### Problem Statement

Alex 智能体目前只有 IDEA_BRAINSTORM 工作流（从0到1：模糊想法 → 发散探索 → 选方向），缺少一个帮用户把**已有方向**系统化验证的工作流。用户已经知道想做什么，但说不清楚值不值得做、目标用户是谁、核心场景在哪里。需要一个"价值发现"工作流来通过结构化方法深度梳理产品方向的场景和价值。

### Solution

新增 `VALUE_DISCOVERY` 工作流，包含 4 个 Stage（ELEVATOR 价值定位 → PERSONA 用户画像 → JOURNEY 用户旅程 → BLUEPRINT 需求蓝图）。复用现有的阶段式对话 + Artifact 产出物架构模式，替代原计划中的 `PRD_CREATION`。

### Scope

**In Scope:**
- 4 个 Stage 的 Prompt + Template 文件（`prompts/value_discovery/` 目录下 4 个 `.ts` 文件）
- `types.ts` 注册 `VALUE_DISCOVERY` 工作流类型和 slug
- `workflows.ts` 添加完整工作流定义（含 import、stages、onboarding）
- `agentWorkflows.ts` 将已有的 `prd-creation`（plan 状态）替换为 `value-discovery`（online 状态）
- `WorkflowSelect.tsx` 添加 `Compass` 图标到 import 和 `ICONS` 映射
- `buildSystemPrompt.ts` 将 L37 的硬编码文案通用化
- 单元测试（`workflows.test.ts` 中添加 VALUE_DISCOVERY 相关断言）

**Out of Scope:**
- STORY_BREAKDOWN / COMPETITIVE_ANALYSIS 工作流实现
- `buildSystemPrompt.ts` 的架构性重构（仅修改 L37 的文案）
- 中间阶段（PERSONA/JOURNEY）的前序 Artifact 上下文注入（已知限制，后续优化）

## Context for Development

### Codebase Patterns

1. **Stage Prompt + Template 分离模式**：每个 Stage 对应一个 `.ts` 文件，导出 `XXX_PROMPT`（行为指令字符串）和 `XXX_TEMPLATE`（Markdown 产出物模板字符串）。模板中使用 `\${FENCE}` 插值来引用 Mermaid 代码块包裹符。
2. **工作流注册模式**：在 `workflows.ts` 中 import 所有 Stage 的 Prompt/Template，然后在 `WORKFLOWS` 对象中定义工作流结构。
3. **类型注册模式**：在 `types.ts` 中的 `WorkflowType` 联合类型和 `WORKFLOW_SLUGS` 对象中注册新工作流。
4. **Agent 卡片注册模式**：在 `agentWorkflows.ts` 的 `AGENT_WORKFLOWS` 数组中添加工作流卡片配置。
5. **Alex 智能体特殊逻辑**：`buildSystemPrompt.ts` 中 L28 判断 `isLastStage`，L36-38 对 Alex 注入前序 Artifact 整合指令。VALUE_DISCOVERY 的 BLUEPRINT 阶段天然复用此逻辑。**但 L37 硬编码了"产品概念简报"（IDEA_BRAINSTORM 术语），需要通用化**。
6. **图标映射机制**：`WorkflowSelect.tsx` L31-41 定义了 `ICONS: Record<string, LucideIcon>` 映射，将 `agentWorkflows.ts` 中的字符串 icon 名映射到 lucide-react 组件。新增图标必须同时更新此映射。
7. **`SLUG_TO_WORKFLOW` 自动派生**：`types.ts` L30-32 通过 `Object.fromEntries` 从 `WORKFLOW_SLUGS` 自动生成反向映射，无需手动添加。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/core/prompts/idea_brainstorm/define.ts` | 参考 Stage Prompt+Template 文件结构和导出模式 |
| `frontend/src/core/prompts/idea_brainstorm/concept.ts` | 参考最终整合阶段的 Prompt 写法 |
| `frontend/src/core/workflows.ts` | 工作流注册入口，需要添加 VALUE_DISCOVERY |
| `frontend/src/core/types.ts` | 类型注册，需要添加 VALUE_DISCOVERY 类型和 slug |
| `frontend/src/core/config/agentWorkflows.ts` | Agent 卡片注册，需要替换 prd-creation |
| `frontend/src/core/config/__tests__/workflows.test.ts` | 测试文件，需要添加 VALUE_DISCOVERY 测试 |
| `frontend/src/core/prompts/buildSystemPrompt.ts` | System Prompt 构建逻辑，**需修改 L37 通用化文案** |
| `frontend/src/core/utils/constants.ts` | FENCE 常量定义 |
| `frontend/src/pages/WorkflowSelect.tsx` | 图标映射，**需添加 Compass 到 import 和 ICONS** |

### Technical Decisions

- VALUE_DISCOVERY **替代**原来的 `prd-creation`（plan 状态），而非在旁边新增。改 id 为 `value-discovery`，status 改为 `online`。
- `buildSystemPrompt.ts` L37 的硬编码"产品概念简报"需改为通用描述，适用于 Alex 的所有工作流。
- Mermaid 图表使用 `FENCE` 常量，与 IDEA_BRAINSTORM 保持一致。
- JOURNEY 阶段使用 Mermaid `journey` 图类型，**Prompt 中必须包含语法约束规则**（避免使用 `HH:MM` 时间格式，参考历史修复）。
- 4 个 Stage 的 Prompt 文件放在 `prompts/value_discovery/` 目录下，命名为 `elevator.ts`、`persona.ts`、`journey.ts`、`blueprint.ts`。
- 4 个 Stage 的 Prompt 和 Template **具体内容**参见设计文档 `value_discovery_stage_design.md`（完整路径见末尾参考文档）。
- **已知限制**：`previousArtifactsContext` 仅在 `isLastStage` 时注入，PERSONA 和 JOURNEY 阶段无法通过此机制获取前序 Artifact。但 LLM 对话历史中包含前序讨论，实际影响有限。后续可优化为所有非首阶段都注入前序 Artifact 摘要。

## Implementation Plan

### Tasks

> 任务按依赖关系排序：最底层模块优先，注册层在后，测试层最后。

- [x] Task 1: ELEVATOR Prompt + Template
  - File: `frontend/src/core/prompts/value_discovery/elevator.ts`（新建）
  - Action: 导出 `ELEVATOR_PROMPT` 和 `ELEVATOR_TEMPLATE`。
  - Notes: 无 Mermaid，不需要 import FENCE。Prompt 不少于 100 字符。
  - **内容来源**：`value_discovery_stage_design.md` — Stage 1: ELEVATOR 章节。

- [x] Task 2: PERSONA Prompt + Template
  - File: `frontend/src/core/prompts/value_discovery/persona.ts`（新建）
  - Action: 导出 `PERSONA_PROMPT` 和 `PERSONA_TEMPLATE`。
  - Notes: 无 Mermaid，不需要 import FENCE。
  - **内容来源**：`value_discovery_stage_design.md` — Stage 2: PERSONA 章节。

- [x] Task 3: JOURNEY Prompt + Template
  - File: `frontend/src/core/prompts/value_discovery/journey.ts`（新建）
  - Action: 导出 `JOURNEY_PROMPT` 和 `JOURNEY_TEMPLATE`。
  - Notes: 需要 `import { FENCE } from '../../utils/constants'`。Template 中用 `\${FENCE}mermaid` 包裹 journey 图。
  - **Mermaid 语法约束（必须追加到 Prompt 末尾）**：`注意：Mermaid journey 图中不要使用 HH:MM 时间格式，如需表示时间请使用中文描述。section 名称和任务描述中不要使用英文冒号。`
  - **内容来源**：`value_discovery_stage_design.md` — Stage 3: JOURNEY 章节。

- [x] Task 4: BLUEPRINT Prompt + Template
  - File: `frontend/src/core/prompts/value_discovery/blueprint.ts`（新建）
  - Action: 导出 `BLUEPRINT_PROMPT` 和 `BLUEPRINT_TEMPLATE`。
  - Notes: 需要 `import { FENCE } from '../../utils/constants'`。Template 中用 `\${FENCE}mermaid` 包裹 mindmap 和 flowchart。
  - **内容来源**：`value_discovery_stage_design.md` — Stage 4: BLUEPRINT 章节。

- [x] Task 5: 注册 `VALUE_DISCOVERY` 类型
  - File: `frontend/src/core/types.ts`（修改）
  - Action: 在 `WorkflowType` 添加 `'VALUE_DISCOVERY'`，在 `WORKFLOW_SLUGS` 添加 `VALUE_DISCOVERY: 'value-discovery'`。
  - Notes: `SLUG_TO_WORKFLOW` 反向映射由 `Object.fromEntries` 自动派生，无需手动添加。

- [x] Task 6: 注册 `VALUE_DISCOVERY` 工作流定义
  - File: `frontend/src/core/workflows.ts`（修改）
  - Action: import 4 个 Stage，添加 `VALUE_DISCOVERY` 工作流定义（参考 IDEA_BRAINSTORM 结构）。
  - Notes: starterPrompts 改为体现"已有方向"的表述：['我们团队想做一个面向中小企业的智能客户管理系统，初步方向已确定，但还没想清楚核心场景', '我们计划用 AI 帮测试工程师自动生成测试用例，想验证一下这个方向的价值', '我有个想法：做一款帮产品经理自动整理用户反馈的工具，想系统梳理一下']

- [x] Task 7: 更新 Agent 卡片注册
  - File: `frontend/src/core/config/agentWorkflows.ts`（修改）
  - Action: 将 `prd-creation` 替换为 `value-discovery`（icon: Compass, status: online）。

- [x] Task 8: 添加 `Compass` 图标到前端映射
  - File: `frontend/src/pages/WorkflowSelect.tsx`（修改）
  - Action: L3 import 添加 `Compass`，L31-41 ICONS 映射添加 `Compass: Compass`。

- [x] Task 9: 通用化 `buildSystemPrompt.ts` 文案
  - File: `frontend/src/core/prompts/buildSystemPrompt.ts`（修改）
  - Action: L37 将"产品概念简报"改为"本阶段的产出物"。

- [x] Task 10: 添加单元测试
  - File: `frontend/src/core/config/__tests__/workflows.test.ts`（修改）
  - Action: 添加 VALUE_DISCOVERY 结构校验测试和 agent workflows 测试，验证不包含 `prd-creation`。
  - Notes: 检查现有测试是否有隐式依赖 `prd-creation` 的断言，如有则同步修改。

### Acceptance Criteria

- [x] AC 1: Given 新建了 4 个 Stage 文件, when import 并检查导出成员, then 每个文件均导出 `XXX_PROMPT`（string）和 `XXX_TEMPLATE`（string），且 Prompt 字符串长度 > 100。
- [x] AC 2: Given `types.ts` 已更新, when 声明一个 `WorkflowType` 类型变量, then `'VALUE_DISCOVERY'` 是合法的类型值。
- [x] AC 3: Given `types.ts` 已更新, when 访问 `WORKFLOW_SLUGS.VALUE_DISCOVERY`, then 返回 `'value-discovery'`。
- [x] AC 4: Given `workflows.ts` 已更新, when 访问 `WORKFLOWS.VALUE_DISCOVERY`, then 工作流定义完整：id 为 `'VALUE_DISCOVERY'`、agentId 为 `'alex'`、stages 包含 4 个正确配置的阶段。
- [x] AC 5: Given `workflows.ts` 已更新, when 检查每个 Stage 的 template, then JOURNEY 和 BLUEPRINT 的 template 中包含 Mermaid 代码块，ELEVATOR 和 PERSONA 不包含。
- [x] AC 6: Given `agentWorkflows.ts` 已更新, when 调用 `getAgentWorkflows('alex')`, then 返回数组包含 `{id: 'value-discovery', status: 'online'}` 条目，且不再包含 `prd-creation` 条目。
- [x] AC 7: Given 用户在前端选择 Alex 的"价值发现"工作流, when 进入工作区, then 显示正确的 welcomeMessage 和 3 个 starterPrompts（体现"已有方向"而非泛泛想法）。
- [x] AC 8: Given 用户在 ELEVATOR 阶段完成对话, when 确认进入下一阶段, then 顺利转进 PERSONA 阶段。
- [x] AC 9: Given 用户完成前 3 阶段到达 BLUEPRINT 阶段, when 系统构建 System Prompt, then `previousArtifactsContext` 包含前 3 阶段的 Artifact 摘要，且注入文案为通用描述（不含"产品概念简报"字样）。
- [x] AC 10: Given `WorkflowSelect.tsx` 已更新, when Alex 工作流列表渲染 `value-discovery` 卡片, then 显示 `Compass` 图标而非 fallback 的 `FileCode2`。
- [x] AC 11: Given JOURNEY 阶段的 Prompt 已实现, when 检查 Prompt 文本, then 包含 Mermaid journey 图的语法约束规则（禁止 HH:MM 格式、禁止冒号）。
- [x] AC 12: Given 所有代码修改完成, when 运行 `npm run test`, then 所有测试通过（含新增的 VALUE_DISCOVERY 测试）。
- [x] AC 13: Given 所有代码修改完成, when 运行 `npm run build`, then 编译无错误。

## Additional Context

### Dependencies

- 无新增外部依赖
- 仅依赖现有的 `FENCE` 常量（`utils/constants.ts`）和 lucide-react 的 `Compass` 组件

### Testing Strategy

**自动化测试（单元测试）：**
- 在 `workflows.test.ts` 中添加 VALUE_DISCOVERY 的结构校验测试
- 验证 4 个 Stage 的 id、name、description 和 template 均正确配置
- 验证 `agentWorkflows.ts` 中 Alex 的工作流列表包含 `value-discovery`（online 状态）
- 验证不再存在 `prd-creation` 条目

**手动验证（部署后）：**
- 本地部署后在 Alex 工作区选择"价值发现"工作流
- 验证 Compass 图标正确显示
- 验证 4 个阶段的完整对话体验：ELEVATOR -> PERSONA -> JOURNEY -> BLUEPRINT
- 验证 BLUEPRINT 阶段是否正确整合前序 Artifact
- 验证 Mermaid 图表在 JOURNEY 和 BLUEPRINT 阶段正常渲染

### Notes

**风险项：**
- Prompt 质量直接影响 LLM 输出质量，首版 Prompt 可能需要在实际对话中迭代优化
- `journey` Mermaid 图渲染兼容性需部署后验证，**Prompt 中已添加语法约束**
- `buildSystemPrompt.ts` L37 文案通用化可能影响 IDEA_BRAINSTORM 的 CONCEPT 阶段输出风格，但"产出物"比"产品概念简报"语义更宽泛，不会破坏功能

**已知限制（后续优化）：**
- `previousArtifactsContext` 仅在 `isLastStage` 时注入。PERSONA 和 JOURNEY 阶段无法通过此机制获取前序 Artifact，但 LLM 对话历史中包含前序讨论，实际影响有限
- `WorkflowSelect.tsx` 的 `ICONS` 映射缺少多个已注册图标（如 `ShieldAlert`），本次仅修复 `Compass`

**参考文档（实现者必读）：**
- **Stage 设计文档（Prompt + Template 完整内容）**：`/Users/anhui/.gemini/antigravity/brain/f0461403-797b-48ca-8491-84560c734436/value_discovery_stage_design.md`
- 脑暴结论：`_bmad-output/brainstorming/alex-workflows-2026-03-04.md`
