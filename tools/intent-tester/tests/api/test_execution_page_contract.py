"""Execution console contract tests for canonical Flask control."""

import re


def _render_execution_page(client):
    response = client.get("/intent-tester/execution")

    assert response.status_code == 200
    return response.get_data(as_text=True)


def test_execution_page_uses_flask_create_as_the_only_dispatch(client):
    html = _render_execution_page(client)

    assert "axios.post(`${window.API_BASE_URL}/executions`" in html
    assert "currentExecution = response.data.data" in html
    assert "currentExecution.execution_id" in html
    assert "/api/execute-testcase" not in html
    assert "local_execution_id" not in html


def test_execution_page_reconciles_create_even_if_proxy_events_arrive_early(client):
    html = _render_execution_page(client)

    create_success = re.search(
        r"if \(response\.data\.code === 200\) \{"
        r"\s+currentExecution = response\.data\.data;"
        r"\s+const expectedExecutionId = currentExecution\.execution_id;"
        r".*?refreshExecutionStatus\(\{"
        r"\s+expectedExecutionId,"
        r"\s+reconcileUntilTerminal: true"
        r"\s+\}\);",
        html,
        re.DOTALL,
    )

    assert create_success


def test_execution_page_guards_async_testcase_display_results_by_create_id(client):
    html = _render_execution_page(client)

    testcase_display = re.search(
        r"try \{\s+const testcaseResponse = await axios\.get\("
        r"`\$\{window\.API_BASE_URL\}/testcases/\$\{testcaseId\}`\);"
        r"(?P<success>.*?)"
        r"\} catch \(testcaseError\) \{(?P<failure>.*?)\n\s+\}",
        html,
        re.DOTALL,
    )

    assert testcase_display
    id_guard = (
        "if (!durableExecutionControl.isCurrentExecutionId(expectedExecutionId)) {"
    )
    success = testcase_display.group("success")
    failure = testcase_display.group("failure")
    assert id_guard in success
    assert success.index(id_guard) < success.index("currentExecution.totalSteps = totalSteps")
    assert id_guard in failure


def test_execution_page_uses_canonical_flask_stop_and_status(client):
    html = _render_execution_page(client)

    assert "js/durable-execution-control.js" in html
    assert "DurableExecutionControl.createDurableExecutionControl" in html
    assert "apiBaseUrl: window.API_BASE_URL" in html
    assert "durableExecutionControl.stop()" in html
    assert "durableExecutionControl.refresh({" in html
    assert "/api/stop-execution" not in html
    assert "/api/execution-status/" not in html


def test_execution_page_ignores_websocket_events_from_other_executions(client):
    html = _render_execution_page(client)

    assert re.search(
        r"data\.executionId\s*===\s*currentExecution\.execution_id", html
    )

    execution_events = (
        "execution-start",
        "execution-completed",
        "execution-stopped",
        "step-start",
        "step-completed",
        "step-failed",
        "step-skipped",
        "screenshot-taken",
        "log-message",
    )
    for event_name in execution_events:
        guarded_handler = re.compile(
            rf"localProxySocket\.on\('{re.escape(event_name)}', function \(data\) \{{"
            r"\s+if \(!isCurrentExecutionEvent\(data\)\) \{\s+return;\s+\}"
        )
        assert guarded_handler.search(html), f"{event_name} must use the execution ID guard"


def test_execution_page_reconciles_completion_signals_through_durable_control(client):
    html = _render_execution_page(client)

    completion_handler = re.search(
        r"localProxySocket\.on\('execution-completed'.*?\n\s*}\);",
        html,
        re.DOTALL,
    )
    stopped_handler = re.search(
        r"localProxySocket\.on\('execution-stopped'.*?\n\s*}\);",
        html,
        re.DOTALL,
    )

    assert completion_handler
    assert stopped_handler
    for handler in (completion_handler.group(), stopped_handler.group()):
        assert "expectedExecutionId: data.executionId" in handler
        assert "reconcileUntilTerminal: true" in handler
        assert "onExecutionCompleted(data" not in handler


def test_execution_page_guards_terminal_callback_with_expected_execution_id(client):
    html = _render_execution_page(client)

    assert "function onExecutionCompleted(data, expectedExecutionId)" in html
    assert re.search(
        r"function onExecutionCompleted\(data, expectedExecutionId\) \{"
        r"\s+if \(!durableExecutionControl\.isCurrentExecutionId\(expectedExecutionId\)\) \{"
        r"\s+return false;",
        html,
    )
    assert re.search(
        r"data\.execution_id\s*!==\s*expectedExecutionId",
        html,
    )


def test_execution_page_rechecks_step_timer_execution_id(client):
    html = _render_execution_page(client)

    step_completed = re.search(
        r"localProxySocket\.on\('step-completed'.*?\n\s*}\);",
        html,
        re.DOTALL,
    )

    assert step_completed
    handler = step_completed.group()
    assert "const expectedExecutionId = data.executionId" in handler
    assert re.search(
        r"setTimeout\(\(\) => \{"
        r"\s+if \(!durableExecutionControl\.isCurrentExecutionId\(expectedExecutionId\)\) \{"
        r"\s+return;",
        handler,
    )


def test_execution_page_has_hidden_disabled_same_id_retry_control(client):
    html = _render_execution_page(client)

    assert re.search(
        r'<button id="retry-execution"[^>]*disabled[^>]*style="[^"]*display:\s*none',
        html,
    )
    assert "addEventListener('click', retryExecution)" in html
    assert "durableExecutionControl.retry()" in html


def test_execution_page_preserves_canonical_id_when_create_dispatch_returns_502(client):
    html = _render_execution_page(client)

    create_failure = re.search(
        r"function adoptCreateDispatchFailure\(response\) \{(?P<body>.*?)"
        r"\n\s+// 开始执行",
        html,
        re.DOTALL,
    )
    assert create_failure
    body = create_failure.group("body")
    assert "response.status !== 502" in body
    assert "response.data.data.execution_id" in body
    assert "currentExecution = { execution_id: executionId, status: 'pending' }" in body
    assert "调度失败，可重试" in body
    assert "showRetryControl" in body

    catch_block = re.search(
        r"\} catch \(error\) \{\s+console\.error\('启动执行失败:', error\);"
        r"(?P<body>.*?)\n\s+\}",
        html,
        re.DOTALL,
    )
    assert catch_block
    assert "adoptCreateDispatchFailure(error.response)" in catch_block.group("body")


def test_execution_page_retry_failure_stays_visible_and_success_reconciles_same_id(client):
    html = _render_execution_page(client)

    retry_function = re.search(
        r"async function retryExecution\(\) \{(?P<body>.*?)"
        r"\n\s+// 停止执行",
        html,
        re.DOTALL,
    )
    assert retry_function
    body = retry_function.group("body")
    assert "const expectedExecutionId = currentExecution.execution_id" in body
    assert "const outcome = await durableExecutionControl.retry()" in body
    assert "durableExecutionControl.isCurrentExecutionId(expectedExecutionId)" in body
    assert "hideRetryControl()" in body
    assert re.search(
        r"refreshExecutionStatus\(\{\s+expectedExecutionId,\s+reconcileUntilTerminal: true",
        body,
    )
    assert "showRetryControl" in body


def test_execution_page_only_shows_retry_for_failed_exhaustion_and_terminal_clears_it(client):
    html = _render_execution_page(client)

    refresh = re.search(
        r"async function refreshExecutionStatus\(options = \{\}\) \{(?P<body>.*?)"
        r"\n\s+// 更新执行进度",
        html,
        re.DOTALL,
    )
    assert refresh
    body = refresh.group("body")
    assert "!outcome.lastFailure" in body
    assert "['pending', 'running'].includes(outcome.lastStatus)" in body
    assert "hideRetryControl()" in body
    assert "reconcileOutcome.status === 'running' ? '执行中' : '等待启动'" in body
    assert "showRetryControl('调度失败，可重试')" in body

    completion = re.search(
        r"function onExecutionCompleted\(data, expectedExecutionId\) \{(?P<body>.*?)"
        r"\n\s+// 添加日志",
        html,
        re.DOTALL,
    )
    assert completion
    assert "hideRetryControl()" in completion.group("body")


def test_execution_page_writes_canonical_id_to_url_after_create_adoption(client):
    html = _render_execution_page(client)

    assert "function setCanonicalExecutionIdInUrl(executionId)" in html
    assert "url.searchParams.set('execution_id', executionId)" in html
    assert "window.history.replaceState" in html
    assert "localStorage" not in html

    start_execution = re.search(
        r"async function startExecution\(\) \{(?P<body>.*?)"
        r"\n\s+async function retryExecution",
        html,
        re.DOTALL,
    )
    assert start_execution
    assert "setCanonicalExecutionIdInUrl(expectedExecutionId)" in start_execution.group(
        "body"
    )

    create_failure = re.search(
        r"function adoptCreateDispatchFailure\(response\) \{(?P<body>.*?)"
        r"\n\s+// 开始执行",
        html,
        re.DOTALL,
    )
    assert create_failure
    assert "setCanonicalExecutionIdInUrl(executionId)" in create_failure.group("body")


def test_execution_page_restores_url_execution_through_same_id_durable_control(client):
    html = _render_execution_page(client)

    assert "void restoreExecutionFromUrl()" in html
    restore = re.search(
        r"async function restoreExecutionFromUrl\(\) \{(?P<body>.*?)"
        r"\n\s+// 加载测试用例列表",
        html,
        re.DOTALL,
    )
    assert restore
    body = restore.group("body")
    assert "url.searchParams.get('execution_id')" in body
    assert "currentExecution = { execution_id: executionId, status: 'pending' }" in body
    assert re.search(
        r"durableExecutionControl\.refresh\(\{\s+expectedExecutionId: executionId",
        body,
    )
    assert "outcome.kind === 'active'" in body
    assert re.search(
        r"refreshExecutionStatus\(\{\s+expectedExecutionId: executionId,"
        r"\s+reconcileUntilTerminal: true",
        body,
    )
    assert "outcome.kind === 'execution_id_mismatch'" in body
    assert "outcome.kind === 'http_failure' && outcome.httpStatus === 404" in body
    assert "clearCanonicalExecutionIdFromUrl(executionId)" in body
    assert "durableExecutionControl.isCurrentExecutionId(executionId)" in body


def test_execution_page_handles_callback_failure_event_only_for_current_id(client):
    html = _render_execution_page(client)

    handler = re.search(
        r"localProxySocket\.on\('lifecycle-callback-failed', function \(data\) \{"
        r"(?P<body>.*?)\n\s+\}\);",
        html,
        re.DOTALL,
    )
    assert handler
    body = handler.group("body")
    assert "if (!isCurrentExecutionEvent(data))" in body
    assert "data.executionId" in body
    assert "data.event" in body
    assert "data.code" in body
    assert "data.attempts" in body
    assert "终态同步失败，可重试同一任务" in body
    assert "showRetryControl" in body


def test_execution_page_reconciles_healthy_exhaustion_through_flask_once(client):
    html = _render_execution_page(client)

    refresh = re.search(
        r"async function refreshExecutionStatus\(options = \{\}\) \{(?P<body>.*?)"
        r"\n\s+// 更新执行进度",
        html,
        re.DOTALL,
    )
    assert refresh
    body = refresh.group("body")
    assert "const reconcileOutcome = await durableExecutionControl.reconcile()" in body
    assert "durableExecutionControl.isCurrentExecutionId(expectedExecutionId)" in body
    assert "reconcileOutcome.kind === 'terminal'" in body
    assert "reconcileOutcome.kind === 'active'" in body
    assert "hasLifecycleCallbackExhaustedDiagnostic(currentExecution)" in body
    assert "终态同步失败，可重试同一任务" in body
    assert "/api/execute-testcase" not in body
    assert "/api/execution-status/" not in body


def test_execution_page_active_reconcile_without_diagnostic_stays_active(client):
    html = _render_execution_page(client)

    assert "function hasLifecycleCallbackExhaustedDiagnostic(execution)" in html
    assert "lifecycle_callback_exhausted" in html
    assert re.search(
        r"if \(hasLifecycleCallbackExhaustedDiagnostic\(currentExecution\)\) \{"
        r".*?showRetryControl\('终态同步失败，可重试同一任务'\);"
        r".*?\} else \{"
        r".*?hideRetryControl\(\);"
        r".*?reconcileOutcome\.status === 'running' \? '执行中' : '等待启动'",
        html,
        re.DOTALL,
    )


def test_execution_page_url_restore_uses_bounded_refresh_then_flask_reconcile(client):
    html = _render_execution_page(client)

    restore = re.search(
        r"async function restoreExecutionFromUrl\(\) \{(?P<body>.*?)"
        r"\n\s+// 加载测试用例列表",
        html,
        re.DOTALL,
    )
    assert restore
    body = restore.group("body")
    assert re.search(
        r"refreshExecutionStatus\(\{\s+expectedExecutionId: executionId,"
        r"\s+reconcileUntilTerminal: true",
        body,
    )
    assert "clearCanonicalExecutionIdFromUrl(executionId)" in body
