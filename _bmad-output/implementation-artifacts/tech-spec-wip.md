---
title: 'Mermaid 图表渲染健壮性增强'
slug: 'mermaid-rendering-robustness'
created: '2026-03-04T16:16:00+08:00'
status: 'in-progress'
stepsCompleted: [1]
tech_stack:
  - React
  - TypeScript
  - Mermaid v11.12.3
  - Vitest
files_to_modify:
  - tools/new-agents/frontend/src/components/Mermaid.tsx
  - tools/new-agents/frontend/src/core/utils/mermaidSanitizer.ts
  - tools/new-agents/frontend/src/core/prompts/systemPrompt.ts
  - tools/new-agents/frontend/src/core/__tests__/mermaidSanitizer.test.ts
code_patterns:
  - 'Mermaid.tsx 使用 mermaid.render() + try-catch 异步渲染'
  - 'markdownUtils.ts 现有 LLM 输出预处理模式（preprocessMarkdown）'
  - 'ArtifactPane.tsx 中 code block language=mermaid 时走 Mermaid 组件'
  - 'mermaid.parse() 官方预校验 API（suppressErrors 选项）'
test_patterns:
  - 'Vitest 单元测试 (frontend/src/core/__tests__/)'
  - 'mermaid.test.ts 现有 Mermaid 语法校验测试'
  - 'npx vitest run 运行全部测试'
  - 'npm run build (tsc 编译检查)'
---

# Tech-Spec: Mermaid 图表渲染健壮性增强

**Created:** 2026-03-04T16:16:00+08:00

## Overview

### Problem Statement

系统中 LLM 生成的 Mermaid 图表有很大概率渲染失败，用户只能看到红色错误信息和原始代码，体验非常差。失败的根因有两层：

1. **LLM 生成的 Mermaid 语法不稳定**：常见问题包括节点文本含未转义特殊字符（`()[]<>"`）、使用 HTML 标签（`<br/>`）、缩进不规范（mindmap/timeline 对缩进敏感）、不闭合引号等。
2. **前端渲染层缺乏容错**：当前 `Mermaid.tsx` 仅有 try-catch，渲染失败后直接展示错误，**没有任何清洗、预校验或重试机制**。

### Solution

采用"Prompt 约束 + 前端清洗 + 预校验 + 优雅降级"的**分层防御策略**：

1. **Prompt 层**：在 `systemPrompt.ts` 中注入 Mermaid 语法约束规则，从源头减少 LLM 语法错误（预估减少 60-70%）
2. **清洗层**：新增 `mermaidSanitizer.ts`，在渲染前自动修正常见 LLM 错误（HTML 标签、特殊字符、不可见字符）
3. **校验层**：利用 `mermaid.parse()` 官方 API 预校验，失败后走二级清洗 + 重试
4. **降级层**：改进错误 UI，提供折叠代码展示 + Mermaid Live Editor 跳转链接

### Scope

**In Scope:**
- `Mermaid.tsx`：集成清洗 + 预校验 + 重试 + 改进降级 UI
- `mermaidSanitizer.ts` [NEW]：Mermaid 代码清洗工具函数
- `systemPrompt.ts`：在 System Prompt 末尾追加 Mermaid 语法约束规则
- `mermaidSanitizer.test.ts` [NEW]：清洗函数的单元测试
- 现有 `mermaid.test.ts` 补充清洗逻辑测试

**Out of Scope:**
- 服务端渲染方案（Kroki 等）
- AI 辅助修复（mermaid-fixer，需额外 LLM 调用）
- 替换第三方组件（react-x-mermaid）
- Mermaid 版本升级
- 后端代码改动

## Context for Development

### Codebase Patterns

- **Mermaid.tsx 渲染模式**：使用 `mermaid.render(id, chart)` 异步渲染 SVG，结果通过 `dangerouslySetInnerHTML` 注入 DOM。流式传输期间（`isGenerating=true`）展示 loading，结束后展示错误。
- **markdownUtils.ts 预处理模式**：项目已有 LLM 输出预处理先例 — `preprocessMarkdown()` 修复 LLM 生成的 `<mark>` 标签问题。新的 `mermaidSanitizer.ts` 应遵循同样的"预处理函数"模式。
- **ArtifactPane.tsx 集成点**：在 `code` 组件中，当 `language === 'mermaid'` 时渲染 `<Mermaid chart={...} />`。清洗逻辑应在 `Mermaid.tsx` 内部处理，不影响 `ArtifactPane` 调用方式。
- **mermaid.parse() API**：Mermaid 官方提供 `mermaid.parse(code, { suppressErrors: true })` 进行语法预校验，返回 `false` 表示语法错误，不会抛异常。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/components/Mermaid.tsx` | 当前 Mermaid 渲染组件（改造目标） |
| `frontend/src/core/utils/markdownUtils.ts` | 现有 LLM 输出预处理（参考模式） |
| `frontend/src/components/ArtifactPane.tsx` | Mermaid 组件调用方（不需改动） |
| `frontend/src/core/prompts/systemPrompt.ts` | System Prompt 构建函数（追加规则） |
| `frontend/src/core/__tests__/mermaid.test.ts` | 现有 Mermaid 语法测试 |
| `frontend/src/core/workflows.ts` | 工作流 Stage prompts（Mermaid 模板来源） |

### Technical Decisions

- 清洗函数 `sanitizeMermaidCode()` 放在独立的 `mermaidSanitizer.ts` 中，遵循单一职责原则
- 预校验使用 `mermaid.parse(code, { suppressErrors: true })`，不抛异常，通过返回值判断
- 重试策略为两级：第一级轻度清洗 → 第二级激进清洗（移除所有非标准字符）
- 降级 UI 使用 `<details>` 标签折叠原始代码，减少视觉噪音
- Mermaid Live Editor 链接通过 Base64 编码拼接 URL 参数

## Implementation Plan

### Tasks

- [ ] **Task 1**: 创建 `mermaidSanitizer.ts` — 实现 `sanitizeMermaidCode()` 和 `aggressiveSanitize()` 函数
  - 移除 HTML 标签（`<br/>` → 换行）
  - 自动引号包裹含特殊字符的节点标签
  - 移除不可见字符（NBSP、零宽空格）
  - 统一换行符
  - 激进清洗：移除所有非标准字符、简化复杂节点文本

- [ ] **Task 2**: 创建 `mermaidSanitizer.test.ts` — 清洗函数的单元测试
  - 测试 HTML 标签移除
  - 测试特殊字符自动引号包裹
  - 测试不可见字符清理
  - 测试已正确的代码不被误改
  - 测试激进清洗模式

- [ ] **Task 3**: 改造 `Mermaid.tsx` — 集成清洗 + 预校验 + 重试 + 降级
  - 引入 `sanitizeMermaidCode` 和 `aggressiveSanitize`
  - 渲染前调用清洗函数
  - 使用 `mermaid.parse()` 预校验
  - 实现两级重试机制
  - 改进错误降级 UI（折叠代码 + Live Editor 链接）

- [ ] **Task 4**: 修改 `systemPrompt.ts` — 追加 Mermaid 语法约束
  - 在 System Prompt 末尾追加 Mermaid 语法规则段落
  - 规则内容：特殊字符引号包裹、禁止 HTML 标签、缩进规范、引号闭合、节点 ID 规范

- [ ] **Task 5**: 运行测试并验证
  - `npx vitest run` 全部通过
  - `npm run build` 编译无错误
  - 浏览器验证渲染效果

### Acceptance Criteria

- [ ] **AC1**: Given LLM 生成的 Mermaid 代码包含 `<br/>` 标签, When 传入 `Mermaid` 组件, Then 能自动清洗并正确渲染（不显示错误）
- [ ] **AC2**: Given Mermaid 代码包含未引号包裹的特殊字符节点文本, When 传入 `Mermaid` 组件, Then `sanitizeMermaidCode` 自动包裹引号后正确渲染
- [ ] **AC3**: Given 经两级清洗后仍无法修复的语法错误, When 渲染失败, Then 显示折叠的原始代码 + "在 Mermaid Live Editor 中打开" 链接（非当前红色报错）
- [ ] **AC4**: Given System Prompt 包含 Mermaid 语法约束, When LLM 生成 Mermaid 代码, Then 语法错误率显著降低
- [ ] **AC5**: Given 流式传输期间的不完整代码, When `isGenerating=true`, Then 仍显示 loading 动画（不受清洗逻辑影响）
- [ ] **AC6**: 所有现有测试（`npx vitest run`）通过，`npm run build` 编译无错误

## Additional Context

### Dependencies

- 无新增 npm 依赖
- 仅使用 Mermaid v11.12.3 已有的 `mermaid.parse()` API

### Testing Strategy

- **单元测试**：`mermaidSanitizer.test.ts` 覆盖所有清洗规则
- **回归测试**：`npx vitest run`（含现有 `mermaid.test.ts`）
- **编译检查**：`npm run build`
- **浏览器验证**：`./scripts/dev/deploy-dev.sh` 部署后，在 INCIDENT_REVIEW 工作流中触发 Mermaid 图表，确认渲染正常；故意输入错误代码，确认降级 UI 展示
- **手动测试场景**：
  1. 正常 Mermaid 代码渲染（timeline、mindmap、pie）
  2. 含 `<br/>` 的代码自动清洗后渲染
  3. 含特殊字符未引号包裹的代码自动修复后渲染
  4. 完全无法修复的语法错误 → 折叠代码 + Live Editor 链接

### Notes

- 研究报告参考: `mermaid-robustness-research.md`（brain artifact）
- `mermaid.parse()` 在 Mermaid v11+ 中稳定可用，返回 `{ diagramType: string }` 或 `false`（suppressErrors 模式）
- Live Editor URL 格式: `https://mermaid.live/edit#pako:{base64_encoded_code}`
