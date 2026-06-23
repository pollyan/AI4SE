# DeepSeek V4 格式化输出失败诊断设计

## Current State Gap

DeepSeek V4 Flash 当前已经按 `json_object_only` provider 使用，所有在线 workflow stage 都具备 `artifact_data` renderer、deterministic Markdown/visual renderer、contract-valid fixture 和 readiness tests。现有 `test_deepseek_v4_readiness.py` 已证明成功路径覆盖全部 manifest stage。

剩余缺口不再是“某个 stage 还不会渲染”，而是失败路径的诊断质量：当 DeepSeek 输出非法 JSON、`artifact_data` 缺字段/跨字段不一致、renderer 未配置或 renderer 输出不满足 artifact contract 时，runtime 主要抛出底层异常或泛化 validation error。retry prompt 已经要求修正 `artifact_data`，但缺少统一错误分类、workflow/stage 上下文和 schema path 摘要，后续真实 DeepSeek smoke 或 E09 observability 难以判断到底是 JSON 语法、schema、renderer 还是 contract 问题。

## Milestone

建立 DeepSeek V4 格式化输出失败诊断闭环。

用户现在可以：

- 在 DeepSeek V4 结构化输出失败时获得明确的失败类别。
- 区分 `json_decode`、`artifact_data_schema`、`artifact_data_renderer` 和 `artifact_contract`。
- 让 retry prompt 聚焦修正 `artifact_data` 数据问题，而不是要求模型重写 Markdown。
- 为后续运行统计产品化提供稳定错误分类来源。

## Design Decisions

- 保持共享 Agent Runtime，不新增 DeepSeek 专属 runtime、API path、store 或 renderer。
- 新增轻量诊断异常类型，包装底层异常并保留原始异常链。
- 错误分类只发生在 raw JSON streaming final parse / renderer / contract validation 路径，不改变成功路径、typed SSE payload 或 persisted artifact 模型。
- `ValidationError` 来自 `render_agent_turn_from_artifact_data()` 时归类为 `artifact_data_schema`。
- renderer 未配置或 renderer 返回 `None` 归类为 `artifact_data_renderer`。
- `json.JSONDecodeError` 归类为 `json_decode`；如果已有可用 partial delta，保留现有中断 artifact 行为。
- `ContractValidationError` 或最终 `AgentTurnOutput` validation failure 归类为 `artifact_contract`。
- retry prompt 包含诊断类别、workflow/stage 和错误摘要；对 artifact_data stage 仍禁止 Markdown、Mermaid、表格直写。

## Requirements

- `agent_runtime.py` 暴露可测试的诊断对象或异常，至少包含 `kind`、`workflow_id`、`stage_id`、`message` 和可选 `path`。
- raw JSON streaming 在最终失败时抛出的异常可被测试断言为对应 kind。
- retry prompt 对 artifact_data stage 包含 kind 和 workflow/stage，并继续要求完整 JSON object + `artifact_data`。
- schema validation failure 能提取至少一个可读 schema path。
- 成功路径 readiness 不变。
- 不改变前端 SSE schema、run persistence schema 或 workflow manifest。

## Non-Goals

- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
- 不新增前端错误展示 UI；本轮是后端诊断信任闭环，后续 E09 可消费。
- 不持久化错误分类到数据库；如后续运行统计需要，再接入 turn metrics。
- 不重新迁移任何 stage 的 artifact_data schema 或 renderer。

## Acceptance Checks

- JSON decode failure test proves final error kind is `json_decode`.
- artifact_data schema failure test proves retry prompt and final error kind are `artifact_data_schema` and include schema path.
- missing renderer test proves error kind is `artifact_data_renderer`.
- artifact contract failure test proves retry prompt remains artifact_data-focused and final error kind is `artifact_contract`.
- DeepSeek readiness tests still pass.
- `agent_runtime.py` py_compile passes.
