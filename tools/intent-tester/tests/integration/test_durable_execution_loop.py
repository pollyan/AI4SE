"""Real-loopback durable execution recovery against the production Node app.

This L3 test fakes only Playwright and the MidScene adapter. Flask, SQLite,
requests, Express routes, axios callbacks, and the Node execution runtime are
all exercised over real HTTP sockets.
"""

import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time

import requests
import socketio
from werkzeug.serving import make_server

from backend.app import create_app
from backend.models import db, ExecutionHistory, StepExecution


HERE = Path(__file__).resolve().parent
INTENT_TESTER_ROOT = HERE.parents[1]
NODE_FIXTURE = HERE / "durable_execution_node_fixture.js"
PRODUCTION_NODE_SERVER = (
    INTENT_TESTER_ROOT / "browser-automation" / "midscene_server.js"
)
TEST_PUBLIC_ORIGIN = "http://127.0.0.1:5001"
TEST_PROXY_TOKEN = "integration-proxy-token-with-at-least-32-bytes"


class LiveFlaskServer:
    def __init__(self, app):
        self.app = app
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.closed = False

    def start(self):
        self.thread.start()
        _wait_until(
            lambda: requests.get(f"{self.base_url}/health", timeout=0.5).ok,
            description="Flask health endpoint",
        )
        return self

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        assert not self.thread.is_alive(), "Flask server thread did not stop"


def _unused_loopback_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _wait_until(probe, *, timeout=8, interval=0.05, description):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = probe()
            if result:
                return result
        except (AssertionError, requests.RequestException) as error:
            last_error = error
        time.sleep(interval)
    detail = f"; last error: {last_error}" if last_error else ""
    raise AssertionError(f"Timed out waiting for {description}{detail}")


def _execution_url(flask_base_url, execution_id, suffix=""):
    return (
        f"{flask_base_url}/intent-tester/api/executions/"
        f"{execution_id}{suffix}"
    )


def _get_execution(flask_base_url, execution_id, client=requests):
    response = client.get(
        _execution_url(flask_base_url, execution_id), timeout=1
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    return payload["data"]


def _wait_for_execution_status(
    flask_base_url, execution_id, expected_status, client=requests
):
    return _wait_until(
        lambda: (
            execution
            if (execution := _get_execution(flask_base_url, execution_id, client))["status"]
            == expected_status
            else None
        ),
        description=f"execution {execution_id} to become {expected_status}",
    )


def _start_node(node_port, flask_base_url, log_path):
    assert NODE_FIXTURE.exists(), f"missing Node adapter fixture: {NODE_FIXTURE}"
    environment = os.environ.copy()
    environment.update(
        {
            "OPENAI_API_KEY": "offline-test-key",
            "OPENAI_BASE_URL": "http://127.0.0.1/unused-provider",
            "MIDSCENE_MODEL_NAME": "offline-fake-model",
            "MAIN_APP_URL": f"{flask_base_url}/intent-tester/api",
            "PORT": str(node_port),
            "BLOCKED_NAVIGATION_MS": "2200",
            "INTENT_PROXY_TOPOLOGY": "local-host",
            "INTENT_PROXY_TOKEN": TEST_PROXY_TOKEN,
            "INTENT_PUBLIC_ORIGIN": TEST_PUBLIC_ORIGIN,
        }
    )
    log_file = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            "node",
            str(NODE_FIXTURE),
            str(PRODUCTION_NODE_SERVER),
            str(node_port),
        ],
        cwd=INTENT_TESTER_ROOT,
        env=environment,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_until(
            lambda: requests.get(
                f"http://127.0.0.1:{node_port}/health", timeout=0.5
            ).ok,
            description="production Node health endpoint",
        )
    except Exception:
        process.terminate()
        process.wait(timeout=5)
        log_file.close()
        raise AssertionError(log_path.read_text(encoding="utf-8"))
    return process, log_file


def _stop_node(process, log_file):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    log_file.close()


def _new_app(database_path, node_port):
    return create_app(
        {
            "TESTING": False,
            "AI4SE_ENV": "test",
            "INTENT_ACCESS_MODE": "local-dev",
            "INTENT_EXECUTION_ENABLED": True,
            "INTENT_PUBLIC_ORIGIN": TEST_PUBLIC_ORIGIN,
            "INTENT_PROXY_TOPOLOGY": "local-host",
            "INTENT_PROXY_TOKEN": TEST_PROXY_TOKEN,
            "SECRET_KEY": "integration-secret-key-with-at-least-32-bytes",
            "OPENAI_API_KEY": "offline-test-key",
            "OPENAI_BASE_URL": "http://127.0.0.1/unused-provider",
            "MIDSCENE_MODEL_NAME": "offline-fake-model",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "MIDSCENE_SERVER_URL": f"http://127.0.0.1:{node_port}",
            "MIDSCENE_API_TIMEOUT": 1,
        }
    )


def _local_dev_session(flask_base_url):
    client = requests.Session()
    page = client.get(f"{flask_base_url}/intent-tester/execution", timeout=2)
    assert page.status_code == 200, page.text
    match = re.search(
        r'<meta name="intent-csrf-token" content="([^"]+)"', page.text
    )
    assert match, "execution page did not expose its CSRF meta token"
    client.headers.update(
        {
            "Origin": TEST_PUBLIC_ORIGIN,
            "X-CSRF-Token": match.group(1),
        }
    )
    return client


def _seed_testcases(app):
    from backend.models import TestCase

    with app.app_context():
        fast = TestCase(
            name="real-http-fast",
            steps=json.dumps(
                [
                    {
                        "action": "navigate",
                        "description": "fast navigation",
                        "params": {"url": "http://fixture.invalid/fast"},
                    }
                ]
            ),
            is_active=True,
        )
        blocked = TestCase(
            name="real-http-blocked",
            steps=json.dumps(
                [
                    {
                        "action": "navigate",
                        "description": "progress before block",
                        "params": {"url": "http://fixture.invalid/fast"},
                    },
                    {
                        "action": "navigate",
                        "description": "blocked navigation",
                        "params": {"url": "http://fixture.invalid/blocked"},
                    }
                ]
            ),
            is_active=True,
        )
        db.session.add_all([fast, blocked])
        db.session.commit()
        return fast.id, blocked.id


def test_real_http_retry_callbacks_stop_and_restart_are_one_durable_loop(tmp_path):
    database_path = tmp_path / "durable-loop.sqlite"
    node_log = tmp_path / "production-node.log"
    node_port = _unused_loopback_port()
    app = _new_app(database_path, node_port)
    fast_testcase_id, blocked_testcase_id = _seed_testcases(app)
    flask_server = LiveFlaskServer(app).start()
    node_process = None
    node_log_file = None
    socket_client = socketio.Client(reconnection=False)

    try:
        client = _local_dev_session(flask_server.base_url)
        create_response = client.post(
            f"{flask_server.base_url}/intent-tester/api/executions",
            json={"testcase_id": fast_testcase_id, "mode": "headless"},
            timeout=3,
        )
        assert create_response.status_code == 502
        create_payload = create_response.json()
        canonical_id = create_payload["data"]["execution_id"]

        with app.app_context():
            persisted = ExecutionHistory.query.all()
            assert len(persisted) == 1
            assert persisted[0].execution_id == canonical_id
            assert persisted[0].status == "pending"

        node_process, node_log_file = _start_node(
            node_port, flask_server.base_url, node_log
        )

        ticket_response = client.post(
            _execution_url(flask_server.base_url, canonical_id, "/proxy-ticket"),
            timeout=3,
        )
        assert ticket_response.status_code == 200, ticket_response.text
        ticket = ticket_response.json()["data"]["ticket"]
        socket_client.connect(
            f"http://127.0.0.1:{node_port}",
            auth={"ticket": ticket, "executionId": canonical_id},
            headers={"Origin": TEST_PUBLIC_ORIGIN},
            transports=["polling"],
            wait_timeout=3,
        )
        assert socket_client.connected
        socket_client.disconnect()

        retry_response = client.post(
            _execution_url(flask_server.base_url, canonical_id, "/retry"),
            timeout=3,
        )
        assert retry_response.status_code == 200, retry_response.text
        assert retry_response.json()["data"]["execution_id"] == canonical_id

        succeeded = _wait_for_execution_status(
            flask_server.base_url, canonical_id, "success", client
        )
        assert len(succeeded["step_executions"]) == 1

        # Failure injection: model a lifecycle callback that was missed after Node
        # reached a terminal state.  Reconciliation must pull the production Node
        # status over HTTP and restore the same durable Flask record.
        with app.app_context():
            execution = ExecutionHistory.query.filter_by(
                execution_id=canonical_id
            ).one()
            StepExecution.query.filter_by(execution_id=canonical_id).delete()
            execution.status = "pending"
            execution.end_time = None
            execution.duration = None
            execution.steps_passed = None
            execution.steps_failed = None
            execution.result_summary = json.dumps(
                {
                    "diagnostics": [
                        {
                            "code": "lifecycle_callback_exhausted",
                            "message": "执行生命周期回调重试已耗尽，需要状态协调恢复",
                        }
                    ]
                }
            )
            execution.error_message = (
                "执行生命周期回调重试已耗尽，需要状态协调恢复"
            )
            db.session.commit()

        reconcile_response = client.post(
            _execution_url(flask_server.base_url, canonical_id, "/reconcile"),
            timeout=3,
        )
        assert reconcile_response.status_code == 200, reconcile_response.text
        reconciled = reconcile_response.json()["data"]
        assert reconciled["execution_id"] == canonical_id
        assert reconciled["status"] == "success"
        assert reconciled["error_message"] is None
        assert reconciled["result_summary"] == {}
        assert len(reconciled["step_executions"]) == 1

        duplicate_result = requests.post(
            _execution_url(flask_server.base_url, canonical_id, "/lifecycle"),
            json={
                "event": "result",
                "status": "success",
                "steps": [
                    {
                        "index": 0,
                        "description": "fast navigation",
                        "status": "success",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {TEST_PROXY_TOKEN}"},
            timeout=1,
        )
        assert duplicate_result.status_code == 200, duplicate_result.text
        assert duplicate_result.json()["data"]["idempotent"] is True
        with app.app_context():
            assert ExecutionHistory.query.count() == 1
            assert StepExecution.query.filter_by(execution_id=canonical_id).count() == 1

        blocked_create = client.post(
            f"{flask_server.base_url}/intent-tester/api/executions",
            json={"testcase_id": blocked_testcase_id, "mode": "headless"},
            timeout=3,
        )
        assert blocked_create.status_code == 200, blocked_create.text
        blocked_id = blocked_create.json()["data"]["execution_id"]
        _wait_for_execution_status(
            flask_server.base_url, blocked_id, "running", client
        )

        def reconcile_running_progress():
            response = client.post(
                _execution_url(flask_server.base_url, blocked_id, "/reconcile"),
                timeout=1,
            )
            assert response.status_code == 200, response.text
            execution = response.json()["data"]
            if execution["status"] != "running" or not execution["step_executions"]:
                return None
            return execution

        active_progress = _wait_until(
            reconcile_running_progress,
            timeout=5,
            description="running step progress to persist through Flask",
        )
        assert active_progress["execution_id"] == blocked_id
        assert active_progress["step_executions"][0]["step_description"] == (
            "progress before block"
        )
        assert active_progress["step_executions"][0]["screenshot_path"] is None
        assert active_progress["step_executions"][0]["error_message"] is None

        stop_response = client.post(
            _execution_url(flask_server.base_url, blocked_id, "/stop"), timeout=3
        )
        assert stop_response.status_code == 200, stop_response.text
        assert stop_response.json()["data"]["execution_id"] == blocked_id
        assert stop_response.json()["data"]["status"] == "stopped"
        assert _get_execution(
            flask_server.base_url, canonical_id, client
        )["status"] == "success"
        _wait_for_execution_status(
            flask_server.base_url, blocked_id, "stopped", client
        )
        _wait_until(
            lambda: requests.get(
                f"http://127.0.0.1:{node_port}/api/status",
                headers={"Authorization": f"Bearer {TEST_PROXY_TOKEN}"},
                timeout=0.5,
            ).json()["status"]
            == "ready",
            timeout=5,
            description="Node runtime to release the stopped execution",
        )

        flask_server.close()
        restarted_app = _new_app(database_path, node_port)
        flask_server = LiveFlaskServer(restarted_app).start()

        restarted_success = _get_execution(
            flask_server.base_url, canonical_id, client
        )
        restarted_stopped = _get_execution(
            flask_server.base_url, blocked_id, client
        )
        assert restarted_success["status"] == "success"
        assert len(restarted_success["step_executions"]) == 1
        assert restarted_stopped["status"] == "stopped"
        with restarted_app.app_context():
            assert ExecutionHistory.query.count() == 2
            assert StepExecution.query.filter_by(execution_id=canonical_id).count() == 1
    finally:
        if socket_client.connected:
            socket_client.disconnect()
        flask_server.close()
        if node_process is not None and node_log_file is not None:
            _stop_node(node_process, node_log_file)
