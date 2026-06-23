# DeepSeek V4 结构化输出 readiness 收口设计

## 背景

当前 `tools/new-agents/` 已把现有 5 个在线 workflow、17 个 stage 迁移到 `artifact_data` 路径：模型只输出 JSON 数据，后端通过 Pydantic schema 和 deterministic renderer 生成 Markdown、Mermaid 与 `ai4se-visual`。`docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 仍处于活动候选状态，说明主线还缺一个可重复运行的收口证据，证明当前 manifest 中所有在线 stage 都受 DeepSeek V4 结构化输出边界保护。

## 用户故事

作为后续维护 New Agents 的开发者或目标模式 Agent，当我新增、修改或审查 workflow stage 时，我可以运行一个专项 readiness gate，确认所有在线 stage 都支持 `artifact_data`、DeepSeek V4 仍走 JSON object only、prompt 不要求模型拼完整 Markdown artifact，从而避免格式化输出风险重新进入主路径。

## 范围

本轮纳入：

- 新增 DeepSeek V4 readiness 后端测试文件。
- 暴露或固化当前 artifact_data ready stage 集合，供测试与后续工具读取。
- 验证 readiness gate 覆盖当前 `workflow_manifest.json` 全部 stage。
- 验证每个 ready stage 的 structured output instruction 要求 `artifact_data`，且不要求 `artifact_update.markdown` 或完整 Markdown 文档正文。
- 验证 DeepSeek V4 Flash capability 为 `json_object_only`，model settings 关闭 thinking。
- 更新 `docs/todos/`，把 DeepSeek V4 结构化输出主线从活动候选收口为已完成闭环。

本轮不纳入：

- 不新增 Alex `PRD_REVIEW` 或 `STORY_BREAKDOWN` workflow 到当前 `master`。
- 不调用真实 DeepSeek V4 Flash；真实 smoke 仍需要凭证、网络和额度。
- 不改变 typed SSE、run persistence、artifact persistence 或前端协议。
- 不为 Lisa、Alex、DeepSeek 或未来 agent 增加专属 runtime/API/store/renderer。

## 设计

### Readiness 数据源

后端 runtime 增加只读 helper `get_artifact_data_ready_stages()`，返回 `ARTIFACT_DATA_READY_STAGES` 的副本。生产代码继续通过 `supports_artifact_data_rendering(workflow_id, current_stage_id)` 判断单个 stage 是否 ready；测试通过 helper 比对 manifest，避免重复硬编码 ready stage 列表。

### Readiness 测试

新增 `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`：

1. 读取 `tools/new-agents/workflow_manifest.json`，提取所有 `(workflow_id, stage_id)`。
2. 断言 `get_artifact_data_ready_stages()` 与 manifest stage 集合完全一致。
3. 遍历所有 ready stage，断言 `build_structured_output_instruction()` 包含 `artifact_data`，不包含 `artifact_update.markdown`，并明确不要输出完整 Markdown。
4. 断言 `resolve_structured_output_capability("deepseek-v4-flash") == "json_object_only"`。
5. 断言 `build_model_settings("deepseek-v4-flash") == {"extra_body": {"thinking": {"type": "disabled"}}}`。

### 文档收口

DeepSeek V4 todo 更新为已完成状态，并记录 readiness gate 的验证命令。`docs/todos/refactor/README.md` 移除 DeepSeek V4 文件作为活动入口，保留 New Agents 增强诊断作为后续活跃工作池。

## 验收条件

1. Given 当前 manifest 中的所有在线 stage，When 运行 DeepSeek V4 readiness 测试，Then ready stage 集合必须与 manifest 完全一致。
2. Given 任一 ready stage，When 构建 structured output instruction，Then 指令必须要求 `artifact_data`，且不能要求 `artifact_update.markdown`。
3. Given DeepSeek V4 Flash 模型名，When resolve capability 和 model settings，Then capability 为 `json_object_only`，thinking disabled。
4. Given readiness 测试和现有 runtime/contract 测试均通过，When 更新 todo，Then `docs/todos/` 反映 DeepSeek V4 格式化输出主线已收口。

## 风险

- 当前 `master` 不包含后续隔离分支里的 `PRD_REVIEW` / `STORY_BREAKDOWN`，因此 readiness gate 只覆盖当前 manifest 的 17 个 stage；后续这些 workflow 主线化时，readiness gate 会强制它们同步接入 `artifact_data`。
- 真实模型输出质量没有在本轮验证；该风险由可选 real smoke 管理，不作为默认本地门禁。
