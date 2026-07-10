# ADR-0001：以持久化 Turn Request 作为共享运行时的幂等边界

状态：已接受（QS-02）

## 决策

New Agents 的每一次逻辑发送由客户端生成并保留稳定的 `(runId, requestId)`：首次发送同时生成两者，重试复用两者；后续新发送复用既有 `runId`、生成新的 `requestId`。`requestId` 是 API 必填字段，服务端不得在缺失时隐式生成。服务端以 `(run_id, request_id)` 的唯一约束保存 `AgentRunTurnRequest`，其状态是 `active`、`completed` 或 `failed`，并保存可重放的 terminal outcome。相同身份不得再次调用模型、重复追加用户/助手消息或创建 artifact version。

## 原因与取舍

`runId` 表示长生命周期的工作流历史，不能区分同一个 run 内的两次用户发送；只有先由客户端生成并随首个请求发送，网络层重试才有可重放的服务端身份。把 request identity 放在前端 localStorage 也无法提供服务器端的唯一性或网络断开后的恢复。复用 metric JSON 会丢失事务语义和唯一约束。独立持久化记录带来一个共享表，但把幂等、重放和并发冲突放在正确的 durable boundary。

## 后果

所有 workflow 继续走同一 `/api/agent/runs/stream`、同一 persistence adapter 和 typed SSE 事件；不会新增 agent 专属路径。完成、失败与运行中重复请求必须有明确 SSE verdict。这个表由现有 `db.create_all()` 创建；本 ADR 不扩展为通用数据库迁移框架，该机制仍由既有 P3 owner 管理。
