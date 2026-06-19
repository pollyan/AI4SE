# New Agents Artifact 模型生成遵守章节锁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让已锁定 artifact 章节在后续模型生成中保持不变。

**Architecture:** 后端 `context_builder` 从 run snapshot 的 `artifactSectionLocks` 生成一个锁定章节上下文块，提示模型不得修改。前端 `chatService` 在应用模型 artifact update 前，用当前 stage 的锁定章节对新 Markdown 做保护合并，避免模型失误覆盖已确认内容。

**Tech Stack:** Flask/Pytest、React/Zustand/Vitest、Markdown 文本 section 解析。

---

### Task 1: 后端 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_context_builder.py`

- [ ] **Step 1: 增加锁定章节上下文测试**

创建 run，调用 `replace_artifact_collaboration_state` 保存 `artifactSectionLocks`，再调用 `build_run_context_prompt`。断言 prompt 包含 `[已锁定产物章节]`、stageId、heading、content 和“不得修改”。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_context_builder.py::test_build_run_context_prompt_includes_locked_artifact_sections
```

Expected: FAIL，prompt 不包含锁定章节。

### Task 2: 前端 RED 测试

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

- [ ] **Step 1: 增加 artifact update 保护锁定章节测试**

设置当前 artifact 包含 `## 已确认范围` 与 `## 可更新建议`，设置 `artifactSectionLocks` 锁定前者。mock stream 返回改写后的 `## 已确认范围` 和新的建议。断言最终 artifact 保留旧锁定章节，采用新建议。

- [ ] **Step 2: 运行测试确认失败**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts
```

Expected: FAIL，当前实现会覆盖锁定章节。

### Task 3: 后端实现

**Files:**
- Modify: `tools/new-agents/backend/context_builder.py`

- [ ] **Step 1: 新增锁定章节 formatter**

新增 `LOCKED_ARTIFACT_SECTIONS_HEADING` 和 `_locked_sections_from_snapshot(snapshot)`。

- [ ] **Step 2: 插入 context block**

在 artifact summaries 之前或之后加入锁定章节 block，确保 max chars 截断机制统一处理。

### Task 4: 前端实现

**Files:**
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`

- [ ] **Step 1: 新增 Markdown section parser**

解析 `#{1,3}` 标题章节，记录 heading、start、end、content。

- [ ] **Step 2: 新增 `preserveLockedSections`**

按当前 stage 的 locks，将新 artifact 中同 heading section 替换为 lock.content；如果新 artifact 缺少锁定章节，则把锁定章节追加到文末。

- [ ] **Step 3: 应用 artifact update 前保护**

在 `decision.artifactUpdate` 分支中对 content 做保护，`latestRunArtifactContent` 也使用保护后的内容。

### Task 5: 验证和记录

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: 运行后端和前端测试**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_context_builder.py
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/chatService.test.ts
```

- [ ] **Step 2: 运行 lint/build/diff**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [ ] **Step 3: 更新 todo**

追加第十七块 CGA，说明章节锁已对模型生成链路生效，剩余重复标题精确锚点和服务端审阅轨迹。
