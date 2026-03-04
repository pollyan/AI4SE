---
title: 'Mermaid 图表渲染重试机制'
slug: 'mermaid-render-retry'
created: '2026-03-04T16:56:00+08:00'
status: 'Completed'
stepsCompleted: [1, 2, 3, 4, 5, 6]
tech_stack:
  - React
  - TypeScript
  - Zustand (State Management)
  - Mermaid v11.12.3
  - OpenAI SDK (前端直连 / 后端代理两条路径)
files_to_modify:
  - tools/new-agents/frontend/src/components/Mermaid.tsx
  - tools/new-agents/frontend/src/components/ArtifactPane.tsx
  - tools/new-agents/frontend/src/services/mermaidRetryService.ts [NEW]
  - tools/new-agents/frontend/src/core/utils/llmClient.ts [NEW]
  - tools/new-agents/frontend/src/components/__tests__/Mermaid.test.tsx
  - tools/new-agents/frontend/src/services/__tests__/mermaidRetryService.test.ts [NEW]
code_patterns:
  - 'Mermaid.tsx 两级清洗 + error catch + dangerouslySetInnerHTML'
  - 'ArtifactPane.tsx ReactMarkdown custom code component 透传 mermaid 渲染'
  - 'llm.ts 双路径调用: 前端直连 OpenAI / 后端 SSE 代理'
  - 'llmParser.ts 使用 <CHAT><ARTIFACT><ACTION> 标签解析流'
  - 'store.ts Zustand setArtifactContent 覆盖产出物'
test_patterns:
  - 'Vitest 单元测试 (frontend/src/components/__tests__/)'
  - 'Vitest 单元测试 (frontend/src/core/__tests__/)'
  - 'npx vitest run 运行全部测试'
---

# Tech-Spec: Mermaid 图表渲染重试机制

**Created:** 2026-03-04T16:56:00+08:00

## Overview

### Problem Statement

之前我们通过前端清洗 + 预校验 + 降级 UI 大幅降低了 Mermaid 渲染失败率。但在极少数复杂语法完全错乱的边缘场景下，清洗仍无法修复，用户只能看到静态的降级代码块和 Live Editor 链接。当前缺乏闭环的自动恢复机制 — 无法让 LLM "再试一次"。

### Solution

引入**"自动隐式重试 1 次 + 显式手动重试按钮"**的前端闭环机制：

1. **自动隐式重试**：当 `Mermaid` 组件经两级清洗仍失败时，若尚未自动重试过，组件自动调用 `mermaidRetryService`。该服务将出错的 Mermaid 源码 + 错误信息 + 图表类型上下文组成修正 Prompt，通过现有 LLM 调用链路请求模型"仅输出修正后的 Mermaid 代码"。获得修正代码后，直接在 artifact 内容中替换对应的 ` ```mermaid ` 代码块并更新 Store，触发 React 重新渲染。
2. **显式手动重试**：若自动重试后依然失败，展示最终降级 UI，并在其中新增【🔄 重新生成图表】按钮。用户点击后走同一条修正路径再次尝试。
3. **保底不变**：若手动重试也失败，仍显示折叠代码 + Live Editor 链接（已有能力）。

### Scope

**In Scope:**
- 新增 `mermaidRetryService.ts`：封装"发送修正 Prompt 到 LLM 并提取纯 Mermaid 代码"的逻辑。
- 新增 `llmClient.ts`：抽取 `llm.ts` 中"获取 LLM 配置 + 发起请求"的共享逻辑，供 `mermaidRetryService` 和 `llm.ts` 共同复用（**F9**）。
- 改造 `Mermaid.tsx`：将降级 UI 从 HTML 字符串改为 React JSX 渲染（**F6**），增加 `onRetry` callback prop，增加基于 `useRef<Set>` 的已重试代码追踪（**F1**），添加自动重试逻辑及手动重试按钮。
- 改造 `ArtifactPane.tsx`：向 `<Mermaid>` 透传 `onRetry` 回调，回调内部完成 artifact 内容中对应代码块的索引定位替换（**F2**）。
- 新增 `mermaidRetryService.test.ts`（双路径测试 **F8**）和扩展 `Mermaid.test.tsx`。

**Out of Scope:**
- LLM Tool Calling / Function Calling 架构重构（远期方向，不在本轮）。
- 后端代码改动（重试完全在前端闭环）。
- 对 Chat Pane 中已有的消息级别"重试"按钮的改动。

## Context for Development

### Codebase Patterns

- **`Mermaid.tsx` 渲染模式**：`useEffect` 内调用 `mermaid.render(id, chart)` 生成 SVG，通过 `dangerouslySetInnerHTML` 注入。已有两级清洗：`sanitizeMermaidCode` → `mermaid.parse` → 失败则 `aggressiveSanitize` → 再失败则抛错走降级 UI。**注意：当前降级 UI 是用 `setSvg()` 注入 HTML 字符串，由于 `dangerouslySetInnerHTML` 无法绑定 React 事件，降级 UI 必须重构为条件式 JSX 渲染。**
- **`ArtifactPane.tsx` 集成点**：`ReactMarkdown` 的 `components.code` 自定义渲染器中，当 `language === 'mermaid'` 时创建 `<Mermaid chart={children} />`。这是透传 `onRetry` 的注入点。**注意：同一 artifact 内可能有多个 mermaid 块，需要基于出现顺序的索引定位。**
- **`llm.ts` LLM 调用**：提供 `generateResponseStream` 异步生成器，支持"用户自配 API Key 前端直连"和"后端代理 SSE"两条路径。
- **`store.ts`**：`setArtifactContent(content)` 可以将新产出物内容写入 Zustand Store，触发 `ArtifactPane` 重渲染。
- **`app.py` 后端代理**：`/api/chat/stream` 硬编码 `stream=True`，**不支持非流式请求**。因此 retry service 必须以 SSE 方式收集全部 chunk 后拼接。

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `frontend/src/components/Mermaid.tsx` | 当前 Mermaid 渲染组件（改造目标） |
| `frontend/src/components/ArtifactPane.tsx` | Mermaid 调用方（需注入 onRetry） |
| `frontend/src/core/llm.ts` | LLM 调用入口（抽取共享逻辑） |
| `frontend/src/core/utils/llmParser.ts` | 流解析器（retry 不使用，但须参考） |
| `frontend/src/store.ts` | Zustand 状态管理（setArtifactContent） |
| `frontend/src/services/chatService.ts` | 消息级重试参考模式 |
| `frontend/src/core/utils/mermaidSanitizer.ts` | 现有清洗工具（不改动） |
| `backend/app.py` | 后端代理（不改动，但须知其 stream=True 限制） |

### Technical Decisions

1. **防止无限循环（F1）**：不使用简单的 `retryCount` + reset 机制。改用 `useRef<Set<string>>` 存储"已经自动重试过的代码 hash"。当 chart prop 变化后进入渲染失败时，检查新代码的 hash 是否已在 Set 中 — 若在，说明是重试返回的新代码仍然失败，直接展示降级 UI 而非再次自动重试。手动重试按钮始终可用，不受 Set 约束（因为是用户主动行为）。
2. **索引定位替换（F2）**：`ArtifactPane.tsx` 在渲染时用一个递增计数器为每个 mermaid 块分配 `blockIndex`。`onRetry(brokenCode, error, blockIndex)` 携带索引。替换时，在 artifact 内容中按正则找到第 N 个 ` ```mermaid...``` ` 块进行替换，而非依赖代码文本子串匹配。
3. **Prompt 携带上下文（F3）**：修正 prompt 除了携带错误代码和错误信息外，还附带代码首行（通常包含图表类型声明如 `graph TD`、`timeline`、`mindmap`）作为类型提示，以及当前 stage 名称作为业务上下文线索。
4. **SSE 收集而非非流式（F4）**：由于后端代理 `app.py` 硬编码 `stream=True`，retry service 在后端代理路径上必须以 SSE 方式请求并收集全部 chunk 拼接为完整响应。前端直连 OpenAI 路径同理使用 stream 收集。不修改后端代码。
5. **`onRetry` 返回 Promise（F5）**：`onRetry` 的签名改为 `(brokenCode: string, errorMessage: string, blockIndex: number) => Promise<boolean>`。`Mermaid.tsx` await 该 Promise：返回 true 表示替换成功（组件将因 chart prop 变化自动重渲染），返回 false 表示失败（组件立即展示降级 UI + 手动按钮）。
6. **降级 UI 改为 JSX（F6）**：将 `Mermaid.tsx` 从"所有内容都通过 `setSvg` + `dangerouslySetInnerHTML`"的单一渲染模式，改为三态条件渲染：`renderState: 'success' | 'loading' | 'error'`。success 时用 `dangerouslySetInnerHTML` 展示 SVG，loading/error 时用 JSX 渲染（支持 React 事件绑定）。
7. **共享 LLM Client（F9）**：从 `llm.ts` 中抽取"读取 store 配置 + 创建 OpenAI 客户端或 fetch 后端代理"的逻辑到 `llmClient.ts`，导出 `sendLlmRequest(messages, options): Promise<string>` 函数。`llm.ts` 和 `mermaidRetryService.ts` 共同复用。

## Implementation Plan

### Tasks

- [x] **Task 1**: 创建 `llmClient.ts` — 抽取共享 LLM 请求逻辑
- [x] **Task 2**: 创建 `mermaidRetryService.ts`
- [x] **Task 3**: 改造 `Mermaid.tsx` — JSX 三态渲染 + 重试逻辑
- [x] **Task 4**: 改造 `ArtifactPane.tsx` — 索引定位 + 注入 onRetry
- [x] **Task 5**: 创建 `mermaidRetryService.test.ts`（双路径 F8）
- [x] **Task 6**: 扩展 `Mermaid.test.tsx`
- [x] **Task 7**: 运行测试并验证
  - 运行 `npx vitest run` 全部通过。
  - 部署本地 Docker 环境 (`./scripts/dev/deploy-dev.sh`)。
  - 浏览器验证自动重试和手动重试的端到端效果。

### Acceptance Criteria

- [x] **AC1**: Given Mermaid 代码经两级清洗后仍无法通过 `mermaid.parse`, When 该代码 hash 不在 `retriedCodes` Set 中且 `onRetry` 已传入, Then 自动调用 `onRetry` 一次并显示"正在自动修复图表…"的 loading 动画（JSX 渲染，非 HTML 字符串）。
- [x] **AC2**: Given 自动重试返回了修正后的 Mermaid 代码, When `onRetry` 返回 `true`（替换成功）, Then artifact 中对应索引的代码块被替换，组件因 chart prop 变化自动重渲染。若替换后的新代码仍然失败，因其 hash 已在 Set 中，直接展示降级 UI 而非再次自动重试（**F1/F7**）。
- [x] **AC3**: Given 自动重试失败（`onRetry` 返回 `false`）或代码 hash 已在 Set 中, When 组件进入 error 态, Then 展示降级 UI（折叠代码 + Live Editor）且包含 🔄【重新生成图表】按钮。
- [x] **AC4**: Given 用户点击【重新生成图表】按钮, When 按钮被点击, Then 触发 `onRetry`（不受 Set 约束），显示 loading 动画，根据返回值展示结果或降级。
- [x] **AC5**: Given `mermaidRetryService` 调用 LLM 失败, When 服务返回 null, Then `onRetry` 返回 `false`，组件展示降级 UI 且不崩溃、不卡在永久 loading（**F5**）。
- [x] **AC6**: Given 正在流式传输中 (`isGenerating === true`), When Mermaid 代码不完整导致解析失败, Then 仍展示 loading 动画（不触发自动重试）。
- [x] **AC7**: Given 同一 artifact 中包含多个 mermaid 块, When 第 2 个块渲染失败并触发重试, Then 仅替换第 2 个块（基于 blockIndex 索引），不影响其他块（**F2**）。
- [x] **AC8**: Given 正常可渲染的 Mermaid 代码, When 组件初次渲染, Then 不触发 `onRetry`，正常展示 SVG（**F10 回归保护**）。
- [x] **AC9**: 所有现有测试（`npx vitest run`）通过，无回归。

## Additional Context

### Dependencies

- 无新增 npm 依赖。
- 复用现有 OpenAI SDK 和后端 `/api/chat/stream` 接口。

### Testing Strategy

- **单元测试**：
  - `mermaidRetryService.test.ts` 覆盖双路径（直连 + 代理）、围栏移除、错误处理。
  - `Mermaid.test.tsx` 覆盖自动重试触发、防循环、手动按钮、Promise 返回值处理、回归保护。
  - 运行命令: `cd tools/new-agents/frontend && npx vitest run`
- **本地环境验证**：
  - 运行 `./scripts/dev/deploy-dev.sh` 部署本地 Docker 环境。
  - 打开 `http://localhost/new-agents/` 进入 INCIDENT_REVIEW 工作流。
  - 正常使用触发 Mermaid 图表生成，验证正常图表不受影响。

### Adversarial Review Findings 修复追踪

| Finding | 严重性 | 修复方式 | 涉及 Task |
|---------|--------|----------|----------|
| F1 竞态无限循环 | 🔴 | `useRef<Set<string>>` 存储已重试 hash | Task 3 |
| F2 多块精确定位 | 🔴 | blockIndex 索引 + `replaceMermaidBlockByIndex` | Task 4 |
| F3 Prompt 缺上下文 | 🟠 | 附带首行图表类型 + stage 名称 | Task 2 |
| F4 后端不支持非流式 | 🟠 | 改为 SSE stream 收集拼接 | Task 1 |
| F5 onRetry 异步悬挂 | 🟠 | 签名改为 `Promise<boolean>` | Task 3、4 |
| F6 HTML 无法绑定事件 | 🟡 | 三态 JSX 条件渲染 | Task 3 |
| F7 AC2 路径不全 | 🟡 | AC2 明确 hash Set 防再次自动重试 | AC2 更新 |
| F8 缺直连路径测试 | 🟡 | 增加 OpenAI SDK mock 测试 | Task 5 |
| F9 代码重复 | 🟢 | 抽取 `llmClient.ts` | Task 1 |
| F10 缺回归 AC | 🟢 | 新增 AC8 + 测试用例 | Task 6、AC8 |

### Notes

- **高风险：** `llmClient.ts` 抽取时需小心不破坏 `llm.ts` 现有的流式 yield 行为。若风险过高，Task 1 可降级为仅在 `mermaidRetryService.ts` 内部独立实现请求逻辑（接受有限的重复），待后续重构统一。
- **已知限制：** 自动重试需要额外一次 LLM 调用，有 API 配额消耗成本。
- **远期方向：** Tool Calling 架构可从根源提升 Mermaid 生成质量，但需重构后端代理层，留待后续迭代。

## Review Notes
- Adversarial review completed
- Findings: 10 total, 8 fixed, 2 skipped (F1, F2 Identified as false-positives/noise by user and technical analysis).
- Resolution approach: Auto-fix
