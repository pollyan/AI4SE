# New Agents E2E Judge Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 New Agents 浏览器 E2E runner 输出完整工作流轨迹，并让可选 LLM judge 能消费这份轨迹。

**Architecture:** 在 `workflow_runner.py` 中新增轻量 dataclass 表达运行结果和事件；`run_complete_workflow(...)` 继续驱动真实页面，但返回结构化 `WorkflowRunResult`。`llm_judge.py` 只负责把 `WorkflowRunResult` 序列化进 judge prompt，真实 API 调用仍由环境变量显式启用。

**Tech Stack:** Python 3.11, pytest, Playwright sync API, existing New Agents E2E fixtures.

---

### Task 1: Judge Prompt 接收结构化轨迹

**Files:**
- Modify: `tests/e2e/new_agents_browser/workflow_runner.py`
- Modify: `tests/e2e/new_agents_browser/llm_judge.py`
- Test: `tests/e2e/new_agents_browser/test_llm_judge.py`

- [x] **Step 1: 写失败测试**

新增 `test_llm_judge.py`，构造 `WorkflowRunResult`，断言 prompt 包含 workflow、conversation、stage transition、stage artifacts 和 final artifact。

- [x] **Step 2: 运行测试确认失败**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Expected: FAIL，因为当前没有 `WorkflowRunResult` 和 prompt builder。

- [x] **Step 3: 新增数据结构和 prompt builder**

在 `workflow_runner.py` 中定义 `ConversationEvent`、`StageTransitionEvent`、`StageArtifactSnapshot`、`WorkflowRunResult`。在 `llm_judge.py` 中新增 `build_judge_prompt(workflow_name, run_result)` 并让 `assert_llm_judges_artifact_quality(...)` 使用它。

- [x] **Step 4: 运行聚焦测试确认通过**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_llm_judge.py -q`

Expected: PASS。

### Task 2: Runner 采集轨迹并保持现有 E2E 行为

**Files:**
- Modify: `tests/e2e/new_agents_browser/workflow_runner.py`
- Modify: `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`
- Modify: `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`
- Test: `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`
- Test: `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`

- [x] **Step 1: 更新 runner 返回值**

让 `run_complete_workflow(...)` 记录初始 prompt、每次用户补充、每次助手可见文本、确认 / 拒绝阶段切换事件和每阶段 artifact 快照，并返回 `WorkflowRunResult`。

- [x] **Step 2: 更新现有测试调用**

Lisa / Alex 测试改为读取 `run_result.final_artifact`。可选 judge 改为传入完整 `run_result`。

- [x] **Step 3: 增加 E2E 轨迹断言**

在 Lisa/Alex 确定性测试中断言 `stage_artifacts` 覆盖全部阶段、`stage_transitions` 非空且包含确认事件、`conversation_events` 包含用户和助手事件。

- [x] **Step 4: 运行聚焦 E2E**

Run: `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py -q`

Expected: deterministic tests pass; optional judge tests skip unless env enabled。

### Task 3: 更新 todo 进展和最终验证

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: 记录 P0 #1 的首个完成切片**

在 P0 #1 下记录 E2E runner 已可收集完整工作流轨迹，注明验证命令。

- [x] **Step 2: 运行格式检查**

Run: `git diff --check -- tests/e2e/new_agents_browser docs/todos/new-agents-evolution.md docs/superpowers/specs/2026-06-19-new-agents-e2e-judge-trace-design.md docs/superpowers/plans/2026-06-19-new-agents-e2e-judge-trace.md`

Expected: no output, exit 0。
