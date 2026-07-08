# DeepSeek Tool Calls 能力 Spike Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 形成 DeepSeek tool calls 是否进入 New Agents 正式结构化产出主链路的工程结论。

**Architecture:** 本轮是文档型工程信任闭环，不改共享 runtime。结论基于官方文档、本地 `llm_client.py` / `agent_runtime.py` 静态事实和密钥可用性检查，输出后续是否实现 provider capability / stream parser 的 gate。

**Tech Stack:** Markdown docs, DeepSeek Chat Completion API docs, New Agents Python backend runtime.

---

### Task 1: 官方能力核对

**Files:**
- Read: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Read: DeepSeek official docs pages linked in the spec

- [x] **Step 1: 读取官方 Tool Calls 文档**

Run:

```bash
curl -L -A Mozilla https://api-docs.deepseek.com/guides/tool_calls | rg -n "strict|Strict|Beta|tools|tool_choice|tool_calls|/beta|required|additionalProperties|minLength|maxLength|minItems|maxItems|Unsupported"
```

Expected: output shows tool calls page, strict beta instructions, schema subset constraints.

- [x] **Step 2: 读取官方 Chat Completion 文档**

Run:

```bash
curl -L -A Mozilla https://api-docs.deepseek.com/api/create-chat-completion | rg -n "tools|tool_choice|tool_calls|response_format|json_object|chat.completion.chunk|finish_reason|delta|stream"
```

Expected: output shows `response_format` values, stream chunk shape, and `finish_reason=tool_calls`.

- [x] **Step 3: 读取官方 JSON Output 文档**

Run:

```bash
curl -L -A Mozilla https://api-docs.deepseek.com/guides/json_mode | rg -n "response_format|json_object|JSON|stream|must|Output"
```

Expected: output shows JSON Output uses `response_format={'type':'json_object'}` and still requires JSON prompt guidance.

### Task 2: 本地 runtime 差距核对

**Files:**
- Read: `tools/new-agents/backend/llm_client.py`
- Read: `tools/new-agents/backend/agent_runtime.py`
- Read: `tools/new-agents/backend/stream_services.py`

- [x] **Step 1: 确认 content-only stream client**

Run:

```bash
rg -n "ChatDelta|extract_delta_content|stream_chat_completion_content|tools|tool_choice|tool_calls" tools/new-agents/backend/llm_client.py
```

Expected: `ChatDelta` only models `content`, and no request path passes `tools` / `tool_choice`.

- [x] **Step 2: 确认 DeepSeek V4 使用 json_object_only**

Run:

```bash
rg -n "deepseek-v4|json_object_only|response_format|thinking" tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_agent_runtime.py
```

Expected: `deepseek-v4-*` resolves to `response_format={"type":"json_object"}` and disables thinking.

- [x] **Step 3: 确认真实 smoke 阻塞状态**

Run:

```bash
if [ -n "$DEEPSEEK_API_KEY" ]; then echo present; else echo missing; fi
```

Expected: `missing`; do not call external model.

### Task 3: 记录结论并更新 backlog

**Files:**
- Create: `docs/superpowers/specs/2026-07-08-new-agents-deepseek-tool-calling-capability-spike-design.md`
- Create: `docs/superpowers/plans/2026-07-08-new-agents-deepseek-tool-calling-capability-spike.md`
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`

- [x] **Step 1: 写入 spec**

Expected: spec contains official facts, local runtime facts, capability table, design conclusion, and verification limitations.

- [x] **Step 2: 写入 plan**

Expected: plan records concrete commands used to establish the spike conclusion.

- [x] **Step 3: 更新 todo 状态**

Expected: 第 0 轮标记为静态 spike 已完成，live provider smoke 因缺少 `DEEPSEEK_API_KEY` 未执行，后续不启用正式 tool calls 主链路。

### Task 4: 文档验证和提交

**Files:**
- Verify: `docs/superpowers/specs/2026-07-08-new-agents-deepseek-tool-calling-capability-spike-design.md`
- Verify: `docs/superpowers/plans/2026-07-08-new-agents-deepseek-tool-calling-capability-spike.md`
- Verify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`

- [x] **Step 1: 检查占位和开放标记**

Run:

```bash
rg -n "T[B]D|TO[ ]?DO|待[ ]?补|未[ ]?决|place[ ]?holder" docs/superpowers/specs/2026-07-08-new-agents-deepseek-tool-calling-capability-spike-design.md docs/superpowers/plans/2026-07-08-new-agents-deepseek-tool-calling-capability-spike.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

Expected: no unexplained open markers in the new spike artifacts.

- [x] **Step 2: 检查 Markdown diff**

Run:

```bash
git diff --check -- docs/superpowers/specs/2026-07-08-new-agents-deepseek-tool-calling-capability-spike-design.md docs/superpowers/plans/2026-07-08-new-agents-deepseek-tool-calling-capability-spike.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

Expected: no whitespace errors.

- [x] **Step 3: 提交并推送**

Run:

```bash
git add docs/superpowers/specs/2026-07-08-new-agents-deepseek-tool-calling-capability-spike-design.md docs/superpowers/plans/2026-07-08-new-agents-deepseek-tool-calling-capability-spike.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
git commit -m "docs(new-agents): 补齐DeepSeek工具调用能力结论"
git push
```

Expected: branch pushed; `git rev-parse HEAD` equals `git rev-parse @{u}`.
