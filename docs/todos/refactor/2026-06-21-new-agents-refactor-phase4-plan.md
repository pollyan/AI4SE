# New Agents 智能体重构阶段 4 计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for serial implementation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在阶段 3 route 分组完成后，继续拆分 `test_assets.py` 的纯解析边界，降低 Lisa test assets 大模块复杂度，同时保持所有 API、数据库 schema 和用户可见行为不变。

**Architecture:** 本阶段不泛化 Lisa test assets 为通用资产框架，也不新增 workflow-specific runtime/API/store/UI。只把 Markdown 解析、coverage summary、risk matrix、intent-tester draft 生成这些无 Flask/DB 依赖的逻辑移入独立模块，再由现有 `test_assets.py` 调用。

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, pytest.

---

## 当前轮次状态

- 推荐路线总轮数：`6 个目标模式执行轮 + 后续可选模块边界轮`
- 已完成：目标模式第 1-6 轮
- 当前计划对应：目标模式第 7 轮
- 当前状态：待执行

## 每轮完成后的 Summary 模板

每完成一轮，必须向用户报告：

- 总体轮次：例如 `第 7 轮 / 原 6 轮已完成 + 后续模块边界轮`
- 本轮目标
- 本轮改动
- 验证命令和结果
- Commit
- 下轮建议
- 风险或阻塞

## Current State Gap Analysis

### 事实源快照

已读取：

- `docs/todos/refactor/2026-06-21-new-agents-refactor-options.md`
- `docs/todos/refactor/2026-06-21-new-agents-refactor-phase3-plan.md`
- `tools/new-agents/backend/test_assets.py`
- `tools/new-agents/backend/tests/test_test_assets.py`
- `tools/new-agents/backend/routes_test_assets.py`

### 当前事实

- `test_assets.py` 约 1200 行，同时包含：
  - public service functions：export/materialize/update/record/delete。
  - DB serialization 和 persistence helpers。
  - risk lifecycle update helpers。
  - Markdown table parsing、test case/coverage mapping、coverage summary、asset issues、risk matrix、intent-tester draft 生成。
- 解析和派生逻辑目前没有独立模块边界，但它们基本不依赖 Flask、SQLAlchemy 或 DB session。
- `test_test_assets.py` 已覆盖完整导出、物化、编辑、risk、intent-tester mapping 行为，可以作为 behavior lock。
- 不应把 Lisa test assets 过早抽象为通用 framework；本轮只拆“纯解析模块”，不改变产品语义。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| Lisa test assets 解析边界闭环 | `test_assets.py` 中纯解析和 DB/service 逻辑混合 | 解析逻辑可单独测试，public service 输出保持不变 | 只移动一个 helper 没有结构收益；一次拆 persistence/risk/intent-tester 全部边界风险过高 | parser tests、test_assets behavior tests、route tests |

### 排序结论

1. 先拆纯解析边界，因为它不触碰 DB schema、route、API 和 runtime。
2. 暂不拆 `run_persistence.py`，其持久化查询和 snapshot 行为回归面更大。
3. 暂不拆 `ArtifactPane.tsx`，UI DOM 和交互回归面更大，应单独作为可选后续轮。

## 目标模式第 7 轮：Lisa test assets 解析边界闭环

### 目标

新增 `tools/new-agents/backend/test_asset_parsing.py`，承接以下纯逻辑：

- Markdown table parsing。
- test case row mapping。
- coverage row mapping。
- coverage summary。
- asset issue detection。
- risk matrix derivation。
- intent-tester draft generation。

`test_assets.py` 继续保留 public service API、DB 查询/写入、serialization、risk lifecycle 和 intent-tester mapping persistence。外部调用仍使用原函数：

- `export_lisa_test_assets`
- `materialize_lisa_test_assets`
- `get_lisa_test_asset_collection`
- update/record/delete functions

### 文件范围

- Create: `tools/new-agents/backend/test_asset_parsing.py`
- Create: `tools/new-agents/backend/tests/test_test_asset_parsing.py`
- Modify: `tools/new-agents/backend/test_assets.py`
- Modify: `docs/todos/refactor/2026-06-21-new-agents-refactor-phase4-plan.md`
- Modify: `docs/todos/refactor/README.md`

### TDD 任务

- [ ] **Step 1: parser module RED**

  新增 `test_test_asset_parsing.py`，导入 `parse_lisa_test_asset_markdown`，用现有 Lisa CASES markdown 验证它返回：

  - `testCases`
  - `coverageTrace`
  - `coverageSummary`
  - `assetIssues`
  - `riskMatrix`
  - `intentTesterDrafts`

  Expected before implementation: fail because `test_asset_parsing` module does not exist.

- [ ] **Step 2: create parser module**

  新增 `test_asset_parsing.py`，把 `test_assets.py` 中无 DB 依赖的 parsing/building helpers 移入新模块，并提供 public function:

  ```python
  def parse_lisa_test_asset_markdown(markdown: str) -> dict:
      ...
  ```

  缺少用例清单表格时继续抛出 `ValueError("测试用例集缺少可解析的用例清单表格")`。

- [ ] **Step 3: wire `test_assets.py` to parser**

  `export_lisa_test_assets` 改为调用 `parse_lisa_test_asset_markdown(markdown)`，并把返回字段合并进现有 export payload。`_serialize_collection` 和 `_sync_risk_matrix` 等现有内部函数可继续调用从 parser module import 的 builder，或通过更窄的 public helper 调用。

- [ ] **Step 4: remove duplicate pure helpers from `test_assets.py`**

  从 `test_assets.py` 删除已迁移的 Markdown parsing、coverage summary、asset issues、risk matrix 和 intent-tester draft helpers，避免形成新旧双事实源。

- [ ] **Step 5: run verification**

  ```bash
  /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_asset_parsing.py tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/backend/tests/test_routes_blueprint.py -q
  git diff --check
  ```

### 完成标准

- `test_assets.py` 行数明显下降，且不再直接包含 Markdown table parsing helpers。
- `test_asset_parsing.py` 不 import Flask、SQLAlchemy、models、db 或 run persistence。
- `export_lisa_test_assets` 输出与本轮前一致。
- test assets route URL、request/response JSON、DB schema 不变。
- 不新增通用 asset framework，不新增 Lisa/Alex 专属 runtime/API/store/UI。
