# AI 生成 UI 协议与工具深度对比分析报告

**日期**: 2026-01-21
**分析对象**: AG-UI, A2UI, json-render
**背景**: AI4SE 项目寻求解决 Mermaid 图表渲染不稳定问题，探索通过结构化 UI 生成固定产出物模板的可行性。

---

## 1. 协议栈定位

在 AI Agent 技术栈中，这些工具处于不同的层级：

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Agent 协议栈                           │
├─────────────────────────────────────────────────────────────┤
│  MCP (Model Context Protocol)  │ 给 Agent 提供工具能力       │
├─────────────────────────────────────────────────────────────┤
│  A2A (Agent-to-Agent)          │ Agent 之间的通信协议        │
├─────────────────────────────────────────────────────────────┤
│  AG-UI / A2UI / json-render    │ Agent 与用户界面的交互      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 三大方案核心对比

| 维度 | **AG-UI** (CopilotKit) | **A2UI** (Google) | **json-render** (Vercel) |
|------|------------------------|-------------------|--------------------------|
| **GitHub Stars** | ⭐ 11.5k | ⭐ 10.4k | ⭐ 7.9k |
| **维护方** | CopilotKit (创业公司) | Google | Vercel Labs |
| **核心本质** | **通信协议** (Event Protocol) | **数据格式** (Data Format) | **渲染框架** (Rendering Lib) |
| **设计理念** | 事件驱动，实时交互 | 安全声明式 UI，跨平台 | Schema 约束，流式渲染 |
| **适用场景** | 复杂交互流，人机协作 | 跨平台渲染，远程 Agent | 动态仪表盘，受控生成 |
| **成熟度** | 稳定 (多版本) | v0.8 公开预览 | ~0.2 实验性 |
| **License** | MIT | Apache-2.0 | Apache-2.0 |

---

## 3. 深度解析

### 3.1 AG-UI：事件驱动的交互协议

**核心机制**:
```
Agent Backend ──(Events)──> Frontend Application
              TEXT_DELTA / TOOL_CALL / STATE_SYNC ...
```

- **特点**: 标准化 Agent 执行过程中的事件流，支持双向状态同步。
- **优势**: 生态整合强 (LangGraph, CrewAI)，适合需要深度介入 Agent 执行过程的场景。
- **劣势**: 对于"静态产出物渲染"场景显得过重，需要改造后端适配其协议。

### 3.2 A2UI：安全的声明式 UI 格式

**核心机制**:
```
Agent ──(JSON Payload)──> A2UI Renderer ──> Native Components
         { "type": "card", ... }            Flutter/React/Lit
```

- **特点**: "Safe like data, expressive like code"。强调安全性（非可执行代码）和跨平台能力。
- **优势**: Google 背书，潜力大，适合移动端+Web 混合开发。
- **劣势**: **目前缺失官方 React renderer**，生态尚在早期。

### 3.3 json-render：Schema 约束的 UI 框架

**核心机制**:
```
AI ──(Catalog Constraints)──> JSON Tree ──> React Components
           Zod Schema
```

- **特点**: 强约束 (Zod Schema)，流式渲染 (Streaming)，数据绑定。
- **优势**: React 原生支持，与 Vercel AI SDK 无缝集成，极其适合"受控生成"场景。
- **劣势**: 实验性项目，版本号较低。

---

## 4. 与 AI4SE 项目适配性分析

**项目痛点**: Mermaid 语法复杂导致渲染失败；产出物模板固定（脑图、流程图等）。

| 方案 | 适配度 | 理由 |
|------|--------|------|
| **AG-UI** | ⭐⭐ | 侧重通信过程，而非 UI 渲染结果，解决不了 Mermaid 渲染问题。 |
| **A2UI** | ⭐⭐⭐ | 思想契合（组件目录+安全渲染），但缺乏 React 支持，落地成本高。 |
| **json-render** | ⭐⭐⭐⭐ | **高度契合**。React 技术栈，Schema 约束能完美解决 Mermaid 不稳定问题。 |

---

## 5. 建议实施路线

### 5.1 短期策略 (1-2周): "轻量级自研"

鉴于 `json-render` 仍处于早期，且我们需求明确（仅需图表控件），建议**借鉴 json-render 思想，自研轻量级实现**：

1.  **定义 Schema**: 使用 Zod 定义图表数据结构 (MindMap, FlowChart, RiskMatrix)。
2.  **实现控件**: 封装 React Flow / D3.js 为标准 React 组件。
3.  **改造 Prompt**: 让 Agent 输出符合 Schema 的 JSON 而非 Mermaid 文本。
4.  **渲染集成**: 在 `MarkdownText.tsx` 的 `CodeOverride` 中拦截 `json:chart` 类型进行渲染。

### 5.2 长期策略: "标准化迁移"

- 持续关注 **A2UI** 的 React 生态发展。如果 Google 推出官方 React Renderer，可考虑迁移以获得跨平台能力。
- 或等待 **json-render** 发布 1.0 正式版后，引入用于更复杂的动态 UI 生成场景。

---

## 6. 附录：图表 Schema 设计示例

```typescript
// types/chart-schemas.ts
import { z } from 'zod';

export const MindMapSchema = z.object({
  type: z.literal('mindmap'),
  title: z.string(),
  root: z.object({
    label: z.string(),
    children: z.array(z.lazy(() => MindMapNodeSchema)).optional(),
  }),
});

const MindMapNodeSchema = z.object({
  label: z.string(),
  children: z.array(z.lazy(() => MindMapNodeSchema)).optional(),
});
```
