"""
测试执行历史管理API测试
"""

import ast
from datetime import datetime
import inspect
import threading
import textwrap
from typing import get_type_hints

import pytest
from sqlalchemy import text

from backend.services.proxy_execution_client import ProxyExecutionClientError

PROXY_TOKEN = "qs04-canary-proxy-token-0123456789abcdef"


class RecordingProxyExecutionClient:
    """Injectable proxy double that records the controller boundary."""

    def __init__(self):
        self.dispatch_payloads = []
        self.stopped_execution_ids = []
        self.status_execution_ids = []
        self.dispatch_error = None
        self.stop_error = None
        self.status_error = None
        self.status_payload = None

    def dispatch_execution(self, payload):
        self.dispatch_payloads.append(payload)
        if self.dispatch_error:
            raise ProxyExecutionClientError(self.dispatch_error)
        return {"success": True, "executionId": payload["executionId"]}

    def stop_execution(self, execution_id):
        self.stopped_execution_ids.append(execution_id)
        if self.stop_error:
            raise ProxyExecutionClientError(self.stop_error)
        return {"success": True}

    def get_execution_status(self, execution_id):
        self.status_execution_ids.append(execution_id)
        if self.status_error:
            raise ProxyExecutionClientError(self.status_error)
        return self.status_payload


@pytest.fixture
def proxy_execution_client(app):
    client = RecordingProxyExecutionClient()
    app.config["PROXY_EXECUTION_CLIENT"] = client
    return client


class StubProxyResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        if self._payload is None:
            raise ValueError("not JSON")
        return self._payload


class StubProxySession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


class TestProxyExecutionClient:
    def test_should_attach_canonical_bearer_to_every_proxy_request(self):
        from backend.services.proxy_execution_client import ProxyExecutionClient

        token = "qs04-canary-proxy-token-0123456789abcdef"
        session = StubProxySession(
            StubProxyResponse(
                payload={
                    "success": True,
                    "executionId": "flask-execution-id",
                    "status": "running",
                }
            )
        )
        client = ProxyExecutionClient(
            base_url="http://proxy.example", session=session, token=token
        )
        client.dispatch_execution(
            {"executionId": "flask-execution-id", "testcase": {"id": 1}}
        )
        client.stop_execution("flask-execution-id")
        client.get_execution_status("flask-execution-id")

        assert len(session.calls) == 3
        assert all(
            kwargs["headers"] == {"Authorization": f"Bearer {token}"}
            for _, kwargs in session.calls
        )
        assert token not in repr([response for response in ()])

    def test_should_fail_closed_without_base_url_or_token(self):
        from backend.services.proxy_execution_client import ProxyExecutionClient

        with pytest.raises(ValueError, match="base_url"):
            ProxyExecutionClient(token="x" * 32)
        with pytest.raises(ValueError, match="token"):
            ProxyExecutionClient(base_url="http://proxy.example")

    def test_should_post_dispatch_body_and_scoped_stop_path(self):
        from backend.services.proxy_execution_client import ProxyExecutionClient

        session = StubProxySession(
            StubProxyResponse(
                payload={"success": True, "executionId": "flask-execution-id"}
            )
        )
        client = ProxyExecutionClient(
            base_url="http://proxy.example/", timeout=7, session=session, token=PROXY_TOKEN
        )
        dispatch_payload = {
            "executionId": "flask-execution-id",
            "testcase": {"id": 1},
        }

        client.dispatch_execution(dispatch_payload)
        session.response = StubProxyResponse(payload={"success": True})
        client.stop_execution("flask-execution-id")

        assert session.calls == [
            (
                "http://proxy.example/api/execute-testcase",
                {"json": dispatch_payload, "timeout": 7, "headers": {"Authorization": f"Bearer {PROXY_TOKEN}"}},
            ),
            (
                "http://proxy.example/api/stop-execution/flask-execution-id",
                {"json": None, "timeout": 7, "headers": {"Authorization": f"Bearer {PROXY_TOKEN}"}},
            ),
        ]

    def test_should_raise_diagnostic_error_for_http_rejection(self):
        from backend.services.proxy_execution_client import (
            ProxyExecutionClient,
            ProxyExecutionClientError,
        )

        session = StubProxySession(
            StubProxyResponse(
                status_code=503,
                payload={"success": False, "error": "proxy overloaded"},
            )
        )
        client = ProxyExecutionClient(base_url="http://proxy.example", session=session, token=PROXY_TOKEN)

        with pytest.raises(ProxyExecutionClientError, match="503.*proxy overloaded"):
            client.dispatch_execution(
                {"executionId": "flask-execution-id", "testcase": {"id": 1}}
            )

    def test_should_raise_diagnostic_error_for_network_failure(self):
        import requests

        from backend.services.proxy_execution_client import (
            ProxyExecutionClient,
            ProxyExecutionClientError,
        )

        session = StubProxySession(error=requests.ConnectionError("connection reset"))
        client = ProxyExecutionClient(base_url="http://proxy.example", session=session, token=PROXY_TOKEN)

        with pytest.raises(ProxyExecutionClientError, match="connection reset"):
            client.stop_execution("flask-execution-id")

    def test_should_get_and_validate_matching_execution_status(self):
        from backend.services.proxy_execution_client import ProxyExecutionClient

        session = StubProxySession(
            StubProxyResponse(
                payload={
                    "success": True,
                    "executionId": "flask/execution-id",
                    "status": "running",
                }
            )
        )
        client = ProxyExecutionClient(base_url="http://proxy.example/", session=session, token=PROXY_TOKEN)

        payload = client.get_execution_status("flask/execution-id")

        assert payload["status"] == "running"
        assert session.calls == [
            (
                "http://proxy.example/api/execution-status/flask%2Fexecution-id",
                {"timeout": 30.0, "headers": {"Authorization": f"Bearer {PROXY_TOKEN}"}},
            )
        ]

    @pytest.mark.parametrize(
        "payload",
        [
            {"success": True, "executionId": "other-id", "status": "running"},
            {
                "success": True,
                "executionId": "flask-execution-id",
                "status": "unknown",
            },
            {
                "success": False,
                "executionId": "flask-execution-id",
                "status": "running",
            },
        ],
    )
    def test_should_reject_untrusted_execution_status_payload(self, payload):
        from backend.services.proxy_execution_client import ProxyExecutionClient

        client = ProxyExecutionClient(
            base_url="http://proxy.example",
            session=StubProxySession(StubProxyResponse(payload=payload)),
            token=PROXY_TOKEN,
        )

        with pytest.raises(ProxyExecutionClientError):
            client.get_execution_status("flask-execution-id")


def test_qs03_helpers_and_proxy_client_methods_have_complete_type_annotations():
    from backend.api import executions
    from backend.services.database_service import DatabaseService
    from backend.services.proxy_execution_client import ProxyExecutionClient

    callables = (
        executions._get_proxy_execution_client,
        executions._require_proxy_acceptance,
        executions._proxy_failure_response,
        executions._log_unexpected_execution_failure,
        executions._build_dispatch_payload,
        executions._validate_lifecycle_payload,
        executions._get_durable_execution_details,
        executions._reconcile_execution_from_proxy,
        executions.create_execution,
        executions.record_execution_lifecycle,
        executions.retry_execution,
        executions.reconcile_execution,
        DatabaseService._parse_lifecycle_timestamp,
        DatabaseService._replace_step_snapshots,
        DatabaseService.apply_execution_lifecycle,
        DatabaseService.record_lifecycle_callback_exhausted,
        ProxyExecutionClient.__init__,
        ProxyExecutionClient.dispatch_execution,
        ProxyExecutionClient.get_execution_status,
        ProxyExecutionClient.stop_execution,
    )

    for callable_object in callables:
        signature = inspect.signature(callable_object)
        hints = get_type_hints(callable_object)
        expected_parameters = {
            name for name in signature.parameters if name not in {"self", "cls"}
        }
        assert expected_parameters <= hints.keys(), callable_object.__qualname__
        assert "return" in hints, callable_object.__qualname__


def test_qs03_create_retry_and_stop_do_not_use_broad_exception_handlers():
    from backend.api import executions

    for endpoint in (
        executions.create_execution,
        executions.retry_execution,
        executions.stop_execution,
    ):
        source = textwrap.dedent(inspect.getsource(endpoint))
        tree = ast.parse(source)
        broad_handlers = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "Exception"
        ]
        assert broad_handlers == [], endpoint.__name__


@pytest.mark.usefixtures("proxy_execution_client")
class TestCreateExecutionAPI:
    """创建执行任务API测试 (POST /api/executions)"""

    def test_should_create_execution_with_valid_data(
        self,
        api_client,
        create_test_testcase,
        sample_execution_data,
        assert_api_response,
    ):
        """测试使用有效数据创建执行任务"""
        testcase = create_test_testcase(name="测试执行创建")
        execution_data = sample_execution_data.copy()
        execution_data["testcase_id"] = testcase.id

        response = api_client.post(
            "/api/executions", json=execution_data, content_type="application/json"
        )

        data = assert_api_response(response, 200)

        # 验证返回的执行数据 (assert_api_response已经返回data字段内容)
        assert "execution_id" in data
        assert data["status"] == "pending"

    def test_should_create_execution_with_optional_params(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试使用可选参数创建执行任务"""
        testcase = create_test_testcase(name="测试可选参数执行")

        execution_data = {
            "testcase_id": testcase.id,
            "mode": "browser",
            "browser": "firefox",
            "executed_by": "test_user",
        }

        response = api_client.post(
            "/api/executions", json=execution_data, content_type="application/json"
        )

        data = assert_api_response(response, 200)

        # assert_api_response已经返回data字段内容
        assert "execution_id" in data
        assert data["status"] == "pending"

    def test_should_validate_required_testcase_id(
        self, api_client, assert_api_response
    ):
        """测试验证必需的testcase_id字段"""
        execution_data = {"mode": "headless", "browser": "chrome"}

        response = api_client.post(
            "/api/executions", json=execution_data, content_type="application/json"
        )

        assert_api_response(response, 400)

    def test_should_validate_testcase_exists(self, api_client, assert_api_response):
        """测试验证测试用例存在"""
        execution_data = {"testcase_id": 99999}  # 不存在的测试用例ID

        response = api_client.post(
            "/api/executions", json=execution_data, content_type="application/json"
        )

        assert_api_response(response, 404)

    def test_should_reject_inactive_testcase(
        self, api_client, create_test_testcase, assert_api_response
    ):
        """测试拒绝已删除的测试用例"""
        testcase = create_test_testcase(name="已删除测试用例", is_active=False)

        execution_data = {"testcase_id": testcase.id}

        response = api_client.post(
            "/api/executions", json=execution_data, content_type="application/json"
        )

        assert_api_response(response, 404)

    def test_should_dispatch_with_flask_execution_id_as_canonical_id(
        self,
        api_client,
        create_test_testcase,
        proxy_execution_client,
        assert_api_response,
    ):
        testcase = create_test_testcase(name="canonical ID dispatch")

        response = api_client.post(
            "/api/executions",
            json={"testcase_id": testcase.id, "mode": "headless"},
        )

        data = assert_api_response(response, 200)
        assert len(proxy_execution_client.dispatch_payloads) == 1
        assert (
            proxy_execution_client.dispatch_payloads[0]["executionId"]
            == data["execution_id"]
        )

    def test_should_keep_pending_when_proxy_dispatch_is_rejected(
        self,
        app,
        api_client,
        create_test_testcase,
        proxy_execution_client,
        assert_api_response,
        monkeypatch,
    ):
        from backend.models import ExecutionHistory

        testcase = create_test_testcase(name="rejected proxy dispatch")
        upstream_secret = "proxy refused dispatch secret=do-not-leak"
        proxy_execution_client.dispatch_error = upstream_secret
        logged_messages = []

        def record_warning(message, *args, **_kwargs):
            logged_messages.append(message % args)

        monkeypatch.setattr(app.logger, "warning", record_warning)

        response = api_client.post(
            "/api/executions",
            json={"testcase_id": testcase.id, "mode": "headless"},
        )

        error = assert_api_response(response, 502)
        persisted = ExecutionHistory.query.filter_by(test_case_id=testcase.id).one()
        assert persisted.status == "pending"
        assert error == {
            "code": 502,
            "message": "调度执行失败",
            "data": {"execution_id": persisted.execution_id},
        }
        assert upstream_secret not in response.get_data(as_text=True)
        assert any(persisted.execution_id in message for message in logged_messages)
        assert all(upstream_secret not in message for message in logged_messages)

    def test_should_return_real_500_for_unexpected_dispatch_adapter_error(
        self,
        app,
        api_client,
        create_test_testcase,
        proxy_execution_client,
        assert_api_response,
        monkeypatch,
    ):
        from backend.models import ExecutionHistory

        testcase = create_test_testcase(name="unexpected adapter error")
        logged_messages = []

        def record_error(message, *args, **_kwargs):
            logged_messages.append(message % args)

        def reject_traceback_logging(*_args, **_kwargs):
            raise AssertionError("unexpected exception traceback logging")

        monkeypatch.setattr(app.logger, "error", record_error)
        monkeypatch.setattr(app.logger, "exception", reject_traceback_logging)

        def raise_unexpected_error(_payload):
            raise RuntimeError("adapter crashed with secret=do-not-leak")

        proxy_execution_client.dispatch_execution = raise_unexpected_error

        response = api_client.post(
            "/api/executions",
            json={"testcase_id": testcase.id, "mode": "headless"},
        )

        error = assert_api_response(response, 500)
        persisted = ExecutionHistory.query.filter_by(test_case_id=testcase.id).one()
        assert persisted.status == "pending"
        assert persisted.end_time is None
        assert error["data"]["execution_id"] == persisted.execution_id
        assert "do-not-leak" not in response.get_data(as_text=True)
        assert any(persisted.execution_id in message for message in logged_messages)
        assert all("do-not-leak" not in message for message in logged_messages)


class TestExecutionLifecycleCallbackAPI:
    """Durable lifecycle callback contract (POST /api/executions/<id>/lifecycle)."""

    def test_should_apply_started_and_duplicate_result_without_duplicate_snapshots(
        self, proxy_api_client, create_execution_history, assert_api_response
    ):
        execution = create_execution_history(
            status="pending",
            end_time=None,
            error_message="执行生命周期回调重试已耗尽，需要状态协调恢复",
            result_summary='{"diagnostics":[{"code":"lifecycle_callback_exhausted"}]}',
        )
        lifecycle_url = f"/api/executions/{execution.execution_id}/lifecycle"

        started_payload = {"event": "started", "status": "running"}
        assert_api_response(proxy_api_client.post(lifecycle_url, json=started_payload), 200)
        assert_api_response(proxy_api_client.post(lifecycle_url, json=started_payload), 200)

        result_payload = {
            "event": "result",
            "status": "success",
            "steps": [
                {
                    "index": 0,
                    "description": "打开登录页",
                    "status": "success",
                    "duration": 15,
                }
            ],
        }
        result = assert_api_response(
            proxy_api_client.post(lifecycle_url, json=result_payload), 200
        )
        duplicate_result = assert_api_response(
            proxy_api_client.post(lifecycle_url, json=result_payload), 200
        )

        from backend.models import ExecutionHistory, StepExecution

        persisted_execution = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert persisted_execution.status == "success"
        assert persisted_execution.error_message is None
        assert persisted_execution.result_summary is None
        assert result["status"] == "success"
        assert duplicate_result["status"] == "success"
        assert (
            ExecutionHistory.query.filter_by(
                execution_id=execution.execution_id
            ).count()
            == 1
        )
        assert (
            StepExecution.query.filter_by(execution_id=execution.execution_id).count()
            == 1
        )

    def test_terminal_commit_wins_over_stale_active_callback_diagnostic(
        self, create_execution_history
    ):
        from backend.models import ExecutionHistory, db
        from backend.services.database_service import DatabaseService

        execution = create_execution_history(status="running", end_time=None)
        session = db.session()
        previous_expire_on_commit = session.expire_on_commit
        session.expire_on_commit = False
        try:
            stale_execution = ExecutionHistory.query.filter_by(
                execution_id=execution.execution_id
            ).one()
            original_result_summary = stale_execution.result_summary
            db.session.execute(
                text(
                    "UPDATE execution_history SET status = 'success' "
                    "WHERE execution_id = :execution_id"
                ),
                {"execution_id": execution.execution_id},
            )
            db.session.commit()
            assert stale_execution.status == "running"

            result = DatabaseService.record_lifecycle_callback_exhausted(
                execution.execution_id
            )

            db.session.expire_all()
            persisted = ExecutionHistory.query.filter_by(
                execution_id=execution.execution_id
            ).one()
            assert result["outcome"] == "invalid_transition"
            assert persisted.status == "success"
            assert persisted.error_message is None
            assert persisted.result_summary == original_result_summary
            assert "lifecycle_callback_exhausted" not in (
                persisted.result_summary or ""
            )
        finally:
            session.expire_on_commit = previous_expire_on_commit

    def test_should_reject_stale_callback_after_terminal_result(
        self, proxy_api_client, create_execution_history, assert_api_response
    ):
        execution = create_execution_history(status="running", end_time=None)
        lifecycle_url = f"/api/executions/{execution.execution_id}/lifecycle"

        assert_api_response(
            proxy_api_client.post(
                lifecycle_url,
                json={
                    "event": "result",
                    "status": "failed",
                    "error_message": "proxy failed",
                },
            ),
            200,
        )
        assert_api_response(
            proxy_api_client.post(
                lifecycle_url, json={"event": "started", "status": "running"}
            ),
            409,
        )

        from backend.models import ExecutionHistory

        persisted_execution = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert persisted_execution.status == "failed"
        assert persisted_execution.error_message == "proxy failed"

    def test_should_reject_invalid_payloads_and_unknown_execution(
        self, proxy_api_client, create_execution_history, assert_api_response
    ):
        execution = create_execution_history(
            status="pending",
            end_time=None,
            error_message="执行生命周期回调重试已耗尽，需要状态协调恢复",
            result_summary='{"diagnostics":[{"code":"lifecycle_callback_exhausted"}]}',
        )
        lifecycle_url = f"/api/executions/{execution.execution_id}/lifecycle"

        assert_api_response(
            proxy_api_client.post(lifecycle_url, json={"status": "running"}), 400
        )
        assert_api_response(
            proxy_api_client.post(
                lifecycle_url, json={"event": "started", "status": "failed"}
            ),
            400,
        )
        assert_api_response(
            proxy_api_client.post(
                lifecycle_url, json={"event": "result", "status": "running"}
            ),
            400,
        )
        assert_api_response(
            proxy_api_client.post(
                "/api/executions/missing-execution/lifecycle",
                json={"event": "started", "status": "running"},
            ),
            404,
        )

    def test_should_reject_malformed_nested_step_fields_as_400(
        self, proxy_api_client, create_execution_history, assert_api_response
    ):
        execution = create_execution_history(status="running", end_time=None)
        url = f"/api/executions/{execution.execution_id}/lifecycle"

        for invalid_step in (
            {"index": True, "description": "步骤", "status": "success"},
            {"index": 0, "description": None, "status": "success"},
            {"index": 0, "description": "步骤", "status": "success", "duration": {}},
            {"index": 0, "description": "步骤", "status": "success", "ai_confidence": 2},
        ):
            assert_api_response(
                proxy_api_client.post(
                    url,
                    json={"event": "result", "status": "success", "steps": [invalid_step]},
                ),
                400,
            )

    @pytest.mark.parametrize(
        "invalid_payload",
        [
            {"start_time": "not-a-timestamp"},
            {"end_time": "not-a-timestamp"},
            {
                "steps": [
                    {
                        "index": 0,
                        "status": "success",
                        "start_time": "not-a-timestamp",
                    }
                ]
            },
            {
                "steps": [
                    {
                        "index": 0,
                        "status": "success",
                        "end_time": "not-a-timestamp",
                    }
                ]
            },
        ],
    )
    def test_should_reject_invalid_iso_timestamps_before_duplicate_noop(
        self,
        invalid_payload,
        proxy_api_client,
        create_execution_history,
        assert_api_response,
    ):
        from backend.models import ExecutionHistory, StepExecution, db

        execution = create_execution_history(
            status="success", error_message="existing diagnostic"
        )
        db.session.add(
            StepExecution(
                execution_id=execution.execution_id,
                step_index=7,
                step_description="existing snapshot",
                status="success",
                start_time=datetime.utcnow(),
            )
        )
        db.session.commit()
        payload = {"event": "result", "status": "success", **invalid_payload}

        response = proxy_api_client.post(
            f"/api/executions/{execution.execution_id}/lifecycle", json=payload
        )

        assert_api_response(response, 400)
        db.session.expire_all()
        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        snapshots = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).all()
        assert persisted.status == "success"
        assert persisted.error_message == "existing diagnostic"
        assert [(step.step_index, step.step_description) for step in snapshots] == [
            (7, "existing snapshot")
        ]

    @pytest.mark.parametrize(
        "steps",
        [
            [{"index": 0, "status": "running"}],
            [
                {"index": 0, "status": "success"},
                {"index": 0, "status": "failed"},
            ],
            [
                {"index": 1, "status": "success"},
                {"status": "skipped"},
            ],
        ],
    )
    def test_should_reject_invalid_terminal_step_contract_without_db_changes(
        self,
        steps,
        proxy_api_client,
        create_execution_history,
        assert_api_response,
    ):
        from backend.models import ExecutionHistory, StepExecution, db

        execution = create_execution_history(
            status="running", end_time=None, error_message="existing diagnostic"
        )
        db.session.add(
            StepExecution(
                execution_id=execution.execution_id,
                step_index=9,
                step_description="existing snapshot",
                status="success",
                start_time=datetime.utcnow(),
            )
        )
        db.session.commit()

        response = proxy_api_client.post(
            f"/api/executions/{execution.execution_id}/lifecycle",
            json={"event": "result", "status": "success", "steps": steps},
        )

        assert_api_response(response, 400)
        db.session.expire_all()
        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        snapshots = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).all()
        assert persisted.status == "running"
        assert persisted.end_time is None
        assert persisted.error_message == "existing diagnostic"
        assert [(step.step_index, step.step_description) for step in snapshots] == [
            (9, "existing snapshot")
        ]

    @pytest.mark.parametrize(
        "steps",
        [
            [{"index": 0, "status": "running"}],
            [
                {"index": 0, "status": "success"},
                {"index": 0, "status": "failed"},
            ],
            [
                {"index": 1, "status": "success"},
                {"status": "skipped"},
            ],
        ],
    )
    def test_database_service_defends_terminal_step_contract_before_replacement(
        self, steps, create_execution_history
    ):
        from backend.models import ExecutionHistory, StepExecution, db
        from backend.services.database_service import DatabaseService

        execution = create_execution_history(status="running", end_time=None)
        db.session.add(
            StepExecution(
                execution_id=execution.execution_id,
                step_index=11,
                step_description="existing snapshot",
                status="success",
                start_time=datetime.utcnow(),
            )
        )
        db.session.commit()

        with pytest.raises(ValueError):
            DatabaseService.apply_execution_lifecycle(
                execution.execution_id,
                "result",
                "success",
                {"event": "result", "status": "success", "steps": steps},
            )

        db.session.expire_all()
        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        snapshots = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).all()
        assert persisted.status == "running"
        assert [(step.step_index, step.step_description) for step in snapshots] == [
            (11, "existing snapshot")
        ]

    def test_should_preserve_steps_when_result_omits_steps_and_clear_on_explicit_empty(
        self, proxy_api_client, create_execution_history, assert_api_response
    ):
        from backend.models import StepExecution, db

        execution = create_execution_history(status="running", end_time=None)
        db.session.add(
            StepExecution(
                execution_id=execution.execution_id,
                step_index=0,
                step_description="既有步骤",
                status="success",
                start_time=datetime.utcnow(),
            )
        )
        db.session.commit()
        url = f"/api/executions/{execution.execution_id}/lifecycle"

        assert_api_response(
            proxy_api_client.post(url, json={"event": "result", "status": "success"}),
            200,
        )
        assert (
            StepExecution.query.filter_by(
                execution_id=execution.execution_id
            ).count()
            == 1
        )

        second = create_execution_history(status="running", end_time=None)
        db.session.add(
            StepExecution(
                execution_id=second.execution_id,
                step_index=0,
                step_description="待清空步骤",
                status="success",
                start_time=datetime.utcnow(),
            )
        )
        db.session.commit()
        assert_api_response(
            proxy_api_client.post(
                f"/api/executions/{second.execution_id}/lifecycle",
                json={"event": "result", "status": "success", "steps": []},
            ),
            200,
        )
        assert StepExecution.query.filter_by(execution_id=second.execution_id).count() == 0

    def test_concurrent_terminal_callbacks_have_one_durable_winner(self, tmp_path):
        from backend.app import create_app
        from backend.models import ExecutionHistory, StepExecution, TestCase, db
        from backend.services.database_service import DatabaseService

        race_app = create_app(
            {
                "TESTING": False,
                "SECRET_KEY": "test-secret-key-with-at-least-32-bytes",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'lifecycle-race.db'}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            }
        )
        execution_id = "concurrent-lifecycle-race"
        with race_app.app_context():
            testcase = TestCase(name="并发回调", steps="[]", is_active=True)
            db.session.add(testcase)
            db.session.flush()
            db.session.add(
                ExecutionHistory(
                    execution_id=execution_id,
                    test_case_id=testcase.id,
                    status="running",
                    mode="headless",
                    start_time=datetime.utcnow(),
                )
            )
            db.session.commit()

        barrier = threading.Barrier(2)
        outcomes = []

        def apply_result(status):
            with race_app.app_context():
                barrier.wait(timeout=5)
                outcomes.append(
                    DatabaseService.apply_execution_lifecycle(
                        execution_id,
                        "result",
                        status,
                        {
                            "event": "result",
                            "status": status,
                            "steps": [
                                {
                                    "index": 0,
                                    "description": status,
                                    "status": "success" if status == "success" else "failed",
                                }
                            ],
                        },
                    )["outcome"]
                )

        threads = [
            threading.Thread(target=apply_result, args=(status,))
            for status in ("success", "failed")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert all(not thread.is_alive() for thread in threads)
        assert sorted(outcomes) == ["applied", "invalid_transition"]
        with race_app.app_context():
            execution = ExecutionHistory.query.filter_by(execution_id=execution_id).one()
            steps = StepExecution.query.filter_by(execution_id=execution_id).all()
            assert execution.status in {"success", "failed"}
            assert len(steps) == 1
            assert steps[0].step_description == execution.status


@pytest.mark.usefixtures("proxy_execution_client")
class TestRetryExecutionAPI:
    """Same-ID retry contract (POST /api/executions/<id>/retry)."""

    def test_should_retry_pending_execution_with_persisted_testcase_mode_and_same_id(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        from backend.models import ExecutionHistory

        execution = create_execution_history(
            status="pending", mode="browser", end_time=None
        )

        data = assert_api_response(
            api_client.post(f"/api/executions/{execution.execution_id}/retry"), 200
        )

        assert data == {
            "execution_id": execution.execution_id,
            "status": "pending",
        }
        assert ExecutionHistory.query.count() == 1
        assert proxy_execution_client.dispatch_payloads == [
            {
                "executionId": execution.execution_id,
                "testcase": execution.test_case.to_dict(include_stats=False),
                "mode": "browser",
                "enable_cache": True,
                "timeout_settings": {},
            }
        ]

    def test_should_allow_running_retry_dispatch_without_mutating_durable_state(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        execution = create_execution_history(status="running", end_time=None)

        data = assert_api_response(
            api_client.post(f"/api/executions/{execution.execution_id}/retry"), 200
        )

        assert data["execution_id"] == execution.execution_id
        assert data["status"] == "running"
        assert proxy_execution_client.dispatch_payloads[0]["executionId"] == execution.execution_id

    @pytest.mark.parametrize("status", ["success", "failed", "stopped"])
    def test_should_reject_terminal_retry_as_immutable(
        self,
        status,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        execution = create_execution_history(status=status)

        error = assert_api_response(
            api_client.post(f"/api/executions/{execution.execution_id}/retry"), 409
        )

        assert "终态" in error["message"]
        assert proxy_execution_client.dispatch_payloads == []

    def test_should_return_404_for_unknown_retry(
        self, api_client, proxy_execution_client, assert_api_response
    ):
        assert_api_response(api_client.post("/api/executions/missing/retry"), 404)
        assert proxy_execution_client.dispatch_payloads == []

    def test_should_keep_status_and_steps_when_retry_dispatch_fails(
        self,
        app,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
        monkeypatch,
    ):
        from backend.models import ExecutionHistory, StepExecution, db

        execution = create_execution_history(status="running", end_time=None)
        db.session.add(
            StepExecution(
                execution_id=execution.execution_id,
                step_index=0,
                step_description="既有步骤",
                status="success",
                start_time=datetime.utcnow(),
            )
        )
        db.session.commit()
        upstream_secret = "proxy still owns active execution secret=do-not-leak"
        proxy_execution_client.dispatch_error = upstream_secret
        logged_messages = []

        def record_warning(message, *args, **_kwargs):
            logged_messages.append(message % args)

        monkeypatch.setattr(app.logger, "warning", record_warning)

        response = api_client.post(f"/api/executions/{execution.execution_id}/retry")
        error = assert_api_response(response, 502)

        db.session.expire_all()
        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert error["data"]["execution_id"] == execution.execution_id
        assert error["message"] == "重试调度失败"
        assert upstream_secret not in response.get_data(as_text=True)
        assert any(execution.execution_id in message for message in logged_messages)
        assert all(upstream_secret not in message for message in logged_messages)
        assert persisted.status == "running"
        assert persisted.end_time is None
        assert (
            StepExecution.query.filter_by(
                execution_id=execution.execution_id
            ).count()
            == 1
        )

    def test_should_sanitize_unexpected_retry_adapter_error_and_log_execution_id(
        self,
        app,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
        monkeypatch,
    ):
        execution = create_execution_history(status="pending", end_time=None)
        logged_messages = []

        def record_error(message, *args, **_kwargs):
            logged_messages.append(message % args)

        def reject_traceback_logging(*_args, **_kwargs):
            raise AssertionError("unexpected exception traceback logging")

        def raise_unexpected_error(_payload):
            raise RuntimeError("secret adapter detail")

        monkeypatch.setattr(app.logger, "error", record_error)
        monkeypatch.setattr(app.logger, "exception", reject_traceback_logging)
        proxy_execution_client.dispatch_execution = raise_unexpected_error

        response = api_client.post(f"/api/executions/{execution.execution_id}/retry")
        error = assert_api_response(response, 500)

        assert error["data"]["execution_id"] == execution.execution_id
        assert "secret adapter detail" not in response.get_data(as_text=True)
        assert any(execution.execution_id in message for message in logged_messages)
        assert all("secret adapter detail" not in message for message in logged_messages)


@pytest.mark.usefixtures("proxy_execution_client")
class TestReconcileExecutionAPI:
    """Pull reconciliation contract (POST /api/executions/<id>/reconcile)."""

    def test_should_converge_pending_execution_from_terminal_proxy_state(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        execution = create_execution_history(
            status="pending",
            end_time=None,
            error_message="执行生命周期回调重试已耗尽，需要状态协调恢复",
            result_summary='{"diagnostics":[{"code":"lifecycle_callback_exhausted"}]}',
        )
        proxy_execution_client.status_payload = {
            "success": True,
            "executionId": execution.execution_id,
            "status": "success",
            "startTime": "2026-07-11T08:00:00.000Z",
            "endTime": "2026-07-11T08:00:03.000Z",
            "steps": [
                {
                    "index": 0,
                    "description": "missed websocket step",
                    "status": "success",
                    "start_time": "2026-07-11T08:00:00.000Z",
                    "end_time": "2026-07-11T08:00:03.000Z",
                    "duration": 3000,
                }
            ],
        }

        reconciled = assert_api_response(
            api_client.post(f"/api/executions/{execution.execution_id}/reconcile"),
            200,
        )
        durable_get = assert_api_response(
            api_client.get(f"/api/executions/{execution.execution_id}"), 200
        )

        assert reconciled == durable_get
        assert reconciled["status"] == "success"
        assert reconciled["error_message"] is None
        assert reconciled["result_summary"] == {}
        assert reconciled["step_executions"][0]["step_description"] == (
            "missed websocket step"
        )
        assert proxy_execution_client.status_execution_ids == [execution.execution_id]

    def test_should_persist_fixed_active_callback_diagnostic_across_get(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        from backend.models import ExecutionHistory

        raw_secret = "raw callback secret=do-not-persist"
        execution = create_execution_history(status="pending", end_time=None)
        proxy_execution_client.status_payload = {
            "success": True,
            "executionId": execution.execution_id,
            "status": "running",
            "startTime": "2026-07-11T08:00:00.000Z",
            "steps": [],
            "callbackErrors": [
                {
                    "code": "lifecycle_callback_exhausted",
                    "message": raw_secret,
                }
            ],
        }

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/reconcile"
        )
        reconciled = assert_api_response(response, 200)
        restarted_get = assert_api_response(
            api_client.get(f"/api/executions/{execution.execution_id}"), 200
        )

        assert reconciled["status"] == "running"
        assert reconciled["error_message"] == (
            "执行生命周期回调重试已耗尽，需要状态协调恢复"
        )
        assert reconciled["result_summary"]["diagnostics"] == [
            {"code": "lifecycle_callback_exhausted"}
        ]
        assert restarted_get == reconciled
        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert raw_secret not in response.get_data(as_text=True)
        assert raw_secret not in (persisted.result_summary or "")
        assert raw_secret not in (persisted.error_message or "")

    def test_should_persist_only_safe_running_step_projection(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        from backend.models import StepExecution

        raw_secret = "running-secret=do-not-persist"
        execution = create_execution_history(status="pending", end_time=None)
        proxy_execution_client.status_payload = {
            "success": True,
            "executionId": execution.execution_id,
            "status": "running",
            "startTime": "2026-07-11T08:00:00.000Z",
            "steps": [
                {
                    "index": 0,
                    "description": "safe active step",
                    "status": "success",
                    "start_time": "2026-07-11T08:00:00.000Z",
                    "end_time": "2026-07-11T08:00:01.000Z",
                    "duration": 1000,
                    "params": {"token": raw_secret},
                    "error_message": raw_secret,
                    "screenshot_path": "/private/screenshot.png",
                }
            ],
            "logs": [raw_secret],
            "screenshots": [raw_secret],
            "error": raw_secret,
        }

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/reconcile"
        )
        reconciled = assert_api_response(response, 200)
        persisted = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).one()

        assert reconciled["status"] == "running"
        assert reconciled["step_executions"][0]["step_description"] == (
            "safe active step"
        )
        assert persisted.screenshot_path is None
        assert persisted.error_message is None
        assert persisted.ai_confidence is None
        assert persisted.ai_decision == '{"action": "unknown", "result_data": {}}'
        assert raw_secret not in response.get_data(as_text=True)

    @pytest.mark.parametrize(
        "unsafe_steps",
        [
            [
                {"index": 0, "description": "one", "status": "success"},
                {"index": 0, "description": "duplicate", "status": "failed"},
            ],
            [{"index": 0, "description": "invalid", "status": "unknown"}],
        ],
    )
    def test_should_reject_invalid_running_step_projection_without_mutation(
        self,
        unsafe_steps,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        from backend.models import StepExecution

        execution = create_execution_history(status="running", end_time=None)
        proxy_execution_client.status_payload = {
            "success": True,
            "executionId": execution.execution_id,
            "status": "running",
            "steps": unsafe_steps,
        }

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/reconcile"
        )
        assert_api_response(response, 502)

        assert (
            StepExecution.query.filter_by(
                execution_id=execution.execution_id
            ).count()
            == 0
        )

    def test_terminal_lifecycle_replaces_progress_and_late_progress_is_noop(
        self, create_execution_history
    ):
        from backend.models import StepExecution
        from backend.services.database_service import DatabaseService

        execution = create_execution_history(status="running", end_time=None)
        progress = DatabaseService.apply_execution_progress(
            execution.execution_id,
            [
                {
                    "index": 0,
                    "description": "intermediate",
                    "status": "running",
                    "start_time": "2026-07-11T08:00:00.000Z",
                    "end_time": None,
                    "duration": None,
                }
            ],
        )
        terminal = DatabaseService.apply_execution_lifecycle(
            execution.execution_id,
            "result",
            "success",
            {
                "event": "result",
                "status": "success",
                "end_time": "2026-07-11T08:00:03.000Z",
                "steps": [
                    {
                        "index": 0,
                        "description": "final",
                        "status": "success",
                        "start_time": "2026-07-11T08:00:00.000Z",
                        "end_time": "2026-07-11T08:00:03.000Z",
                        "duration": 3000,
                    }
                ],
            },
        )
        late = DatabaseService.apply_execution_progress(
            execution.execution_id,
            [{"index": 0, "description": "late", "status": "running"}],
        )
        snapshots = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).all()

        assert progress["outcome"] == "applied"
        assert terminal["outcome"] == "applied"
        assert late["outcome"] == "terminal_noop"
        assert len(snapshots) == 1
        assert snapshots[0].step_description == "final"

    def test_should_sanitize_failed_proxy_state_before_persisting_or_responding(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        from backend.models import ExecutionHistory, StepExecution

        raw_secret = "node failure secret=do-not-persist"
        execution = create_execution_history(status="running", end_time=None)
        proxy_execution_client.status_payload = {
            "success": True,
            "executionId": execution.execution_id,
            "status": "failed",
            "startTime": "2026-07-11T08:00:00.000Z",
            "endTime": "2026-07-11T08:00:02.000Z",
            "error": raw_secret,
            "steps": [
                {
                    "index": 0,
                    "description": "failed step",
                    "status": "failed",
                    "start_time": "2026-07-11T08:00:00.000Z",
                    "end_time": "2026-07-11T08:00:02.000Z",
                    "error_message": raw_secret,
                }
            ],
        }

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/reconcile"
        )
        data = assert_api_response(response, 200)

        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        step = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert data["status"] == "failed"
        assert data["error_message"] == "代理报告执行失败（已通过状态协调确认）"
        assert step.error_message is None
        assert raw_secret not in response.get_data(as_text=True)
        assert raw_secret not in (persisted.error_message or "")

    def test_should_return_502_without_mutation_when_proxy_is_unavailable(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        from backend.models import ExecutionHistory

        execution = create_execution_history(status="pending", end_time=None)
        raw_secret = "proxy unavailable secret=do-not-leak"
        proxy_execution_client.status_error = raw_secret

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/reconcile"
        )
        error = assert_api_response(response, 502)

        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert error["data"]["execution_id"] == execution.execution_id
        assert raw_secret not in response.get_data(as_text=True)
        assert persisted.status == "pending"
        assert persisted.end_time is None

    def test_should_sanitize_unexpected_reconcile_adapter_error_in_logs(
        self,
        app,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
        monkeypatch,
    ):
        execution = create_execution_history(status="pending", end_time=None)
        logged_messages = []

        def record_error(message, *args, **_kwargs):
            logged_messages.append(message % args)

        def reject_traceback_logging(*_args, **_kwargs):
            raise AssertionError("unexpected exception traceback logging")

        def raise_unexpected_error(_execution_id):
            raise RuntimeError("reconcile crashed secret=do-not-leak")

        monkeypatch.setattr(app.logger, "error", record_error)
        monkeypatch.setattr(app.logger, "exception", reject_traceback_logging)
        proxy_execution_client.get_execution_status = raise_unexpected_error

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/reconcile"
        )
        error = assert_api_response(response, 500)

        assert error["data"]["execution_id"] == execution.execution_id
        assert "do-not-leak" not in response.get_data(as_text=True)
        assert any(execution.execution_id in message for message in logged_messages)
        assert all("do-not-leak" not in message for message in logged_messages)

    @pytest.mark.parametrize(
        "untrusted_payload",
        [
            {"success": True, "executionId": "other-execution", "status": "running"},
            {"success": True, "executionId": None, "status": "unknown"},
            {"success": False, "executionId": None, "status": "running"},
        ],
    )
    def test_should_return_502_for_untrusted_proxy_state(
        self,
        untrusted_payload,
        app,
        api_client,
        create_execution_history,
        assert_api_response,
    ):
        from backend.models import ExecutionHistory
        from backend.services.proxy_execution_client import ProxyExecutionClient

        execution = create_execution_history(status="pending", end_time=None)
        payload = dict(untrusted_payload)
        if payload["executionId"] is None:
            payload["executionId"] = execution.execution_id
        session = StubProxySession(
            StubProxyResponse(payload=payload)
        )
        app.config["PROXY_EXECUTION_CLIENT"] = ProxyExecutionClient(
            base_url="http://proxy.example", session=session, token=PROXY_TOKEN
        )

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/reconcile"
        )
        assert_api_response(response, 502)

        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert "other-execution" not in response.get_data(as_text=True)
        assert persisted.status == "pending"

    @pytest.mark.parametrize("terminal_status", ["success", "failed", "stopped"])
    def test_should_return_terminal_durable_state_without_proxy_dependency(
        self,
        terminal_status,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        execution = create_execution_history(status=terminal_status)
        proxy_execution_client.status_error = "must not be called"

        reconciled = assert_api_response(
            api_client.post(f"/api/executions/{execution.execution_id}/reconcile"),
            200,
        )

        assert reconciled["status"] == terminal_status
        assert proxy_execution_client.status_execution_ids == []

    def test_should_repeat_terminal_reconcile_idempotently(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        from backend.models import StepExecution

        execution = create_execution_history(status="running", end_time=None)
        proxy_execution_client.status_payload = {
            "success": True,
            "executionId": execution.execution_id,
            "status": "success",
            "endTime": "2026-07-11T08:00:01.000Z",
            "steps": [
                {
                    "index": 0,
                    "description": "only snapshot",
                    "status": "success",
                }
            ],
        }
        url = f"/api/executions/{execution.execution_id}/reconcile"

        first = assert_api_response(api_client.post(url), 200)
        second = assert_api_response(api_client.post(url), 200)

        assert first == second
        assert proxy_execution_client.status_execution_ids == [execution.execution_id]
        assert (
            StepExecution.query.filter_by(execution_id=execution.execution_id).count()
            == 1
        )

    def test_concurrent_reconcile_has_one_durable_terminal_snapshot(self, tmp_path):
        from backend.app import create_app
        from backend.models import ExecutionHistory, StepExecution, TestCase, db

        reconcile_app = create_app(
            {
                "TESTING": False,
                "SECRET_KEY": "test-secret-key-with-at-least-32-bytes",
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'reconcile-race.db'}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            }
        )
        execution_id = "concurrent-reconcile"
        barrier = threading.Barrier(2)

        class BarrierStatusProxy:
            def get_execution_status(self, requested_execution_id):
                barrier.wait(timeout=5)
                return {
                    "success": True,
                    "executionId": requested_execution_id,
                    "status": "success",
                    "endTime": "2026-07-11T08:00:01.000Z",
                    "steps": [
                        {
                            "index": 0,
                            "description": "concurrent snapshot",
                            "status": "success",
                        }
                    ],
                }

        reconcile_app.config["PROXY_EXECUTION_CLIENT"] = BarrierStatusProxy()
        with reconcile_app.app_context():
            db.create_all()
            testcase = TestCase(name="并发协调", steps="[]", is_active=True)
            db.session.add(testcase)
            db.session.flush()
            db.session.add(
                ExecutionHistory(
                    execution_id=execution_id,
                    test_case_id=testcase.id,
                    status="running",
                    mode="headless",
                    start_time=datetime.utcnow(),
                )
            )
            db.session.commit()

        response_codes = []

        def reconcile():
            with reconcile_app.test_client() as client:
                client.get("/intent-tester/login")
                with client.session_transaction() as current:
                    login_csrf = current["csrf_token"]
                login_response = client.post(
                    "/intent-tester/login",
                    data={
                        "username": "admin",
                        "password": "test-admin-password",
                        "csrf_token": login_csrf,
                    },
                    headers={"Origin": "http://127.0.0.1:5001"},
                )
                assert login_response.status_code == 302
                with client.session_transaction() as current:
                    csrf_token = current["csrf_token"]
                response_codes.append(
                    client.post(
                        f"/intent-tester/api/executions/{execution_id}/reconcile",
                        headers={
                            "Origin": "http://127.0.0.1:5001",
                            "X-CSRF-Token": csrf_token,
                        },
                    ).status_code
                )

        threads = [threading.Thread(target=reconcile) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert all(not thread.is_alive() for thread in threads)
        assert sorted(response_codes) == [200, 200]
        with reconcile_app.app_context():
            execution = ExecutionHistory.query.filter_by(
                execution_id=execution_id
            ).one()
            steps = StepExecution.query.filter_by(execution_id=execution_id).all()
            assert execution.status == "success"
            assert len(steps) == 1
            assert steps[0].step_description == "concurrent snapshot"


class TestGetExecutionAPI:
    """获取执行详情API测试 (GET /api/executions/<execution_id>)"""

    def test_should_get_execution_by_valid_id(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试使用有效ID获取执行详情"""
        execution = create_execution_history(status="success")

        response = api_client.get(f"/api/executions/{execution.execution_id}")
        data = assert_api_response(response, 200)

        execution_data = data  # assert_api_response已经返回data字段内容
        assert execution_data["execution_id"] == execution.execution_id
        assert execution_data["status"] == "success"
        assert execution_data["test_case_id"] == execution.test_case_id

        # 验证返回的数据结构
        required_fields = [
            "execution_id",
            "test_case_id",
            "test_case_name",
            "status",
            "mode",
            "browser",
            "start_time",
            "executed_by",
            "created_at",
        ]
        for field in required_fields:
            assert field in execution_data, f"执行数据缺少字段: {field}"

    def test_should_get_running_execution(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试获取运行中的执行"""
        execution = create_execution_history(
            status="running", end_time=None, duration=None
        )

        response = api_client.get(f"/api/executions/{execution.execution_id}")
        data = assert_api_response(response, 200)

        execution_data = data  # assert_api_response已经返回data字段内容
        assert execution_data["status"] == "running"
        assert execution_data["end_time"] is None
        assert execution_data["duration"] is None

    def test_should_get_failed_execution_with_error(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试获取失败的执行（包含错误信息）"""
        execution = create_execution_history(
            status="failed", error_message="测试错误消息", error_stack="错误堆栈信息"
        )

        response = api_client.get(f"/api/executions/{execution.execution_id}")
        data = assert_api_response(response, 200)

        execution_data = data  # assert_api_response已经返回data字段内容
        assert execution_data["status"] == "failed"
        assert execution_data["error_message"] == "测试错误消息"

    def test_should_return_404_for_nonexistent_execution(
        self, api_client, assert_api_response
    ):
        """测试不存在的执行ID返回404"""
        response = api_client.get("/api/executions/nonexistent-id")
        assert_api_response(response, 404)


class TestListExecutionsAPI:
    """获取执行列表API测试 (GET /api/executions)"""

    def test_should_get_empty_executions_list(self, api_client, assert_api_response):
        """测试获取空的执行列表"""
        response = api_client.get("/api/executions")
        data = assert_api_response(
            response,
            200,
            {"items": list, "total": int, "page": int, "size": int, "pages": int},
        )

        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["size"] == 20

    def test_should_get_executions_list_with_data(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试获取包含数据的执行列表"""
        # 创建测试执行记录
        execution1 = create_execution_history(status="success")
        execution2 = create_execution_history(status="failed")

        response = api_client.get("/api/executions")
        data = assert_api_response(response, 200)

        assert data["total"] == 2
        assert len(data["items"]) == 2

        # 验证执行数据结构
        execution_data = data["items"][0]  # 检查第一个执行记录的数据结构
        expected_fields = [
            "execution_id",
            "test_case_id",
            "test_case_name",
            "status",
            "start_time",
            "duration",
            "executed_by",
        ]
        for field in expected_fields:
            assert field in execution_data, f"执行列表数据缺少字段: {field}"

    def test_should_support_pagination(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试分页功能"""
        # 创建多个执行记录
        for i in range(5):
            create_execution_history(status="success")

        # 测试第一页，每页2条
        response = api_client.get("/api/executions?page=1&size=2")
        data = assert_api_response(response, 200)

        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert data["pages"] == 3
        assert len(data["items"]) == 2

        # 测试第二页
        response = api_client.get("/api/executions?page=2&size=2")
        data = assert_api_response(response, 200)

        assert data["page"] == 2
        assert len(data["items"]) == 2

        # 测试最后一页
        response = api_client.get("/api/executions?page=3&size=2")
        data = assert_api_response(response, 200)

        assert data["page"] == 3
        assert len(data["items"]) == 1

    def test_should_support_testcase_filter(
        self,
        api_client,
        create_test_testcase,
        create_execution_history,
        assert_api_response,
    ):
        """测试按测试用例过滤功能"""
        testcase1 = create_test_testcase(name="测试用例1")
        testcase2 = create_test_testcase(name="测试用例2")

        # 为不同测试用例创建执行记录
        create_execution_history(test_case_id=testcase1.id, status="success")
        create_execution_history(test_case_id=testcase1.id, status="failed")
        create_execution_history(test_case_id=testcase2.id, status="success")

        # 按testcase1过滤
        response = api_client.get(f"/api/executions?testcase_id={testcase1.id}")
        data = assert_api_response(response, 200)

        assert data["total"] == 2
        for item in data["items"]:
            assert item["test_case_id"] == testcase1.id

        # 按testcase2过滤
        response = api_client.get(f"/api/executions?testcase_id={testcase2.id}")
        data = assert_api_response(response, 200)

        assert data["total"] == 1
        assert data["items"][0]["test_case_id"] == testcase2.id

    def test_should_order_by_created_at_desc(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试按创建时间倒序排列"""
        # 创建执行记录，确保时间不同
        execution1 = create_execution_history(status="success")
        execution2 = create_execution_history(status="failed")

        response = api_client.get("/api/executions")
        data = assert_api_response(response, 200)

        items = data["items"]
        assert len(items) == 2

        # 第一个应该是最新创建的
        assert items[0]["execution_id"] == execution2.execution_id
        assert items[1]["execution_id"] == execution1.execution_id


class TestDeleteExecutionAPI:
    """删除执行报告API测试 (DELETE /api/executions/<execution_id>)"""

    def test_should_delete_execution(
        self, api_client, create_execution_history, db_session, assert_api_response
    ):
        """测试删除执行记录"""
        execution = create_execution_history(status="success")
        execution_id = execution.execution_id

        response = api_client.delete(f"/api/executions/{execution_id}")
        assert_api_response(response, 200)

        # 验证记录已被删除
        from backend.models import ExecutionHistory

        deleted_execution = ExecutionHistory.query.filter_by(
            execution_id=execution_id
        ).first()
        assert deleted_execution is None

    def test_should_delete_execution_with_step_executions(
        self,
        api_client,
        create_execution_history,
        create_step_execution,
        db_session,
        assert_api_response,
    ):
        """测试删除包含步骤执行的执行记录"""
        execution = create_execution_history(status="success")
        step_execution = create_step_execution(execution_id=execution.execution_id)

        response = api_client.delete(f"/api/executions/{execution.execution_id}")
        assert_api_response(response, 200)

        # 验证执行记录和步骤执行都被删除
        from backend.models import ExecutionHistory, StepExecution

        deleted_execution = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).first()
        assert deleted_execution is None

        deleted_step = StepExecution.query.filter_by(
            execution_id=execution.execution_id
        ).first()
        assert deleted_step is None

    def test_should_return_404_for_nonexistent_execution(
        self, api_client, assert_api_response
    ):
        """测试删除不存在的执行记录返回404"""
        response = api_client.delete("/api/executions/nonexistent-id")
        assert_api_response(response, 404)


class TestExportExecutionAPI:
    """导出执行报告API测试"""

    def test_should_export_single_execution_report(
        self, api_client, create_execution_history
    ):
        """测试导出单个执行报告"""
        execution = create_execution_history(
            status="success",
            result_summary='{"total_steps": 3, "passed": 2, "failed": 1}',
        )

        response = api_client.get(f"/api/executions/{execution.execution_id}/export")
        assert response.status_code == 200

        # 验证导出数据包含执行信息（API直接返回报告数据）
        export_data = response.get_json()
        assert export_data["execution_id"] == execution.execution_id
        assert export_data["status"] == "success"
        assert "exported_at" in export_data

    def test_should_export_execution_with_step_details(
        self, api_client, create_execution_history, create_step_execution
    ):
        """测试导出包含步骤详情的执行报告"""
        execution = create_execution_history(status="success")
        step_execution = create_step_execution(
            execution_id=execution.execution_id,
            step_description="测试步骤",
            status="success",
        )

        response = api_client.get(f"/api/executions/{execution.execution_id}/export")
        assert response.status_code == 200

        export_data = response.get_json()
        assert "step_executions" in export_data
        assert len(export_data["step_executions"]) == 1
        assert export_data["step_executions"][0]["step_description"] == "测试步骤"

    def test_should_return_404_for_nonexistent_execution_export(
        self, api_client, assert_api_response
    ):
        """测试导出不存在的执行报告返回404"""
        response = api_client.get("/api/executions/nonexistent-id/export")
        assert_api_response(response, 404)

    def test_should_export_all_executions(self, api_client, create_execution_history):
        """测试导出所有执行报告"""
        # 创建多个执行记录
        execution1 = create_execution_history(status="success")
        execution2 = create_execution_history(status="failed")

        response = api_client.get("/api/executions/export-all")
        assert response.status_code == 200

        # 验证导出数据包含所有执行
        export_data = response.get_json()
        assert "reports" in export_data
        assert len(export_data["reports"]) == 2
        assert "exported_at" in export_data

        execution_ids = [exec["execution_id"] for exec in export_data["reports"]]
        assert execution1.execution_id in execution_ids
        assert execution2.execution_id in execution_ids

    def test_should_support_pagination_in_export_all(
        self, api_client, create_execution_history
    ):
        """测试导出所有报告的分页功能"""
        # 创建多个执行记录
        for i in range(5):
            create_execution_history(status="success")

        # 测试分页导出
        response = api_client.get("/api/executions/export-all?page=1&size=2")
        assert response.status_code == 200

        export_data = response.get_json()
        assert len(export_data["reports"]) == 2
        assert export_data["total_reports"] == 2  # 当前页的报告数量
        assert export_data["page"] == 1
        assert export_data["size"] == 2


class TestRetiredMidSceneRoutes:
    def test_legacy_callbacks_are_404_without_durable_writes(
        self, api_client, create_test_testcase
    ):
        from backend.models import ExecutionHistory

        testcase = create_test_testcase(name="retired MidScene")
        payload = {
            "execution_id": "retired-midscene-write",
            "testcase_id": testcase.id,
            "mode": "headless",
            "status": "success",
        }

        for path in (
            "/api/midscene/execution-start",
            "/api/midscene/execution-result",
        ):
            assert api_client.post(path, json=payload).status_code == 404

        assert (
            ExecutionHistory.query.filter_by(
                execution_id="retired-midscene-write"
            ).first()
            is None
        )


@pytest.mark.usefixtures("proxy_execution_client")
class TestStopExecutionAPI:
    """停止执行API测试 (POST /api/executions/<execution_id>/stop)"""

    def test_should_stop_pending_execution(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试停止pending状态的执行"""
        execution = create_execution_history(
            status="pending", end_time=None, duration=None
        )

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop",
            json={},
        )

        data = assert_api_response(response, 200)

        assert data["status"] == "stopped"
        assert data["error_message"] == "用户手动停止执行"

    def test_should_stop_running_execution(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试停止running状态的执行"""
        execution = create_execution_history(
            status="running", end_time=None, duration=None
        )

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop",
            json={},
        )

        data = assert_api_response(response, 200)

        assert data["status"] == "stopped"
        assert data["end_time"] is not None

    def test_should_return_400_for_completed_execution(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试停止已完成的执行返回400"""
        execution = create_execution_history(status="success")

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop",
            json={},
        )

        assert_api_response(response, 400)

    def test_should_return_400_for_failed_execution(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试停止已失败的执行返回400"""
        execution = create_execution_history(status="failed")

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop",
            json={},
        )

        assert_api_response(response, 400)

    def test_should_return_400_for_already_stopped_execution(
        self, api_client, create_execution_history, assert_api_response
    ):
        """测试停止已停止的执行返回400"""
        execution = create_execution_history(status="stopped")

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop",
            json={},
        )

        assert_api_response(response, 400)

    def test_should_return_404_for_nonexistent_execution(
        self, api_client, assert_api_response
    ):
        """测试停止不存在的执行返回404"""
        response = api_client.post(
            "/api/executions/nonexistent-execution-id/stop",
            json={},
        )

        assert_api_response(response, 404)

    def test_should_update_execution_end_time(
        self, api_client, create_execution_history, db_session, assert_api_response
    ):
        """测试停止执行后end_time被正确设置"""
        from backend.models import ExecutionHistory

        execution = create_execution_history(
            status="running", end_time=None, duration=None
        )

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop",
            json={},
        )

        assert_api_response(response, 200)

        # 验证数据库中的end_time已更新
        updated_execution = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).first()

        assert updated_execution.end_time is not None
        assert updated_execution.status == "stopped"

    def test_should_stop_only_the_same_canonical_execution_id(
        self,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
    ):
        execution = create_execution_history(status="running", end_time=None)

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop", json={}
        )

        assert_api_response(response, 200)
        assert proxy_execution_client.stopped_execution_ids == [
            execution.execution_id
        ]

    @pytest.mark.parametrize("initial_status", ["pending", "running"])
    def test_should_preserve_status_when_proxy_stop_is_rejected(
        self,
        app,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
        initial_status,
        monkeypatch,
    ):
        from backend.models import ExecutionHistory

        execution = create_execution_history(
            status=initial_status,
            end_time=None,
            error_message="existing execution diagnostic",
        )
        upstream_secret = "proxy stop unavailable secret=do-not-leak"
        proxy_execution_client.stop_error = upstream_secret
        logged_messages = []

        def record_warning(message, *args, **_kwargs):
            logged_messages.append(message % args)

        monkeypatch.setattr(app.logger, "warning", record_warning)

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop", json={}
        )

        error = assert_api_response(response, 502)
        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert persisted.status == initial_status
        assert persisted.end_time is None
        assert persisted.error_message == "existing execution diagnostic"
        assert proxy_execution_client.stopped_execution_ids == [
            execution.execution_id
        ]
        assert error["data"]["execution_id"] == execution.execution_id
        assert error["message"] == "停止执行失败"
        assert upstream_secret not in response.get_data(as_text=True)
        assert any(execution.execution_id in message for message in logged_messages)
        assert all(upstream_secret not in message for message in logged_messages)

    def test_should_return_sanitized_500_for_unexpected_stop_adapter_error(
        self,
        app,
        api_client,
        create_execution_history,
        proxy_execution_client,
        assert_api_response,
        monkeypatch,
    ):
        from backend.models import ExecutionHistory

        execution = create_execution_history(
            status="running",
            end_time=None,
            error_message="existing execution diagnostic",
        )
        logged_messages = []

        def record_error(message, *args, **_kwargs):
            logged_messages.append(message % args)

        def reject_traceback_logging(*_args, **_kwargs):
            raise AssertionError("unexpected exception traceback logging")

        monkeypatch.setattr(app.logger, "error", record_error)
        monkeypatch.setattr(app.logger, "exception", reject_traceback_logging)

        def raise_unexpected_error(_execution_id):
            raise RuntimeError("stop crashed with secret=do-not-leak")

        proxy_execution_client.stop_execution = raise_unexpected_error

        response = api_client.post(
            f"/api/executions/{execution.execution_id}/stop", json={}
        )

        error = assert_api_response(response, 500)
        persisted = ExecutionHistory.query.filter_by(
            execution_id=execution.execution_id
        ).one()
        assert persisted.status == "running"
        assert persisted.end_time is None
        assert persisted.error_message == "existing execution diagnostic"
        assert error == {
            "code": 500,
            "message": "停止执行失败",
            "data": {"execution_id": execution.execution_id},
        }
        assert "do-not-leak" not in response.get_data(as_text=True)
        assert logged_messages == [
            "停止执行失败: "
            f"execution_id={execution.execution_id} "
            "error_code=unexpected_execution_error"
        ]
