from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, cast
from urllib.parse import SplitResult, urlsplit, urlunsplit

from werkzeug.security import check_password_hash


class IntentSecurityConfigurationError(ValueError):
    """Raised when Intent Tester cannot start with its security configuration."""


_AccessMode = Literal["restricted", "public-readonly", "local-dev"]
_Environment = Literal["development", "test", "production"]
_ProxyTopology = Literal["managed", "local-host"]

_REJECTED_SECRETS = frozenset(
    {
        "change_me_in_production",
        "dev-secret-key-please-change-in-production",
        "dev-secret-key-please-change",
        "dev-secret-key-change-in-production",
    }
)
_REJECTED_PRODUCTION_API_KEYS = frozenset(
    {
        "change_me_in_production",
        "your-api-key-here",
        "sk-your-api-key-here",
    }
)
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_MAX_PBKDF2_ITERATIONS = 10_000_000
_MAX_SCRYPT_N = 2**18
_MAX_SCRYPT_R = 32
_MAX_SCRYPT_P = 16
_MAX_SCRYPT_WORK = 2**20


def _trimmed_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _parse_boolean(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def _parse_url(value: str | None) -> SplitResult | None:
    if value is None:
        return None
    try:
        parsed = urlsplit(value)
        # Accessing port validates malformed values such as non-numeric ports.
        parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None
    return parsed


def _canonical_origin(value: str | None) -> str | None:
    parsed = _parse_url(value)
    if parsed is None:
        return None
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


@dataclass(frozen=True)
class IntentSecurityConfig:
    environment: _Environment
    access_mode: _AccessMode
    execution_enabled: bool
    public_origin: str
    proxy_topology: _ProxyTopology | None
    proxy_token: str | None = field(repr=False, compare=False)
    secret_key: str | None = field(repr=False, compare=False)
    admin_password_hash: str | None = field(repr=False, compare=False)
    provider_api_key: str | None = field(repr=False, compare=False)
    provider_base_url: str | None = field(repr=False, compare=False)
    provider_model: str | None = field(repr=False, compare=False)
    _parse_errors: tuple[str, ...] = field(repr=False, compare=False)

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> IntentSecurityConfig:
        parse_errors: list[str] = []

        environment_value = _trimmed_string(mapping.get("AI4SE_ENV")) or "development"
        if environment_value not in {"development", "test", "production"}:
            parse_errors.append("AI4SE_ENV")

        access_default = "local-dev" if environment_value != "production" else None
        access_value = _trimmed_string(mapping.get("INTENT_ACCESS_MODE")) or access_default
        if access_value not in {"restricted", "public-readonly", "local-dev"}:
            parse_errors.append("INTENT_ACCESS_MODE")

        execution_default = False if environment_value != "production" else None
        execution_value = _parse_boolean(
            mapping.get("INTENT_EXECUTION_ENABLED", execution_default)
        )
        if execution_value is None:
            parse_errors.append("INTENT_EXECUTION_ENABLED")

        public_origin_value = _trimmed_string(mapping.get("INTENT_PUBLIC_ORIGIN"))
        canonical_origin = _canonical_origin(public_origin_value)
        if canonical_origin is None:
            parse_errors.append("INTENT_PUBLIC_ORIGIN")

        topology_value = _trimmed_string(mapping.get("INTENT_PROXY_TOPOLOGY"))
        if topology_value is not None and topology_value not in {
            "managed",
            "local-host",
        }:
            parse_errors.append("INTENT_PROXY_TOPOLOGY")

        execution_enabled = execution_value if execution_value is not None else False
        return cls(
            environment=cast(_Environment, environment_value),
            access_mode=cast(_AccessMode, access_value or ""),
            execution_enabled=execution_enabled,
            public_origin=canonical_origin or public_origin_value or "",
            proxy_topology=cast(
                _ProxyTopology | None,
                topology_value if execution_enabled else None,
            ),
            proxy_token=(
                _trimmed_string(mapping.get("INTENT_PROXY_TOKEN"))
                if execution_enabled
                else None
            ),
            secret_key=_trimmed_string(mapping.get("SECRET_KEY")),
            admin_password_hash=_trimmed_string(
                mapping.get("INTENT_TESTER_ADMIN_PASSWORD_HASH")
            ),
            provider_api_key=(
                _trimmed_string(mapping.get("OPENAI_API_KEY"))
                if execution_enabled
                else None
            ),
            provider_base_url=(
                _trimmed_string(mapping.get("OPENAI_BASE_URL"))
                if execution_enabled
                else None
            ),
            provider_model=(
                _trimmed_string(mapping.get("MIDSCENE_MODEL_NAME"))
                if execution_enabled
                else None
            ),
            _parse_errors=tuple(parse_errors),
        )


def _has_minimum_utf8_length(value: str | None, minimum: int) -> bool:
    return value is not None and len(value.encode("utf-8")) >= minimum


def _is_werkzeug_password_hash(value: str | None) -> bool:
    if value is None:
        return False
    encoded_parts = value.split("$")
    if len(encoded_parts) != 3 or not all(encoded_parts):
        return False

    method_parts = encoded_parts[0].split(":")
    method = method_parts[0]
    try:
        if method == "pbkdf2":
            if len(method_parts) != 3 or not method_parts[1]:
                return False
            iterations = int(method_parts[2])
            if not 0 < iterations <= _MAX_PBKDF2_ITERATIONS:
                return False
        elif method == "scrypt":
            if len(method_parts) != 4:
                return False
            n, r, p = (int(parameter) for parameter in method_parts[1:])
            if (
                not 0 < n <= _MAX_SCRYPT_N
                or n & (n - 1) != 0
                or not 0 < r <= _MAX_SCRYPT_R
                or not 0 < p <= _MAX_SCRYPT_P
                or n * r * p > _MAX_SCRYPT_WORK
            ):
                return False
        else:
            return False
    except (TypeError, ValueError, OverflowError):
        return False

    try:
        # A mismatched password is expected. The call is used to make Werkzeug
        # parse and execute the configured method, rejecting unsupported digests
        # and invalid scrypt parameters before startup.
        check_password_hash(value, "")
    except (TypeError, ValueError, OverflowError):
        return False
    return True


def validate_startup_config(
    config: IntentSecurityConfig, database_uri: str | None
) -> None:
    errors = set(config._parse_errors)

    if config.environment not in {"development", "test", "production"}:
        errors.add("AI4SE_ENV")
    if config.access_mode not in {"restricted", "public-readonly", "local-dev"}:
        errors.add("INTENT_ACCESS_MODE")
    if config.proxy_topology is not None and config.proxy_topology not in {
        "managed",
        "local-host",
    }:
        errors.add("INTENT_PROXY_TOPOLOGY")

    origin = _parse_url(config.public_origin)
    if origin is None or _canonical_origin(config.public_origin) is None:
        errors.add("INTENT_PUBLIC_ORIGIN")

    if config.access_mode in {"restricted", "public-readonly"}:
        if (
            not _has_minimum_utf8_length(config.secret_key, 32)
            or config.secret_key in _REJECTED_SECRETS
        ):
            errors.add("SECRET_KEY")
        if not _is_werkzeug_password_hash(config.admin_password_hash):
            errors.add("INTENT_TESTER_ADMIN_PASSWORD_HASH")

    if config.access_mode == "local-dev":
        if config.environment == "production":
            errors.add("INTENT_ACCESS_MODE")
        if origin is None or origin.hostname not in _LOOPBACK_HOSTS:
            errors.add("INTENT_PUBLIC_ORIGIN")
        if config.execution_enabled and config.proxy_topology not in {
            "managed",
            "local-host",
        }:
            errors.add("INTENT_PROXY_TOPOLOGY")

    if config.environment == "production":
        if config.access_mode not in {"restricted", "public-readonly"}:
            errors.add("INTENT_ACCESS_MODE")
        if origin is None or origin.scheme != "https":
            errors.add("INTENT_PUBLIC_ORIGIN")
        if config.execution_enabled and config.proxy_topology != "managed":
            errors.add("INTENT_PROXY_TOPOLOGY")

        database_value = _trimmed_string(database_uri)
        try:
            database = urlsplit(database_value) if database_value else None
            if database is not None:
                database.port
        except ValueError:
            database = None
        if (
            database is None
            or database.scheme.startswith("sqlite")
            or database.hostname is None
            or not _trimmed_string(database.username)
            or not _trimmed_string(database.password)
            or "change_me_in_production" in database_value
        ):
            errors.add("DATABASE_URL")

    if config.execution_enabled:
        if config.proxy_topology not in {"managed", "local-host"}:
            errors.add("INTENT_PROXY_TOPOLOGY")
        if (
            not _has_minimum_utf8_length(config.proxy_token, 32)
            or config.proxy_token in _REJECTED_SECRETS
        ):
            errors.add("INTENT_PROXY_TOKEN")

        if config.provider_api_key is None or (
            config.environment == "production"
            and config.provider_api_key in _REJECTED_PRODUCTION_API_KEYS
        ):
            errors.add("OPENAI_API_KEY")

        provider_url = _parse_url(config.provider_base_url)
        if provider_url is None or (
            config.environment == "production" and provider_url.scheme != "https"
        ):
            errors.add("OPENAI_BASE_URL")

        if config.provider_model is None:
            errors.add("MIDSCENE_MODEL_NAME")

    if errors:
        raise IntentSecurityConfigurationError(
            "Invalid Intent Tester configuration: " + ", ".join(sorted(errors))
        )
