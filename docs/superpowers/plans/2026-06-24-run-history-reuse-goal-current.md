# Run History Reuse Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 New Agents 历史会话从恢复列表升级为可筛选、可预览、可继续、可复制的新 run 复用中心。

**Current Baseline:** 本计划在隔离 worktree `.worktrees/run-history-reuse-goal-current` 执行，分支为 `codex/run-history-reuse-goal-current`，基线为 `e35c9643 docs(goal): 明确 Superpowers 头脑风暴细化规则`。主工作区存在既有未提交改动，本轮不触碰。

**Architecture:** 复用现有 run persistence、snapshot restore、Header modal、`runSnapshotService` 和 workspace state。后端只扩展 run list/clone API；前端只扩展共享 Header 历史中心，不新增 Agent Runtime、SSE、workflow manifest、artifact renderer 或 agent 专属 store。

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, pytest, React, TypeScript, Vitest.

---

## 文件结构

- Create: `docs/superpowers/specs/2026-06-24-run-history-reuse-goal-current-design.md`
- Create: `docs/superpowers/plans/2026-06-24-run-history-reuse-goal-current.md`
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

## Task 1: RED - 证明当前主线缺少复用中心

- [ ] **Step 1: 写后端 RED 检查**

运行：

```bash
node -e "const fs=require('fs'); const routes=fs.readFileSync('tools/new-agents/backend/routes.py','utf8'); if (!routes.includes('/agent/runs/<run_id>/clone')) throw new Error('clone route missing')"
```

Expected: FAIL with `clone route missing`。

- [ ] **Step 2: 写前端 RED 检查**

运行：

```bash
node -e "const fs=require('fs'); const service=fs.readFileSync('tools/new-agents/frontend/src/services/runSnapshotService.ts','utf8'); if (!service.includes('cloneRun')) throw new Error('cloneRun service missing')"
```

Expected: FAIL with `cloneRun service missing`。

## Task 2: GREEN - 移植并对齐后端 run persistence/API

- [ ] **Step 1: 移植后端测试**

从既有 E06 工程输入移植并保留以下行为测试：

- `test_run_persistence.py` 覆盖 `clone_agent_run()` 复制 messages/current artifacts/context summaries、不修改源 run。
- `test_run_persistence.py` 覆盖 `reuseStatus=ready|needs_artifact|failed` 过滤。
- `test_agent_endpoint.py` 覆盖 `POST /api/agent/runs/<run_id>/clone` 和非法 `reuseStatus` 400。

- [ ] **Step 2: 移植后端实现**

在 `run_persistence.py` 实现：

- `RUN_REUSE_STATUSES`
- `_run_reuse_status(...)`
- run list 的 `reuse_status` 过滤和返回字段 `reuseStatus`
- `clone_agent_run(source_run_id)`

在 `routes.py` 实现：

- `GET /api/agent/runs` 读取 `reuseStatus` 参数。
- `POST /api/agent/runs/<run_id>/clone` 返回新 run snapshot。

- [ ] **Step 3: 跑后端 GREEN**

运行：

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
```

Expected: PASS。

## Task 3: GREEN - 移植并对齐前端 service/Header

- [ ] **Step 1: 移植前端 service 测试和类型**

更新：

- `AgentRunListItem.reuseStatus`
- `RunReuseStatus`
- `fetchRunList(..., reuseStatus)`
- `cloneRun(runId)`

测试必须覆盖严格解析、非法 `reuseStatus` fixture、query 参数和 clone API。

- [ ] **Step 2: 移植 Header 复用中心交互**

Header 历史弹窗必须支持：

- 全部 / 当前 workflow / 复用状态筛选。
- run card 展示 reuse status、最后消息、artifact 摘要。
- 选中 run 后读取 snapshot 并预览 artifact。
- “继续此 run”恢复源 snapshot 并导航。
- “复制为新 run”调用 clone API、恢复新 snapshot 并导航。
- 列表、预览、复制失败分别展示错误。

- [ ] **Step 3: 跑前端 GREEN**

如 worktree 缺 `node_modules`，临时 symlink 主仓库已有依赖，验证后删除：

```bash
ln -s /Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules tools/new-agents/frontend/node_modules
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx
cd ../.. && rm -f frontend/node_modules
```

Expected: PASS。

## Task 4: 文档、验证和提交

- [ ] **Step 1: 更新 todo 文档**

更新：

- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`：将 E06 标记为已消化，说明 run history reuse center 覆盖筛选、预览、继续、复制。
- `docs/todos/refactor/README.md`：修正当前入口状态，记录 E06 已消化，保留 E03/E05/E08/E09 等后续候选。

- [ ] **Step 2: 最终验证**

运行：

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/run_persistence.py tools/new-agents/backend/routes.py
ln -s /Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules tools/new-agents/frontend/node_modules
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx
npm run lint
cd ../../..
rm -f tools/new-agents/frontend/node_modules
git diff --check e35c9643..HEAD
```

Expected: 全部退出码为 0。

- [ ] **Step 3: 提交**

运行：

```bash
git status --short
git add docs/superpowers/specs/2026-06-24-run-history-reuse-goal-current-design.md \
  docs/superpowers/plans/2026-06-24-run-history-reuse-goal-current.md \
  docs/todos/refactor/README.md \
  docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md \
  tools/new-agents/backend/run_persistence.py \
  tools/new-agents/backend/routes.py \
  tools/new-agents/backend/tests/test_run_persistence.py \
  tools/new-agents/backend/tests/test_agent_endpoint.py \
  tools/new-agents/frontend/src/core/types.ts \
  tools/new-agents/frontend/src/services/runSnapshotService.ts \
  tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts \
  tools/new-agents/frontend/src/components/Header.tsx \
  tools/new-agents/frontend/src/components/__tests__/Header.test.tsx
git commit -m "feat(new-agents): 增强历史会话复用中心"
```

Expected: 形成隔离分支聚焦提交。

## Plan Self-Review

- Spec coverage: 覆盖筛选、预览、继续、复制、失败反馈、状态承接和测试证据。
- Placeholder scan: 无 TBD/TODO/未裁决占位。
- Type consistency: `reuseStatus`、`RunReuseStatus`、`cloneRun`、`clone_agent_run` 在计划内命名一致。
- Scope check: 不包含 E08/E09/E05，不新增 runtime/store/API 分支。
