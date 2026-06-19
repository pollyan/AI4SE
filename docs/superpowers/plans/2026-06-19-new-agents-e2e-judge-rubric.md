# New Agents E2E Judge Rubric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 升级 New Agents E2E LLM judge 的 prompt 和 verdict 解析，使其支持 Lisa/Alex 分角色 rubric 与严格 JSON 结果。

**Architecture:** `llm_judge.py` 保持为 E2E 测试 helper。Prompt 构造负责选择角色维度并序列化 `WorkflowRunResult`；JSON parser 负责机械校验模型返回结构。真实 API 调用仍只在显式环境变量启用时发生。

**Tech Stack:** Python 3.11, pytest, requests, existing New Agents E2E helpers.

---

### Task 1: 严格 verdict parser

**Files:**
- Modify: `tests/e2e/new_agents_browser/llm_judge.py`
- Test: `tests/e2e/new_agents_browser/test_llm_judge.py`

- [x] **Step 1: 写失败测试**

在 `test_llm_judge.py` 中新增合法 verdict、缺字段 verdict 和非法分数 verdict 的解析测试。

- [x] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Expected: FAIL，因为 parser 尚未实现。

- [x] **Step 3: 实现 parser**

新增 `parse_judge_result(content: str) -> JudgeResult`，要求字段齐全、score 在 0-100、dimension_scores 是非空 dict 且每个维度分数在 0-100、issues/evidence/recommendations 都是字符串列表。

- [x] **Step 4: 运行测试确认通过**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Expected: PASS。

### Task 2: 分角色 rubric prompt

**Files:**
- Modify: `tests/e2e/new_agents_browser/llm_judge.py`
- Test: `tests/e2e/new_agents_browser/test_llm_judge.py`

- [x] **Step 1: 写失败测试**

新增 Lisa / Alex prompt 测试，分别断言测试专家维度和业务分析师维度存在，且通用交互体验、可视化维度和严格 JSON 字段存在。

- [x] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Expected: FAIL，因为 prompt 仍是泛化标准。

- [x] **Step 3: 实现 rubric 选择**

在 `build_judge_prompt(...)` 中根据 workflow 名称选择 Lisa / Alex rubric，未知 workflow 使用通用专业产物 rubric；始终追加交互体验和可视化 rubric。

- [x] **Step 4: 运行聚焦和 E2E 验证**

Run:
`python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Run:
`NEW_AGENTS_E2E_LLM_JUDGE=0 python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py -q`

Expected: prompt/parser tests pass；确定性 E2E pass/skip 不依赖模型。

### Task 3: 更新 todo 和格式检查

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: 记录 P0 #1 rubric 进展**

记录严格 verdict 和分角色 rubric 已完成，注明验证命令。

- [x] **Step 2: 运行 diff 检查**

Run: `git diff --check -- tests/e2e/new_agents_browser docs/todos/new-agents-evolution.md docs/superpowers/specs/2026-06-19-new-agents-e2e-judge-rubric-design.md docs/superpowers/plans/2026-06-19-new-agents-e2e-judge-rubric.md`

Expected: no output, exit 0。
