# New Agents 错误信息低占用时间线展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 New Agents 生成失败或右侧产物渲染异常时，在最新对话位置展示低占用错误摘要，并按需展开完整诊断详情。

**Architecture:** 在共享 `Message` 类型上增加可选 `errorDiagnostic` 元数据，`chatService` 写结构化诊断，`ChatPane` 在消息时间线内渲染折叠卡片。右侧产物可视化诊断继续复用 `artifactVisualDiagnostics`，只把原顶部 notice 移到消息流最新位置并默认折叠。继续复用共享 store、typed Agent Runtime 和现有错误归因，不新增 workflow 专属 UI 或 runtime 分支。

**Tech Stack:** React 19、TypeScript、Zustand、Vitest、Testing Library、lucide-react。

---

## 文件结构

- Modify: `tools/new-agents/frontend/src/core/types.ts`，为 `Message` 增加错误诊断元数据类型。
- Modify: `tools/new-agents/frontend/src/store.ts`，持久化 hydration 时校验并保留 `errorDiagnostic`。
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`，把错误 Markdown 字符串替换为短摘要 + 结构化详情元数据。
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`，渲染低占用折叠错误卡片、移动右侧产物诊断 notice，并保留现有 recovery actions。
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`，补服务层红绿测试。
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`，补默认折叠、展开和时间线位置测试。
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`，补 prompt 过滤回归。
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`，补持久化 sanitize 回归。
- Modify: `docs/todos/refactor/2026-06-25-new-agents-error-message-placement-ux.md`，记录完成情况和验证。
- Modify: `docs/todos/refactor/README.md`，如本轮完成则移除该活跃入口。

### Task 1: Red Tests

- [x] **Step 1: 写 chatService 失败测试**

在 `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts` 增加测试：
- 首帧前 provider 错误时，assistant `content` 只包含短摘要，不包含原始错误；`errorDiagnostic.rawMessage` 保留原始错误；`kind` 为 `provider`。
- 中途普通错误时，错误摘要追加到最新 assistant 消息，`errorDiagnostic` 保留原始错误，artifact 不被正常保存。

- [x] **Step 2: 写 ChatPane 失败测试**

在 `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx` 增加测试：
- 默认只显示短摘要和“查看详情”，不显示原始错误详情。
- 点击“查看详情”后显示原始错误，再点击收起。
- 错误卡片随消息时间线出现，用户消息之后的最新 assistant 消息内可见。
- 右侧产物可视化诊断 notice 出现在已有聊天消息之后，而不是对话区域顶部；诊断详情默认折叠。

- [x] **Step 3: 写 store / prompt 失败测试**

在 `tools/new-agents/frontend/src/__tests__/store.test.ts` 增加 hydration 测试，证明 `errorDiagnostic` 被保留且非法字段被丢弃。

在 `tools/new-agents/frontend/src/core/__tests__/llm.test.ts` 扩展控制反馈过滤测试，加入新摘要文案，确保不会进入 runtime prompt。

- [x] **Step 4: 运行红测**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/llm.test.ts
```

Expected: 新增断言失败，原因是 `Message.errorDiagnostic` 尚不存在或 UI 仍展开显示原始详情。

### Task 2: Minimal Implementation

- [x] **Step 1: 扩展类型**

在 `core/types.ts` 增加：
- `MessageErrorDiagnosticKind = 'structured' | 'provider' | 'generic'`
- `MessageErrorDiagnostic`，字段包含 `kind`、`summary`、`rawMessage`、可选 `reason`、`action`、`code`
- `Message.errorDiagnostic?: MessageErrorDiagnostic`

- [x] **Step 2: 扩展 store sanitize**

在 `store.ts` 新增 `sanitizeMessageErrorDiagnostic(...)`，只接受字符串字段和合法 kind；`sanitizeChatHistory(...)` 对合法 `errorDiagnostic` 赋值，非法值丢弃。

- [x] **Step 3: 重构 chatService 错误格式化**

把 `formatAssistantErrorContent(...)` 改为返回 `{ content, errorDiagnostic }`：
- structured：`content` 为 `⚠️ 结构化输出生成失败：右侧产出物已保持不变，可重试本阶段。`
- provider：`content` 为 `⚠️ 模型调用未完成：<reason>，右侧产出物已保持不变。`
- generic：`content` 为 `⚠️ 本轮生成失败：请查看错误详情后重试。`
- `rawMessage` 永远保留原始错误，供展开详情使用。

中途失败时更新最后一条 assistant 消息时保留原内容，并把 `errorDiagnostic` 写到同一消息。

- [x] **Step 4: 调整 ChatPane 渲染**

在 `ChatPane.tsx` 中：
- 用 `msg.errorDiagnostic?.kind` 判断错误类型，兼容旧内容关键短语。
- 默认渲染紧凑卡片：图标、summary、`查看详情` 按钮、现有 recovery actions。
- 详情展开后显示 reason、action、code、rawMessage；再次点击收起。
- provider 卡片保留打开设置、检测连接、重试按钮。
- structured 卡片保留重试、连续失败补充信息。

### Task 3: Verification and Records

- [x] **Step 1: 运行聚焦测试**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/llm.test.ts
```

Expected: all pass。若出现既有 React `act(...)` warning，记录但不把它包装成失败。

- [x] **Step 2: 运行前端 owning package 验证**

Run:

```bash
cd tools/new-agents/frontend && npm run test
cd tools/new-agents/frontend && npm run lint
```

Expected: pass。

- [x] **Step 3: 更新 todo**

更新 `docs/todos/refactor/2026-06-25-new-agents-error-message-placement-ux.md`，记录完成状态、改动、验证和残余风险。若已完成，从 `docs/todos/refactor/README.md` 当前入口移除或标注完成去向。

- [x] **Step 4: 全量本地自动化和 CI 等价**

Run:

```bash
./scripts/test/test-local.sh all
```

Expected: pass。若可选外部 LLM judge 因环境或质量门禁失败，按 `docs/strategy/goal-mode-ci-verification.md` 记录确定性替代命令和风险。

- [x] **Step 5: Diff check and commit**

Run:

```bash
git diff --check
git status --short
```

只 stage 本轮相关 frontend / docs 文件，不 stage 既有生成物脏文件。提交信息建议：

```bash
git commit -m "fix(new-agents): 优化错误信息折叠展示"
```
