# Alex PRD Review Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前主线落地 Alex `PRD_REVIEW` 在线 workflow，让用户能通过共享 Agent Runtime 生成 PRD 质量评审与补全建议 artifact。

**Current Baseline:** 本计划在隔离 worktree `codex/alex-prd-review-goal-mainline` 执行，并已 rebase 到当前 `master`，包含 2026-06-24 目标模式 playbook 对 Superpowers 头脑风暴的最新要求。主工作区存在既有未提交改动，本轮不触碰。

**Architecture:** 所有差异通过 `workflow_manifest.json`、前端 prompt/template、backend workflow contract、`artifact_data` schema 和 deterministic renderer 表达。继续复用 `/api/agent/runs/stream`、typed SSE、run/artifact persistence、共享 store 和共享 UI，不新增 Alex 专属运行链路。

**Tech Stack:** Python 3.11, Flask/PydanticAI runtime, Pydantic artifact data schemas, React 19, TypeScript 5.x, Vitest, pytest.

---

## 文件结构

- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Create: `tools/new-agents/frontend/src/core/prompts/prd_review/*.ts`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_registry.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

## Task 1: RED - 前端和后端同步测试先描述 PRD Review

- [x] **Step 1: 添加前端 workflow RED 测试**

在 `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts` 添加 `WORKFLOWS.PRD_REVIEW`、`prd-review` slug、四个 stage、Alex online listing 的断言。

- [x] **Step 2: 添加后端 contract sync RED 测试**

在 `tools/new-agents/backend/tests/test_workflow_contract_sync.py` 添加 `test_prd_review_manifest_and_backend_contract_are_synchronized`，要求 manifest 与 `WORKFLOW_STAGES` 同步包含四个 PRD Review stage。

- [x] **Step 3: 运行 RED 验证**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_prd_review_manifest_and_backend_contract_are_synchronized -q
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts
```

Expected: 两个测试都失败，原因是当前主线没有 `PRD_REVIEW`。

## Task 2: GREEN - 接入 manifest、前端类型和 prompt/template

- [x] **Step 1: 修改 manifest**

在 `tools/new-agents/workflow_manifest.json` 新增 `PRD_REVIEW`，包含 `agentId: alex`、`slug: prd-review`、listing preview、onboarding 和四个 stages：`INVENTORY`、`QUALITY_AUDIT`、`COMPLETION_PLAN`、`REVISION_BLUEPRINT`。

- [x] **Step 2: 修改前端 workflow 类型和 prompt registry**

在 `types.ts` 扩展 `WorkflowType`，在 `workflows.ts` import 并注册四个 `prd_review.*` prompt/template。

- [x] **Step 3: 新增四个 prompt/template 文件**

每个 prompt 文件要求模型输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`，并明确不要输出 Markdown fence。

- [x] **Step 4: 运行前端 GREEN 验证**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: PRD workflow config 和 prompt 构造测试通过。

## Task 3: RED/GREEN - 后端 contract、artifact_data schema 和 renderer

- [x] **Step 1: 添加 renderer/runtime RED 测试**

在 `test_artifact_data_renderers.py` 添加 `VALID_PRD_REVISION_BLUEPRINT_ARTIFACT_DATA` 和 deterministic/contract-valid 测试。在 `test_agent_runtime.py` 添加 parse 测试，要求 `PRD_REVIEW/REVISION_BLUEPRINT` 的 `artifact_data` 被渲染。

- [x] **Step 2: 运行 RED 验证**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_prd_revision_blueprint_artifact_data_is_deterministic_and_contract_valid -q
```

Expected: 失败，原因是 renderer 不支持 `PRD_REVIEW/REVISION_BLUEPRINT`。

- [x] **Step 3: 修改 backend contract**

在 `agent_contracts.py` 新增 `WORKFLOW_STAGES["PRD_REVIEW"]`、每阶段 required headings、required Mermaid / structured visual contract。

- [x] **Step 4: 修改 renderer**

在 `artifact_data_renderers.py` 新增 PRD Review Pydantic models、跨字段校验和渲染函数，覆盖文档信息、质量评分矩阵、缺口清单、补全行动项、修订版 PRD 大纲、Lisa 需求评审输入、阶段门禁。

- [x] **Step 5: 修改 runtime 分发**

在 `agent_runtime.py` 把 `PRD_REVIEW` stages 加入 artifact_data 支持集合，并路由到 renderer。

- [x] **Step 6: 运行后端 GREEN 验证**

Run:

```bash
python3 -m pytest \
  tools/new-agents/backend/tests/test_workflow_contract_sync.py \
  tools/new-agents/backend/tests/test_workflow_contract_registry.py \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/backend/tests/test_artifact_data_renderers.py \
  -q
```

Expected: 相关后端测试通过。

## Task 4: 文档消化与 CI 等价验证

- [x] **Step 1: 更新 todo**

修改 `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 和 `docs/todos/refactor/README.md`，记录 E14 已消化，DeepSeek V4 证据门禁为下一轮优先候选。

- [x] **Step 2: 运行最小验证**

Run:

```bash
python3 -m pytest \
  tools/new-agents/backend/tests/test_workflow_contract_sync.py \
  tools/new-agents/backend/tests/test_agent_contracts.py \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/backend/tests/test_artifact_data_renderers.py \
  tools/new-agents/backend/tests/test_workflow_contract_registry.py \
  -q
python3 -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: 全部退出码为 0。若 frontend worktree 缺 `node_modules`，临时使用主工作区 `node_modules` symlink，验证后删除 symlink 并在收尾记录。

- [x] **Step 3: 提交**

Run:

```bash
git status --short
git add docs/superpowers/specs/2026-06-23-alex-prd-review-goal-mainline-design.md docs/superpowers/plans/2026-06-23-alex-prd-review-goal-mainline.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents
git commit -m "feat(new-agents): 上线 Alex PRD 质量评审 workflow"
```

Expected: 形成聚焦 commit；主工作区未提交改动不受影响。

## Plan Self-Review

- Spec coverage: 覆盖用户入口、四阶段 workflow、artifact contract、shared runtime 约束、失败路径、验证和 todo 更新。
- Placeholder scan: 未发现未决占位或延期补写类占位。
- Type consistency: `PRD_REVIEW`、`prd-review`、`INVENTORY`、`QUALITY_AUDIT`、`COMPLETION_PLAN`、`REVISION_BLUEPRINT` 在 manifest、frontend 和 backend 中保持一致。
- Superpowers brainstorming: spec 已按 playbook 覆盖 Explore Project Context、Visual Companion Decision、Clarifying Questions、Approaches 和 Presented Design。
