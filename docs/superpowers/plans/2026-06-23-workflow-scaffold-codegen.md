# Workflow Scaffold Codegen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 New Agents workflow scaffold/codegen 工具，让维护者能从 JSON spec 预览或生成共享 workflow 骨架，并继续用现有 dry-run 暴露剩余 contract/readiness 缺口。

**Architecture:** 新增独立 Python CLI `scripts/validation/new_agents_workflow_scaffold.py`，负责 spec 校验、生成 planned writes、preview 输出、write 防覆盖和 manifest/prompt skeleton 写入。现有 `new_agents_workflow_dry_run.py` 保持诊断职责不变；scaffold 只提示并衔接 dry-run，不伪造完整 workflow 上线。

**Tech Stack:** Python 3.11 standard library, dataclasses, argparse, json, pytest.

---

## 文件结构

- Create: `scripts/validation/new_agents_workflow_scaffold.py`
  - 负责 `WorkflowScaffoldSpec` / `WorkflowScaffoldStage` / `WorkflowScaffoldPlan` 数据结构、JSON spec 加载校验、manifest workflow block 构建、prompt skeleton 构建、preview/write CLI。
- Modify: `tools/new-agents/backend/tests/test_workflow_dry_run.py`
  - 在现有 dry-run 测试旁增加 scaffold preview/write/conflict/invalid/CLI 测试，复用临时目录避免改真实 manifest。
- Modify: `tools/new-agents/backend/tests/conftest.py`
  - 为从 `tools/new-agents/backend` 目录执行的 CI 等价 pytest 增加 repo root import path，使 `scripts.validation.*` 测试导入稳定。
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
  - 对齐当前 PRD/STORY workflow visual contract 事实：要求每个 workflow 至少有一个 visual contract，且 visual contract 不引用未知 stage；不再要求所有 workflow 都有 Mermaid 或第一阶段 visual。
- Modify: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`
  - 使用绝对 repo root 读取 `workflow_manifest.json`，避免从 backend 目录运行时依赖当前工作目录。
- Modify: `docs/todos/refactor/README.md`
  - 从剩余候选中移除 E12 scaffold/codegen，记录本轮消化结果。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 更新 E12 状态和 Goal Mode 消化记录。

预计 commit 边界：本轮是一个工程信任闭环，代码、测试、spec/plan 和 todo 记录同一个聚焦 commit。

## Task 1: RED - Scaffold 行为测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_dry_run.py`

- [ ] **Step 1: 写失败测试**

在文件现有 imports 中加入：

```python
import json
```

追加这些测试代码：

```python
def _write_scaffold_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "support_triage_spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "workflowId": "SUPPORT_TRIAGE",
                "agentId": "lisa",
                "slug": "support-triage",
                "name": "支持工单分诊",
                "description": "帮助支持团队结构化分诊支持工单",
                "welcomeMessage": "你好，我会帮助你完成支持工单分诊。",
                "starterPrompts": ["请帮我分诊这个线上支持工单。"],
                "stages": [
                    {
                        "id": "INTAKE",
                        "name": "信息收集",
                        "promptTemplateId": "support_triage.intake",
                        "artifactTitle": "# 支持工单分诊",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return spec_path


def _create_minimal_scaffold_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    manifest_path = repo_root / "tools/new-agents/workflow_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"handoffs": [], "workflows": {}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return repo_root


def test_workflow_scaffold_preview_plans_manifest_and_prompt_writes(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        build_scaffold_plan,
        load_workflow_scaffold_spec,
    )

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    spec = load_workflow_scaffold_spec(_write_scaffold_spec(tmp_path))

    plan = build_scaffold_plan(repo_root, spec)

    planned_paths = {write.relative_path for write in plan.writes}
    assert "tools/new-agents/workflow_manifest.json" in planned_paths
    assert (
        "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
        in planned_paths
    )
    assert "SUPPORT_TRIAGE" in plan.summary
    assert "python3 scripts/validation/new_agents_workflow_dry_run.py" in plan.next_command
    prompt_write = next(
        write
        for write in plan.writes
        if write.relative_path.endswith("support_triage/intake.ts")
    )
    assert "SUPPORT_TRIAGE_INTAKE_PROMPT" in prompt_write.content
    assert "SUPPORT_TRIAGE_INTAKE_TEMPLATE" in prompt_write.content


def test_workflow_scaffold_write_creates_prompt_and_updates_manifest(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        apply_scaffold_plan,
        build_scaffold_plan,
        load_workflow_scaffold_spec,
    )

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    spec = load_workflow_scaffold_spec(_write_scaffold_spec(tmp_path))
    plan = build_scaffold_plan(repo_root, spec)

    apply_scaffold_plan(plan)

    manifest = json.loads(
        (repo_root / "tools/new-agents/workflow_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    workflow = manifest["workflows"]["SUPPORT_TRIAGE"]
    assert workflow["agentId"] == "lisa"
    assert workflow["slug"] == "support-triage"
    assert workflow["stages"][0]["id"] == "INTAKE"
    assert workflow["stages"][0]["promptTemplateId"] == "support_triage.intake"
    prompt_path = (
        repo_root
        / "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
    )
    assert prompt_path.exists()
    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert "export const SUPPORT_TRIAGE_INTAKE_PROMPT" in prompt_text
    assert "export const SUPPORT_TRIAGE_INTAKE_TEMPLATE" in prompt_text


def test_workflow_scaffold_rejects_existing_prompt_file_without_overwrite(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        WorkflowScaffoldError,
        apply_scaffold_plan,
        build_scaffold_plan,
        load_workflow_scaffold_spec,
    )

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    prompt_path = (
        repo_root
        / "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
    )
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("existing", encoding="utf-8")
    spec = load_workflow_scaffold_spec(_write_scaffold_spec(tmp_path))
    plan = build_scaffold_plan(repo_root, spec)

    try:
        apply_scaffold_plan(plan)
    except WorkflowScaffoldError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected existing prompt file conflict")

    assert prompt_path.read_text(encoding="utf-8") == "existing"


def test_workflow_scaffold_rejects_duplicate_stage_ids(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        WorkflowScaffoldError,
        load_workflow_scaffold_spec,
    )

    spec_path = _write_scaffold_spec(tmp_path)
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    data["stages"].append(dict(data["stages"][0]))
    spec_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    try:
        load_workflow_scaffold_spec(spec_path)
    except WorkflowScaffoldError as exc:
        assert "duplicate stage id" in str(exc)
    else:
        raise AssertionError("expected duplicate stage id to fail")


def test_workflow_scaffold_cli_preview_does_not_write_files(tmp_path, capsys):
    from scripts.validation.new_agents_workflow_scaffold import main as scaffold_main

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    spec_path = _write_scaffold_spec(tmp_path)

    exit_code = scaffold_main(["--repo-root", str(repo_root), "--spec", str(spec_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Preview only; no files written." in captured.out
    assert "support_triage/intake.ts" in captured.out
    assert "new_agents_workflow_dry_run.py" in captured.out
    assert not (
        repo_root
        / "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
    ).exists()
```

- [ ] **Step 2: 运行 RED**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_dry_run.py -q
```

Expected: FAIL，原因是 `ModuleNotFoundError: No module named 'scripts.validation.new_agents_workflow_scaffold'` 或等价缺失模块错误。

## Task 2: GREEN - 实现 scaffold CLI

**Files:**
- Create: `scripts/validation/new_agents_workflow_scaffold.py`

- [ ] **Step 1: 写最小实现**

实现内容包括：
- `WorkflowScaffoldError`
- `WorkflowScaffoldStage`
- `WorkflowScaffoldSpec`
- `ScaffoldWrite`
- `WorkflowScaffoldPlan`
- `load_workflow_scaffold_spec(path)`
- `build_scaffold_plan(repo_root, spec)`
- `apply_scaffold_plan(plan)`
- `main(argv=None)`

核心行为：
- 使用正则校验 `workflowId`、stage `id`、`slug`、`promptTemplateId`。
- 从 `<folder>.<file>` 推导 prompt 文件路径。
- 从 workflow/stage id 推导 TypeScript export 前缀，例如 `SUPPORT_TRIAGE_INTAKE_PROMPT`。
- manifest 写入只更新 `workflows[workflowId]`。
- prompt 文件存在时失败，不覆盖。
- preview 不写文件。

- [ ] **Step 2: 运行 GREEN**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_dry_run.py -q
```

Expected: PASS。

## Task 3: 当前 dry-run 和语法回归

**Files:**
- No code edits unless tests reveal an issue.

- [ ] **Step 1: 运行现有 workflow dry-run**

Run:

```bash
python3 scripts/validation/new_agents_workflow_dry_run.py .
```

Expected: `New Agents workflow dry-run passed`.

- [ ] **Step 2: 运行 Python 语法检查**

Run:

```bash
python3 -m py_compile scripts/validation/new_agents_workflow_scaffold.py scripts/validation/new_agents_workflow_dry_run.py
```

Expected: exit 0。

## Task 4: 更新 todo 记录

**Files:**
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] **Step 1: 更新 README 剩余能力包**

把 E12 从剩余候选移除，保留 4 个后续能力包：
- E08 LLM judge evidence
- Prompt/template 版本管理
- 专业方法库配置化
- DeepSeek 真实外部执行证据

新增一条说明：E12 workflow scaffold/codegen 已完成，从 JSON spec 到 preview/write、冲突保护、dry-run 后续提示和测试证据形成工程信任闭环。

- [ ] **Step 2: 更新诊断文档 E12 和消化记录**

把 E12 验收标准改为已消化完整 scaffold/codegen，并在 Goal Mode 消化记录新增本轮条目。后续 Superpowers 执行颗粒度表中移除 E12，剩余 4 个能力包继续按厚切片执行。

## Task 5: CI 等价 backend 测试环境修复

**Files:**
- Modify: `tools/new-agents/backend/tests/conftest.py`
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`
- Modify: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`

- [ ] **Step 1: 复现 CI 等价失败**

Run:

```bash
cd tools/new-agents/backend
python3 -m pytest tests/ -q -c pytest.ini
```

Observed before fix: collection failed because `scripts` was not importable from backend cwd; after adding repo root to `conftest.py`, the suite exposed two outdated visual contract assertions and one cwd-dependent manifest path.

- [ ] **Step 2: 修复 backend 测试环境 import path**

在 `tools/new-agents/backend/tests/conftest.py` 中加入 repo root：

```python
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))
```

- [ ] **Step 3: 修正 outdated visual contract assertions**

把“每个 workflow 都必须有 Mermaid”和“每个 workflow 第一阶段都必须有 visual”改为当前真实 contract：

```python
def test_visual_contract_covers_every_known_workflow():
    workflows_with_required_visuals = {
        workflow_id
        for workflow_id, _stage_id in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS
    } | {
        workflow_id
        for workflow_id, _stage_id in REQUIRED_ARTIFACT_STRUCTURED_VISUALS
    }

    assert workflows_with_required_visuals == set(WORKFLOW_STAGES)
```

- [ ] **Step 4: 修正 DeepSeek readiness manifest path**

在 `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py` 中使用：

```python
REPO_ROOT = Path(__file__).resolve().parents[4]
REPO_ROOT / "tools/new-agents/workflow_manifest.json"
```

- [ ] **Step 5: 重跑 backend 全量**

Run:

```bash
cd tools/new-agents/backend
python3 -m pytest tests/ -q -c pytest.ini
```

Expected: PASS，允许现有真实 LLM smoke skip。

## Task 6: 完成前验证和提交

**Files:**
- All changed files.

- [ ] **Step 1: 运行聚焦验证**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_workflow_dry_run.py -q
python3 scripts/validation/new_agents_workflow_dry_run.py .
python3 -m py_compile scripts/validation/new_agents_workflow_scaffold.py scripts/validation/new_agents_workflow_dry_run.py
cd tools/new-agents/backend && python3 -m pytest tests/ -q -c pytest.ini
git diff --check
```

Expected: all exit 0。

- [ ] **Step 2: 检查 diff 规模和状态**

Run:

```bash
git diff --stat
git status -sb
```

Expected: 只包含本轮脚本、测试、spec/plan、todo 文档。

- [ ] **Step 3: 提交**

Run:

```bash
git add scripts/validation/new_agents_workflow_scaffold.py tools/new-agents/backend/tests/test_workflow_dry_run.py docs/superpowers/specs/2026-06-23-workflow-scaffold-codegen-design.md docs/superpowers/plans/2026-06-23-workflow-scaffold-codegen.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md
git commit -m "feat(new-agents): 增加 workflow scaffold codegen 闭环"
```

Expected: focused commit created。

## 自检

- Spec 覆盖：preview、write、防覆盖、非法输入、dry-run 承接、todo 更新均有任务。
- 占位扫描：无 TBD/TODO/implement later。
- CI 等价门禁：本轮不触碰前端 TypeScript、runtime、SSE/API、artifact contract 或持久化模型；验证范围为相关 pytest、dry-run、Python py_compile 和 diff check。
