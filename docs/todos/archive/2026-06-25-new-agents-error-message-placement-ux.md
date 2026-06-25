# New Agents 错误信息展示位置与占用空间 UX Todo

状态：已完成
创建日期：2026-06-25
完成日期：2026-06-25
相关模块：`tools/new-agents/`

## 背景

用户在本地测试 New Agents 时观察到：当发生错误时，错误栏总是显示在对话部分最上面，和用户对“最新信息应该出现在最新位置”的预期相反。同时当前错误信息以醒目的彩色方块占用较大对话篇幅，而普通返回内容里已经会告知用户“返回的数据格式有误”等概要信息，导致错误细节重复、压迫主对话流。

## 当前问题

- 错误提示显示在对话区域顶部，用户需要回到上方查看，和时间线/最新反馈顺序不一致。
- 彩色错误块占用对话区域太多空间，影响继续阅读上下文和最新回复。
- 对普通用户来说，详细错误栈、协议错误或结构化输出错误并不总是需要立即展开。
- 当前错误概要和详细错误可能重复展示，导致页面显得“满篇错误信息”。

## 目标能力包

优化 New Agents 错误提示的展示策略：错误应作为最新反馈出现在合理位置，同时默认以低占用、可展开的方式展示详细信息。用户需要排障时可以展开查看完整错误；不需要时，主对话流保持简洁。

## 建议方向

1. 错误位置应遵循时间线语义，作为最新事件靠近最新对话，而不是固定显示在对话顶部。
2. 将详细错误块折叠为小型状态入口，例如图标、窄条、toast-like item 或可展开摘要。
3. 默认只展示一行可读摘要，例如“本轮生成失败：结构化输出格式有误”，详细 code/message/stack 需要点击展开。
4. 如果普通 assistant 回复中已经说明“返回数据格式有误”，彩色错误组件应避免重复长文案。
5. 对开发/调试用户保留完整错误详情入口，不能完全隐藏。
6. 错误组件不应污染下一轮 Agent Runtime prompt；如果当前已有过滤逻辑，改动时必须保持。

## 验收标准

- 新错误出现在当前对话流的最新位置，用户不需要回到顶部寻找。
- 默认状态下错误提示占用空间明显减少，只显示摘要和展开入口。
- 用户点击后可以展开查看完整错误 code/message 和必要诊断信息。
- 多次错误不会在对话区域堆满大块彩色提示。
- 错误摘要、详细错误和普通 assistant 返回不产生明显重复。
- 不破坏现有错误解析、停止生成、重试、pending stage transition 和 prompt 过滤逻辑。

## 建议测试

- 前端组件测试：错误发生后错误提示位于最新消息附近，而不是顶部固定区域。
- 前端组件测试：错误默认折叠，点击后展开，再点击可收起。
- chat service / prompt 测试：折叠错误或错误控制消息不会进入下一轮 runtime prompt。
- 回归测试：已有 `artifact_truncated`、`stage_readiness_blocked`、SSE error code 展示不被破坏。

## 非目标

- 不改变后端错误 code taxonomy。
- 不隐藏所有错误细节。
- 不把错误伪装成成功回复。
- 不为单个 workflow 或 agent 做专属错误 UI。

## 2026-06-25 处理记录

本轮目标模式将该 UX 候选作为一个完整用户故事完成，覆盖两条此前混在一起的错误展示链路：

1. Agent Runtime / 前端 SSE 失败：`chatService` 不再把原始错误详情写成大段 assistant Markdown，而是写入 `Message.errorDiagnostic` 元数据。对话内容只保留短摘要；`ChatPane` 默认折叠详情，用户点击后可查看 `reason`、`action`、`code` 和 `rawMessage`。
2. 右侧产物可视化诊断：原先 `currentArtifactVisualDiagnostic` notice 在 `chatHistory.map(...)` 之前渲染，因此总出现在对话区域顶部。本轮将它移动到消息流之后，作为最新诊断反馈展示，并默认折叠详细诊断文本。

同时保留了既有处理动作：

- 结构化输出失败仍可重试本阶段；连续失败时仍提供“补充信息后再试”。
- provider / 模型配置失败仍可打开模型设置、检测连接、重试本阶段。
- 停止生成、partial artifact truncation、pending stage transition 行为不变。
- 旧版本地历史中的 `**Error:**`、`⚠️ **模型配置或供应商异常**`、`⚠️ **结构化输出生成失败**` 等控制反馈仍会被 prompt builder 过滤。

## 已运行验证

- 红测：新增测试先失败于缺少 `Message.errorDiagnostic`、provider 原始错误仍进入 `content`、右侧产物诊断 notice 位于消息顶部、旧错误摘要未被 prompt 过滤。
- 聚焦前端：`cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/__tests__/store.test.ts src/core/__tests__/llm.test.ts`，210 passed。
- New Agents 前端全量：`cd tools/new-agents/frontend && npm run test`，43 files / 668 tests passed。仍有既有 `ArtifactPane` React `act(...)` warning，退出码为 0。
- TypeScript / lint：`cd tools/new-agents/frontend && npm run lint`，通过。
- 全量确定性本地自动化：`NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`，通过。覆盖 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build、New Agents Frontend 668 passed、New Agents Backend 505 passed，以及 New Agents Browser E2E 3 passed / 3 skipped / 9 deselected。

## 残余风险

- `ArtifactPane` 相关测试仍有既有 React `act(...)` warning，本轮未处理。
- 本轮未改变后端 `context_builder.py` 的文本过滤规则，因为后端当前不会持久化前端失败消息；如后续把前端错误元数据同步到服务端消息，需要同步服务端按语义字段排除 prompt。
