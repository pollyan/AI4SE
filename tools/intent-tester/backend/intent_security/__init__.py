from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from flask import Flask

from .config import (
    IntentSecurityConfig,
    IntentSecurityConfigurationError,
    validate_startup_config,
)
from .policy import (
    EndpointPolicy,
    IntentPrincipal,
    collect_route_policies,
    current_intent_principal,
    enforce_intent_policy,
    intent_policy,
    issue_proxy_ticket,
    require_proxy_bearer,
    require_valid_origin_and_csrf,
)
from .web import (
    add_browser_security_headers,
    create_csp_nonce,
    intent_template_context,
)


@dataclass(frozen=True)
class _IntentSecurityExtension:
    config: IntentSecurityConfig
    route_policies: Mapping[str, EndpointPolicy]


def install_intent_security(app: Flask) -> None:
    """Validate and install Intent Tester's shared security configuration."""
    canonical = IntentSecurityConfig.from_mapping(app.config)
    validate_startup_config(canonical, app.config.get("SQLALCHEMY_DATABASE_URI"))

    app.config.update(
        INTENT_SECURITY_CONFIG=canonical,
        INTENT_ACCESS_MODE=canonical.access_mode,
        INTENT_EXECUTION_ENABLED=canonical.execution_enabled,
        INTENT_PUBLIC_ORIGIN=canonical.public_origin,
        INTENT_PROXY_TOPOLOGY=canonical.proxy_topology,
    )
    route_policies = collect_route_policies(app)
    app.extensions["intent_security"] = _IntentSecurityExtension(
        config=canonical, route_policies=route_policies
    )

    app.config.update(
        SESSION_COOKIE_SECURE=canonical.environment == "production",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    app.before_request(create_csp_nonce)
    app.before_request(enforce_intent_policy)
    app.after_request(add_browser_security_headers)
    app.context_processor(intent_template_context)

    from ..extensions import socketio

    socketio.init_app(app, cors_allowed_origins=canonical.public_origin)


__all__ = [
    "IntentSecurityConfig",
    "IntentSecurityConfigurationError",
    "EndpointPolicy",
    "IntentPrincipal",
    "current_intent_principal",
    "intent_policy",
    "issue_proxy_ticket",
    "require_proxy_bearer",
    "require_valid_origin_and_csrf",
    "install_intent_security",
    "validate_startup_config",
]
