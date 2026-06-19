# New Agents Artifact 批注回复与解决状态 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 artifact 批注支持回复、已解决/重新打开状态，并随 run snapshot 保存恢复。

**Architecture:** 扩展现有 artifact collaboration state，不新增独立运行时。后端在 `AgentArtifactComment` 中保存 `status`、`resolved_at_ms`、`replies_json`；前端扩展 `ArtifactComment` 类型、store action 和 ArtifactPane 批注面板。同步仍复用 `PUT /artifact-collaboration`。

**Tech Stack:** Flask/SQLAlchemy/Pytest、React/Zustand/Vitest。

---

### Task 1: 后端 RED 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: 扩展 persistence 测试**

在 `test_run_snapshot_returns_artifact_collaboration_state` 中加入 comment `status: "resolved"`、`resolvedAt`、`replies`，断言 saved 和 snapshot 都保留。

- [ ] **Step 2: 扩展 endpoint 测试**

在 artifact collaboration endpoint payload 中加入 comment status/replies，断言 response 和 snapshot 保留。

- [ ] **Step 3: 运行测试确认失败**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py::test_run_snapshot_returns_artifact_collaboration_state tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_artifact_collaboration_endpoint_replaces_state
```

Expected: FAIL，当前后端没有返回 status/replies。

### Task 2: 前端 RED 测试

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: service 测试解析 status/replies**

在 snapshot 和 collaboration response 测试中加入 comment status/replies。

- [ ] **Step 2: store 测试新增回复和解决状态 action**

新增测试调用 `addArtifactCommentReply`、`setArtifactCommentStatus`。

- [ ] **Step 3: ArtifactPane 测试回复和解决/重开交互**

新增测试：有 currentRunId 时，回复批注后 UI 显示回复并调用 `updateRunArtifactCollaboration`；点击解决后状态显示已解决，再点击重新打开。

- [ ] **Step 4: 运行测试确认失败**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx
```

Expected: FAIL，缺少类型/action/UI。

### Task 3: 后端实现

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/run_persistence.py`

- [ ] **Step 1: 模型扩展**

`AgentArtifactComment` 增加 `status`、`resolved_at_ms`、`replies_json`。

- [ ] **Step 2: parser/serializer 扩展**

`replace_artifact_collaboration_state` 读取可选 status/replies，默认 status 为 `open`、replies 为 `[]`。

### Task 4: 前端实现

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/store.ts`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: 扩展类型和 parser**

新增 `ArtifactCommentStatus`、`ArtifactCommentReply`，让 comment 包含 status/replies/resolvedAt。

- [ ] **Step 2: store action**

新增 `addArtifactCommentReply(commentId, content)` 和 `setArtifactCommentStatus(commentId, status)`。

- [ ] **Step 3: ArtifactPane UI**

显示状态、回复列表、回复输入、解决/重新打开按钮，并在操作后调用现有协作同步。

### Task 5: 验证和记录

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: 运行验证**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [ ] **Step 2: 更新 todo**

追加第十八块 CGA，说明批注回复与解决状态完成，剩余正文选区精确锚点、服务端审阅轨迹等。
