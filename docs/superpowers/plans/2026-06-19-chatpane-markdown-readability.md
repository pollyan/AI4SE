# ChatPane Markdown Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 恢复左侧对话基础 Markdown 可读性，尤其是 assistant 长回复中的列表、链接、强调和代码层级。

**Architecture:** 继续复用 `ReactMarkdown`、`remarkGfm`、`preprocessMarkdown` 和 `createMarkdownCodeRenderer`；只扩展 `ChatPane` 的 markdown component mapping，不新增解析管线。

**Tech Stack:** React, Vitest, Testing Library, ReactMarkdown.

---

### Task 1: RED 测试

**Files:**
- Add: `tools/new-agents/frontend/src/components/__tests__/ChatPane.markdown.test.tsx`

- [x] **Step 1: 写真实 Markdown 渲染测试**

新增测试：渲染 assistant 长 Markdown 消息，断言列表、链接、强调、行内代码和代码块具备 ChatPane 样式 class。

- [x] **Step 2: 运行测试确认失败**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.markdown.test.tsx`

Expected: FAIL，因为当前 `ChatPane` 没有给列表和链接等元素配置可读样式。

### Task 2: 恢复 Markdown 样式

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`

- [x] **Step 1: 扩展 messageMarkdownComponents**

增加 h1/h2/h3、ul、ol、li、em、a、blockquote、hr 的紧凑样式。

- [x] **Step 2: 保持代码和 Mermaid 渲染复用**

继续使用 `createMarkdownCodeRenderer`，不新增 code/Mermaid 分支。

- [x] **Step 3: 运行 ChatPane 测试**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/components/__tests__/ChatPane.markdown.test.tsx`

Expected: PASS。

### Task 3: 更新记录和验证

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: 记录完成情况**

在 P1 #10 下记录左侧 Markdown 可读性恢复和测试命令。

- [ ] **Step 2: 格式检查**

Run: `git diff --check -- tools/new-agents/frontend/src/components/ChatPane.tsx tools/new-agents/frontend/src/components/__tests__/ChatPane.markdown.test.tsx docs/todos/new-agents-evolution.md docs/superpowers/specs/2026-06-19-chatpane-markdown-readability-design.md docs/superpowers/plans/2026-06-19-chatpane-markdown-readability.md`

Expected: no output, exit 0.
