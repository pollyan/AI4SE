# DeepSeek V4 结构化输出 Readiness Gate 设计

## 背景

`docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 显示 17 个在线 workflow stage 已完成 `artifact_data` 迁移。当前测试覆盖分散在 renderer、runtime 和 contract 测试中，但缺少一个本地可重复的 readiness gate，能从当前 `workflow_manifest.json` 出发证明所有在线 stage 都具备 DeepSeek V4 Flash 兼容链路。

## 目标

新增一个无需联网、无需凭证的后端 readiness gate，验证每个在线 workflow stage 都满足：

- 有显式配置的 `artifact_data` renderer。
- 有可用于本地验收的有效 `artifact_data` fixture。
- renderer 输出的 Markdown 能通过当前 artifact contract。
- structured output instruction 要求 `artifact_data`，且不要求模型输出 `artifact_update.markdown`。
- DeepSeek V4 Flash raw JSON streaming 继续使用 `response_format={"type":"json_object"}` 和 thinking disabled。

## 非目标

- 不调用真实 DeepSeek API，不消耗网络、凭证或额度。
- 不新增 Lisa、Alex、DeepSeek 专属 runtime、API path、store 或 renderer。
- 不改变 typed SSE、run persistence、artifact persistence 或前端协议。
- 不在本轮持久化 raw `artifact_data`；这会触及数据库和 snapshot API，应作为后续独立能力包。

## 方案

1. 在 `artifact_data_renderers.py` 中将现有 `(workflow_id, stage_id) -> Pydantic model + renderer` 分支收束为共享 renderer registry。
2. 暴露 `get_artifact_data_renderer_stage_keys()`，供 readiness test 枚举当前 renderer 支持面。
3. 新增 `test_deepseek_v4_readiness.py`：
   - 从 `workflow_manifest.json` 读取所有在线 stage。
   - 用 fixture map 覆盖所有 stage。
   - 对每个 stage 调用 `render_agent_turn_from_artifact_data()` 并执行 `validate_agent_turn()`。
   - 对每个 stage 检查 `build_structured_output_instruction()` 使用 `artifact_data`，不出现 `artifact_update.markdown`。
   - 对每个 stage 用 fake DeepSeek stream 验证 runtime 请求配置和最终 artifact。

## 验收

- 新 readiness test 在缺少 renderer registry helper 时先失败。
- 实现后 readiness test 能覆盖全部 17 个 manifest stage。
- 原有 `test_artifact_data_renderers.py`、`test_agent_runtime.py`、`test_agent_contracts.py` 保持通过。
- DeepSeek todo 更新为“本地 readiness gate 已补齐；真实 smoke 和 raw data persistence 仍为后续候选”。
