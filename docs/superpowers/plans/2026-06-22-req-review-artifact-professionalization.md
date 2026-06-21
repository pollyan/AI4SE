# REQ_REVIEW 产出物专业化实施计划

## 目标

完成 `REQ_REVIEW` workflow 下 `REVIEW`、`REPORT` 两个 stage artifact 的专业化升级，并同步 backend artifact contract、contract sync tests、runtime/frontend fixture 和本轮记录文档。

## 文件范围

- `tools/new-agents/frontend/src/core/prompts/req_review/review.ts`
- `tools/new-agents/frontend/src/core/prompts/req_review/report.ts`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/tests/test_agent_contracts.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- 可能受 contract fixture 影响的 backend runtime/endpoint tests
- 本轮 spec/plan

## TDD 步骤

### 1. Contract RED

更新 `test_agent_contracts.py`：

- 断言 `REQ_REVIEW/REVIEW` required headings 包含评审范围、需求质量总览、需求质量结构图、修订建议、阶段门禁，以及问题表头 `评审维度`、`阻断性`、`状态`。
- 断言 `REQ_REVIEW/REVIEW` required Mermaid 包含 `flowchart`。
- 断言 `REQ_REVIEW/REPORT` required headings 包含优先级看板、问题关闭清单、复审条件、签署确认、变更记录，以及表头 `关闭状态`、`复审条件`、`签署状态`。

预期：先失败，因为 contract 仍是旧章节。

### 2. 实现 Contract

更新 `agent_contracts.py`：

- 扩展 `REQ_REVIEW/REVIEW` required headings。
- 为 `REQ_REVIEW/REVIEW` 增加 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 的 `flowchart`。
- 扩展 `REQ_REVIEW/REPORT` required headings。
- 保持 `score-matrix` 和 `priority-board` 结构化 visual 合同。

### 3. 实现 Prompt / Template

更新 `review.ts`：

- 增加评审信息、范围与不评审范围、需求质量总览、Mermaid flowchart、按维度问题清单、修订建议和阶段门禁。
- 问题表新增 `评审维度`、`阻断性`、`状态`。

更新 `report.ts`：

- 把报告升级为可签署评审报告。
- 增加优先级看板章节、问题关闭清单、复审条件、签署确认和变更记录。
- `priority-board` rows 保留 type/columns/rows 结构。

### 4. 更新 Fixture

- 更新 `frontend/src/core/__tests__/llm.test.ts` 中 `REQ_REVIEW/REVIEW` 的 typed artifact fixture，使其满足新 contract。
- 如 backend runtime/endpoint 中有 `REQ_REVIEW` 合法样例，也同步更新。

### 5. 验证

最小验证命令：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py
```

前端聚焦验证：

```bash
cd tools/new-agents/frontend && ./node_modules/.bin/tsc --noEmit --allowImportingTsExtensions --moduleResolution Bundler --module ESNext --target ES2022 --jsx react-jsx --resolveJsonModule --esModuleInterop --strict src/core/workflows.ts
```

辅助验证：

```bash
git diff --check
```

## 风险与取舍

- 后端 contract 只能校验标题、字段和 visual 存在，不能完全判断问题证据是否专业；语义质量应在后续 LLM judge/evidence 加强。
- 本轮不新增 UI 控件，Mermaid 和 `ai4se-visual` 继续走现有渲染。
- 当前工作区有无关 zip 改动，提交时不得 stage。

## 每轮提交规则

完成验证后形成聚焦 commit，并在远端权限可用时 push 到 Git。只提交本轮 `REQ_REVIEW` 相关文件和本轮文档。

## 本轮完成记录

- 完成 workflow：`REQ_REVIEW`
- 覆盖 stage：`REVIEW`、`REPORT`
- 已修改：两个 `req_review` prompt/template、backend artifact contract、structured visual schema prompt、backend contract tests、frontend typed runtime fixture、本轮 spec/plan
- 验证通过：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py`
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts`
  - `cd tools/new-agents/frontend && ./node_modules/.bin/tsc --noEmit --allowImportingTsExtensions --moduleResolution Bundler --module ESNext --target ES2022 --jsx react-jsx --resolveJsonModule --esModuleInterop --strict src/core/workflows.ts`
  - `git diff --check`
- 未运行 / 未作为本轮通过门禁：
  - `cd tools/new-agents/frontend && npm run lint` 已知会失败于既有非本轮问题：`src/core/__tests__/artifactMerge.test.ts` 的 `"context"` 类型不属于 `"removed" | "unchanged" | "added"`；额外聚焦 tsc 包含 `llm.test.ts` 时也会暴露既有 `type-fest`、store、workspaceState 严格类型问题。
- 残余风险：
  - 后端 contract 可约束关键标题、字段和 visual 存在，但不能判断问题证据是否足够专业；后续仍需要 LLM judge / E2E evidence 补充语义质量评审。
  - 本轮未开发新的需求质量看板 UI，`score-matrix` 和 `priority-board` 继续复用通用结构化表格渲染。
- 下一轮推荐：`VALUE_DISCOVERY`，用于提升产品经理视角，并增强 Alex 到 Lisa 的 handoff 质量。
- 当前全量进度：已完成 2/5 workflow。
