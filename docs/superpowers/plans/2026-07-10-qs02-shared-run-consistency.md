# QS-02 Execution Plan

> 历史状态说明（2026-07-16）：第 1 步的固定进度话术是当时的局部缓解，已由 [`2026-07-16-qg017-chat-before-artifact.md`](2026-07-16-qg017-chat-before-artifact.md) 取代；当前 QG-017 以有意义自然对话先行、共享 service sequencer 和浏览器 DOM 顺序为准。

1. Lock the user-visible artifact-first failure with backend raw-stream and frontend typed-SSE regression tests (red, then green).
2. Add terminal-protocol tests for delta-only EOF and `[DONE] ordering; implement explicit failure paths without saving normal artifact history.
3. Inject persistence failures at assistant-message, artifact-version, and metric boundaries; establish an atomic transaction/outcome contract.
4. Require client-generated `(runId, requestId)` at the API boundary, retain that identity through UI retry, and add endpoint replay plus independent-session unique-constraint coverage at the shared persistence boundary.
5. Run focused backend/frontend suites, shared runtime regression, browser-visible timing evidence where no mocks can hide ordering, then full New Agents suite.
6. Independently review the final diff against this design and `AGENTS.md`; record evidence in the active todo, commit directly to `master`, and push.
