from __future__ import annotations

import secrets
from urllib.parse import urlsplit

from flask import Response, current_app, g, redirect, render_template, request, session
from werkzeug.security import check_password_hash

from .policy import (
    current_intent_principal,
    ensure_csrf_token,
    intent_capabilities,
    rotate_csrf_token,
)


def _safe_next(value: str | None) -> str:
    fallback = "/intent-tester/testcases"
    if not isinstance(value, str):
        return fallback
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return fallback
    if parsed.path == "/intent-tester" or parsed.path.startswith("/intent-tester/"):
        return value
    return fallback


def login_response() -> str | Response | tuple[str, int]:
    if request.method == "GET":
        return render_template("login.html")

    config = current_app.extensions["intent_security"].config
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    password_matches = bool(
        config.admin_password_hash
        and check_password_hash(config.admin_password_hash, password)
    )
    if username != "admin" or not password_matches:
        return (
            render_template(
                "login.html", error_message="Invalid username or password"
            ),
            401,
        )

    session.clear()
    session["intent_principal"] = "admin"
    rotate_csrf_token()
    return redirect(_safe_next(request.args.get("next")))


def logout_response() -> Response:
    session.clear()
    rotate_csrf_token()
    return redirect("/intent-tester/login")


def create_csp_nonce() -> None:
    """Create the response-local nonce before a routed page is rendered."""
    g.intent_csp_nonce = secrets.token_urlsafe(24)


def add_browser_security_headers(response: Response) -> Response:
    nonce = getattr(g, "intent_csp_nonce", None)
    if nonce is None:
        nonce = secrets.token_urlsafe(24)
        g.intent_csp_nonce = nonce

    connect_sources = ["'self'"]
    if intent_capabilities()["can_use_local_proxy"]:
        connect_sources.extend(
            ["http://localhost:3001", "ws://localhost:3001"]
        )
    directives = (
        "default-src 'none'",
        f"script-src 'self' 'nonce-{nonce}'",
        "script-src-attr 'none'",
        f"style-src 'self' 'nonce-{nonce}'",
        "style-src-attr 'none'",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        f"connect-src {' '.join(connect_sources)}",
        "img-src 'self' data:",
        "font-src 'self'",
    )
    response.headers["Content-Security-Policy"] = "; ".join(directives)
    response.headers["X-Content-Type-Options"] = "nosniff"
    # A no-referrer policy serializes the Origin of a basic browser form POST
    # as `null` in Chromium, which makes the exact-origin login CSRF contract
    # reject its own legitimate form. Keep referrers confined to this origin
    # while preserving a non-opaque Origin for same-origin form submissions.
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = (
        "camera=(), geolocation=(), microphone=()"
    )
    return response


def intent_template_context() -> dict[str, object]:
    return {
        "csp_nonce": g.intent_csp_nonce,
        "csrf_token": ensure_csrf_token(),
        "intent_principal": current_intent_principal(),
        "intent_capabilities": intent_capabilities(),
        "intent_public_origin": current_app.extensions[
            "intent_security"
        ].config.public_origin,
    }


__all__ = [
    "add_browser_security_headers",
    "create_csp_nonce",
    "intent_template_context",
    "login_response",
    "logout_response",
]
