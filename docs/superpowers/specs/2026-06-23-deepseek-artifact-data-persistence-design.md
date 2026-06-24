# DeepSeek Artifact Data Persistence Design

## Milestone

DeepSeek 结构化产物数据持久化与 snapshot 审计闭环。

## 用户故事

当用户通过 New Agents 生成 DeepSeek V4 兼容的结构化 artifact 时，后端不仅保存 renderer 输出的 Markdown，也保存已经通过 Pydantic schema 校验的 `artifact_data`。维护者或后续功能读取 run snapshot 时，可以看到当前 artifact 的结构化业务数据来源；旧版本和手工编辑版本保持可用，并明确没有结构化来源。

## 范围

- `render_agent_turn_from_artifact_data()` 返回 `AgentTurnOutput` 时携带 validated `artifact_data` 的 JSON-safe 数据。
- `AgentTurnOutput` 允许内部字段 `artifact_data`，但 typed SSE 主路径仍保留现有 `artifact_update.markdown`。
- `AgentArtifactVersion` 增加 nullable JSON text 字段保存结构化产物数据；旧版本与手工编辑版本为 `None`。
- `stream_agent_run_events()` 在 artifact replace 时把 `final_output.artifact_data` 随同 Markdown 写入 artifact version。
- `get_run_snapshot()` 的当前 artifacts 返回 `artifactData`，用于审计和后续质量诊断。
- `app.py` 沿用当前轻量列迁移模式，为已有 `agent_artifact_versions` 表补列。
- 更新 DeepSeek todo，记录“同时持久化 `artifact_data`”已裁决并完成。

## 非目标

- 不新增 DeepSeek 专属 API、runtime、store、renderer 或前端分支。
- 不改变 `/api/agent/runs/stream` 的事件类型和主用户展示行为。
- 不引入真实 DeepSeek 网络 smoke 作为默认门禁。
- 不做前端质量诊断 UI，不做 artifact 重渲染按钮。

## 验收条件

- `render_agent_turn_from_artifact_data()` 返回的 `AgentTurnOutput.artifact_data` 等于 validated model 的 JSON-safe dump。
- `record_artifact_version(..., artifact_data=...)` 后，run snapshot artifact 返回 `artifactData`；未传入时返回 `artifactData: null`。
- `stream_agent_run_events()` 将 final output 的 `artifact_data` 传给 persistence；无 `artifact_data` 的传统输出仍能保存 Markdown。
- `/api/agent/runs/stream` 生成的 persisted snapshot 包含当前 artifact 的 `artifactData`。
- app 初始化能为已有 `agent_artifact_versions` 表补齐 `artifact_data_json` 列。
- 相关后端测试通过，且不要求外部网络、凭证或模型额度。

## 风险

- 这是跨层契约变更，必须避免把 `artifact_data` 误当成模型端必填字段破坏旧路径。
- 数据库字段采用 JSON text 保存，避免引入迁移框架；序列化必须保持 UTF-8 且对象语义稳定。
- snapshot 响应新增字段可能影响严格前端类型或测试；本轮以后端 snapshot 契约为准，前端消费可在后续质量诊断 UI 中补齐。
