from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import os
import re
import subprocess
import sys
from typing import Any

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

from backend.app import create_app
from backend.intent_security import (
    IntentSecurityConfigurationError,
    IntentSecurityConfig,
    install_intent_security,
    validate_startup_config,
)
from backend.models import db


_MISSING = object()
_SECRET_VALUE = "never-echo-this-production-secret-value"
_INTENT_TESTER_ROOT = Path(__file__).resolve().parents[2]


def valid_production_config() -> dict[str, Any]:
    return {
        "AI4SE_ENV": "production",
        "INTENT_ACCESS_MODE": "restricted",
        "INTENT_EXECUTION_ENABLED": True,
        "INTENT_PUBLIC_ORIGIN": "https://intent.example",
        "INTENT_PROXY_TOPOLOGY": "managed",
        "INTENT_PROXY_TOKEN": "proxy-token-with-at-least-32-bytes",
        "SECRET_KEY": _SECRET_VALUE,
        "INTENT_TESTER_ADMIN_PASSWORD_HASH": generate_password_hash(
            "test-admin-password", method="scrypt"
        ),
        "OPENAI_API_KEY": "sk-real-production-provider-key",
        "OPENAI_BASE_URL": "https://provider.example/v1",
        "MIDSCENE_MODEL_NAME": "provider-vision-model",
        "SQLALCHEMY_DATABASE_URI": "postgresql://intent:strong-password@db/intent",
    }


def with_override(
    config: Mapping[str, Any], key: str, value: object
) -> dict[str, Any]:
    result = dict(config)
    if value is _MISSING:
        # Explicitly clear values that create_app may otherwise load from the
        # developer's environment.
        result[key] = None
    else:
        result[key] = value
    return result


@pytest.mark.parametrize(
    ("key", "value", "error_key"),
    [
        ("INTENT_ACCESS_MODE", _MISSING, "INTENT_ACCESS_MODE"),
        ("INTENT_ACCESS_MODE", "local-dev", "INTENT_ACCESS_MODE"),
        ("INTENT_ACCESS_MODE", "invalid", "INTENT_ACCESS_MODE"),
        ("INTENT_EXECUTION_ENABLED", _MISSING, "INTENT_EXECUTION_ENABLED"),
        ("INTENT_EXECUTION_ENABLED", "sometimes", "INTENT_EXECUTION_ENABLED"),
        ("SQLALCHEMY_DATABASE_URI", "sqlite:///production.db", "DATABASE_URL"),
        (
            "SQLALCHEMY_DATABASE_URI",
            "postgresql://intent:change_me_in_production@db/intent",
            "DATABASE_URL",
        ),
        (
            "SQLALCHEMY_DATABASE_URI",
            "postgresql://db/intent",
            "DATABASE_URL",
        ),
        (
            "SQLALCHEMY_DATABASE_URI",
            "postgresql://intent@db/intent",
            "DATABASE_URL",
        ),
        ("SECRET_KEY", _MISSING, "SECRET_KEY"),
        ("SECRET_KEY", "short-secret", "SECRET_KEY"),
        ("SECRET_KEY", "change_me_in_production", "SECRET_KEY"),
        ("SECRET_KEY", "dev-secret-key-please-change-in-production", "SECRET_KEY"),
        ("SECRET_KEY", "dev-secret-key-please-change", "SECRET_KEY"),
        ("SECRET_KEY", "dev-secret-key-change-in-production", "SECRET_KEY"),
        (
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
            _MISSING,
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        ),
        (
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
            "plain-text-password",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        ),
        (
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
            "scrypt:",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        ),
        (
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
            "pbkdf2:sha256$missing-digest",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        ),
        (
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
            "pbkdf2:not-a-digest:1$salt$digest",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        ),
        (
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
            "pbkdf2:sha256:999999999999999999999$salt$digest",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        ),
        (
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
            "scrypt:3:1:1$salt$digest",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        ),
        ("INTENT_PUBLIC_ORIGIN", _MISSING, "INTENT_PUBLIC_ORIGIN"),
        ("INTENT_PUBLIC_ORIGIN", "http://prod.example", "INTENT_PUBLIC_ORIGIN"),
        (
            "INTENT_PUBLIC_ORIGIN",
            "https://user@prod.example",
            "INTENT_PUBLIC_ORIGIN",
        ),
        (
            "INTENT_PUBLIC_ORIGIN",
            "https://prod.example/application",
            "INTENT_PUBLIC_ORIGIN",
        ),
        ("INTENT_PROXY_TOPOLOGY", _MISSING, "INTENT_PROXY_TOPOLOGY"),
        ("INTENT_PROXY_TOPOLOGY", "local-host", "INTENT_PROXY_TOPOLOGY"),
        ("INTENT_PROXY_TOKEN", _MISSING, "INTENT_PROXY_TOKEN"),
        ("INTENT_PROXY_TOKEN", "short-token", "INTENT_PROXY_TOKEN"),
        ("INTENT_PROXY_TOKEN", "change_me_in_production", "INTENT_PROXY_TOKEN"),
        ("OPENAI_API_KEY", _MISSING, "OPENAI_API_KEY"),
        ("OPENAI_API_KEY", "your-api-key-here", "OPENAI_API_KEY"),
        ("OPENAI_API_KEY", "sk-your-api-key-here", "OPENAI_API_KEY"),
        ("OPENAI_BASE_URL", _MISSING, "OPENAI_BASE_URL"),
        ("OPENAI_BASE_URL", "provider.example/v1", "OPENAI_BASE_URL"),
        ("OPENAI_BASE_URL", "http://provider.example/v1", "OPENAI_BASE_URL"),
        ("OPENAI_BASE_URL", "https://user@provider.example/v1", "OPENAI_BASE_URL"),
        ("MIDSCENE_MODEL_NAME", _MISSING, "MIDSCENE_MODEL_NAME"),
        ("MIDSCENE_MODEL_NAME", "   ", "MIDSCENE_MODEL_NAME"),
    ],
)
def test_production_preflight_fails_before_database_init(
    monkeypatch: pytest.MonkeyPatch,
    key: str,
    value: object,
    error_key: str,
) -> None:
    config = with_override(valid_production_config(), key, value)

    def unexpected_database_init(*args: object, **kwargs: object) -> None:
        pytest.fail("database initialization ran before security preflight")

    monkeypatch.setattr(db, "init_app", unexpected_database_init)

    with pytest.raises(IntentSecurityConfigurationError, match=error_key) as error:
        create_app(config)

    assert _SECRET_VALUE not in str(error.value)


@pytest.mark.parametrize("access_mode", ["restricted", "public-readonly"])
def test_valid_production_modes_install_canonical_security_config(
    access_mode: str,
) -> None:
    app = Flask(__name__)
    app.config.update(valid_production_config() | {"INTENT_ACCESS_MODE": access_mode})
    install_intent_security(app)

    canonical = app.config["INTENT_SECURITY_CONFIG"]
    assert isinstance(canonical, IntentSecurityConfig)
    assert canonical.access_mode == access_mode
    assert canonical.execution_enabled is True
    assert canonical.public_origin == "https://intent.example"
    assert canonical.proxy_topology == "managed"
    assert app.config["INTENT_ACCESS_MODE"] == access_mode
    assert app.config["INTENT_EXECUTION_ENABLED"] is True
    assert app.config["INTENT_PUBLIC_ORIGIN"] == "https://intent.example"
    assert app.config["INTENT_PROXY_TOPOLOGY"] == "managed"
    assert app.extensions["intent_security"].config is canonical


def test_execution_disabled_does_not_require_proxy_or_provider_credentials() -> None:
    config = valid_production_config() | {"INTENT_EXECUTION_ENABLED": False}
    for key in (
        "INTENT_PROXY_TOPOLOGY",
        "INTENT_PROXY_TOKEN",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "MIDSCENE_MODEL_NAME",
    ):
        config.pop(key)

    app = Flask(__name__)
    app.config.update(config)
    install_intent_security(app)

    assert app.config["INTENT_SECURITY_CONFIG"].execution_enabled is False
    assert app.config["INTENT_PROXY_TOPOLOGY"] is None


@pytest.mark.parametrize("topology", ["managed", "local-host"])
def test_local_dev_execution_accepts_managed_and_local_host_topology(
    topology: str,
) -> None:
    app = create_app(
        {
            "TESTING": True,
            "AI4SE_ENV": "test",
            "INTENT_ACCESS_MODE": "local-dev",
            "INTENT_EXECUTION_ENABLED": True,
            "INTENT_PUBLIC_ORIGIN": "http://[::1]:5001",
            "INTENT_PROXY_TOPOLOGY": topology,
            "INTENT_PROXY_TOKEN": "test-proxy-token-with-at-least-32b",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_BASE_URL": "http://127.0.0.1:3000/v1",
            "MIDSCENE_MODEL_NAME": "qwen-vl-max-latest",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    canonical = app.config["INTENT_SECURITY_CONFIG"]
    assert canonical.environment == "test"
    assert canonical.access_mode == "local-dev"
    assert canonical.proxy_topology == topology


def test_all_modes_require_an_explicit_public_origin() -> None:
    mapping = {
        "AI4SE_ENV": "development",
        "INTENT_ACCESS_MODE": "local-dev",
        "INTENT_EXECUTION_ENABLED": False,
    }

    canonical = IntentSecurityConfig.from_mapping(mapping)
    with pytest.raises(
        IntentSecurityConfigurationError, match="INTENT_PUBLIC_ORIGIN"
    ):
        validate_startup_config(canonical, "sqlite:///:memory:")


@pytest.mark.parametrize("access_mode", ["restricted", "public-readonly"])
def test_non_local_access_requires_strong_secret_in_development(
    access_mode: str,
) -> None:
    mapping = {
        "AI4SE_ENV": "development",
        "INTENT_ACCESS_MODE": access_mode,
        "INTENT_EXECUTION_ENABLED": False,
        "INTENT_PUBLIC_ORIGIN": "http://intent.example",
        "SECRET_KEY": "short-development-secret",
        "INTENT_TESTER_ADMIN_PASSWORD_HASH": generate_password_hash(
            "test-admin-password", method="scrypt"
        ),
    }

    canonical = IntentSecurityConfig.from_mapping(mapping)
    with pytest.raises(IntentSecurityConfigurationError, match="SECRET_KEY"):
        validate_startup_config(canonical, "sqlite:///:memory:")


def test_canonical_config_exposes_consumer_fields_without_repr_or_equality_leaks() -> None:
    first = IntentSecurityConfig.from_mapping(valid_production_config())
    second = IntentSecurityConfig.from_mapping(
        valid_production_config()
        | {
            "INTENT_PROXY_TOKEN": "different-proxy-token-of-32-bytes",
            "SECRET_KEY": "different-production-secret-value",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH": generate_password_hash(
                "different-admin-password", method="pbkdf2:sha256:1000"
            ),
            "OPENAI_API_KEY": "different-provider-key",
            "OPENAI_BASE_URL": "https://different-provider.example/v1",
            "MIDSCENE_MODEL_NAME": "different-model",
        }
    )

    assert first.secret_key == _SECRET_VALUE
    assert first.admin_password_hash.startswith("scrypt:")
    assert first.provider_api_key == "sk-real-production-provider-key"
    assert first.provider_base_url == "https://provider.example/v1"
    assert first.provider_model == "provider-vision-model"
    assert not hasattr(first, "_openai_api_key")
    assert first == second
    representation = repr(first)
    for secret_value in (
        first.proxy_token,
        first.secret_key,
        first.admin_password_hash,
        first.provider_api_key,
        first.provider_base_url,
        first.provider_model,
    ):
        assert secret_value not in representation


@pytest.mark.parametrize(
    "origin",
    [
        "https://remote.example",
        "http://127.0.0.2:5001",
        "http://localhost:5001/path",
        "http://localhost:5001?query=yes",
    ],
)
def test_local_dev_rejects_non_loopback_or_non_origin_url(origin: str) -> None:
    mapping = {
        "AI4SE_ENV": "development",
        "INTENT_ACCESS_MODE": "local-dev",
        "INTENT_EXECUTION_ENABLED": False,
        "INTENT_PUBLIC_ORIGIN": origin,
        "INTENT_PROXY_TOPOLOGY": "local-host",
    }

    with pytest.raises(
        IntentSecurityConfigurationError, match="INTENT_PUBLIC_ORIGIN"
    ):
        canonical = IntentSecurityConfig.from_mapping(mapping)
        validate_startup_config(canonical, "sqlite:///:memory:")


def test_install_initializes_socketio_with_exact_canonical_origin() -> None:
    app = Flask(__name__)
    app.config.update(valid_production_config())
    install_intent_security(app)

    socketio_server = app.extensions["socketio"]
    assert socketio_server.server.eio.cors_allowed_origins == "https://intent.example"


def test_configuration_error_accumulates_sorted_keys_without_secret_values() -> None:
    config = valid_production_config() | {
        "SECRET_KEY": "leaked-secret-value",
        "INTENT_PROXY_TOKEN": "leaked-token-value",
        "OPENAI_API_KEY": "your-api-key-here",
    }

    with pytest.raises(IntentSecurityConfigurationError) as error:
        create_app(config)

    message = str(error.value)
    assert message == (
        "Invalid Intent Tester configuration: "
        "INTENT_PROXY_TOKEN, OPENAI_API_KEY, SECRET_KEY"
    )
    assert "leaked-secret-value" not in message
    assert "leaked-token-value" not in message
    assert "your-api-key-here" not in message


@pytest.mark.parametrize(
    "database_uri",
    [
        "postgresql://db/intent",
        "postgresql://intent@db/intent",
        "postgresql://:strong-password@db/intent",
        "postgresql://intent:@db/intent",
    ],
)
def test_production_database_requires_nonempty_username_and_password(
    database_uri: str,
) -> None:
    canonical = IntentSecurityConfig.from_mapping(valid_production_config())

    with pytest.raises(IntentSecurityConfigurationError, match="DATABASE_URL"):
        validate_startup_config(canonical, database_uri)


@pytest.mark.parametrize("entry", [["-m", "backend.app"], ["run.py"]])
def test_production_direct_main_exits_with_gunicorn_instruction(
    entry: list[str],
) -> None:
    result = subprocess.run(
        [sys.executable, *entry],
        cwd=_INTENT_TESTER_ROOT,
        env={**os.environ, "AI4SE_ENV": "production"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    diagnostics = result.stdout + result.stderr
    assert "gunicorn" in diagnostics.lower()
    assert "backend.app:create_app()" in diagnostics
    assert "Database" not in diagnostics


def test_production_container_uses_locked_gunicorn_gthread_contract() -> None:
    requirements = (_INTENT_TESTER_ROOT / "requirements.txt").read_text(
        encoding="utf-8"
    )
    dockerfile = (_INTENT_TESTER_ROOT / "docker/Dockerfile").read_text(
        encoding="utf-8"
    )

    assert re.search(r"(?m)^gunicorn==\d+\.\d+\.\d+$", requirements)
    assert (
        'CMD ["gunicorn", "--worker-class", "gthread", "--threads", "100", '
        '"--bind", "0.0.0.0:5001", "backend.app:create_app()"]'
        in dockerfile
    )


def test_direct_main_sources_never_enable_unsafe_or_non_loopback_dev_server() -> None:
    app_source = (_INTENT_TESTER_ROOT / "backend/app.py").read_text(encoding="utf-8")
    run_source = (_INTENT_TESTER_ROOT / "run.py").read_text(encoding="utf-8")

    assert "allow_unsafe_werkzeug" not in app_source + run_source
    assert "host='127.0.0.1'" in app_source
    assert "host='0.0.0.0'" not in app_source + run_source
