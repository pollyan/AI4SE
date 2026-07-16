# New Agents Ubiquitous Language

- **Run**：一次由用户输入触发、可恢复的工作流执行历史。
- **Progress frame**：在最终结论前向用户展示的本地执行状态；它可以提示用户，但不能替代模型针对当前输入给出的有意义自然对话。
- **Renderable artifact**：可由右侧工作区安全显示的产出物内容；它不是完整回合成功的证明。
- **Natural-chat-first delta**：首个用户可见业务 delta 只携带与当前分析直接相关的自然对话；首个 artifact 必须在其后单独出现。
- **Artifact-first delta**：provider 或历史服务可能产生的、先携带可渲染产出物但尚无自然对话的内部更新；共享 sequencer 必须缓存它，不能直接暴露给客户端。
- **Render commit barrier**：前端在首个自然对话更新与首个 artifact 更新之间保留的一次异步渲染提交机会，用于保证真实 DOM 可观察顺序，而不是人为延迟完整产物。
- **Terminal outcome**：明确结束一个 run 的成功或错误结果；连接 EOF 本身不是 terminal outcome。
- **Normal artifact version**：只在成功 terminal outcome 后保存到历史中的完整产出物版本。
- **Turn request**：一次逻辑用户发送的持久化身份 `(runId, requestId)`；首次发送由客户端同时生成两者，用户重试必须复用两者；它不同于覆盖整个工作流历史的 Run。
- **Idempotent replay**：相同 Run 与 turn request 再次到达时，服务端返回已经记录的同一 terminal outcome，而不再次调用模型或追加消息/版本；服务端不为缺失 `requestId` 隐式生成身份。
