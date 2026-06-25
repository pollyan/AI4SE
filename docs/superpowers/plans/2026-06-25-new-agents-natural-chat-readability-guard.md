# New Agents 左侧自然聊天防模板化回归 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 New Agents 左侧 `chat` 指令明确支持自然短段落和按需列表，同时禁止固定 bullet 数量、固定标签和固定字段模板回归。

**Architecture:** 保持共享 Agent Runtime、typed SSE、ChatPane Markdown 渲染和 artifact contract。只调整 shared prompt/contract 文案与对应测试，不新增 agent/workflow 专属分支。

**Tech Stack:** Python 3.12, pytest, TypeScript 5.x, Vitest.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`

- [x] **Step 1: Add frontend prompt anti-template assertions**

Add assertions proving the prompt includes natural/optional scanability requirements and does not contain fixed bullet or fixed-label hard requirements:

```ts
expect(prompt).toContain('按内容复杂度');
expect(prompt).toContain('简单同步可以使用自然短段落');
expect(prompt).toContain('不要要求每轮固定 bullet 数量');
expect(prompt).toContain('不要要求每条以固定标签开头');
expect(prompt).not.toContain('每次必须输出固定数量 bullet');
expect(prompt).not.toContain('每条必须以固定标签开头');
```

- [x] **Step 2: Add backend prompt anti-template assertions**

In `test_agent_contracts.py`, assert the artifact contract prompt keeps natural chat guidance and the raw structured instruction no longer contains `2 到 4 个短段落或短列表`.

- [x] **Step 3: Run red tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: FAIL because current prompt/structured instruction lacks the new anti-template wording and still contains `2 到 4 个短段落或短列表`.

Result: FAIL as expected. Frontend prompt lacked `按内容复杂度`; backend contract lacked `固定 bullet 数量`; raw structured instruction still contained `2 到 4 个短段落或短列表`.

### Task 2: Prompt and Contract Update

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [x] **Step 1: Update frontend prompt wording**

Change the left chat requirement to say simple updates can be natural short paragraphs, and complex/high-confirmation updates can use short lists, emphasis, or quotes. Add explicit anti-template wording for fixed bullet counts and fixed labels.

- [x] **Step 2: Update backend artifact contract wording**

Keep `chat`/artifact separation and natural consultant-style guidance. Add explicit anti-template wording if missing.

- [x] **Step 3: Update raw structured output instructions**

Replace every `建议保留 2 到 4 个短段落或短列表，让左侧对话有独立阅读价值。` with softer wording:

```text
chat 字段必须像一次自然的工作对话；简单同步可以使用自然短段落，信息较多、存在风险或需要用户确认时再使用短列表、少量重点加粗或引用块帮助扫读。不要每轮套用固定 bullet 数量、固定标签或固定字段模板。
```

### Task 3: Verification

**Files:**
- Existing tests plus updated prompt/contract tests.

- [x] **Step 1: Run frontend prompt tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: PASS.

Result: PASS, 24 tests.

- [x] **Step 2: Run backend contract tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: PASS.

Result: PASS, 87 tests.

- [x] **Step 3: Run ChatPane Markdown readability test**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ChatPane.markdown.test.tsx
```

Expected: PASS.

Result: PASS, 1 test.

- [x] **Step 4: Run lint/compile checks**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
.venv/bin/python -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py
```

Expected: PASS.

Result: PASS.

### Task 4: Todo Record and Commit

**Files:**
- Move/update: `docs/todos/2026-06-25-new-agents-natural-chat-readability.md`
- Create/update: `docs/todos/archive/2026-06-25-new-agents-natural-chat-readability.md`
- Create: this spec and plan.

- [x] **Step 1: Archive completed todo**

Move the todo to archive, mark status `已完成`, and record verification commands.

Result: Archived with status `已完成` and verification notes.

- [x] **Step 2: Run diff and doc checks**

Run targeted diff check for this story's files and the doc placeholder Python check.

Result: PASS.

- [ ] **Step 3: Stage only this story**

Stage prompt/contract/test/spec/plan/archive files only. Do not stage intent-tester generated files or remaining active todo files.

- [ ] **Step 4: Commit**

Run:

```bash
git commit -m "test: 防止左侧聊天模板化回归"
```
