# New Agents Ubiquitous Language

- **Run**：一次由用户输入触发、可恢复的工作流执行历史。
- **Progress frame**：在最终结论前向用户展示的、诚实描述当前执行状态的对话更新。
- **Renderable artifact**：可由右侧工作区安全显示的产出物内容；它不是完整回合成功的证明。
- **Artifact-first delta**：先携带可渲染产出物、尚未携带自然对话内容的中间更新。
- **Terminal outcome**：明确结束一个 run 的成功或错误结果；连接 EOF 本身不是 terminal outcome。
- **Normal artifact version**：只在成功 terminal outcome 后保存到历史中的完整产出物版本。
- **Turn request**：一次逻辑用户发送的持久化身份 `(runId, requestId)`；首次发送由客户端同时生成两者，用户重试必须复用两者；它不同于覆盖整个工作流历史的 Run。
- **Idempotent replay**：相同 Run 与 turn request 再次到达时，服务端返回已经记录的同一 terminal outcome，而不再次调用模型或追加消息/版本；服务端不为缺失 `requestId` 隐式生成身份。
