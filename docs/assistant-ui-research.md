# assistant-ui 深度调研报告

> **调研日期**: 2026-01-21
> **项目状态**: 已安装 `@assistant-ui/react ^0.11.56`，但**实际未使用**

---

## 1. 框架概述

### 什么是 assistant-ui？

[assistant-ui](https://github.com/assistant-ui/assistant-ui) 是一个为 AI 聊天界面构建的 React 组件库，专注于提供"UI 原语"而非完整模板。

| 属性 | 值 |
|------|-----|
| **GitHub Stars** | ~8.1k |
| **定位** | Chat UI Primitives (聊天 UI 原语) |
| **核心理念** | 无头组件 + 高度可定制 |
| **依赖兼容** | Vercel AI SDK, LangChain, OpenAI SDK |

### 核心特性

1. **Primitives 模式**: 提供无样式原语组件，开发者完全控制 UI
2. **Runtime Adapters**: 支持多种后端 (Vercel AI SDK, LangChain, 自定义)
3. **Streaming 原生支持**: 内置流式消息处理
4. **Tool Calling UI**: 原生支持工具调用的可视化
5. **附件/文件上传**: 内置文件处理能力

---

## 2. 当前项目使用情况

### 依赖分析

```json
// tools/ai-agents/frontend/package.json
{
  "@assistant-ui/react": "^0.11.56",
  "@assistant-ui/react-markdown": "^0.11.56"
}
```

### 实际使用状态: **遗留代码**

| 文件 | 状态 | 说明 |
|------|------|------|
| `CustomComposer.tsx` | 未使用 | 存在但无引用 |
| `CustomUserMessage.tsx` | 未使用 | 存在但无引用 |
| `AssistantChat.tsx` | **主组件** | 使用原生 Vercel AI SDK 实现 |
| `MarkdownText.tsx` | 活跃 | 原生 react-markdown 实现 |

### 为什么没有使用？

项目已迁移到更直接的实现方式：
1. **Vercel AI SDK** (`useChat` hook) - 处理流式对话
2. **自定义 Tailwind 组件** - 完全控制 UI 样式
3. **react-markdown** - 直接渲染 Markdown

---

## 3. 竞品对比分析

### 3.1 全栈模板类

| 框架 | Stars | 优势 | 劣势 | 适用场景 |
|------|-------|------|------|----------|
| **Vercel AI Chatbot** | 19.3k | 完整模板，Next.js 集成好 | 定制需要大量修改 | 从零构建独立聊天应用 |
| **Chatbot UI** | 32.9k | 功能完整，社区大 | 耦合度高，难以嵌入 | 自建 ChatGPT 替代品 |

### 3.2 应用内集成类

| 框架 | Stars | 优势 | 劣势 | 适用场景 |
|------|-------|------|------|----------|
| **CopilotKit** | 28.1k | 深度应用集成，AG-UI 协议 | 学习曲线陡 | SaaS 内嵌 AI 副驾驶 |
| **Ant Design X** | ~2k+ | 企业级，中文生态好 | 组件数量有限 | B 端管理后台 |

### 3.3 UI 原语类

| 框架 | Stars | 优势 | 劣势 | 适用场景 |
|------|-------|------|------|----------|
| **assistant-ui** | 8.1k | 高度可定制，原语设计 | 需要自己组装 | 需要完全控制 UI 的项目 |

### 对比矩阵

```
定制化程度 (高 → 低)
│
├─ assistant-ui      ████████████░░░░  (最高定制)
├─ Ant Design X      ████████░░░░░░░░  (中等)
├─ CopilotKit        ██████░░░░░░░░░░  (框架约束)
├─ Vercel AI Chatbot ████░░░░░░░░░░░░  (模板约束)
└─ Chatbot UI        ██░░░░░░░░░░░░░░  (最低)

开箱即用 (高 → 低)
│
├─ Chatbot UI        ████████████░░░░  (最完整)
├─ Vercel AI Chatbot ██████████░░░░░░  
├─ CopilotKit        ████████░░░░░░░░  
├─ Ant Design X      ██████░░░░░░░░░░  
└─ assistant-ui      ████░░░░░░░░░░░░  (需要组装)
```

---

## 4. 架构分析

### assistant-ui 核心概念

```
┌─────────────────────────────────────────┐
│              AssistantUI                │
├─────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────────┐ │
│  │  Primitives │    │ Runtime Adapters│ │
│  │  (UI 原语)  │ ←→ │ (后端适配器)   │ │
│  └─────────────┘    └─────────────────┘ │
│         │                    │          │
│         ▼                    ▼          │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │  Thread     │    │ Vercel AI SDK   │ │
│  │  Message    │    │ LangChain       │ │
│  │  Composer   │    │ Custom Runtime  │ │
│  │  Attachment │    │                 │ │
│  └─────────────┘    └─────────────────┘ │
└─────────────────────────────────────────┘
```

### 与当前项目架构对比

```
当前项目实现:
┌─────────────────────────────────────────┐
│  AssistantChat.tsx (自定义)             │
│  └─ useChat (Vercel AI SDK)             │
│     └─ MarkdownText.tsx (react-markdown)│
│        └─ CodeOverride (Mermaid 处理)   │
└─────────────────────────────────────────┘

assistant-ui 方案:
┌─────────────────────────────────────────┐
│  Thread.Root (assistant-ui)             │
│  └─ VercelAIRuntime                     │
│     └─ MarkdownText (assistant-ui-md)   │
│        └─ Custom CodeBlock              │
└─────────────────────────────────────────┘
```

---

## 5. 决策建议

### 场景分析

| 场景 | 推荐方案 |
|------|----------|
| **当前项目已有自定义实现，运行良好** | 维持现状，清理 assistant-ui 依赖 |
| **需要快速添加复杂功能 (附件、工具调用 UI)** | 迁移到 assistant-ui |
| **需要企业级 B 端风格** | 考虑 Ant Design X |
| **需要深度应用集成** | 考虑 CopilotKit |

### 当前项目建议

**推荐: 清理 assistant-ui 依赖**

理由:
1. 已有稳定的原生实现
2. assistant-ui 增加了不必要的抽象层
3. 当前问题 (Mermaid 渲染) 与 UI 框架选择无关
4. 减少依赖可降低维护成本

### 如果要清理

```bash
# 移除依赖
npm uninstall @assistant-ui/react @assistant-ui/react-markdown

# 删除遗留文件
rm components/ui/assistant-ui/*
```

### 如果要启用

需要重写 `AssistantChat.tsx`，使用 assistant-ui 的 `Thread` 和 `VercelAIRuntime`。
工作量: ~2-3 天，需要重新实现所有自定义样式。

---

## 6. 总结

| 维度 | 结论 |
|------|------|
| **assistant-ui 定位** | 适合需要高度定制的新项目 |
| **当前项目状态** | 已有更直接的实现，assistant-ui 是技术债务 |
| **建议动作** | 清理依赖，专注解决 Mermaid 渲染问题 |
| **替代方案** | 借鉴 json-render 思想，用结构化 JSON 替代自由文本 |

---

## 相关文档

- [AI-UI 协议对比分析](./ai-ui-protocol-analysis.md)
- [assistant-ui 官方文档](https://www.assistant-ui.com/)
- [Vercel AI SDK 文档](https://sdk.vercel.ai/docs)
