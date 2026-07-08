---
status: completed
type: feature
priority: high
created: 2026-03-04
title: 智能体聊天页面冷启动引导体验优化 (Onboarding Welcome Kit)
---

# Quick Tech Spec: 智能体聊天页面冷启动引导体验优化

## 1. 目标
解决用户进入全新对话时"不知道跟系统说什么"的问题，通过为不同工作流配置专属的结构化欢迎语、示例提问片段以及动态 Placeholder，降低用户初次使用门槛。

## 2. 方案概览
引入 **Onboarding Welcome Kit**（冷启动欢迎套件）：当对话历史为空时，在 `ChatPane` 组件中间显示基于当前选定工作流的数据驱动面板，包含能力介绍和预设动作；一旦用户发起任何消息则此界面关闭，转入正常的聊天模式。

## 3. 技术设计

### 3.1. 数据模型与定义扩展 (`types.ts`, `workflows.ts`)
在 `WorkflowDef` 接口加入 `onboarding` 配置结构，使得每个工作流具有独有的初始信息。
```typescript
export interface OnboardingConfig {
    welcomeMessage: string;    // Markdown 语法的欢迎词
    starterPrompts: string[];  // 2-3 个预设快捷提问
    inputPlaceholder: string;  // 输入框空状态指引
}

export interface WorkflowDef {
    // ... 原有字段
    onboarding: OnboardingConfig;
}
```
**说明：** 
- 在 `workflows.ts` 中的 `TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW` 中均配置对应的初始状态。

### 3.2. 视图组件改造 (`ChatPane.tsx`)
- 拦截渲染逻辑：当 `chatHistory.length === 0` 时，读取当前选定工作流对应的 `onboarding` 配置并替换原本的文字提示和 Logo 图标。
- 使用 `ReactMarkdown` 安全渲染 `welcomeMessage`。
- 将 `starterPrompts` 循环渲染为可以快捷点击的按钮。
- **发送动作改造**：`handleSend()` 需要能支持传参（快捷输入的文本项）并直接发起请求，跳过等待用户再二次确认的工作流。

### 3.3. 测试支持 (`onboarding.test.ts`)
对 `WORKFLOWS` 这个数据结构编写对应的有效性验证：
- 确保所有工作流都补齐了 onboarding 数据。
- 确保 starterPrompts 长度有效 (推荐2-3条，无空内容)。
- 确保 placeholder 不过长。

## 4. 验证测试
- 已编写验证其配置内容的单元测试：`src/core/__tests__/onboarding.test.ts`
- 通过前端全量组件化 Vitest ( `npm run test` ) 确认无退化
- 通过完整的 docker 测试环境起用测试功能，手动走查页面渲染情况。

## 5. 变更列表
- `src/core/types.ts`: 引入了 `OnboardingConfig`。
- `src/core/workflows.ts`: 在所有已知工作流中硬编码了初始文字。
- `src/core/__tests__/onboarding.test.ts`: 新增 4 个配置验证单元测试。
- `src/components/ChatPane.tsx`: 将文字换成了排版有设计的 Welcome Kit 结构，并修复 onClick 闭包捕获问题。
- `src/services/chatService.ts`: 支持了 `handleSend(overrideInput?: string)` 接口直接送报文。

## 6. 完成情况
**状态：已完成/已部署。**
