# New Agents Artifact 协作元数据服务端同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Artifact 批注和章节锁随 run snapshot 保存和恢复。

**Architecture:** 后端新增通用 artifact collaboration metadata 持久化模型，按 run/stage 保存 comment 和 section lock 两类记录；snapshot 返回两个数组。前端扩展 snapshot type/parser/store restore，不改变 Agent Runtime、workflow manifest 或 LLM prompt。

**Tech Stack:** Flask、SQLAlchemy、Pytest、React/Zustand、TypeScript、Vitest。

---

### Task 1: 后端 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: `test_run_persistence.py` 增加 snapshot 协作元数据测试**

新增测试调用 `replace_artifact_collaboration_state`，期望 `get_run_snapshot` 返回 `artifactComments` 和 `artifactSectionLocks`。

- [ ] **Step 2: `test_agent_endpoint.py` 增加 API 测试**

新增测试调用 `PUT /api/agent/runs/<run_id>/artifact-collaboration`，期望返回保存后的 comments / locks，并且随后 GET snapshot 可恢复。

- [ ] **Step 3: 运行测试确认失败**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py::test_run_snapshot_returns_artifact_collaboration_state tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_collaboration_endpoint_replaces_state
```

Expected: FAIL，缺少函数或路由。

### Task 2: 前端 RED 测试

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`

- [ ] **Step 1: service 测试期望解析协作元数据**

在 `fetchRunSnapshot` 测试 payload 中加入 `artifactComments` 和 `artifactSectionLocks`，断言 snapshot 返回这些字段。

- [ ] **Step 2: store 测试期望恢复 snapshot 协作元数据**

新增 `restoreRunSnapshot` 测试，给 snapshot 带 CLARIFY 批注和锁，断言 `getArtifactCommentsForStage('CLARIFY')` 与 `getArtifactSectionLocksForStage('CLARIFY')` 可读。

- [ ] **Step 3: 运行测试确认失败**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts
```

Expected: FAIL，缺少字段解析或恢复。

### Task 3: 后端实现

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/routes.py`

- [ ] **Step 1: 新增模型**

新增 `AgentArtifactComment` 和 `AgentArtifactSectionLock`，字段包含 run_id、stage_id、content/excerpt 或 heading/content、created_at。

- [ ] **Step 2: 新增持久化函数**

实现 `replace_artifact_collaboration_state(run_id, patch)`，校验 stage 属于 run workflow，删除该 run 原协作记录后重建。

- [ ] **Step 3: snapshot 返回字段**

`get_run_snapshot` 增加 `artifactComments` 和 `artifactSectionLocks`。

- [ ] **Step 4: 新增路由**

`PUT /agent/runs/<run_id>/artifact-collaboration` 调用持久化函数并返回保存后的状态。

### Task 4: 前端实现

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Modify: `tools/new-agents/frontend/src/store.ts`

- [ ] **Step 1: 扩展 snapshot 类型**

`AgentRunSnapshot` 增加 `artifactComments: ArtifactComment[]` 和 `artifactSectionLocks: ArtifactSectionLock[]`。

- [ ] **Step 2: parser 解析并校验字段**

`parseRunSnapshot` 要求两个数组存在，并使用专用 parser 校验字段。

- [ ] **Step 3: store 恢复 snapshot 协作元数据**

`restoreRunSnapshot` 使用现有 sanitizer 过滤当前 workflow stage 后填充 `artifactComments` / `artifactSectionLocks`。

### Task 5: 验证和记录

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: 运行后端测试**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py::test_run_snapshot_returns_artifact_collaboration_state tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_collaboration_endpoint_replaces_state
```

- [ ] **Step 2: 运行前端测试**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts
```

- [ ] **Step 3: 运行 lint/build/diff**

Run:

```bash
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [ ] **Step 4: 更新 todo**

在 P1.7 追加第十六块 CGA，说明批注/章节锁已随 run snapshot 保存和恢复，剩余批注回复、解决状态、精确锚点仍待后续。
