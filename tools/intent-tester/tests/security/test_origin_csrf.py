from __future__ import annotations

import re

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

from backend.intent_security import install_intent_security
from backend.models import ExecutionHistory, TestCase as CaseModel
from intent_test_config import intent_test_config


ORIGIN = "http://127.0.0.1:5001"


def _login_csrf(client) -> str:
    response = client.get("/intent-tester/login")
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert response.status_code == 200
    assert match is not None
    return match.group(1)


def _error_code(response) -> str:
    return response.get_json()["error"]["code"]


@pytest.mark.parametrize("origin", [None, "https://foreign.example", "null"])
def test_login_rejects_missing_foreign_and_null_origin(anonymous_client, origin):
    csrf = _login_csrf(anonymous_client)
    headers = {} if origin is None else {"Origin": origin}

    response = anonymous_client.post(
        "/intent-tester/login",
        data={"username": "admin", "password": "test-admin-password", "csrf_token": csrf},
        headers=headers,
    )

    assert response.status_code == 403
    assert _error_code(response) == "ORIGIN_REJECTED"
    assert "127.0.0.1" not in response.get_data(as_text=True)


@pytest.mark.parametrize("csrf", [None, "wrong-csrf-token"])
def test_login_rejects_missing_or_wrong_pre_auth_csrf(anonymous_client, csrf):
    _login_csrf(anonymous_client)
    data = {"username": "admin", "password": "test-admin-password"}
    if csrf is not None:
        data["csrf_token"] = csrf

    response = anonymous_client.post(
        "/intent-tester/login", data=data, headers={"Origin": ORIGIN}
    )

    assert response.status_code == 403
    assert _error_code(response) == "CSRF_FAILED"


@pytest.mark.parametrize(
    ("username", "password"),
    [("unknown", "test-admin-password"), ("admin", "wrong-password")],
)
def test_login_uses_one_failure_for_unknown_user_and_wrong_password(
    anonymous_client, username, password
):
    csrf = _login_csrf(anonymous_client)

    response = anonymous_client.post(
        "/intent-tester/login",
        data={"username": username, "password": password, "csrf_token": csrf},
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 401
    assert "Invalid username or password" in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("next_value", "expected_location"),
    [
        ("/intent-tester/execution", "/intent-tester/execution"),
        (
            "/intent-tester/testcases?category=security",
            "/intent-tester/testcases?category=security",
        ),
        ("https://attacker.example/steal", "/intent-tester/testcases"),
        ("//attacker.example/steal", "/intent-tester/testcases"),
        ("/not-intent-tester", "/intent-tester/testcases"),
        ("/intent-tester.evil/steal", "/intent-tester/testcases"),
    ],
)
def test_login_redirects_only_to_safe_scoped_relative_next(
    anonymous_client, next_value, expected_location
):
    csrf = _login_csrf(anonymous_client)

    response = anonymous_client.post(
        "/intent-tester/login",
        query_string={"next": next_value},
        data={"username": "admin", "password": "test-admin-password", "csrf_token": csrf},
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == expected_location


def test_login_clears_fixated_session_and_rotates_csrf(anonymous_client):
    old_csrf = _login_csrf(anonymous_client)
    with anonymous_client.session_transaction() as current:
        current["attacker_seed"] = "must disappear"

    response = anonymous_client.post(
        "/intent-tester/login",
        data={
            "username": "admin",
            "password": "test-admin-password",
            "csrf_token": old_csrf,
        },
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 302
    with anonymous_client.session_transaction() as current:
        assert current["intent_principal"] == "admin"
        assert current["csrf_token"] != old_csrf
        assert "attacker_seed" not in current


def test_logout_is_post_only_and_clears_principal_with_csrf_rotation(operator_client):
    get_response = operator_client.get("/intent-tester/logout")
    assert get_response.status_code == 405
    with operator_client.session_transaction() as current:
        old_csrf = current["csrf_token"]

    post_response = operator_client.post("/intent-tester/logout")

    assert post_response.status_code == 302
    with operator_client.session_transaction() as current:
        assert "intent_principal" not in current
        assert current["csrf_token"] != old_csrf


@pytest.mark.parametrize(
    ("origin", "csrf_mode", "expected"),
    [
        (None, "valid", "ORIGIN_REJECTED"),
        ("https://foreign.example", "valid", "ORIGIN_REJECTED"),
        ("null", "valid", "ORIGIN_REJECTED"),
        (ORIGIN, "missing", "CSRF_FAILED"),
        (ORIGIN, "wrong", "CSRF_FAILED"),
    ],
)
def test_unsafe_operator_request_rejects_origin_or_csrf_without_writing(
    operator_client, origin, csrf_mode, expected
):
    with operator_client.session_transaction() as current:
        valid_csrf = current["csrf_token"]
    saved_origin = operator_client.environ_base.pop("HTTP_ORIGIN", None)
    saved_csrf = operator_client.environ_base.pop("HTTP_X_CSRF_TOKEN", None)
    headers = {}
    if origin is not None:
        headers["Origin"] = origin
    if csrf_mode == "valid":
        headers["X-CSRF-Token"] = valid_csrf
    elif csrf_mode == "wrong":
        headers["X-CSRF-Token"] = "wrong-csrf-token"
    try:
        response = operator_client.post(
            "/intent-tester/api/testcases",
            json={"name": "must not exist", "steps": []},
            headers=headers,
        )
    finally:
        if saved_origin is not None:
            operator_client.environ_base["HTTP_ORIGIN"] = saved_origin
        if saved_csrf is not None:
            operator_client.environ_base["HTTP_X_CSRF_TOKEN"] = saved_csrf

    assert response.status_code == 403
    assert _error_code(response) == expected
    with operator_client.application.app_context():
        assert CaseModel.query.count() == 0


def test_client_created_by_is_ignored_in_favor_of_operator_principal(operator_client):
    response = operator_client.post(
        "/intent-tester/api/testcases",
        json={
            "name": "principal audit",
            "steps": [],
            "created_by": "forged-client",
        },
    )

    assert response.status_code == 200
    with operator_client.application.app_context():
        testcase = CaseModel.query.one()
        assert testcase.created_by == "admin"


def test_client_executed_by_is_ignored_in_favor_of_operator_principal(
    app, operator_client, create_test_testcase
):
    class AcceptingProxy:
        def dispatch_execution(self, payload):
            return {"success": True, "executionId": payload["executionId"]}

    app.config["PROXY_EXECUTION_CLIENT"] = AcceptingProxy()
    testcase = create_test_testcase(name="execution audit")

    response = operator_client.post(
        "/intent-tester/api/executions",
        json={"testcase_id": testcase.id, "executed_by": "forged-client"},
    )

    assert response.status_code == 200
    with app.app_context():
        execution = ExecutionHistory.query.one()
        assert execution.executed_by == "admin"


def test_local_dev_principal_is_fixed_and_audits_mutation():
    from backend.app import create_app

    app = create_app(intent_test_config(INTENT_ACCESS_MODE="local-dev"))
    client = app.test_client()
    client.get("/intent-tester/testcases")
    with client.session_transaction() as current:
        csrf = current["csrf_token"]

    response = client.post(
        "/intent-tester/api/testcases",
        json={"name": "local audit", "steps": [], "created_by": "forged"},
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
    )

    assert response.status_code == 200
    with app.app_context():
        assert CaseModel.query.one().created_by == "local-dev"


def test_proxy_bearer_sets_fixed_proxy_principal(app):
    from backend.intent_security import current_intent_principal, require_proxy_bearer

    with app.test_request_context(
        "/intent-tester/api/executions/x/lifecycle",
        method="POST",
        headers={"Authorization": "Bearer test-proxy-token-with-at-least-32b"},
    ):
        assert require_proxy_bearer() is None
        assert current_intent_principal().name == "proxy"


def test_production_session_cookie_flags_are_secure():
    app = Flask(__name__)
    app.config.update(
        {
            "AI4SE_ENV": "production",
            "INTENT_ACCESS_MODE": "restricted",
            "INTENT_EXECUTION_ENABLED": False,
            "INTENT_PUBLIC_ORIGIN": "https://intent.example",
            "SECRET_KEY": "production-secret-with-at-least-32-bytes",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH": generate_password_hash("password"),
            "SQLALCHEMY_DATABASE_URI": "postgresql://intent:password@db/intent",
        }
    )

    install_intent_security(app)

    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
