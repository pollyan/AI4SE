# New Agents 阶段推进选择控件历史保留 Todo

状态：已归档
创建日期：2026-06-24  
完成日期：2026-06-25
相关模块：`tools/new-agents/`

## 完成记录

2026-06-25 已修复：用户点击阶段推进确认控件后，`chatService` 会在切换阶段前追加普通用户历史消息 `已确认进入{目标阶段名}`，再以同一确认文本触发下一阶段生成。生成调用继续使用 `appendUserMessage: false` 和非重试 assistant 响应，避免重复追加用户消息；`请继续生成当前阶段产出物` 仅保留给“重试当前阶段生成”的内部续写路径。

验证覆盖：

- 确认阶段推进后，chatHistory 中保留用户确认事件。
- 新阶段 assistant 响应追加在确认事件之后。
- stale pending transition 会被清理，但不会生成确认事件或续写。
- pending 卡片消失后，聊天历史仍可显示用户确认进入目标阶段的记录。

验证记录：

- `npm run test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx`：2 个测试文件、93 个测试通过。
- `npm run test`（`tools/new-agents/frontend`）：43 个测试文件、662 个测试通过；保留既有 `ArtifactPane` act warning。
- `git diff --check`：通过。
- `./scripts/test/test-local.sh all`：在当前环境开启可选 LLM judge 时失败于 `test_alex_final_artifact_passes_optional_llm_judge`，原因为外部 judge 返回非严格 JSON；该失败不属于本用户故事 deterministic 覆盖面。
- `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`：通过；Browser E2E 为 3 passed / 3 skipped。

## 背景

New Agents 在左侧对话框中会提示用户可以推进到下一个阶段，例如从需求澄清进入策略制定。这个选择本身是合理的，因为它让用户显式确认阶段切换。

当前体验问题是：用户点击这个推进选择后，原本的选择控件会从对话历史中完全消失，并被后续流式响应替换。用户未来回看对话时，看不到自己曾在这一轮执行过“推进到下一阶段”的操作，导致历史记录与用户记忆中的交互场景割裂。

## 当前问题

阶段推进控件现在更像一个临时操作入口，而不是对话历史中的可追溯事件。

具体表现：

- 用户点击“进入下一阶段”后，左侧原选择控件不再保留。
- 后续 agent 流式响应占据了该位置，历史中缺少用户做出选择的证据。
- 对话回放无法清晰表达“系统建议推进、用户确认推进、系统开始下一阶段”这一完整链路。
- 如果未来客户审计或复盘 agent 工作过程，无法从聊天记录中准确定位阶段切换是由用户主动确认触发的。

## 目标能力包

让阶段推进选择控件成为对话历史的一部分。用户点击后，控件应保留在左侧对话流中，并呈现为已选择、disabled 或等价的只读状态，用于表达该操作已经发生。

该能力包应继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run / message / artifact 模型和共享 UI 基础设施，不新增 Lisa、Alex、DeepSeek 或未来 agent 专属 runtime、API path、store 或 renderer。

## 期望交互

1. Agent 在当前阶段完成时，在左侧对话中显示“建议进入下一阶段”的选择控件。
2. 用户点击该控件后，控件不从历史中消失。
3. 已点击控件转换为只读状态，例如：
   - disabled 按钮；
   - 已选择的 action chip；
   - 带时间或状态的“已确认进入策略制定”记录。
4. 新阶段的流式响应应作为后续消息追加，而不是覆盖或替换该控件所在的历史事件。
5. 用户回看历史时，可以清楚看到阶段切换是在哪一轮由自己确认的。

## 设计建议

阶段推进动作应被建模为可持久化的 conversation event，而不是纯前端临时 UI 状态。

建议考虑：

- 在消息模型或 agent turn metadata 中记录用户选择的 `stage_action`、源阶段、目标阶段、确认时间和显示文案。
- 前端渲染时将已确认的阶段动作展示为 disabled / selected 状态的控件或只读确认项。
- 后续流式响应追加为新的 agent turn，不应复用同一个消息槽位覆盖原交互控件。
- 如果存在失败或撤销语义，需要明确显示“已点击但推进失败”或“用户取消推进”，避免历史状态误导。
- 控件样式应与现有左侧对话操作组件保持一致，不引入单个 workflow 的特殊渲染分支。

## 验收标准

- 用户点击“进入下一阶段”后，原阶段推进选择仍保留在左侧对话历史中。
- 保留后的控件不可再次点击，视觉上明确表达已选择或已确认。
- 新阶段的流式响应作为后续消息渲染，不覆盖已确认控件。
- 刷新页面或重新打开 run 后，已确认的阶段推进记录仍可见。
- 如果阶段推进请求失败，历史中应能表达该操作失败，而不是静默删除控件。
- 实现不得破坏 typed SSE、共享状态管理、artifact 渲染、持久化 run / message 模型和现有阶段推进流程。

## 建议测试

- 前端组件测试：点击阶段推进控件后，控件以 disabled / selected 状态留在消息列表中。
- 前端状态测试：后续 agent turn 流式消息追加时，不覆盖已确认的阶段推进控件。
- 持久化或回放测试：重新加载 run 后，历史中仍显示用户已确认推进到下一阶段。
- 异常路径测试：阶段推进 API 或 runtime 失败时，历史中显示失败状态，且不会误导用户以为已成功推进。
- 端到端或等价验收：从 CLARIFY 点击进入 STRATEGY 后，左侧对话同时保留“用户确认进入策略制定”的历史记录和新阶段响应。

## 非目标

- 不改变阶段是否允许推进的成熟度门禁规则；该问题由阶段推进成熟度门禁 todo 处理。
- 不要求重新设计整个聊天消息系统。
- 不新增单个 agent 或 workflow 专属的选择控件渲染管线。
- 不把所有普通按钮都持久化为历史事件；本 todo 聚焦会改变 workflow 状态的阶段推进选择。

## 待决策问题

- 历史中应保留原始按钮样式，还是转换为更像审计记录的只读 action chip？
- 是否需要显示确认时间、源阶段和目标阶段？
- 失败状态是否允许用户重试，还是必须生成新的可点击推进控件？
- 该确认事件应归类为 user message、system event，还是 agent turn 内的 user action metadata？
