# New Agents Mermaid Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 New Agents 核心 workflow 增加后端 Mermaid 可视化契约，保证关键阶段稳定包含适合当前任务的图表。

**Architecture:** 新增独立 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 配置和 fenced Mermaid 解析函数，不复用标题 substring 校验；prompt contract 负责把必需图类型告知模型；测试覆盖缺图拒绝和 workflow 覆盖率。

**Tech Stack:** Python pytest, Markdown fenced code parsing, TypeScript Vitest Mermaid syntax tests.

---

### Task 1: 后端契约 RED

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`

- [x] **Step 1: 写失败测试**

新增测试：构造一个 `TEST_DESIGN/STRATEGY` artifact，标题和字段完整但缺少 Mermaid `quadrantChart` / `block-beta`，期望 `validate_agent_turn(...)` 抛出 `ContractValidationError`。

- [x] **Step 2: 覆盖 workflow 可视化契约**

新增测试：断言 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 至少覆盖每个 `WORKFLOW_STAGES` workflow。

- [x] **Step 3: 运行测试确认失败**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'mermaid_contract' -q`

Expected: FAIL，因为当前没有 Mermaid contract。

### Task 2: 实现 Mermaid contract

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`

- [x] **Step 1: 新增 REQUIRED_ARTIFACT_MERMAID_DIAGRAMS**

定义首轮覆盖的 workflow/stage 和图类型。

- [x] **Step 2: 增加 fenced Mermaid 解析和校验**

解析 ` ```mermaid ` / ` ~~~mermaid ` code block，不把 `mermaid-js` 当作 Mermaid。

- [x] **Step 3: 更新 contract prompt**

让 `build_artifact_contract_prompt(...)` 输出当前阶段必需 Mermaid 图类型。

- [x] **Step 4: 更新完整模板测试辅助**

让 `test_validate_agent_turn_accepts_complete_required_artifact_template` 为可视化阶段补最小 Mermaid code block。

### Task 3: 更新记录和验证

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: 记录 P0 #3 首轮完成情况**

记录 Mermaid contract 首轮覆盖和验证命令。

- [x] **Step 2: 运行验证**

Run:
- `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/mermaid.test.ts src/core/__tests__/markdownUtils.test.ts`
- `git diff --check -- tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py docs/todos/new-agents-evolution.md docs/superpowers/specs/2026-06-19-new-agents-mermaid-contract-design.md docs/superpowers/plans/2026-06-19-new-agents-mermaid-contract.md`

Expected: all pass.
