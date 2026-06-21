# New Agents 智能体重构阶段 2 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for independent implementation slices, or `superpowers:executing-plans` for serial implementation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立共享 workflow contract registry，让 workflow/stage、prompt template id、handoff template、artifact headings 和 visual contract 逐步从多事实源收敛到 manifest-derived registry。

**Architecture:** 阶段 2 继续保留 `/api/agent/runs/stream` typed Agent Runtime 主链路，不改变 API/SSE event shape、数据库 schema、snapshot API、test assets API 或前端 store shape。manifest 先承载 metadata，Python/TypeScript 侧继续负责 runtime validation 和渲染实现。

**Tech Stack:** Python 3.11, Flask, Pydantic, pytest, TypeScript 5.x, React 19, Zustand, Vitest.

---

## Current State Gap Analysis

### 事实源快照

已读取：

- `docs/todos/refactor/2026-06-21-new-agents-refactor-scan.md`
- `docs/todos/refactor/2026-06-21-new-agents-refactor-options.md`
- `docs/todos/refactor/2026-06-21-new-agents-refactor-phase1-plan.md`
- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/backend/workflow_manifest.py`
- `tools/new-agents/backend/request_schemas.py`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/frontend/src/core/workflows.ts`
- `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

阶段 1 已完成的基础：

- 每个 manifest stage 必须有前端 prompt/template 映射。
- Handoff 已有 `promptTemplateId`，并由后端 template registry 解析。
- typed SSE 已有共享 fixture。
- workspace state 已抽出低风险 pure helpers。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 共享 workflow contract registry 最小闭环 | `WORKFLOW_STAGES`、manifest stages、promptTemplateId、handoff template metadata 分散 | 后端和前端都能从 registry/adapter 读取低风险 workflow metadata | 只新增 manifest 字段不接入读取方，不能降低多事实源风险 | backend registry tests、request schema tests、frontend config tests |
| Artifact 与 visual contract 注册表闭环 | artifact headings、Mermaid required types、structured visual required types 仍在 Python 常量 | manifest metadata 与 Python validators 保持一致，并逐步由 registry 提供读取入口 | 一次迁移所有 prompt 文本风险过高；只迁 headings 不迁 visual 仍会保留关键漂移 | agent contract tests、workflow contract sync tests、workflow smoke |

### 候选 Gap

| 候选 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 去向 |
| --- | --- | --- | --- | --- | --- | --- |
| 共享 workflow contract registry 最小闭环 | backend registry 和 frontend adapter 都能读取 manifest-derived workflow contract | manifest 已被前后端直接读取 | 缺少 registry 边界，低风险字段仍散在文件中 | 为 artifact/visual contract 迁移提供边界 | 中 | 目标模式第 4 轮 |
| Artifact 与 visual contract 注册表闭环 | artifact headings、visual required types 纳入 manifest metadata 并由后端 registry 校验 | Python constants 已完整表达 contract | metadata 不在 manifest，新增 workflow 仍需同步多个 Python 常量 | 从根上减少 contract 漂移 | 中高 | 目标模式第 5 轮 |
| 大模块边界重组 | routes/persistence/test_assets/store 进一步拆分 | 阶段 1/2 提供契约边界 | 仍需等待 registry 稳定 | 长期维护收益 | 高 | 阶段 3 |

### 排序结论

1. 先做 registry 最小闭环，只迁低风险 metadata：workflow stages、promptTemplateId、handoff promptTemplateId。
2. 再做 artifact/visual contract registry，把 headings、Mermaid required types、structured visual required types 纳入 manifest metadata 或 manifest-derived registry。
3. 不在阶段 2 迁移长 prompt 文本、不拆 `ArtifactPane.tsx`、不重写 persistence 或 routes。

### 切片厚度门禁

- 入口：开发者新增或调整 workflow/stage/contract metadata。
- 动作：registry 读取 manifest，前后端通过 tests 验证派生结果。
- 处理：后端 request schema/contract tests 和前端 workflow config tests 使用 registry/adapter。
- 可见结果：漏配或漂移时测试失败；正常路径行为保持不变。
- 状态承接：阶段 2 完成后可进入模块边界重组。
- 失败反馈：metadata 缺失或非法时测试/validator 显式失败。
- 证据：pytest、Vitest、`git diff --check`。
- 结论：通过，属于可复用工程信任闭环。

## 阶段 2 总体实施顺序

阶段 2 拆成两个目标模式执行轮：

1. 目标模式第 4 轮：共享 workflow contract registry 最小闭环。
2. 目标模式第 5 轮：Artifact 与 visual contract 注册表闭环。

每一轮都必须：

- 保持当前系统功能不被破坏；除明确 bug 修复外，不改变用户可见行为。
- 不改变 `/api/agent/runs/stream`、typed SSE event shape、snapshot API、test assets API、数据库 schema 或 persisted store shape。
- 不把长 prompt 文本迁入 JSON。
- 不新增 agent-specific runtime、transport、store、SSE/API path 或 UI rendering pipeline。
- 完成后形成聚焦 commit。

## 目标模式第 4 轮：共享 workflow contract registry 最小闭环

### 目标

建立 manifest-derived workflow contract registry，先承载低风险字段：

- workflow id / agentId / slug / listing。
- stage id / name / promptTemplateId。
- handoff promptTemplateId。

### 文件范围

- Modify: `tools/new-agents/workflow_manifest.json`
- Create: `tools/new-agents/backend/workflow_contract_registry.py`
- Modify: `tools/new-agents/backend/workflow_manifest.py`
- Modify: `tools/new-agents/backend/request_schemas.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Create or modify: `tools/new-agents/backend/tests/test_workflow_contract_registry.py`
- Create: `tools/new-agents/frontend/src/core/workflowRegistry.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

### TDD 任务

- [ ] **Step 1: 后端 registry RED**

  新增 `test_workflow_contract_registry.py`，断言 registry 能读取每个 workflow/stage 的 `promptTemplateId`，并能导出与 manifest 顺序一致的 `workflowStages`。

  Expected before implementation: fail because registry module does not exist or manifest stages do not have `promptTemplateId`.

- [ ] **Step 2: manifest 增加 stage promptTemplateId**

  在每个 manifest stage 加入 `promptTemplateId`。值应指向现有 TS prompt module key，不迁移 prompt 文本。

- [ ] **Step 3: 后端 registry 最小实现**

  新增 `workflow_contract_registry.py`，从 manifest 构建 registry。`request_schemas.py` 可以继续使用兼容导出的 `WORKFLOW_STAGES`，但来源应可由 registry 证明。

- [ ] **Step 4: 前端 registry adapter RED/GREEN**

  新增 `workflowRegistry.ts`，由 manifest 生成 prompt module key 映射；`workflows.ts` 通过 `promptTemplateId` 查找现有 TS prompt module。前端测试验证每个 stage 都通过 manifest template id 找到 description/template。

- [ ] **Step 5: 运行验证**

  ```bash
  /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_registry.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_request_schemas.py -q
  cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts
  git diff --check
  ```

### 完成标准

- 新增 manifest stage 时，如果没有 `promptTemplateId`，后端 registry 和前端 config tests 会失败。
- `WORKFLOWS` 输出、URL、agent listing、request schema 行为不变。
- 仍不迁移 prompt 文本。

## 目标模式第 5 轮：Artifact 与 visual contract 注册表闭环

### 目标

将 artifact headings、required Mermaid diagram types、required structured visual types 作为 manifest metadata 表达，并由后端 registry 提供读取入口。

### 文件范围

- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/workflow_contract_registry.py`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_registry.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`

### TDD 任务

- [ ] **Step 1: registry contract metadata RED**

  在 registry tests 中断言每个 manifest stage 都有 artifact headings metadata，且 optional visual metadata 与 Python required constants 一致。

- [ ] **Step 2: manifest 增加 artifactContract / visualContract metadata**

  为每个 stage 加入最小 metadata：

  - `artifactContract.requiredHeadings`
  - `visualContract.requiredMermaidDiagrams`
  - `visualContract.requiredStructuredVisuals`

- [ ] **Step 3: 后端 contract 读取入口**

  让 `agent_contracts.py` 的 `WORKFLOW_STAGES`、`REQUIRED_ARTIFACT_HEADINGS`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`、`REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 可由 registry-derived 数据构建，或至少由 tests 证明 manifest metadata 与现有 constants 完全一致后再切换读取源。

- [ ] **Step 4: 运行验证**

  ```bash
  /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_registry.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
  git diff --check
  ```

### 完成标准

- 新增 stage 时，如果没有 artifact headings，测试失败。
- 需要 visual contract 的 stage 若缺少 Mermaid 或 structured visual metadata，测试失败。
- Artifact validation 行为不变。
- 不改变 prompt 文本、runtime API、SSE 或数据库 schema。
