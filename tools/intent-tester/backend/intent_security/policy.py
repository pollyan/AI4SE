from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Callable, Mapping, ParamSpec, TypeVar
from urllib.parse import urlencode

from flask import Flask, Response, current_app, g, jsonify, redirect, request, session


class EndpointPolicy(StrEnum):
    PUBLIC = "public"
    PUBLIC_READONLY = "public-readonly"
    OPERATOR = "operator"
    PROXY_MACHINE = "proxy-machine"


@dataclass(frozen=True)
class IntentPrincipal:
    name: str
    principal_type: str
    authenticated: bool

    @property
    def is_operator(self) -> bool:
        return self.principal_type == "operator"


ANONYMOUS_PRINCIPAL = IntentPrincipal("anonymous", "anonymous", False)
ADMIN_PRINCIPAL = IntentPrincipal("admin", "operator", True)
LOCAL_DEV_PRINCIPAL = IntentPrincipal("local-dev", "operator", True)
PROXY_PRINCIPAL = IntentPrincipal("proxy", "proxy-machine", True)

P = ParamSpec("P")
R = TypeVar("R")


def intent_policy(
    policy: EndpointPolicy,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(view: Callable[P, R]) -> Callable[P, R]:
        setattr(view, "__intent_policy__", policy)
        return view

    return decorate


def collect_route_policies(app: Flask) -> Mapping[str, EndpointPolicy]:
    policies: dict[str, EndpointPolicy] = {}
    builtins = {
        "static": EndpointPolicy.PUBLIC,
        "health_check": EndpointPolicy.PUBLIC,
        "root_redirect": EndpointPolicy.PUBLIC,
    }
    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        view = app.view_functions[endpoint]
        policy = getattr(view, "__intent_policy__", None) or builtins.get(endpoint)
        if not isinstance(policy, EndpointPolicy):
            raise ValueError(f"Unclassified Intent Tester endpoint: {endpoint}")
        existing = policies.get(endpoint)
        if existing is not None and existing is not policy:
            raise ValueError(f"Conflicting Intent Tester endpoint policy: {endpoint}")
        policies[endpoint] = policy
    return MappingProxyType(policies)


def current_intent_principal() -> IntentPrincipal:
    assigned = getattr(g, "intent_principal", None)
    request_object = request._get_current_object()
    if (
        isinstance(assigned, IntentPrincipal)
        and getattr(g, "intent_principal_request", None) is request_object
    ):
        return assigned
    config = current_app.extensions["intent_security"].config
    if config.access_mode == "local-dev":
        return LOCAL_DEV_PRINCIPAL
    if session.get("intent_principal") == "admin":
        return ADMIN_PRINCIPAL
    return ANONYMOUS_PRINCIPAL


def _assign_principal(principal: IntentPrincipal) -> None:
    g.intent_principal = principal
    g.intent_principal_request = request._get_current_object()


def ensure_csrf_token() -> str:
    token = session.get("csrf_token")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def rotate_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return token


def _security_error(status: int, message: str, code: str) -> tuple[Response, int]:
    return jsonify({"code": status, "message": message, "error": {"code": code}}), status


def require_valid_origin_and_csrf() -> tuple[Response, int] | None:
    config = current_app.extensions["intent_security"].config
    supplied_origin = request.headers.get("Origin")
    if supplied_origin != config.public_origin:
        return _security_error(403, "Request origin rejected", "ORIGIN_REJECTED")

    expected = ensure_csrf_token()
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not isinstance(supplied, str) or not secrets.compare_digest(supplied, expected):
        return _security_error(403, "CSRF validation failed", "CSRF_FAILED")
    return None


def require_proxy_bearer() -> tuple[Response, int] | None:
    config = current_app.extensions["intent_security"].config
    authorization = request.headers.get("Authorization", "")
    prefix = "Bearer "
    supplied = authorization[len(prefix) :] if authorization.startswith(prefix) else ""
    expected = config.proxy_token
    if (
        not supplied
        or not isinstance(expected, str)
        or not secrets.compare_digest(supplied, expected)
    ):
        return _security_error(
            401, "Proxy authentication required", "PROXY_AUTH_REQUIRED"
        )
    _assign_principal(PROXY_PRINCIPAL)
    return None


_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _is_api_request() -> bool:
    return request.path.startswith("/intent-tester/api/")


def _requires_execution_capability(endpoint: str) -> bool:
    return endpoint == "views.view_execution" or endpoint.startswith("executions.")


def _require_operator() -> Response | tuple[Response, int] | None:
    principal = current_intent_principal()
    if principal.is_operator:
        _assign_principal(principal)
        return None
    if _is_api_request():
        return _security_error(401, "Authentication required", "AUTH_REQUIRED")
    login_query = urlencode({"next": request.path})
    return redirect(f"/intent-tester/login?{login_query}")


def enforce_intent_policy() -> Response | tuple[Response, int] | None:
    endpoint = request.endpoint
    if endpoint is None:
        return None
    extension = current_app.extensions["intent_security"]
    policy = extension.route_policies[endpoint]
    config = extension.config

    ensure_csrf_token()
    _assign_principal(current_intent_principal())

    # The execution kill switch is a capability gate, so it precedes both
    # human and proxy authentication. When disabled there is intentionally no
    # proxy credential to validate and no execution surface to probe.
    if _requires_execution_capability(endpoint) and not config.execution_enabled:
        return _security_error(403, "Execution is disabled", "EXECUTION_DISABLED")

    if policy is EndpointPolicy.PROXY_MACHINE:
        rejected = require_proxy_bearer()
        if rejected is not None:
            return rejected
    elif policy is EndpointPolicy.OPERATOR:
        if (
            config.access_mode == "public-readonly"
            and not current_intent_principal().is_operator
        ):
            return _security_error(403, "Read-only mode", "READ_ONLY_MODE")
        rejected = _require_operator()
        if rejected is not None:
            return rejected
    elif policy is EndpointPolicy.PUBLIC_READONLY:
        if config.access_mode != "public-readonly":
            rejected = _require_operator()
            if rejected is not None:
                return rejected

    if policy is not EndpointPolicy.PROXY_MACHINE and request.method in _UNSAFE_METHODS:
        return require_valid_origin_and_csrf()
    return None


def intent_capabilities() -> dict[str, bool]:
    config = current_app.extensions["intent_security"].config
    principal = current_intent_principal()
    operator = principal.is_operator
    can_execute = operator and config.execution_enabled
    return {
        "can_read_full": operator,
        "can_mutate": operator,
        "can_execute": can_execute,
        "can_use_local_proxy": can_execute and config.proxy_topology == "local-host",
    }


def issue_proxy_ticket(execution_id: str) -> str:
    config = current_app.extensions["intent_security"].config
    if not isinstance(config.proxy_token, str):
        raise RuntimeError("Proxy ticket signing is unavailable")
    issued_at = int(time.time())
    payload = {
        "executionId": execution_id,
        "origin": config.public_origin,
        "aud": "intent-proxy-socket",
        "iat": issued_at,
        "exp": issued_at + 60,
        "nonce": secrets.token_urlsafe(24),
    }
    payload_bytes = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    signature = hmac.new(
        config.proxy_token.encode("utf-8"), payload_bytes, hashlib.sha256
    ).digest()
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode("ascii")
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{encoded_payload}.{encoded_signature}"


def proxy_ticket_unavailable_response() -> tuple[Response, int]:
    return _security_error(
        403, "Proxy ticket unavailable", "PROXY_TICKET_UNAVAILABLE"
    )


__all__ = [
    "EndpointPolicy",
    "IntentPrincipal",
    "collect_route_policies",
    "current_intent_principal",
    "enforce_intent_policy",
    "ensure_csrf_token",
    "intent_capabilities",
    "intent_policy",
    "issue_proxy_ticket",
    "proxy_ticket_unavailable_response",
    "require_proxy_bearer",
    "require_valid_origin_and_csrf",
    "rotate_csrf_token",
]
