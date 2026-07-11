from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime

import pytest
from flask import template_rendered

from backend.app import create_app
from backend.models import ExecutionHistory, TestCase as CaseModel, db
from intent_test_config import intent_test_config


EXPECTED_POLICIES = {
    "public": {
        "static",
        "health_check",
        "root_redirect",
        "views.index",
        "views.login",
    },
    "public-readonly": {
        "views.testcases",
        "views.local_proxy",
        "testcases.get_testcases",
        "proxy.proxy_version",
        "proxy.download_proxy",
    },
    "proxy-machine": {"executions.record_execution_lifecycle"},
}
IGNORE_EXISTING_UTCNOW_WARNING = pytest.mark.filterwarnings(
    r"ignore:datetime\.datetime\.utcnow\(\) is deprecated.*:DeprecationWarning"
)


def _operator_endpoints(app) -> set[str]:
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    fixed = set().union(*EXPECTED_POLICIES.values())
    return endpoints - fixed


def _error_code(response) -> str:
    return response.get_json()["error"]["code"]


def _seed_testcase(app, *, created_by: str = "admin") -> int:
    with app.app_context():
        testcase = CaseModel(
            name="Policy testcase",
            description="policy",
            steps="[]",
            category="security",
            priority=1,
            tags="security",
            created_by=created_by,
        )
        db.session.add(testcase)
        db.session.commit()
        return testcase.id


def _login_operator(client) -> str:
    page = client.get("/intent-tester/login")
    csrf = page.get_data(as_text=True).split(
        'name="csrf_token" value="', 1
    )[1].split('"', 1)[0]
    response = client.post(
        "/intent-tester/login",
        data={
            "username": "admin",
            "password": "test-admin-password",
            "csrf_token": csrf,
        },
        headers={"Origin": "http://127.0.0.1:5001"},
    )
    assert response.status_code == 302
    with client.session_transaction() as current:
        csrf = current["csrf_token"]
        assert current["intent_principal"] == "admin"
    client.environ_base["HTTP_ORIGIN"] = "http://127.0.0.1:5001"
    client.environ_base["HTTP_X_CSRF_TOKEN"] = csrf
    return csrf


@pytest.fixture
def public_readonly_app():
    app = create_app(intent_test_config(INTENT_ACCESS_MODE="public-readonly"))
    with app.app_context():
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def public_readonly_operator(public_readonly_app):
    client = public_readonly_app.test_client()
    _login_operator(client)
    return client


def test_every_routed_endpoint_has_exactly_one_policy(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    policies = app.extensions["intent_security"].route_policies

    assert endpoints == set(policies)
    for endpoint, policy in policies.items():
        assert policy.value in {
            "public",
            "public-readonly",
            "operator",
            "proxy-machine",
        }, endpoint


def test_route_policy_registry_matches_the_required_mechanical_matrix(app):
    policies = app.extensions["intent_security"].route_policies
    projected = {
        value: {endpoint for endpoint, policy in policies.items() if policy.value == value}
        for value in ("public", "public-readonly", "operator", "proxy-machine")
    }

    assert projected["public"] == EXPECTED_POLICIES["public"]
    assert projected["public-readonly"] == EXPECTED_POLICIES["public-readonly"]
    assert projected["proxy-machine"] == EXPECTED_POLICIES["proxy-machine"]
    assert projected["operator"] == _operator_endpoints(app)
    assert "executions.issue_proxy_ticket" in projected["operator"]


def test_unclassified_route_fails_installation_before_database_init():
    from flask import Flask
    from backend.intent_security import install_intent_security

    unclassified = Flask(__name__)
    unclassified.config.update(intent_test_config())

    @unclassified.get("/forgotten")
    def forgotten():
        return "forgotten"

    with pytest.raises(ValueError, match="forgotten"):
        install_intent_security(unclassified)


def test_restricted_anonymous_operator_page_redirects_to_scoped_login(
    anonymous_client,
):
    response = anonymous_client.get("/intent-tester/testcases/create")

    assert response.status_code == 302
    assert response.headers["Location"].startswith(
        "/intent-tester/login?next=%2Fintent-tester%2Ftestcases%2Fcreate"
    )


def test_restricted_anonymous_operator_api_is_stable_401(anonymous_client):
    response = anonymous_client.post(
        "/intent-tester/api/testcases", json={"name": "must not exist", "steps": []}
    )

    assert response.status_code == 401
    assert response.get_json() == {
        "code": 401,
        "message": "Authentication required",
        "error": {"code": "AUTH_REQUIRED"},
    }
    with anonymous_client.application.app_context():
        assert CaseModel.query.count() == 0


def test_public_readonly_anonymous_projection_excludes_sensitive_fields(public_client):
    response = public_client.get("/intent-tester/api/testcases")

    assert response.status_code == 200, response.get_data(as_text=True)
    assert set(response.json["data"]["items"][0]) == {
        "id",
        "name",
        "description",
        "category",
        "priority",
        "tags",
        "is_active",
        "updated_at",
    }


def test_public_readonly_anonymous_mutation_is_denied_without_side_effect(public_client):
    response = public_client.post(
        "/intent-tester/api/testcases",
        json={"name": "must not exist", "steps": []},
    )

    assert response.status_code == 403
    assert _error_code(response) == "READ_ONLY_MODE"
    with public_client.application.app_context():
        assert CaseModel.query.count() == 1


@IGNORE_EXISTING_UTCNOW_WARNING
def test_public_readonly_anonymous_non_allowlist_page_is_denied(public_client):
    response = public_client.get("/intent-tester/testcases/create")

    assert response.status_code == 403
    assert _error_code(response) == "READ_ONLY_MODE"
    with public_client.application.app_context():
        assert CaseModel.query.count() == 1


@IGNORE_EXISTING_UTCNOW_WARNING
def test_public_readonly_logged_admin_can_use_operator_page_full_read_and_mutation(
    public_readonly_app, public_readonly_operator
):
    _seed_testcase(public_readonly_app, created_by="seed-admin")

    page = public_readonly_operator.get("/intent-tester/testcases/create")
    listing = public_readonly_operator.get("/intent-tester/api/testcases")
    mutation = public_readonly_operator.post(
        "/intent-tester/api/testcases",
        json={"name": "operator mutation", "steps": [], "created_by": "forged"},
    )

    assert page.status_code == 200
    assert listing.status_code == 200
    assert listing.json["data"]["items"][0]["created_by"] == "seed-admin"
    assert "steps" in listing.json["data"]["items"][0]
    assert mutation.status_code == 200
    with public_readonly_app.app_context():
        created = CaseModel.query.filter_by(name="operator mutation").one()
        assert created.created_by == "admin"


@IGNORE_EXISTING_UTCNOW_WARNING
def test_public_readonly_logged_admin_can_execute_when_execution_is_enabled(
    public_readonly_app, public_readonly_operator
):
    class AcceptingProxy:
        def dispatch_execution(self, payload):
            return {"success": True, "executionId": payload["executionId"]}

    public_readonly_app.config["PROXY_EXECUTION_CLIENT"] = AcceptingProxy()
    testcase_id = _seed_testcase(public_readonly_app)

    response = public_readonly_operator.post(
        "/intent-tester/api/executions", json={"testcase_id": testcase_id}
    )

    assert response.status_code == 200
    with public_readonly_app.app_context():
        assert ExecutionHistory.query.one().executed_by == "admin"


def test_public_readonly_logged_admin_jinja_capabilities_match_restricted(
    public_readonly_app, public_readonly_operator
):
    captured = []

    def record(_sender, template, context, **_extra):
        captured.append(context)

    template_rendered.connect(record, public_readonly_app)
    try:
        response = public_readonly_operator.get("/intent-tester/testcases")
    finally:
        template_rendered.disconnect(record, public_readonly_app)

    assert response.status_code == 200
    assert captured[-1]["intent_principal"].name == "admin"
    assert captured[-1]["intent_capabilities"] == {
        "can_read_full": True,
        "can_mutate": True,
        "can_execute": True,
        "can_use_local_proxy": True,
    }


def test_execution_disabled_denies_execution_before_dispatch():
    app = create_app(
        intent_test_config(
            INTENT_EXECUTION_ENABLED=False,
            INTENT_PROXY_TOPOLOGY=None,
            INTENT_PROXY_TOKEN=None,
            OPENAI_API_KEY=None,
            OPENAI_BASE_URL=None,
            MIDSCENE_MODEL_NAME=None,
        )
    )
    testcase_id = _seed_testcase(app)
    client = app.test_client()
    login = client.get("/intent-tester/login")
    token = login.get_data(as_text=True).split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    response = client.post(
        "/intent-tester/login",
        data={"username": "admin", "password": "test-admin-password", "csrf_token": token},
        headers={"Origin": "http://127.0.0.1:5001"},
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        csrf = session["csrf_token"]

    response = client.post(
        "/intent-tester/api/executions",
        json={"testcase_id": testcase_id},
        headers={
            "Origin": "http://127.0.0.1:5001",
            "X-CSRF-Token": csrf,
        },
    )

    assert response.status_code == 403
    assert _error_code(response) == "EXECUTION_DISABLED"
    with app.app_context():
        assert ExecutionHistory.query.count() == 0


def test_execution_disabled_kill_switch_covers_page_and_every_execution_endpoint():
    app = create_app(
        intent_test_config(
            INTENT_EXECUTION_ENABLED=False,
            INTENT_PROXY_TOPOLOGY="local-host",
            INTENT_PROXY_TOKEN="test-proxy-token-with-at-least-32b",
            OPENAI_API_KEY=None,
            OPENAI_BASE_URL=None,
            MIDSCENE_MODEL_NAME=None,
        )
    )
    operator = app.test_client()
    _login_operator(operator)
    proxy = app.test_client()
    proxy.environ_base["HTTP_AUTHORIZATION"] = (
        "Bearer test-proxy-token-with-at-least-32b"
    )

    policies = app.extensions["intent_security"].route_policies
    protected_endpoints = {"views.view_execution"} | {
        endpoint for endpoint in policies if endpoint.startswith("executions.")
    }
    routed_endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
    assert protected_endpoints <= routed_endpoints

    adapter = app.url_map.bind("localhost")
    results = {}
    for endpoint in sorted(protected_endpoints):
        rule = next(
            rule
            for rule in app.url_map.iter_rules()
            if rule.endpoint == endpoint and rule.rule.startswith("/intent-tester/")
        )
        method = next(
            method for method in rule.methods if method not in {"HEAD", "OPTIONS"}
        )
        values = {argument: 999 for argument in rule.arguments}
        path = adapter.build(endpoint, values, method=method)
        client = proxy if policies[endpoint].value == "proxy-machine" else operator
        response = client.open(path, method=method)
        results[endpoint] = (
            response.status_code,
            response.get_json(),
        )

    expected = {
        "code": 403,
        "message": "Execution is disabled",
        "error": {"code": "EXECUTION_DISABLED"},
    }
    assert results == {
        endpoint: (403, expected) for endpoint in protected_endpoints
    }


@pytest.mark.parametrize(
    ("authorization", "expected"),
    [
        (None, "PROXY_AUTH_REQUIRED"),
        ("Bearer wrong-proxy-token-with-at-least-32b", "PROXY_AUTH_REQUIRED"),
    ],
)
def test_lifecycle_requires_canonical_proxy_bearer(
    app, anonymous_client, create_execution_history, authorization, expected
):
    execution = create_execution_history(status="pending")
    headers = {} if authorization is None else {"Authorization": authorization}

    response = anonymous_client.post(
        f"/intent-tester/api/executions/{execution.execution_id}/lifecycle",
        json={"event": "started", "status": "running"},
        headers=headers,
    )

    assert response.status_code == 401
    assert _error_code(response) == expected
    db.session.refresh(execution)
    assert execution.status == "pending"


def test_proxy_principal_can_record_lifecycle_without_session_csrf(
    proxy_client, create_execution_history
):
    execution = create_execution_history(status="pending")

    response = proxy_client.post(
        f"/intent-tester/api/executions/{execution.execution_id}/lifecycle",
        json={"event": "started", "status": "running"},
    )

    assert response.status_code == 200
    db.session.refresh(execution)
    assert execution.status == "running"


def test_retired_midscene_routes_are_404_and_cannot_write(
    operator_client, create_test_testcase
):
    testcase = create_test_testcase(name="retired")
    payload = {
        "execution_id": "retired-write",
        "testcase_id": testcase.id,
        "mode": "headless",
        "status": "running",
    }

    for path in (
        "/intent-tester/api/midscene/execution-start",
        "/intent-tester/api/midscene/execution-result",
    ):
        response = operator_client.post(path, json=payload)
        assert response.status_code == 404

    assert ExecutionHistory.query.filter_by(execution_id="retired-write").first() is None


def test_local_host_operator_can_issue_verifiable_scoped_proxy_ticket(
    app, operator_client, create_execution_history
):
    execution = create_execution_history(status="pending")
    with operator_client.session_transaction() as current:
        assert current["intent_principal"] == "admin"

    response = operator_client.post(
        f"/intent-tester/api/executions/{execution.execution_id}/proxy-ticket"
    )

    assert response.status_code == 200, response.get_data(as_text=True)
    assert set(response.json["data"]) == {"ticket", "execution_id", "expires_in"}
    assert response.json["data"]["execution_id"] == execution.execution_id
    assert response.json["data"]["expires_in"] == 60
    encoded_payload, encoded_signature = response.json["data"]["ticket"].split(".")
    payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
    signature = base64.urlsafe_b64decode(encoded_signature + "=" * (-len(encoded_signature) % 4))
    expected_signature = hmac.new(
        b"test-proxy-token-with-at-least-32b", payload_bytes, hashlib.sha256
    ).digest()
    assert hmac.compare_digest(signature, expected_signature)
    payload = json.loads(payload_bytes)
    assert set(payload) == {"executionId", "origin", "aud", "iat", "exp", "nonce"}
    assert payload["executionId"] == execution.execution_id
    assert payload["origin"] == "http://127.0.0.1:5001"
    assert payload["aud"] == "intent-proxy-socket"
    assert isinstance(payload["iat"], int)
    assert payload["exp"] == payload["iat"] + 60
    assert isinstance(payload["nonce"], str) and payload["nonce"]


def test_proxy_ticket_requires_existing_execution(operator_client):
    response = operator_client.post(
        "/intent-tester/api/executions/not-canonical/proxy-ticket"
    )

    assert response.status_code == 404


def test_managed_topology_rejects_local_proxy_ticket():
    app = create_app(intent_test_config(INTENT_PROXY_TOPOLOGY="managed"))
    with app.app_context():
        testcase = CaseModel(name="managed", steps="[]", created_by="admin")
        db.session.add(testcase)
        db.session.flush()
        execution = ExecutionHistory(
            execution_id="managed-execution",
            test_case_id=testcase.id,
            status="pending",
            start_time=datetime.utcnow(),
            executed_by="admin",
        )
        db.session.add(execution)
        db.session.commit()
        execution_id = execution.execution_id
    client = app.test_client()
    page = client.get("/intent-tester/login").get_data(as_text=True)
    csrf = page.split('name="csrf_token" value="', 1)[1].split('"', 1)[0]
    client.post(
        "/intent-tester/login",
        data={"username": "admin", "password": "test-admin-password", "csrf_token": csrf},
        headers={"Origin": "http://127.0.0.1:5001"},
    )
    with client.session_transaction() as session:
        csrf = session["csrf_token"]

    response = client.post(
        f"/intent-tester/api/executions/{execution_id}/proxy-ticket",
        headers={"Origin": "http://127.0.0.1:5001", "X-CSRF-Token": csrf},
    )

    assert response.status_code == 403
    assert _error_code(response) == "PROXY_TICKET_UNAVAILABLE"


def test_jinja_context_exposes_anonymous_principal_capabilities_csrf_and_origin(
    app, anonymous_client
):
    captured = []

    def record(_sender, template, context, **_extra):
        captured.append(context)

    template_rendered.connect(record, app)
    try:
        response = anonymous_client.get("/intent-tester/login")
    finally:
        template_rendered.disconnect(record, app)

    assert response.status_code == 200
    context = captured[-1]
    assert context["csrf_token"]
    assert context["intent_principal"].name == "anonymous"
    assert context["intent_public_origin"] == "http://127.0.0.1:5001"
    assert context["intent_capabilities"] == {
        "can_read_full": False,
        "can_mutate": False,
        "can_execute": False,
        "can_use_local_proxy": False,
    }


def test_jinja_context_derives_operator_capabilities(app, operator_client):
    captured = []

    def record(_sender, template, context, **_extra):
        captured.append(context)

    template_rendered.connect(record, app)
    try:
        response = operator_client.get("/intent-tester/testcases")
    finally:
        template_rendered.disconnect(record, app)

    assert response.status_code == 200
    context = captured[-1]
    assert context["intent_principal"].name == "admin"
    assert context["intent_capabilities"] == {
        "can_read_full": True,
        "can_mutate": True,
        "can_execute": True,
        "can_use_local_proxy": True,
    }
