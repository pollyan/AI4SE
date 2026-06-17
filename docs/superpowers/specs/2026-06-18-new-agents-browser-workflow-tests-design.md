# New Agents Browser Workflow Tests Design

## Context

New Agents currently protects the Lisa and Alex agent runtime with backend contract tests, frontend unit tests, and state orchestration tests. The remaining gap is browser-level verification that a user can complete full agent workflows through the real React UI without using the existing intent-tester or MidScene tooling.

This design adds an independent browser test framework for:

- Lisa `test-design`: `CLARIFY -> STRATEGY -> CASES -> DELIVERY`
- Alex `value-discovery`: `ELEVATOR -> PERSONA -> JOURNEY -> BLUEPRINT`

## Goals

- Drive the real New Agents frontend in a browser.
- Verify the complete workflow organization logic for Lisa test case generation and Alex value discovery.
- Avoid using `tools/intent-tester`, MidScene, or the intent-test proxy.
- Keep normal tests deterministic by mocking the typed SSE agent endpoint.
- Support an optional real LLM judge mode for qualitative review without making it part of the default gate.
- Never store API keys in source files, docs, screenshots, or committed test fixtures.

## Non-Goals

- Do not validate the real model provider on every run.
- Do not replace backend contract tests or frontend unit tests.
- Do not test the legacy intent-tester product.
- Do not add a second product UI or change New Agents user-facing behavior.

## Recommended Approach

Use a root-level `pytest-playwright` browser framework under `tests/e2e/new_agents_browser`.

The repository already declares Python Playwright dependencies in `requirements.txt`, so this avoids modifying the currently dirty `tools/new-agents/frontend/package-lock.json`. Tests will start the New Agents Vite dev server, navigate through the real React routes, intercept the typed Agent Runtime SSE endpoint, and return deterministic stage outputs.

## Architecture

The framework has four focused parts:

1. `conftest.py`
   - Starts `tools/new-agents/frontend` with Vite on a test port.
   - Provides browser page setup.
   - Clears `localStorage` before every scenario.
   - Fails on browser console errors.

2. `sse_mock.py`
   - Maps `(workflowId, stageId)` to valid `AgentTurnOutput` payloads.
   - Emits `text/event-stream` bodies matching `/new-agents/api/agent/runs/stream`.
   - Requests next-stage transitions for every non-final stage.
   - Returns no stage transition for final stages.

3. `workflow_runner.py`
   - Provides reusable browser actions and assertions:
     - select agent
     - select workflow
     - send first prompt
     - confirm stage transitions
     - assert stage artifact headings
     - assert chat/artifact separation
     - assert final stage does not request another transition

4. `llm_judge.py`
   - Optional.
   - Reads judge config only from environment variables:
     - `NEW_AGENTS_E2E_LLM_JUDGE=1`
     - `NEW_AGENTS_E2E_JUDGE_API_KEY`
     - `NEW_AGENTS_E2E_JUDGE_BASE_URL`
     - `NEW_AGENTS_E2E_JUDGE_MODEL`
   - Sends final artifact text to the configured model.
   - Expects a strict JSON verdict with `pass`, `score`, and `issues`.
   - Skips when judge mode is not enabled.

## Test Scenarios

### Lisa Test Design Workflow

The browser starts at `/new-agents/`, selects Lisa, selects `测试策略与用例设计`, sends a login/payment-style product requirement, and completes all four stages.

Assertions:

- The workspace renders the Lisa test design onboarding state.
- The first user prompt appears in the left chat pane.
- `CLARIFY` updates the right artifact with `# 需求分析文档`.
- The UI shows `确认进入 策略制定`.
- Confirming the transition advances to `STRATEGY` and generates `# 测试策略蓝图`.
- Confirming the transition advances to `CASES` and generates `# 测试用例集`.
- Confirming the transition advances to `DELIVERY` and generates `# 测试设计文档`.
- Final stage does not show another `确认进入`.
- Assistant chat bubbles do not contain the full artifact Markdown headings.

### Alex Value Discovery Workflow

The browser starts at `/new-agents/`, selects Alex, selects `价值发现`, sends a product direction, and completes all four stages.

Assertions:

- The workspace renders the Alex value discovery onboarding state.
- The first user prompt appears in the left chat pane.
- `ELEVATOR` updates the right artifact with `# 价值定位分析`.
- The UI shows `确认进入 用户画像`.
- Confirming the transition advances to `PERSONA` and generates `# 用户画像分析`.
- Confirming the transition advances to `JOURNEY` and generates `# 用户旅程分析`.
- Confirming the transition advances to `BLUEPRINT` and generates a `需求蓝图` artifact.
- Final stage does not show another `确认进入`.
- Assistant chat bubbles do not contain the full artifact Markdown headings.

## Mock SSE Contract

Each mocked response uses the same event shape as the backend:

```text
data: {"type":"agent_turn","output":{"chat":"...","artifact_update":{"type":"replace","markdown":"..."},"stage_action":{"type":"request_next_stage","target_stage_id":"..."}}}

data: [DONE]
```

Final stages omit `stage_action`.

The mock is intentionally route-level, not component-level. It only replaces the model backend response while leaving browser rendering, React routing, Zustand state, markdown rendering, input handling, buttons, and stage confirmation behavior intact.

## LLM Judge Behavior

The LLM judge is not required for default test success. When enabled, it evaluates the final artifact text against workflow-specific criteria:

- All expected stages are represented.
- Final artifact is internally coherent.
- It does not contain placeholder-only content.
- It is useful for a human reviewer.
- It respects the intended workflow type.

Judge failures should produce concise diagnostic issues. The judge request must redact or avoid secrets. API keys are read from environment variables only.

## Commands

Default deterministic browser tests:

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

Optional judge mode:

```bash
NEW_AGENTS_E2E_LLM_JUDGE=1 \
NEW_AGENTS_E2E_JUDGE_API_KEY=... \
NEW_AGENTS_E2E_JUDGE_BASE_URL=https://api.deepseek.com \
NEW_AGENTS_E2E_JUDGE_MODEL=deepseek-v4-flash \
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

The command clears root `pytest.ini` addopts because the root config currently enables unrelated intent-tester coverage by default. This keeps the new browser framework independent.

## Risks And Mitigations

- Browser binaries may be missing locally.
  - Mitigation: provide a clear failure message instructing the user to run Playwright browser installation for Python if needed.
- Vite startup may be slow.
  - Mitigation: wait for the dev server health response before running browser actions.
- Existing workspace state may leak through persisted Zustand storage.
  - Mitigation: clear `localStorage` and use a unique test port.
- Model judge may be flaky.
  - Mitigation: judge mode is opt-in and not part of the default deterministic gate.

## Acceptance Criteria

- A new independent browser test framework exists under `tests/e2e/new_agents_browser`.
- The framework does not import or call `tools/intent-tester`.
- Lisa `test-design` completes all four stages in a browser.
- Alex `value-discovery` completes all four stages in a browser.
- Tests verify stage ordering, confirmation gates, artifact headings, and chat/artifact separation.
- Default tests require no API key.
- Optional LLM judge reads credentials only from environment variables.
- Verification command is documented and runnable.
