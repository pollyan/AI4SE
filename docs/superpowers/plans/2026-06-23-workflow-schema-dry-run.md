# Workflow Schema Dry-run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增本地 New Agents workflow schema dry-run 门禁，一次性诊断 manifest、前端 prompt/template、后端 contract、artifact_data renderer/readiness、handoff 和 manifest 打包同步缺口。

**Architecture:** 新增 `scripts/validation/new_agents_workflow_dry_run.py`，分离真实仓库事实加载和纯函数校验。后端 pytest 直接调用同一模块做当前仓库通过测试与负例诊断测试，CLI 复用同一 report 输出诊断。

**Tech Stack:** Python 3.11+/pytest，现有 Flask backend test path，New Agents manifest/frontend/backend contract 文件。

---

## 文件范围

- Create: `scripts/validation/new_agents_workflow_dry_run.py`
- Create: `tools/new-agents/backend/tests/test_workflow_dry_run.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`
- Create: `docs/superpowers/specs/2026-06-23-workflow-schema-dry-run-design.md`
- Create: `docs/superpowers/plans/2026-06-23-workflow-schema-dry-run.md`

## Task 1: RED - dry-run report contract

- [x] Step 1: 新增 `tools/new-agents/backend/tests/test_workflow_dry_run.py`，写三个测试：
  - 当前仓库 `load_workflow_dry_run_inputs()` + `build_workflow_dry_run_report()` 通过。
  - 从 loaded inputs 中移除一个 frontend template id，断言 report 包含 `FRONTEND_TEMPLATE_MAPPING_MISSING`。
  - 从 loaded inputs 中移除一个 renderer stage key，断言 report 包含 `ARTIFACT_DATA_RENDERER_MISSING`。

- [x] Step 2: 运行：
  `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_dry_run.py -q`
  预期失败：`ModuleNotFoundError` 或缺少 `scripts.validation.new_agents_workflow_dry_run`。

## Task 2: GREEN - dry-run loader and pure validation

- [x] Step 1: 新增 `scripts/validation/new_agents_workflow_dry_run.py`：
  - `WorkflowDryRunIssue` dataclass: `code`, `message`, `workflow_id=None`, `stage_id=None`。
  - `WorkflowDryRunInputs` dataclass: manifest workflows/handoffs、stage keys、prompt template ids、prompt files、frontend mapping ids、backend contract keys、renderer/readiness keys、handoff template ids、packaging file contents。
  - `WorkflowDryRunReport` dataclass: `issues`, `checks`; property `passed`。
  - `load_workflow_dry_run_inputs(repo_root: Path) -> WorkflowDryRunInputs`。
  - `build_workflow_dry_run_report(inputs: WorkflowDryRunInputs) -> WorkflowDryRunReport`。

- [x] Step 2: 校验至少实现以下 issue codes：
  - `BACKEND_STAGE_MISMATCH`
  - `ARTIFACT_CONTRACT_MISSING`
  - `PROMPT_TEMPLATE_ID_INVALID`
  - `PROMPT_FILE_MISSING`
  - `FRONTEND_TEMPLATE_MAPPING_MISSING`
  - `FRONTEND_TEMPLATE_MAPPING_ORPHANED`
  - `ARTIFACT_DATA_READY_MISSING`
  - `ARTIFACT_DATA_RENDERER_MISSING`
  - `HANDOFF_TARGET_INVALID`
  - `HANDOFF_TEMPLATE_MISSING`
  - `MANIFEST_PACKAGING_MISSING`

- [x] Step 3: 运行 Task 1 测试，预期通过。

## Task 3: CLI and legacy sync test integration

- [x] Step 1: 给 `new_agents_workflow_dry_run.py` 增加 `main(argv=None) -> int`：
  - 无 issue 时输出 `New Agents workflow dry-run passed` 和检查数。
  - 有 issue 时输出 `New Agents workflow dry-run failed`，逐条输出 `[CODE] WORKFLOW/STAGE message`，返回 1。

- [x] Step 2: 在 `test_workflow_dry_run.py` 增加 CLI 测试：
  - 当前仓库调用 `main([str(repo_root)])` 返回 0。
  - monkeypatch 一个 failing report 时返回 1 且输出 issue code。

- [x] Step 3: 修改 `test_workflow_contract_sync.py`：
  - 删除硬编码 `FRONTEND_PROMPT_FILES`。
  - 从 `load_workflow_dry_run_inputs(REPO_ROOT).prompt_files_by_stage` 获取 prompt 文件。
  - 保留现有 visual/mermaid prompt 示例测试。

- [x] Step 4: 运行：
  `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_dry_run.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q`
  预期通过。

## Task 4: 文档与验证

- [x] Step 1: 更新 New Agents enhancement todo：
  - E12 标为 dry-run 门禁已完成，完整 scaffold/codegen 和 prompt/template 版本管理保留为后续。
  - Goal Mode 消化记录新增本轮条目。

- [x] Step 2: 更新 `docs/todos/refactor/README.md` 当前入口，说明平台化候选已新增 workflow schema dry-run 门禁。

- [x] Step 3: 运行本轮验证：
  - `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python scripts/validation/new_agents_workflow_dry_run.py`
  - `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_workflow_dry_run.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q`
  - `git diff --check`

- [ ] Step 4: 聚焦提交：
  `feat(new-agents): 增加 workflow schema dry-run 门禁`

## Self-review

- Spec 覆盖：计划覆盖 dry-run 输入加载、纯校验、CLI、旧同步测试复用和 todo 记录。
- Placeholder scan：无 TBD/TODO。
- 类型一致性：测试、loader、report、CLI 均使用同一 `WorkflowDryRunInputs` / `WorkflowDryRunReport` 命名。
