---
title: '统一系统提示词模板约束重构'
slug: 'unified-sys-prompt-constraints'
created: '2026-03-05T10:15:00+08:00'
status: 'Implementation Complete'
stepsCompleted: [1, 2, 3, 4]
tech_stack: ['TypeScript', 'React', 'Zustand']
files_to_modify: ['src/core/types.ts', 'src/core/workflows.ts', 'src/core/prompts/buildSystemPrompt.ts', 'src/core/prompts/idea_brainstorm/*.ts', 'src/core/prompts/test_design/*.ts', 'src/core/prompts/req_review/*.ts', 'src/core/prompts/incident_review/*.ts']
code_patterns: ['Exported const strings for prompts', 'Static WORKFLOWS Record definition', 'Template literal system prompt building in buildSystemPrompt.ts']
test_patterns: ['Frontend build (tsc) as compilation check', 'Manual flow testing for prompt generation']
---

# Tech-Spec: 统一系统提示词模板约束重构

**Created:** 2026-03-05T10:15:00+08:00

## Overview

### Problem Statement

目前 AI 智能体（如 Alex 和 Lisa）未能严格遵循各阶段 Prompt 定义的产出物模板结构。主要根因在于：每个阶段的“行为指南”和“产出物模板”目前混合在同一个 `description` 字符串字段中，而在系统提示词工厂（`buildSystemPrompt.ts`）中，它们被作为一个整体以 `阶段目标：${currentStage.description}` 的低权重层级注入给大模型。这导致 LLM 将格式模板视为“参考建议”而非“强制执行的格式”，从而自由发挥改变输出结构。
此外，阶段切换时生成的下一阶段说明中，也遗漏了对下一阶段模板的有效约束。

### Solution

采用“纵深防御”混合方案（架构拆分 + 提示词层级与措辞强化）：

1. **结构拆分**：在 `WorkflowStage` 接口中独立定义强约束的 `template` 字段，分离原有的行为描述与模板输出。
2. **顶层约束增强**：在 `buildSystemPrompt.ts` 中，为 `template` 单独设计最高权重的指令注入块（例如明确标记为【产出物强制结构 — 禁止偏离】）。同时在阶段切换（即 `nextStage` 提示）的指引中补充模板的传递。
3. **彻底贯彻**：对现有的 4 大工作流中的总计 13 个阶段的提示词文件实施解耦重写。剥离后，原说明中诸如“右侧必须严格按照以下模板生成：”之类的口语化冗余指令将被删减，统一交由系统构建器进行强制。

### Scope

**In Scope:**
- 在 `types.ts` 中扩展 `WorkflowStage` 的接口定义。
- 修改 `buildSystemPrompt.ts` 核心提示词构建逻辑，包含对当前阶段模板的高优织入以及在阶段推进规则中对 `nextStage.template` 的支持。
- 拆分修改上述所有 13 个提示词文件：涉及 `idea_brainstorm`, `test_design`, `req_review`, `incident_review` 目录下的所有相关模块文件。
- 改写这些文件中涉及的原本混合在一起的行为描述与模板部分，废弃并删除冗余的“右侧必须严格按照以下模板生成”等硬编码引导语。
- 修改 `workflows.ts`，组装新增的 `*_TEMPLATE` 至对应阶段。
- 处理带历史依赖的阶段（如 `delivery.ts`、`improvement.ts`、`concept.ts`），确保模板要求结构清晰，能与既有的历代阶段上下文信息协同工作；无需修改目前仅对 Alex 生效的硬编码前序逻辑整合规则。

**Out of Scope:**
- 添加新功能、新智能体或彻底新建任何新的工作流。
- 整体重写或更改系统设定的全局 Persona（如 `lisa`, `alex`）。
- 更改目前底层的 LLM 代理或流式生成解析器架构。

## Context for Development

### Codebase Patterns

- **双常量导出模式**：旧模式只导出一个 `XX_PROMPT`；新模式修改为导出 `XX_PROMPT` (行为) 和 `XX_TEMPLATE` (结构模板)。
- **Mermaid 边界处理**：某些阶段通过引入 `import { FENCE } from '../../utils/constants'` 提供图表防护，有些（如 incident_review 下的）使用写死的反引号 `` \`\`\`mermaid ``。我们在拆分时必须基于源文件采取的图表包裹模式原样保留，维持其可用性。
- **阶段切换机制**：`buildSystemPrompt` 第二大段通过判断 `nextStage` 的有无向系统注入自动向下一个阶段行进后的初始产出物要求。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `src/core/types.ts` | 添加 `template?: string;` 字段定义。 |
| `src/core/prompts/buildSystemPrompt.ts` | 增强 `template` 字段的 LLM 解析优先级。处理 `nextStage.template` 注入问题。 |
| `src/core/workflows.ts` | 引入并注册所有新增的 `*_TEMPLATE` 到对象内。 |
| `src/core/prompts/idea_brainstorm/*` | 对应 4 个 Prompt 的解耦。 |
| `src/core/prompts/test_design/*` | 对应 4 个 Prompt 的解耦。 |
| `src/core/prompts/req_review/*` | 对应 2 个 Prompt 的解耦。 |
| `src/core/prompts/incident_review/*` | 对应 3 个 Prompt 的解耦。 |

### Technical Decisions

- **类型后向兼容**：定义 `template` 为可选字段，即使日后有无固定模板的工作流也可以平滑使用。
- **模板与前置特征摘要解耦**：像 `delivery.ts` 这样具有 `[此处完整引用需求澄清阶段的产出物内容...]` 指令的阶段模板，可以很好地与构建器自动注入的 `previousArtifactsContext` 协同；系统自动总结前述，模板要求整合拼接，不造成底层思维冲突。
- **剔除失效指令**：在各个独立 `XX_PROMPT` 中剥离模板后，必须完全删掉类似“右侧产出物必须严格按照以下模板结构生成：”之类的句式，这类指令已由系统全局提示词接管。

## Implementation Plan

### Tasks

*(请务必按顺序执行以确保依赖正常引用)*

- [x] Task 1: Update Typings
  - File: `tools/new-agents/frontend/src/core/types.ts`
  - Action: Update `WorkflowStage` interface to include optional field `template?: string;`

- [x] Task 2: Update System Prompt Builder Integration
  - File: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
  - Action 1: 在“阶段目标：...”块下方注入：`\n\${currentStage.template ? \`【产出物强制结构 — 禁止偏离】\n⚠️ 以下模板为本阶段唯一合法的产出物格式。你必须严格遵守：\n1. 禁止增删章节标题，禁止修改标题名称\n2. 禁止改变表格列定义\n3. 所有 [] 占位符必须替换为实际内容，但结构本身不可变\n4. 如果信息不足，在对应位置填写 [待补充]，但不可省略该章节\n\n\${currentStage.template}\n\` : ''}`
  - Action 2: 更改阶段推进规则第三条，将包含 `nextStage` 产出指示的地方补充完整条件：`3. **生成新阶段产出物**：当你输出 <ACTION>NEXT_STAGE</ACTION> 标签时，必须在 <ARTIFACT> 中直接输出**下一个阶段**的初始产出物内容\${nextStage ? \`（目标：\${nextStage.description}）。\n\${nextStage.template ? \`请严格按照以下模板生成：\n\${nextStage.template}\` : ''}\` : ''}。`

- [x] Task 3: Split Prompts in `idea_brainstorm`
  - File: `tools/new-agents/frontend/src/core/prompts/idea_brainstorm/*.ts` (all 4 files)
  - Action: 把基于“右侧必须严格按照以下模板生成：”之前的内容保留在 `XX_PROMPT`，之后的内容（通常以 `# ` 或模板内容起头）移动到导出的 `XX_TEMPLATE` 常量中。删除分割标记本身的文字。确保保留 FENCE 导入和用法。

- [x] Task 4: Split Prompts in `test_design`
  - File: `tools/new-agents/frontend/src/core/prompts/test_design/*.ts` (all 4 files)
  - Action: 这里变种较多。对于 `clarify.ts`、`strategy.ts`、`cases.ts`、`delivery.ts`，查找“右侧产出物必须严格按照以下模板结构生成” 或者对应的字眼作为切点分离。保留 FENCE 常量。同样的，删除“右侧产出物必须严格按照以下模板结构生成”这类废话。

- [x] Task 5: Split Prompts in `req_review`
  - File: `tools/new-agents/frontend/src/core/prompts/req_review/*.ts` (all 2 files)
  - Action: 找到并在包含“右侧产出物必须严格按照以下模板结构生成”或此类字眼的地方对其切割，拆分为 `XX_PROMPT` 和 `XX_TEMPLATE`。删除分割词。保留其使用的 FENCE 常量（若有）。

- [x] Task 6: Split Prompts in `incident_review`
  - File: `tools/new-agents/frontend/src/core/prompts/incident_review/*.ts` (all 3 files)
  - Action: 找到分割边界并切分为两部分。**注意**，该目录下的文件直接由于采用的是硬编码反引号作为 Mermaid Markdown，请原封不动带到 TEMPLATE 常量里，删除废弃的声明分隔文本即可。

- [x] Task 7: Update Workflow Declarations
  - File: `tools/new-agents/frontend/src/core/workflows.ts`
  - Action: 通过分别引入以上修改好后的 `*_TEMPLATE` 并绑定到对应的大写名称的每个相关的 `stage` 节点的 `template` 属性上，完成注册接入机制。

### Acceptance Criteria

- [ ] AC 1: 给定已构建的工作流类型定义，当在终端中运行 `tsc --noEmit`，系统不提示编译错误。
- [ ] AC 2: 给定系统通过 `buildSystemPrompt` 拼装测试函数，当传入任何阶段且含有 `template` 属性的上下文信息时，其最终返回字符串的中间部分包含明显的“【产出物强制结构 — 禁止偏离】”文字段及其正确拼接的模板代码段。
- [ ] AC 3: 进一步测试 `buildSystemPrompt` 返回字符内容中，当触发非末尾阶段时包含 `<ACTION>NEXT_STAGE</ACTION>` 机制的规则指引里，能够成功注入对应含有目标工作流要求输出的对应下附模板内容部分。

## Additional Context

### Dependencies

无外部新增加的包依赖，全部涉及本地 TypeScript 类型和常量拆分解构操作。

### Testing Strategy

- **编译级单元验证**：在根目录下进行 TypeScript 转译和前端单元构建检查，确保模块导出被正确的应用引用且不出类型缺失。
- **纯代码拼接函数逻辑验证**：由于这是一个 prompt template，如果可能，调用 `console.log(buildSystemPrompt({ ... mock ... }))` 明确观察阶段推进提示词里是否正常打印预期的合并版本。
- **手动验收测试步骤**：
  1. 打开开发服或者本地环境。
  2. 使用 Alex 代理，发送消息：“我有个做宠物社区的想法”。
  3. 观察第一轮返回的 Artifact 标题是否严格为 `# 问题域分析 (Define)` 并拥有所有对应的正确预置结构和表头，没有任何自主创作的大偏离分支内容。
  4. 推进（“同意前往下一阶段”），观察紧跟着生成的 Artifact 是否按照 Diverge 部分进行了强制模板对齐。

### Notes

- 在处理 `concept.ts` 时，必须保留该文档顶部的 “为啥/怎么办/什么功能” 这些说明作为行为指南保留；只抽取其属于 `# 产品概念简报 (Concept Brief)` 下属的所有严格表格和段落等纳入 `template` 字段内。
- 上下文依赖注入：Alex 包含的一个在 `buildSystemPrompt.ts` 里面判断 `agentId === 'alex'` 并对前述所有阶段的信息作引用的硬编码逻辑可以保持不变，不需要在这个工作范围里更改。
