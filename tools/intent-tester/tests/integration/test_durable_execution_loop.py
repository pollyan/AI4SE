"""Real-loopback durable execution recovery against the production Node app.

This L3 test fakes only Playwright and the MidScene adapter. Flask, SQLite,
requests, Express routes, axios callbacks, and the Node execution runtime are
all exercised over real HTTP sockets.
"""

import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

import requests
from werkzeug.serving import make_server

from backend.app import create_app
from backend.models import db, ExecutionHistory, StepExecution


HERE = Path(__file__).resolve().parent
INTENT_TESTER_ROOT = HERE.parents[1]
NODE_FIXTURE = HERE / "durable_execution_node_fixture.js"
PRODUCTION_NODE_SERVER = (
    INTENT_TESTER_ROOT / "browser-automation" / "midscene_server.js"
)


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


def _get_execution(flask_base_url, execution_id):
    response = requests.get(
        _execution_url(flask_base_url, execution_id), timeout=1
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["code"] == 200
    return payload["data"]


def _wait_for_execution_status(flask_base_url, execution_id, expected_status):
    return _wait_until(
        lambda: (
            execution
            if (execution := _get_execution(flask_base_url, execution_id))["status"]
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
            "BLOCKED_NAVIGATION_MS": "1200",
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
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "MIDSCENE_SERVER_URL": f"http://127.0.0.1:{node_port}",
            "MIDSCENE_API_TIMEOUT": 1,
        }
    )


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

    try:
        create_response = requests.post(
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

        retry_response = requests.post(
            _execution_url(flask_server.base_url, canonical_id, "/retry"),
            timeout=3,
        )
        assert retry_response.status_code == 200, retry_response.text
        assert retry_response.json()["data"]["execution_id"] == canonical_id

        succeeded = _wait_for_execution_status(
            flask_server.base_url, canonical_id, "success"
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

        reconcile_response = requests.post(
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
            timeout=1,
        )
        assert duplicate_result.status_code == 200, duplicate_result.text
        assert duplicate_result.json()["data"]["idempotent"] is True
        with app.app_context():
            assert ExecutionHistory.query.count() == 1
            assert StepExecution.query.filter_by(execution_id=canonical_id).count() == 1

        blocked_create = requests.post(
            f"{flask_server.base_url}/intent-tester/api/executions",
            json={"testcase_id": blocked_testcase_id, "mode": "headless"},
            timeout=3,
        )
        assert blocked_create.status_code == 200, blocked_create.text
        blocked_id = blocked_create.json()["data"]["execution_id"]
        _wait_for_execution_status(flask_server.base_url, blocked_id, "running")

        stop_response = requests.post(
            _execution_url(flask_server.base_url, blocked_id, "/stop"), timeout=3
        )
        assert stop_response.status_code == 200, stop_response.text
        assert stop_response.json()["data"]["execution_id"] == blocked_id
        assert stop_response.json()["data"]["status"] == "stopped"
        assert _get_execution(flask_server.base_url, canonical_id)["status"] == "success"
        _wait_for_execution_status(flask_server.base_url, blocked_id, "stopped")
        _wait_until(
            lambda: requests.get(
                f"http://127.0.0.1:{node_port}/api/status", timeout=0.5
            ).json()["status"]
            == "ready",
            timeout=5,
            description="Node runtime to release the stopped execution",
        )

        flask_server.close()
        restarted_app = _new_app(database_path, node_port)
        flask_server = LiveFlaskServer(restarted_app).start()

        restarted_success = _get_execution(flask_server.base_url, canonical_id)
        restarted_stopped = _get_execution(flask_server.base_url, blocked_id)
        assert restarted_success["status"] == "success"
        assert len(restarted_success["step_executions"]) == 1
        assert restarted_stopped["status"] == "stopped"
        with restarted_app.app_context():
            assert ExecutionHistory.query.count() == 2
            assert StepExecution.query.filter_by(execution_id=canonical_id).count() == 1
    finally:
        flask_server.close()
        if node_process is not None and node_log_file is not None:
            _stop_node(node_process, node_log_file)
