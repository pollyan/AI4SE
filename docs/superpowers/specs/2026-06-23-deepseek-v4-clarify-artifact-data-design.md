# DeepSeek V4 CLARIFY 结构化 Artifact Data 设计

## 背景

当前 New Agents 后端已经具备共享 `/api/agent/runs/stream`、raw JSON streaming、typed SSE、`AgentTurnOutput` 契约、artifact contract 和 run/artifact 持久化。DeepSeek V4 Flash 路径也已经通过 OpenAI-compatible Chat Completions 使用 `response_format={"type":"json_object"}`，并关闭 thinking。

但当前 raw JSON 输出仍要求模型直接生成完整 Markdown artifact，包括标题、表格、Mermaid 和 `ai4se-visual` fenced block。DeepSeek V4 JSON mode 只能保证合法 JSON，不能保证 Markdown/Mermaid 结构完整，导致“结构化输出生成失败”的根因仍然是模型承担了最终交付格式职责。

## 本轮目标

为 `TEST_DESIGN/CLARIFY` 建立首个后端垂直切片：

用户输入 -> DeepSeek JSON object mode -> Pydantic `artifact_data` schema -> 后端 deterministic renderer -> 现有 `AgentTurnOutput.artifact_update.markdown` -> `validate_agent_turn()` -> typed SSE -> run artifact persistence。

完成后，首个阶段可以让模型只输出业务结构化数据，后端负责生成完整需求分析 Markdown 和 Mermaid flowchart。前端协议和持久化模型保持不变。

## 用户故事

作为使用 DeepSeek V4 Flash 的 New Agents 用户，我希望测试设计的需求澄清阶段不再依赖模型手写整篇 Markdown/Mermaid，而是让模型输出清晰业务数据，由系统稳定生成右侧需求分析文档，这样格式缺失、表格破损或 Mermaid fence 不完整不会成为高频失败原因。

## 范围

纳入本轮：

- `TEST_DESIGN/CLARIFY` 专属 `artifact_data` Pydantic schema。
- 后端 deterministic renderer，将数据渲染为当前 contract 要求的完整 Markdown。
- raw JSON streaming 在该阶段提示模型输出 `artifact_data`，并在 final parse 时转换为现有 `AgentTurnOutput`。
- DeepSeek V4 provider capability tier 标记为 `json_object_only`，继续只发送 `response_format={"type":"json_object"}` 和 disabled thinking。
- schema / renderer / raw streaming / endpoint 相关后端测试。
- 更新 DeepSeek todo，记录首个阶段切片完成与后续迁移顺序。

不纳入本轮：

- 迁移 `TEST_DESIGN` 其它阶段或其它 workflow。
- 保存 `artifact_data` 原文到持久化模型。
- 修改 typed SSE schema、前端 state、frontend service 或 artifact renderer。
- 真实 DeepSeek 网络 smoke；需要凭证和网络，仍作为可选人工验证。

## 数据契约

`TEST_DESIGN/CLARIFY` 的 `artifact_data` 由以下非空结构组成：

- `document_info`: artifact 名称、workflow、stage、status。
- `requirement_facts`: 需求事实清单。
- `system_boundaries`: 被测系统与边界。
- `business_rules`: 业务规则与数据状态。
- `flow_links`: 核心链路与异常链路，用于生成 `flowchart TD`。
- `clarification_questions`: 待澄清问题。
- `quality_requirements`: 隐式质量需求。
- `downstream_inputs`: 后续测试设计输入。
- `stage_gate`: 阶段门禁检查项。

所有模型使用 `extra="forbid"`；字符串必须非空；数组必须非空。未知字段、空数组和空白字符串必须失败。

## 渲染规则

Renderer 生成固定顺序 Markdown：

1. `# 需求分析文档`
2. `## 文档信息`
3. `## 1. 需求事实清单`
4. `## 2. 被测系统与边界`
5. `## 3. 业务规则与数据状态`
6. `## 4. 核心链路与异常链路`
7. `## 5. 待澄清问题`
8. `## 6. 隐式质量需求`
9. `## 7. 后续测试设计输入`
10. `## 8. 阶段门禁`

表格由后端确定性生成。Mermaid 使用 `flowchart TD`，节点 ID 由后端 sanitize，节点 label 来自结构化数据。Renderer 输出必须每次稳定一致，并通过 `validate_agent_turn(workflow_id="TEST_DESIGN", current_stage_id="CLARIFY")`。

## Runtime 行为

raw streaming 在 `TEST_DESIGN/CLARIFY` 阶段的 JSON 输出要求变为：

```json
{
  "chat": "面向用户的自然工作对话",
  "artifact_data": {},
  "stage_action": null,
  "warnings": []
}
```

后端 final parse 发现 `artifact_data` 后执行：

1. 按 workflow/stage 找到对应 schema。
2. 校验业务数据。
3. 渲染 Markdown。
4. 组装现有 `AgentTurnOutput`：`artifact_update.type="replace"`，`markdown=<renderer output>`。
5. 调用 `validate_agent_turn()` 作为最终守门。

如果 schema 或 renderer 失败，raw stream retry prompt 反馈具体错误路径；连续失败后进入现有 `SCHEMA_VALIDATION_FAILED`，不伪造 artifact。

## 验收条件

- DeepSeek V4 capability resolver 返回 `json_object_only`，请求参数仍是 `response_format={"type":"json_object"}`，thinking disabled。
- `TEST_DESIGN/CLARIFY` artifact data schema 拒绝未知字段、空数组和空白字符串。
- 同一份 artifact data 渲染结果完全一致。
- renderer 输出包含所有 required headings、Markdown 表格、`flowchart TD`，并通过现有 artifact contract。
- raw JSON streaming 接收 `artifact_data` final JSON 后，最终输出仍是现有 `AgentTurnOutput`，typed SSE 消费方无需改变。
- endpoint 层仍返回 typed `agent_turn`，右侧 artifact markdown 由后端 renderer 生成并可持久化。

## 验证计划

- RED/GREEN 聚焦测试：
  - `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
  - `tools/new-agents/backend/tests/test_agent_runtime.py`
  - 必要时补 `tools/new-agents/backend/tests/test_agent_endpoint.py`
- 最小验证：
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_artifact_data_renderers.py tests/test_agent_runtime.py -q`
- 扩展验证：
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py tests/test_agent_endpoint.py -q`
  - `python3 -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`

## Worktree 决策

已执行 worktree 隔离检查。当前主工作区有未提交 zip、tech-debt 文档、todo README，以及本轮必须消费的未跟踪 DeepSeek todo。为避免隔离 worktree 丢失当前活跃工作池输入，本轮在当前工作区串行执行，并严格限定写入范围：New Agents backend、对应 tests、本轮 spec/plan、DeepSeek todo。不会修改或 stage 既有 zip、`docs/plans/tech-debt.md` 或 `docs/todos/refactor/README.md`。
