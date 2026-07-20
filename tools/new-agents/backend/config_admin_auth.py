"""Fail-closed helpers for the independent LLM configuration capability."""

from __future__ import annotations

import os
import hmac
from collections.abc import Mapping


class ServiceCredentialCollisionError(ValueError):
    """Raised when provider, runtime, and admin capabilities share a secret."""


def _environment_values(
    environment: Mapping[str, str] | None = None,
) -> tuple[str, str, str, str, bool]:
    values = os.environ if environment is None else environment
    proxy_api_key = (values.get("PROXY_API_KEY") or "").strip()
    config_admin_api_key = (values.get("NEW_AGENTS_CONFIG_ADMIN_API_KEY") or "").strip()
    provider_api_key = (values.get("NEW_AGENTS_DEFAULT_LLM_API_KEY") or "").strip()
    deployment_environment = (values.get("AI4SE_ENV") or "").strip().lower()
    explicit_local_opt_in = (
        values.get("NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED") or ""
    ).strip().lower() in {"1", "true", "yes"}
    return (
        proxy_api_key,
        config_admin_api_key,
        provider_api_key,
        deployment_environment,
        explicit_local_opt_in,
    )


def config_admin_keys_collide(
    environment: Mapping[str, str] | None = None,
) -> bool:
    proxy_api_key, config_admin_api_key, provider_api_key, _, _ = _environment_values(
        environment
    )
    credentials = [
        value
        for value in (proxy_api_key, config_admin_api_key, provider_api_key)
        if value
    ]
    return len(credentials) != len(set(credentials))


def browser_config_admin_available(
    environment: Mapping[str, str] | None = None,
) -> bool:
    (
        proxy_api_key,
        config_admin_api_key,
        _,
        deployment_environment,
        explicit_local_opt_in,
    ) = _environment_values(environment)
    return (
        deployment_environment in {"development", "test", "local"}
        and not proxy_api_key
        and not config_admin_api_key
        and explicit_local_opt_in
    )


def ensure_provider_api_key_is_independent(
    provider_api_key: str,
    environment: Mapping[str, str] | None = None,
) -> None:
    values = os.environ if environment is None else environment
    normalized_provider_key = (provider_api_key or "").strip()
    protected_credentials = (
        (values.get("PROXY_API_KEY") or "").strip(),
        (values.get("NEW_AGENTS_CONFIG_ADMIN_API_KEY") or "").strip(),
    )
    if normalized_provider_key and any(
        credential and hmac.compare_digest(normalized_provider_key, credential)
        for credential in protected_credentials
    ):
        raise ServiceCredentialCollisionError(
            "模型密钥不得与配置管理或运行时代理密钥复用"
        )
