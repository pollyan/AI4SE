# DeepSeek Confidence Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 DeepSeek readiness gate、`artifact_data` persistence 和真实 smoke gate 三个已验证分支整合成一个可继续推进 DS 格式化输出需求的信任闭环分支。

**Architecture:** 本计划只整合共享 New Agents 后端能力，不新增 agent 专属 runtime/API/store/renderer。冲突处理以共享 `AgentTurnOutput`、typed SSE snapshot、run/artifact persistence、renderer registry 和现有 artifact contract 为准。

**Tech Stack:** Python 3.11、Flask/PydanticAI backend、Pydantic schema、pytest、SQLite migration、Git worktree/cherry-pick。

---

### Task 1: 记录隔离工作区与红灯验收

**Files:**
- Read: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Read: `tools/new-agents/backend/tests/`

- [x] **Step 1: 创建隔离分支**

Run:

```bash
git worktree add .worktrees/deepseek-confidence-consolidation -b codex/deepseek-confidence-consolidation master
```

Expected: 新 worktree 位于 `.worktrees/deepseek-confidence-consolidation`，HEAD 为 `master` 当前提交。

- [x] **Step 2: 验证红灯**

Run:

```bash
git merge-base --is-ancestor codex/deepseek-readiness-gate HEAD
git merge-base --is-ancestor codex/deepseek-artifact-data-persistence HEAD
git merge-base --is-ancestor codex/deepseek-real-smoke-gate HEAD
```

Expected: 三条命令均返回非 0，证明当前整合分支尚未包含目标能力。

### Task 2: 整合 readiness gate

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Create/Modify: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [x] **Step 1: Cherry-pick readiness commit**

Run:

```bash
git cherry-pick bab76d2b
```

Expected: readiness commit 进入整合分支；如出现冲突，保留 renderer registry/helper 结构。

- [x] **Step 2: 验证 readiness 测试**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q
```

Expected: 测试通过。

### Task 3: 整合 artifact_data persistence

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/stream_models.py`
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/db_migrations.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`

- [x] **Step 1: Cherry-pick persistence commit**

Run:

```bash
git cherry-pick 877f6019
```

Expected: `AgentTurnOutput.artifact_data`、snapshot `artifactData`、持久化 JSON 字段和迁移进入整合分支。

- [x] **Step 2: 冲突处理规则**

If `artifact_data_renderers.py` conflicts, keep both:

```python
rendered = ARTIFACT_DATA_RENDERERS[stage_key](artifact_data)
return AgentTurnOutput(
    chat=chat,
    artifact=rendered,
    artifact_data=artifact_data.model_dump(mode="json"),
    stage_action=stage_action,
)
```

Expected: renderer registry 仍是单一共享入口，且渲染后的 turn output 携带原始结构化数据。

- [x] **Step 3: 验证 persistence 测试**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_stream_services.py -q
```

Expected: 测试通过。

### Task 4: 整合真实 DeepSeek smoke gate

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_real_smoke.py`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [x] **Step 1: Cherry-pick smoke commit**

Run:

```bash
git cherry-pick 926d2ad2
```

Expected: smoke gate 校验 raw JSON 中的 `artifact_data`，无凭证/网络时 skip 而非伪造成功。

- [x] **Step 2: 验证 smoke gate 本地行为**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_real_smoke.py -q
```

Expected: 本地无显式 DeepSeek 配置时测试 skip；有配置时校验真实模型输出含合法 `artifact_data`。

### Task 5: 更新整合记录并运行扩展验证

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Create: `docs/superpowers/specs/2026-06-23-deepseek-confidence-consolidation-design.md`
- Create: `docs/superpowers/plans/2026-06-23-deepseek-confidence-consolidation.md`

- [x] **Step 1: 更新 todo 当前进展**

Add an entry stating that readiness gate、`artifact_data` persistence 和真实 smoke gate 已整合到 `codex/deepseek-confidence-consolidation`。

- [x] **Step 2: 运行扩展验证**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_real_smoke.py -q
```

Expected: 本地可运行测试通过；真实 DeepSeek smoke 在缺少显式环境配置时 skip。

- [x] **Step 3: 检查 whitespace**

Run:

```bash
git diff --check
```

Expected: 无输出，exit 0。

- [x] **Step 4: 提交整合记录**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-deepseek-confidence-consolidation-design.md docs/superpowers/plans/2026-06-23-deepseek-confidence-consolidation.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md
git commit -m "chore: 整合 DeepSeek 结构化输出信任闭环"
```

Expected: 最终分支包含三个目标能力和本轮整合记录。
