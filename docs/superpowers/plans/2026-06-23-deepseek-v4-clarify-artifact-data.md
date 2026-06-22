# DeepSeek V4 CLARIFY 结构化 Artifact Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `TEST_DESIGN/CLARIFY` 在 DeepSeek V4 JSON object mode 下由模型输出业务结构化数据，后端确定性渲染完整 Markdown artifact，并保持现有 typed SSE / persistence 协议不变。

**Architecture:** 新增后端 `artifact_data_renderers.py` 承载 stage data schema 与 renderer。`agent_runtime.py` 在 raw JSON streaming final parse 时识别 `artifact_data`，把它转换为现有 `AgentTurnOutput`，再复用 `validate_agent_turn()`、`stream_services.py` 和 run persistence。

**Tech Stack:** Python 3.11、Pydantic v2、pytest、OpenAI-compatible Chat Completions raw JSON streaming。

---

### Task 1: RED - Artifact Data Schema 与 Renderer 测试

**Files:**
- Create: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] Step 1: 写失败测试 `test_clarify_artifact_data_rejects_blank_required_values`，构造空白字符串或空数组，期望 schema 抛出 `ValidationError`。

- [ ] Step 2: 写失败测试 `test_render_clarify_artifact_data_is_deterministic_and_contract_valid`，用一份完整 `artifact_data` 调用 `render_agent_turn_from_artifact_data()` 两次，断言输出相等、包含 `# 需求分析文档`、`flowchart TD`，且 `validate_agent_turn()` 通过。

- [ ] Step 3: 运行：

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_artifact_data_renderers.py -q
```

Expected: FAIL，原因是 `artifact_data_renderers` 模块不存在。

### Task 2: GREEN - 实现 CLARIFY Schema 与 Renderer

**Files:**
- Create: `tools/new-agents/backend/artifact_data_renderers.py`

- [ ] Step 1: 定义 Pydantic models，全部 `extra="forbid"`，所有字符串经 validator 禁止空白，所有 list 字段禁止空数组。

- [ ] Step 2: 实现 `render_agent_turn_from_artifact_data(raw, workflow_id, current_stage_id, chat, stage_action, warnings)`；首批只支持 `TEST_DESIGN/CLARIFY`，其它 stage 返回 `None` 或抛出明确错误。

- [ ] Step 3: Renderer 输出固定 Markdown 表格和 `flowchart TD`。

- [ ] Step 4: 运行 Task 1 测试，确认通过。

### Task 3: RED - Runtime 解析 artifact_data 与 DeepSeek capability 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] Step 1: 添加测试 `test_parse_agent_turn_output_text_renders_clarify_artifact_data`，传入包含 `artifact_data` 的 JSON 字符串和 `workflow_id="TEST_DESIGN"`、`current_stage_id="CLARIFY"`，断言返回 `AgentTurnOutput` 且 artifact markdown 由 renderer 生成。

- [ ] Step 2: 添加测试 `test_runtime_raw_json_stream_turn_renders_artifact_data_before_final_output`，mock `stream_chat_completion_content()` 返回 artifact_data JSON，断言 final output markdown 通过 contract，且请求仍发送 `response_format={"type":"json_object"}`。

- [ ] Step 3: 添加测试 `test_deepseek_v4_resolves_json_object_only_capability`，断言 DeepSeek V4 tier 是 `json_object_only`。

- [ ] Step 4: 运行：

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_runtime.py -q
```

Expected: FAIL，原因是 runtime 还不能识别 `artifact_data` 或 capability resolver 不存在。

### Task 4: GREEN - Runtime 接线

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] Step 1: 新增 provider capability resolver，并在 raw stream 请求中使用 resolver 的 `response_format`。

- [ ] Step 2: 将 `parse_agent_turn_output_text()` 扩展为可接收 `workflow_id`、`current_stage_id`；当 JSON 包含 `artifact_data` 时调用 renderer 转换为 `AgentTurnOutput` payload。

- [ ] Step 3: 为 `TEST_DESIGN/CLARIFY` 生成专属输出指令，要求模型返回 `artifact_data` 而不是完整 Markdown。

- [ ] Step 4: raw stream retry prompt 在 schema/contract 失败时继续给出明确错误，不伪造 artifact。

- [ ] Step 5: 运行 Task 3 测试，确认通过。

### Task 5: Endpoint/SSE 兼容回归

**Files:**
- Modify only if RED requires: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] Step 1: 如现有 endpoint tests 未覆盖 artifact_data raw path，补一条 patch runtime builder 的端点测试或保留 runtime-level coverage。

- [ ] Step 2: 运行：

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_artifact_data_renderers.py tests/test_agent_runtime.py tests/test_agent_contracts.py tests/test_agent_endpoint.py -q
```

Expected: PASS。

### Task 6: 文档记录与提交

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] Step 1: 记录 `TEST_DESIGN/CLARIFY` 首个垂直切片完成，后续迁移顺序仍为 `STRATEGY`、`CASES`、`DELIVERY` 和其它 workflow。

- [ ] Step 2: 运行：

```bash
python3 -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
git diff --check -- tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/superpowers/specs/2026-06-23-deepseek-v4-clarify-artifact-data-design.md docs/superpowers/plans/2026-06-23-deepseek-v4-clarify-artifact-data.md
```

- [ ] Step 3: Stage only 本轮文件，不包含 zip、tech-debt、todo README。

- [ ] Step 4: Commit:

```bash
git commit -m "feat: 支持 DeepSeek CLARIFY 结构化产物数据"
```
