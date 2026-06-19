# TEST_DESIGN CASES Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收紧 `TEST_DESIGN/CASES` 测试用例集 artifact contract，防止标题完整但字段不可执行的用例集通过契约。

**Architecture:** 复用现有 `REQUIRED_ARTIFACT_HEADINGS` 的非标题 substring 校验机制，增加用例表必备字段；同步更新前端 prompt/template；用后端契约测试验证缺字段拒绝。

**Tech Stack:** Python pytest, Pydantic contract validation, TypeScript prompt/template constants.

---

### Task 1: 后端契约 RED

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`

- [x] **Step 1: 写失败测试**

新增测试：构造包含当前 CASES 必备标题但缺少新增用例字段的 artifact，期望 `validate_agent_turn(...)` 抛出 `ContractValidationError`。

- [x] **Step 2: 运行测试确认失败**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'test_design_cases' -q`

Expected: FAIL，因为当前 contract 仍会放过该 artifact。

### Task 2: 收紧 contract 并同步模板

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/frontend/src/core/prompts/test_design/cases.ts`

- [x] **Step 1: 更新 REQUIRED_ARTIFACT_HEADINGS**

为 `("TEST_DESIGN", "CASES")` 添加非标题必备字段：`ID`、`用例标题`、`优先级`、`测试维度`、`关联测试点`、`关联风险`、`前置条件`、`操作步骤`、`测试数据`、`预期结果`。

- [x] **Step 2: 更新 CASES_PROMPT 和 CASES_TEMPLATE**

Prompt 和模板中的用例表字段同步包含新增字段。

- [x] **Step 3: 运行聚焦测试**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_contracts.py -k 'test_design' -q`

Expected: PASS。

### Task 3: 更新记录和验证

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/plans/2026-06-19-new-agents-artifact-audit.md`

- [x] **Step 1: 记录完成情况**

在 todo 和审计文档中记录 `TEST_DESIGN/CASES` 字段收紧已完成。

- [x] **Step 2: 格式检查**

Run: `git diff --check -- tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/frontend/src/core/prompts/test_design/cases.ts docs/todos/new-agents-evolution.md docs/plans/2026-06-19-new-agents-artifact-audit.md docs/superpowers/specs/2026-06-19-test-design-cases-contract-design.md docs/superpowers/plans/2026-06-19-test-design-cases-contract.md`

Expected: no output, exit 0.
