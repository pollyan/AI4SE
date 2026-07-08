# ROOT_CAUSE cause-map Contract Prompt 同步 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 ROOT_CAUSE 的 `cause-map` artifact contract prompt 与当前 `nodes/edges` 协议一致，避免模型 / retry prompt 被旧 `columns/rows` 指令误导。

**Architecture:** 继续使用现有 `STRUCTURED_VISUAL_SCHEMA_PROMPTS` 和 `build_artifact_contract_prompt()` 入口，不新增 registry 或 workflow 专属分支。新增聚焦 contract test 锁定 ROOT_CAUSE prompt 的节点 / 边协议，矩阵类 visual prompt 保持不变。

**Tech Stack:** Python 3.11, pytest, shared New Agents backend contract tests, Playwright Browser E2E.

---

### Task 1: 写 RED contract prompt 测试

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_contracts.py`

- [x] **Step 1: 新增 ROOT_CAUSE cause-map prompt 协议测试**

在 `test_build_artifact_contract_prompt_requires_delivery_coverage_and_traceability_visuals()` 后添加：

```python
def test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract():
    prompt = build_artifact_contract_prompt(
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    )

    assert "cause-map" in prompt
    assert '"nodes"' in prompt
    assert '"edges"' in prompt
    assert '"source"' in prompt
    assert '"target"' in prompt
    assert "id 唯一" in prompt
    assert '"columns": ["层级", "问题", "回答"' not in prompt
```

- [x] **Step 2: 运行 RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py::test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract -q
```

Result: failed as expected. The prompt did not contain `"nodes"` because `STRUCTURED_VISUAL_SCHEMA_PROMPTS["cause-map"]` still used the old `columns/rows` example.

### Task 2: 更新 cause-map schema prompt

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`

- [x] **Step 1: 替换 `STRUCTURED_VISUAL_SCHEMA_PROMPTS["cause-map"]`**

把旧表格示例替换为：

```python
    "cause-map": (
        'cause-map 必须严格使用如下 JSON 结构：{"type": '
        '"cause-map", "title": "可选标题", "nodes": ['
        '{"id": "Why-1", "label": "Why-1", "title": "直接原因", '
        '"description": "发布前缺少关键路径回归门禁", "category": "流程", '
        '"evidence": "发布记录与测试记录", "confidence": "高", '
        '"status": "已确认"}], "edges": [{"source": "Why-1", '
        '"target": "Why-2", "label": "继续追问"}]}。'
        "nodes 必须是非空对象数组；每个 node 必须包含非空且 id 唯一的 id、"
        "非空 label 和非空 title；description、category、evidence、confidence、"
        "status 可选，但如果出现必须是非空字符串。edges 必须是对象数组；"
        "每条 edge 必须包含非空 source 和 target，并且 source/target 必须引用已存在 node；"
        "label 可选，但如果出现必须是非空字符串。禁止把 cause-map 写成 columns/rows 表格协议。"
    ),
```

- [x] **Step 2: 运行 GREEN**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py::test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract -q
```

Result: `1 passed`

### Task 3: 聚焦回归和记录

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify: this plan

- [x] **Step 1: 运行 backend contract 回归**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py -q
```

Result: `109 passed`

- [x] **Step 2: 运行 New Agents 回归**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Result: New Agents Frontend `724 passed`; New Agents Backend `628 passed, 1 deselected`. Existing React `ArtifactPane.test.tsx` `act(...)` warnings appeared without failing tests.

- [x] **Step 3: 更新 todo 执行记录**

In `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`, under the 第 7 轮执行记录, add a short subsection:

```markdown
### 2026-07-08 第 7 轮补充：ROOT_CAUSE cause-map contract prompt 同步

已关闭上一轮后发现的 `cause-map` contract prompt 矛盾：后端 `build_artifact_contract_prompt()` 现在要求 `nodes/edges` 节点 / 边协议，不再提示旧 `columns/rows` 表格示例。

验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py::test_build_artifact_contract_prompt_requires_cause_map_node_edge_contract -q
```

结果：`1 passed`

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_contract_registry.py -q
```

结果：`109 passed`

```bash
./scripts/test/test-local.sh new-agents
```

结果：New Agents Frontend `724 passed`；New Agents Backend `628 passed, 1 deselected`。
```

### Task 4: 全量验证、提交和推送

**Files:**
- Modify: this plan
- Modify: `tests/e2e/new_agents_browser/conftest.py`

- [x] **Step 1: 运行全量本地验证**

Run:

```bash
./scripts/test/test-local.sh all
```

If default sandbox fails on MidScene port binding or Playwright Chromium permissions, rerun non-sandbox:

```bash
/bin/zsh -lc './scripts/test/test-local.sh all > /private/tmp/ai4se-cause-map-contract-prompt-full-all.log 2>&1; rc=$?; tail -120 /private/tmp/ai4se-cause-map-contract-prompt-full-all.log; echo EXIT_STATUS:$rc; exit $rc'
```

Result:

- 默认沙箱 `./scripts/test/test-local.sh all` 失败，失败点为 MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002` 与 Playwright Chromium `bootstrap_check_in ... Permission denied (1100)`，属于端口 / 浏览器权限限制。
- 第一次非沙箱全量重跑在 New Agents Browser E2E setup 阶段出现 4 个 `Page.goto` / `Page.reload` `load` 等待超时；单独非沙箱 `./scripts/test/test-local.sh e2e` 通过，结果为 `11 passed, 10 deselected`。
- 第二次非沙箱全量重跑仍在 Browser E2E setup 阶段出现 1 个 `Page.goto` `load` 等待超时。根因定位为 E2E fixture 使用默认 `waitUntil='load'`，在全量串行后的资源状态下不稳定；测试实际只需要 React home 页面可交互。
- 已将 `new_agents_page` fixture 的首页打开逻辑改为 `wait_until="domcontentloaded"` 并等待 `选择你的 AI 助手` 标题出现。
- 修复后单独非沙箱 `./scripts/test/test-local.sh e2e` 通过，结果为 `11 passed, 10 deselected`。
- 修复后非沙箱 `./scripts/test/test-local.sh all` 通过，退出码 `0`。关键结果：Intent Tester API `294 passed`；MidScene proxy `17 passed`；Common Frontend lint/build 通过；New Agents Frontend `724 passed`；New Agents Backend `628 passed, 1 deselected`；New Agents Browser E2E `11 passed, 10 deselected`。

- [x] **Step 2: 运行文档和 diff 检查**

Run:

```bash
rg -n "T[B]D|TO[ ]?DO|未[ ]?决|记录[实]际|填[入]" docs/superpowers/specs/2026-07-08-new-agents-cause-map-contract-prompt-sync-design.md docs/superpowers/plans/2026-07-08-new-agents-cause-map-contract-prompt-sync.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
git diff --check -- tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/tests/test_agent_contracts.py tests/e2e/new_agents_browser/conftest.py docs/superpowers/specs/2026-07-08-new-agents-cause-map-contract-prompt-sync-design.md docs/superpowers/plans/2026-07-08-new-agents-cause-map-contract-prompt-sync.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

Stage only this slice and run:

```bash
git diff --cached --check
git diff --cached --name-only
```

- [x] **Step 3: Commit and push**

Commit message:

```bash
git commit -m "fix(new-agents): 同步根因链路契约并稳定浏览器验证"
git push
```

After push:

```bash
git rev-parse HEAD
git rev-parse @{u}
```

Expected: both SHAs match.
