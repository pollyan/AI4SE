# Run History Reuse Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强 New Agents 历史会话中心，让用户按复用质量筛选历史 run、预览当前产物，并复制为新的持久化 run 继续工作。

**Status:** 已完成。因当前可用 multi-agent 工具要求用户显式请求 subagent，本轮未派发 subagent，改由主线程按 TDD 执行完整切片。

**Architecture:** 继续复用共享 run persistence、现有 `/api/agent/runs` 列表、snapshot restore、Header 历史弹层和 workspace URL runId 恢复链路。新增一个通用 clone endpoint 和 run list 质量状态字段，不新增 agent-specific runtime、SSE、store 或 renderer。

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, pytest, TypeScript 5.x, React, Vitest, Testing Library.

---

## File Structure

- Modify: `tools/new-agents/backend/run_persistence.py`
  - 增加 run quality status 派生与 filter。
  - 增加 `clone_agent_run(run_id)`，复制 run/messages/current artifact/context summaries。
- Modify: `tools/new-agents/backend/routes.py`
  - `GET /api/agent/runs` 接收 `qualityStatus`。
  - 新增 `POST /api/agent/runs/<run_id>/clone`。
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
  - RED 覆盖 clone persistence 语义。
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - RED 覆盖 list quality filter 和 clone API。
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 增加 `RunQualityStatus`，并扩展 `AgentRunListItem.qualityStatus`。
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
  - 解析 `qualityStatus`，支持 `qualityStatus` query，新增 `cloneRun`。
- Modify: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`
  - RED 覆盖 qualityStatus parsing/filter、cloneRun、malformed qualityStatus。
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
  - 历史会话弹层增加质量筛选、预览块、复制按钮、失败反馈。
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
  - RED 覆盖筛选、预览、复制成功/失败。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 标记 E06 本轮消化。
- Modify: `docs/todos/refactor/README.md`
  - 更新剩余候选摘要。

## Task 1: RED Backend Quality Filter And Clone

- [x] **Step 1: Add failing backend tests**

In `tools/new-agents/backend/tests/test_agent_endpoint.py`:

```python
def test_agent_runs_list_endpoint_filters_by_quality_status(app, client, default_config):
    with app.app_context():
        reusable_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        record_artifact_version(reusable_run.id, "CLARIFY", "# 需求分析文档\n\n## 1. 被测系统与边界\n系统")
        draft_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        failed_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY", status="failed")
        reusable_run_id = reusable_run.id
        draft_run_id = draft_run.id
        failed_run_id = failed_run.id

    response = client.get("/api/agent/runs?qualityStatus=reusable")

    assert response.status_code == 200
    assert [run["id"] for run in response.json["runs"]] == [reusable_run_id]
    assert response.json["runs"][0]["qualityStatus"] == "reusable"
    assert draft_run_id not in [run["id"] for run in response.json["runs"]]
    assert failed_run_id not in [run["id"] for run in response.json["runs"]]
```

Add an unknown status test expecting 400.

Add clone endpoint test:

```python
def test_agent_run_clone_endpoint_creates_independent_reusable_run(app, client, default_config):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY", model="gpt-test")
        append_run_message(source.id, "user", "原始需求")
        append_run_message(source.id, "assistant", "原始回复")
        record_artifact_version(source.id, "CLARIFY", "# 需求分析文档\n\n## 1. 被测系统与边界\n系统", artifact_data={"requirement_facts": [{"fact_id": "F-001"}]})
        record_artifact_version(source.id, "STRATEGY", "# 测试策略\n\n## 1. 测试范围\n范围")
        source_id = source.id

    response = client.post(f"/api/agent/runs/{source_id}/clone")

    assert response.status_code == 201
    assert response.json["run"]["id"] != source_id
    assert response.json["run"]["workflowId"] == "TEST_DESIGN"
    assert response.json["run"]["currentStageId"] == "STRATEGY"
    assert [message["content"] for message in response.json["messages"]] == ["原始需求", "原始回复"]
    assert {artifact["stageId"] for artifact in response.json["artifacts"]} == {"CLARIFY", "STRATEGY"}
    assert all(artifact["versionNumber"] == 1 for artifact in response.json["artifacts"])
    assert response.json["artifactComments"] == []
    assert response.json["artifactSectionLocks"] == []
    assert response.json["artifactAuditEvents"] == []
```

In `tools/new-agents/backend/tests/test_run_persistence.py`, add a direct `clone_agent_run` test that asserts source and clone snapshots are independent.

- [x] **Step 2: Run backend RED**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_list_endpoint_filters_by_quality_status tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_run_clone_endpoint_creates_independent_reusable_run tools/new-agents/backend/tests/test_run_persistence.py::test_clone_agent_run_copies_messages_artifacts_and_context -q
```

Expected: FAIL because `qualityStatus`, clone endpoint and `clone_agent_run` are missing.

## Task 2: GREEN Backend Quality Filter And Clone

- [x] **Step 1: Implement backend quality status**

In `run_persistence.py`:

```python
RUN_QUALITY_STATUSES = {"reusable", "needs_artifact", "failed"}

def _run_quality_status(run: AgentRun) -> str:
    if run.status == "failed":
        return "failed"
    return "reusable" if _current_artifact_summary(run.id) is not None else "needs_artifact"
```

Apply `quality_status` filtering in `list_agent_runs` after workflow/query filtering using current artifact existence subquery or simple query filter that matches tests.

Add `"qualityStatus": _run_quality_status(run)` to `_run_list_item`.

- [x] **Step 2: Implement clone**

In `run_persistence.py`, implement `clone_agent_run(run_id: str) -> dict` by creating a new run and copying:

- messages with same roles/content/sequence indexes.
- current artifact versions into new artifacts with version `1`.
- context summaries.

Return `get_run_snapshot(clone.id)`.

- [x] **Step 3: Add route**

In `routes.py`, import `clone_agent_run`, read `qualityStatus`, pass it to `list_agent_runs`, and add:

```python
@api_bp.route("/agent/runs/<run_id>/clone", methods=["POST"])
def agent_run_clone(run_id: str):
    try:
        return jsonify(clone_agent_run(run_id)), 201
    except ValueError as e:
        return json_error_response(str(e), 404)
```

- [x] **Step 4: Run backend GREEN**

Run the RED command again. Expected: PASS.

## Task 3: RED Frontend Service And Header

- [x] **Step 1: Add service RED**

In `runSnapshotService.test.ts`, update run list fixtures to include `qualityStatus: 'reusable'`, assert `fetchRunList({ qualityStatus: 'reusable' })` calls `/new-agents/api/agent/runs?limit=20&qualityStatus=reusable`, add malformed status failure, and add `cloneRun('run-123')` expecting POST `/new-agents/api/agent/runs/run-123/clone`.

- [x] **Step 2: Add Header RED**

In `Header.test.tsx`, add tests:

- quality filter calls `fetchRunList({ limit: 20, qualityStatus: 'reusable' })`.
- history card shows `可复用` quality label and artifact preview summary/version.
- clicking `复制为新会话` calls `cloneRun`, then navigates to `/workspace/lisa/test-design?runId=<newId>`.
- clone rejection shows `无法复制历史会话`.

- [x] **Step 3: Run frontend RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx
```

Expected: FAIL because parser, service and UI do not yet exist.

## Task 4: GREEN Frontend Service And Header

- [x] **Step 1: Implement frontend types/service**

Add `RunQualityStatus = 'reusable' | 'needs_artifact' | 'failed'`, `qualityStatus` to `AgentRunListItem`, `qualityStatus?: RunQualityStatus` to `fetchRunList` options, and `cloneRun(runId): Promise<AgentRunSnapshot>`.

- [x] **Step 2: Implement Header UI**

Add state:

```ts
const [runQualityFilter, setRunQualityFilter] = useState<RunQualityStatus | ''>('');
const [cloningRunId, setCloningRunId] = useState<string | null>(null);
```

Pass `qualityStatus` into `loadRuns`.

Render a quality select in the history modal, show preview labels, and add per-card buttons:

- `打开原会话`
- `复制为新会话`

On clone success navigate to the cloned run workspace URL. On failure set `runsError` to `无法复制历史会话`.

- [x] **Step 3: Run frontend GREEN**

Run the RED frontend command again. Expected: PASS.

## Task 5: Docs, Verification, Commit

- [x] **Step 1: Update todos**

Update active todo:

- Mark E06 as consumed with completion definition and verification record.
- Update functional route to remove E06 from remaining list.
- Keep E05/E08/E09/E10/E11/E12 active.

Update README current entry summary.

- [x] **Step 2: Final validation**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_list_endpoint_returns_recent_runs_with_summaries tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_list_endpoint_filters_by_quality_status tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_list_endpoint_rejects_unknown_quality_status tools/new-agents/backend/tests/test_agent_run_clone_endpoint_creates_independent_reusable_run -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx src/__tests__/store.test.ts
cd tools/new-agents/frontend && npm run lint
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m black --check tools/new-agents/backend/run_persistence.py tools/new-agents/backend/routes.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py
git diff --check
```

Actual results:

- Backend: `28 passed in 1.22s`
- Frontend: `84 passed`
- Frontend lint: `tsc --noEmit` passed
- Black check: 4 files left unchanged
- `git diff --check`: passed

- [x] **Step 3: Commit**

Stage only this milestone files and commit:

```bash
git add docs/superpowers/specs/2026-06-23-run-history-reuse-center-design.md docs/superpowers/plans/2026-06-23-run-history-reuse-center.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/backend/run_persistence.py tools/new-agents/backend/routes.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/services/runSnapshotService.ts tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx
git commit -m "feat: 增强历史会话复用中心"
```
