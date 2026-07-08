# Alex Requirement to Story Packet Evidence Plan

**Goal:** 用浏览器级证据证明 Alex 需求蓝图可以 handoff 到用户故事拆解，并最终生成单故事需求包；同时保留 Lisa 既有 handoff 回归。

**Architecture:** 只扩展 E2E mock 和测试记录。系统实现仍复用现有 workflow handoff、run snapshot restore、Agent Runtime typed SSE、ArtifactPane story packet API，不新增 runtime 或真实 AI Coding workflow。

## Tasks

### Task 1: RED browser E2E for blueprint-to-story-packet chain

Files:
- Modify: `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`

- [x] Add a browser test that runs Alex 需求蓝图梳理, clicks `从需求蓝图继续拆用户故事`, runs user story breakdown from the restored workspace, generates `US-001` packet, and copies it.
- [x] Run:

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py::test_alex_requirement_blueprint_handoff_to_story_packet_chain -q
```

Expected: fail because the browser mock does not yet return the Alex user-story handoff from `VALUE_DISCOVERY/BLUEPRINT`.

### Task 2: E2E mock support for Alex-to-Alex handoff

Files:
- Modify: `tests/e2e/new_agents_browser/conftest.py`

- [x] Add `value-discovery-blueprint-to-user-story-breakdown` to `route_run_handoffs` while keeping existing Lisa handoffs.
- [x] Branch `route_start_handoff` by handoff id, returning Alex / `USER_STORY_BREAKDOWN` / `mock-run-user_story_breakdown-handoff` for the new target.
- [x] Add a run snapshot route for `mock-run-user_story_breakdown-handoff` with `currentStageId=SCOPE` and an initial user message that includes the upstream blueprint context.
- [x] Make story packet candidate/list mock use the active user-story run id from the URL.
- [x] Rerun the RED E2E and expect pass.

### Task 3: Evidence documentation

Files:
- Modify: `docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`
- Modify: `docs/TESTING.md`

- [x] Mark 第 5 轮 completed.
- [x] Record E2E evidence and Lisa handoff regression.
- [x] Record CI-equivalent verification commands.

### Task 4: Verification and checkpoint commit

- [x] Run focused browser E2E:

```bash
.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py -q
```

- [x] Run New Agents suite:

```bash
./scripts/test/test-local.sh new-agents
```

- [x] Run full local automation:

```bash
./scripts/test/test-local.sh all
```

- [x] Stage only 第 5 轮 files.
- [x] Commit and push unless verification or remote is blocked.
