# DeepSeek V4 格式化输出主线完成闭环 Spec

## 背景

DeepSeek V4 Flash 当前只能稳定使用 OpenAI-compatible JSON mode，即 `response_format={"type":"json_object"}`，不能被当作 strict Structured Outputs。仓库已经把 5 个在线 workflow、17 个 stage 逐步迁移为 `artifact_data`：模型只输出业务 JSON，后端用 Pydantic schema 校验并确定性渲染 Markdown、Mermaid 和 `ai4se-visual`。

当前剩余风险不是某个单独 stage 未迁移，而是主线缺少一个集中门禁来证明“所有在线 stage 都已经完成 DeepSeek V4 格式化输出收口”。如果以后新增 stage 或改动 runtime，可能静默回退到 `artifact_update.markdown` 指令，让模型重新承担完整 Markdown/Mermaid 格式拼接职责。

## 用户故事

作为 New Agents 的维护者，当我继续使用 DeepSeek V4 Flash 生成各 workflow 产物时，我需要一个可重复运行的门禁证明所有在线 stage 都走 `artifact_data` schema + deterministic renderer，而不是依赖模型直接拼最终 Markdown，从而降低“格式不完整 / 结构化输出生成失败”的回归风险。

## 范围

纳入本轮：

- 为 DeepSeek V4 artifact_data 路径建立集中 readiness gate。
- readiness gate 覆盖当前 manifest 中所有在线 workflow/stage。
- gate 需要验证：
  - stage 被声明为支持 artifact_data renderer。
  - stage 的结构化输出指令不再要求 `artifact_update.markdown`。
  - stage 的结构化输出指令要求 `artifact_data`。
  - DeepSeek V4 capability 仍是 `json_object_only`，并关闭 thinking。
  - renderer 不支持未知 stage 时显式失败或返回不可用，而不是假成功。
- 最小化实现方式：优先抽出共享 stage 集合或 helper，避免 runtime 指令、renderer 和测试各维护一套难以发现漂移的列表。
- 更新 DeepSeek todo 状态，让 `docs/todos/` 反映本轮完成闭环。

不纳入本轮：

- 新增真实 DeepSeek V4 Flash smoke 作为默认本地门禁。真实 smoke 仍需要凭证、网络和额度。
- 新增或迁移新的 workflow/stage。
- 重构全部 renderer schema 文件结构。
- 改 typed SSE 协议、共享 Agent Runtime API path、frontend store 或 renderer。

## 验收条件

1. Given 当前 `workflow_manifest.json` 的所有在线 stage，When 运行 readiness gate 测试，Then 每个 stage 都被判定为 artifact_data ready。
2. Given 任一在线 stage，When 构造结构化输出指令，Then 指令包含 `artifact_data`，且不包含 `artifact_update.markdown` 作为模型输出要求。
3. Given DeepSeek V4 Flash model name，When 解析 provider capability，Then 仍返回 `json_object_only` 和 `{"type": "json_object"}`，并通过 model settings 关闭 thinking。
4. Given 未配置 renderer 的未知 stage，When 传入 `artifact_data` payload，Then 后端显式返回不可渲染状态或抛出可诊断错误，不伪造 artifact。
5. Given 本轮完成，When 查看 `docs/todos/refactor/`，Then DeepSeek V4 结构化产物数据不再表现为未收口的活动候选。

## 风险

- readiness gate 如果只检查静态列表，仍可能漏掉 renderer 行为。为降低风险，测试应同时覆盖 manifest stage、runtime 指令和 renderer 支持入口。
- 当前 renderer 文件较大，本轮不做大拆分，避免扩大风险。
- 主工作区存在未提交 todo 文档改动；本轮在隔离 worktree 修改文档，收尾说明必须标注主工作区未提交文件未被触碰。

## 验证计划

- `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q`
- `python3 -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py -q`
- `git diff --check`
