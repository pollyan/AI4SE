# New Agents Stage Action Choice Persistence Design

## CGA 摘要

`docs/todos/refactor/2026-06-24-new-agents-stage-action-choice-persistence.md` 是当前活跃候选。当前阶段推进确认卡由 `pendingStageTransition` 在 `ChatPane` 的消息列表外部渲染；点击确认后 `confirmStageTransition()` 会清空 pending 状态并触发内部续写，因此确认控件从历史中消失，聊天历史只剩下一阶段 assistant 响应，缺少“用户确认推进”的可追溯事件。

## 用户故事

作为 New Agents 用户，我点击“确认进入下一阶段”后，左侧对话历史应保留一条只读的用户确认记录，表达我已经确认从源阶段进入目标阶段；后续新阶段生成作为后续 assistant 消息追加，不覆盖该确认事件。

## 设计

- 点击确认阶段推进时，在切换阶段前追加一条普通 `user` message，例如 `已确认进入策略制定`。
- 确认推进触发的新阶段生成复用同一条确认文本作为请求 prompt，并继续使用 `appendUserMessage: false`，避免重复追加用户消息；`请继续生成当前阶段产出物` 仅保留给“重试当前阶段生成”的内部续写路径。
- 复用现有 `chatHistory` 和 run snapshot 消息恢复能力，不新增 workflow/agent 专属 UI、store 或 API。
- 取消“暂不进入”仍只清除 pending 状态，不追加历史事件。

## 非目标

- 不改变阶段是否允许推进的成熟度门禁。
- 不新增阶段动作专属后端 API 或消息表字段。
- 不改变 typed SSE `stage_action` contract。
- 不实现撤销或失败重试审计语义。

## 验收

- 点击确认后，chatHistory 中出现用户确认进入目标阶段的消息。
- 新阶段 assistant 响应追加在用户确认消息之后。
- pending 确认卡消失后，历史仍能回看用户确认动作。
- 阶段推进确认不会在历史中重复追加用户消息；当前阶段重试的内部续写 prompt 不作为用户消息出现在历史中。
