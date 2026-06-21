# New Agents 智能体重构阶段 1 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` when implementing independent tasks from this plan, or `superpowers:executing-plans` for serial implementation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 New Agents 重构阶段 1 的实施拆解，让后续目标模式按可验证的工程信任闭环推进契约护栏、handoff/SSE 协议护栏和 workspace 状态稳定性。

**Architecture:** 阶段 1 不改变 `/api/agent/runs/stream`、typed SSE event shape、snapshot API、test assets API、数据库 schema 或 persisted store shape。所有改动都围绕现有共享 runtime、manifest、后端 validators、前端 adapters 和测试护栏展开，不新增 Lisa/Alex 专属 runtime、store、API path 或 rendering pipeline。

**Tech Stack:** Python 3.11, Flask, Pydantic, pytest, TypeScript 5.x, React 19, Zustand, Vitest.

---

## Current State Gap Analysis

### 事实源快照

已读取：

- `AGENTS.md`
- `docs/index.md`
- `docs/strategy/goal-mode-playbook.md`
- `docs/plans/goal-mode-tech-debt-rules.md`
- `docs/todos/refactor/2026-06-21-new-agents-refactor-scan.md`
- `docs/todos/refactor/2026-06-21-new-agents-refactor-options.md`
- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/backend/workflow_handoffs.py`
- `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- `tools/new-agents/backend/sse_schemas.py`
- `tools/new-agents/backend/tests/test_sse_encoder.py`
- `tools/new-agents/frontend/src/core/workflows.ts`
- `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- `tools/new-agents/frontend/src/core/llm.ts`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- `tools/new-agents/frontend/src/store.ts`
- `tools/new-agents/frontend/src/__tests__/store.test.ts`

按需未展开：

- `ArtifactPane.tsx`、`run_persistence.py`、`test_assets.py` 大模块细节暂不展开；阶段 1 明确不做这些模块的结构性拆分。
- 浏览器 E2E 只作为阶段 1 末尾可选 smoke；本计划不重写 E2E。

工作树隔离：

- 基线文档已在主工作区提交到 `codex/new-agents-refactor-goal`。
- 本计划在隔离 worktree `.worktrees/new-agents-refactor-phase1`、分支 `codex/new-agents-refactor-phase1` 中编写。
- 主工作区存在未纳入本轮的 zip 改动：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`。后续实现不得触碰这两个文件。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| Workflow 契约漂移可检测闭环 | manifest/backend stages/artifact headings/visual contract/prompt template/handoff metadata 多事实源 | 开发者新增或修改 workflow/stage 时，测试能立即发现漏配、错配或漂移 | 只补某一个 sync test 会让其他事实源继续靠人工同步，不能形成可信护栏 | backend contract sync tests、frontend workflow config tests |
| Handoff 与 typed SSE 协议护栏闭环 | handoff prompt 写死 Alex 语义；SSE 前后端双实现缺少共享样本 | 开发者新增 handoff 或调整 SSE event 时，配置和双端 parser/encoder 测试能阻止协议漂移 | handoff 与 SSE 都是跨边界 contract，单独只改实现或只补测试都无法证明不破坏主链路 | handoff tests、SSE encoder/parser tests、runtime targeted tests |
| Workspace 状态恢复与承接稳定闭环 | `store.ts` 过宽，snapshot restore、workflow switching、currentRunId、artifact history 混在 store action 内 | 用户恢复 run、切换 workflow/stage、继续对话时行为保持不变；内部 pure helper 抽取降低后续修改风险 | 只抽一个 helper 是过薄；必须围绕恢复和承接行为锁定测试，证明不破坏当前功能 | store tests、chatService targeted tests |

### 候选 Gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Workflow 契约漂移可检测闭环 | 第一轮 P0、多事实源风险 | 漏配 workflow/stage/prompt/visual/handoff metadata 时测试失败 | 已有 stage/headings/visual prompt 部分测试 | prompt map 和 handoff metadata 仍可能形成手写同步清单 | 为阶段 2 registry 提供安全网 | 中；主要是测试和小配置 | 高 | 目标模式第 1 轮 |
| Handoff 与 typed SSE 协议护栏闭环 | 第一轮 P1、handoff/SSE 风险 | handoff prompt 来源配置化；SSE 双端共享样本 | handoff 可运行；SSE 双端分别校验 | handoff 文案写死 Alex；SSE 无共享 fixture | 防止新增 workflow 时产生专用分支或协议漂移 | 中；跨 Python/TS 测试 | 高 | 目标模式第 2 轮 |
| Workspace 状态恢复与承接稳定闭环 | 第一轮 P0、`store.ts` 过宽 | 抽取低风险 pure helper，同时锁定恢复/承接行为 | store 行为已有大量测试 | 关键恢复逻辑仍在大 action 中，不利于后续 registry 接入 | 降低后续状态层改动风险 | 中；容易误改 persisted shape | 高 | 目标模式第 3 轮 |
| 共享 workflow contract registry 最小闭环 | 第二轮方案 B | manifest-derived registry 开始承载低风险字段 | manifest 已被前后端读取 | 还未建立统一 registry 边界 | 从根上减少多事实源 | 中高 | 高 | 阶段 2，目标模式第 4 轮 |
| 大模块边界重组 | 第二轮方案 C | routes/persistence/test_assets/ArtifactPane 分批拆分 | 大模块功能已可用 | 文件过大、职责混合 | 长期维护收益 | 高 | 中高 | 阶段 3，目标模式第 6 轮以后 |

### 排序结论

1. 先执行 Workflow 契约漂移可检测闭环，因为它是后续 handoff/SSE、store helper 和 registry 迁移的共同安全网。
2. 再执行 Handoff 与 typed SSE 协议护栏闭环，因为它触及跨 workflow 和跨前后端协议边界，但仍不需要改变主链路。
3. 再执行 Workspace 状态恢复与承接稳定闭环，因为它减少后续 frontend registry adapter 接入风险，但应在契约测试更强后进行。
4. 阶段 2 registry 和阶段 3 大模块拆分暂不进入阶段 1，实现时必须另做 CGA。

### 切片准入判断

- 用户功能包边界：本轮文档计划本身是工程信任闭环，为后续目标模式提供可执行路线，不直接改用户可见功能。
- 用户可感知动作链：后续开发者按计划新增或调整 workflow/agent 时，系统能通过测试阻止协议漂移和功能破坏。
- 完整功能检查：阶段 1 的三个目标模式轮次分别有入口、处理、结果、状态承接、失败反馈和证据。
- 相邻缺口合并：contract sync、handoff metadata、SSE fixture 和 store restore helper 均纳入阶段 1，但按自然风险边界拆成 3 个目标模式轮次，避免一次大改。
- Superpowers 成本合理性：本轮只写计划，成本合理；后续每个目标模式轮次都有独立验收闭环。
- 过薄风险检查：不把单个 test、helper 或字段作为 milestone，而是聚合为三个工程信任闭环。
- 能力增量句：完成阶段 1 后，调用方现在可以在不破坏当前 New Agents 主链路的前提下，获得 workflow contract、handoff/SSE 协议和 workspace 状态承接的可验证安全网。

### 切片厚度门禁

- 入口：开发者修改 `workflow_manifest.json`、prompt/template、handoff、SSE event 或 store 恢复逻辑。
- 动作：运行目标模式计划中列出的 targeted tests。
- 处理：测试校验 manifest/backend/frontend/协议/state 是否一致。
- 可见结果：测试通过或以明确断言指出漏配、错配、协议漂移或状态破坏。
- 状态承接：通过文档计划、测试文件和后续 commits 记录执行证据。
- 失败反馈：测试失败必须指向具体 workflow/stage/handoff/event/state 行为，不使用 silent fallback。
- 证据：pytest、Vitest、`git diff --check`，必要时 E2E smoke。
- 结论：作为工程信任闭环例外通过。

## 阶段 1 总体实施顺序

阶段 1 拆成三个目标模式执行轮：

1. 目标模式第 1 轮：Workflow 契约漂移可检测闭环。
2. 目标模式第 2 轮：Handoff 与 typed SSE 协议护栏闭环。
3. 目标模式第 3 轮：Workspace 状态恢复与承接稳定闭环。

每一轮都必须：

- 先做该轮 CGA，不直接照搬本计划。
- 先写或强化失败测试，再实现最小改动，再清理。
- 保持当前系统功能不被破坏；除明确 bug 修复外，不改变用户可见行为。
- 不改变 `/api/agent/runs/stream`、typed SSE event shape、snapshot API、test assets API、数据库 schema 或 persisted store shape。
- 不新增 agent-specific runtime、transport、store、SSE/API path 或 UI rendering pipeline。
- 完成后形成聚焦 commit，再进入下一轮。

## 目标模式第 1 轮：Workflow 契约漂移可检测闭环

### 目标

当新增或修改 workflow/stage 时，测试能发现以下漏配：

- manifest stage 与后端 stage contract 不一致。
- manifest stage 缺少 artifact heading contract。
- manifest stage 缺少 prompt/template 映射。
- required Mermaid / structured visual contract 缺少 prompt 示例。
- handoff 缺少后续 template metadata 的准备字段或引用非法。

### 文件范围

- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Do not modify: runtime API routes, `ArtifactPane.tsx`, `run_persistence.py`, `test_assets.py`

### TDD 任务

- [ ] **Step 1: 为 prompt/template 映射完整性写失败测试**

  在 `tools/new-agents/backend/tests/test_workflow_contract_sync.py` 中新增或改造测试，要求每个 manifest stage 都能映射到 prompt/template 文件或 template id。当前可接受的第一步是把现有 prompt file map 提炼成被所有相关测试复用的 helper，避免 structured visual 和 Mermaid 测试各维护一份清单。

  Run:

  ```bash
  .venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
  ```

  Expected before implementation: fail with a clear missing mapping or helper assertion if a stage is not represented.

- [ ] **Step 2: 最小实现 prompt/template 映射护栏**

  调整 `test_workflow_contract_sync.py` 的 helper，使每个 `workflow_manifest.json` stage 都必须在 prompt/template 映射中出现。保持 prompt 文本仍在 TypeScript modules 中，不迁移到 JSON。

- [ ] **Step 3: 为前端 workflow 派生关系补充测试**

  在 `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts` 中补充测试：每个 `WORKFLOWS[workflow].stages` 都有非空 `description`、非空 `template`，并且 slug/agent listing 仍从 manifest 派生。

  Run:

  ```bash
  cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts
  ```

  Expected before implementation: if current code already satisfies this, keep it as a regression lock; if it fails, fix the mapping instead of weakening assertions.

- [ ] **Step 4: 运行第 1 轮验证**

  Run:

  ```bash
  .venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
  cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts
  git diff --check
  ```

  Expected: all pass, no whitespace errors.

### 完成标准

- 修改任意 manifest stage 后，如果缺少 prompt/template、artifact headings、visual contract 或 handoff 引用，测试能失败。
- 不改变 runtime 行为。
- 不新增 production fallback 或 mock。

## 目标模式第 2 轮：Handoff 与 typed SSE 协议护栏闭环

### 目标

Handoff prompt 不再写死 Alex 语义；typed SSE 前后端双实现有共享样本或等价 fixture 护栏。

### 文件范围

- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/workflow_handoffs.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify or create: `tools/new-agents/contract-fixtures/agent-runtime-events.json`
- Modify: `tools/new-agents/backend/tests/test_sse_encoder.py`
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- Do not modify: SSE event names or payload shape.

### TDD 任务

- [ ] **Step 1: 为 handoff template metadata 写失败测试**

  在 `test_workflow_contract_sync.py` 中断言每个 manifest handoff 都有 `promptTemplateId`，且该 id 能被后端 template registry 识别。

  Expected before implementation: fail because current manifest handoffs do not have template ids.

- [ ] **Step 2: 为 handoff prompt 行为写失败测试**

  在 `test_workflow_handoffs.py` 中断言 prompt 文案来自 template id，并仍包含 source workflow/stage、target workflow/stage 和源 artifact 内容。测试不应要求固定写死 “Alex”。

  Expected before implementation: fail because current `_build_handoff_prompt` hardcodes “Alex 产出的需求蓝图”.

- [ ] **Step 3: 实现 handoff template resolution**

  在 `workflow_handoffs.py` 中加入最小 template registry，例如 `HANDOFF_PROMPT_TEMPLATES`，由 manifest `promptTemplateId` 选择模板。模板仍生成当前语义，不改变目标 run 创建行为。

- [ ] **Step 4: 增加 typed SSE fixture**

  新增共享 fixture，至少覆盖：

  - `run_started`
  - `agent_delta`
  - `agent_turn`
  - `error`

  后端 `test_sse_encoder.py` 读取 fixture 并验证 Pydantic schema/encoder 输出。前端 `llm.test.ts` 读取同一 fixture 或等价 JSON 样本并验证 parser 行为。

- [ ] **Step 5: 运行第 2 轮验证**

  Run:

  ```bash
  .venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_sse_encoder.py -q
  cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts
  git diff --check
  ```

  Expected: all pass.

### 完成标准

- 新增 handoff 时，没有 template id 或 template id 无效会失败。
- 现有 Alex -> Lisa handoff 行为保持兼容。
- SSE fixture 不改变 production event shape，只增强测试护栏。

## 目标模式第 3 轮：Workspace 状态恢复与承接稳定闭环

### 目标

在不改变 `useStore` 外部 API、persisted state shape 和用户行为的前提下，抽取低风险 pure helpers，为后续 frontend registry adapter 接入降低风险。

### 文件范围

- Modify: `tools/new-agents/frontend/src/store.ts`
- Create or modify: `tools/new-agents/frontend/src/core/workspaceState.ts`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
- Modify or create: `tools/new-agents/frontend/src/core/__tests__/workspaceState.test.ts`
- Optional modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
- Do not modify: persisted store key, `OLD_KEY`, runtime API, UI components.

### TDD 任务

- [ ] **Step 1: 锁定 snapshot restore 行为**

  在 `store.test.ts` 中补齐或确认以下行为测试：

  - unknown workflow snapshot is ignored or explicitly rejected without corrupting current state.
  - agentId mismatch snapshot is ignored.
  - current stage artifact is restored from snapshot artifacts.
  - missing current stage artifact falls back to initial artifact for that stage.
  - `currentRunId` is restored from `snapshot.run.id`.

- [ ] **Step 2: 锁定 persisted workspace sanitize 行为**

  在 `workspaceState.test.ts` 或 `store.test.ts` 中覆盖：

  - invalid persisted workflow falls back to default workflow.
  - invalid stageIndex falls back to 0.
  - stageArtifacts outside active workflow are dropped.
  - currentRunId is trimmed or set to null.
  - old `lisa-storage` migration behavior remains unchanged if touched.

- [ ] **Step 3: 抽取 pure helpers**

  从 `store.ts` 抽取以下候选 helper 到 `core/workspaceState.ts`：

  - persisted workspace sanitization helpers.
  - snapshot restore normalization helper.
  - workflow stage id validation helper.

  `useStore` actions 继续调用这些 helper，不改变 action 名称、参数和返回行为。

- [ ] **Step 4: 运行第 3 轮验证**

  Run:

  ```bash
  cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/core/__tests__/workspaceState.test.ts src/services/__tests__/chatService.test.ts
  git diff --check
  ```

  Expected: all pass.

### 完成标准

- `useStore` public actions 不变。
- persisted state shape 不变。
- run snapshot restore、workflow switching、artifact history、currentRunId 行为不变。
- helper 抽取没有引入兼容 shim、silent fallback 或 `as any`。

## 阶段 1 末尾验证

三个目标模式轮次全部完成后，运行阶段 1 聚合验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_sse_encoder.py tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_agent_contracts.py -q
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/__tests__/llm.test.ts src/__tests__/store.test.ts src/services/__tests__/chatService.test.ts
git diff --check
```

如任一轮触及 prompt/artifact quality 或主流程行为，再补充：

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py
```

## 后续阶段入口

阶段 1 完成后，下一轮目标模式应重新做 CGA，再进入：

- 目标模式第 4 轮：共享 workflow contract registry 最小闭环。
- 目标模式第 5 轮：Artifact 与 visual contract 注册表闭环。
- 目标模式第 6 轮：大模块边界重组第一批。

不得在阶段 1 未完成前提前拆 `ArtifactPane.tsx` 主渲染结构、重写 `run_persistence.py`、泛化 Lisa test assets 或引入 schema 生成硬依赖。
