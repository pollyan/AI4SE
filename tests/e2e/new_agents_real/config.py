from __future__ import annotations

import hmac
from collections.abc import Callable, Iterator, Mapping, MutableMapping
from contextlib import contextmanager
from ipaddress import ip_address
from pathlib import Path
from typing import Protocol, TypeVar
from urllib.parse import urlsplit

from dotenv import dotenv_values

REAL_LLM_ENV_NAMES = (
    "NEW_AGENTS_SMOKE_API_KEY",
    "NEW_AGENTS_SMOKE_BASE_URL",
    "NEW_AGENTS_SMOKE_MODEL",
)
BACKEND_LLM_ENV_NAMES = (
    "NEW_AGENTS_DEFAULT_LLM_API_KEY",
    "NEW_AGENTS_DEFAULT_LLM_BASE_URL",
    "NEW_AGENTS_DEFAULT_LLM_MODEL",
)
FRONTEND_OS_ENV_NAMES = (
    "PATH",
    "HOME",
    "TMPDIR",
    "TMP",
    "TEMP",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "SHELL",
    "USER",
    "LOGNAME",
)
BACKEND_OS_ENV_NAMES = (*FRONTEND_OS_ENV_NAMES, "PYTHONPATH")
PLAYWRIGHT_DRIVER_OS_ENV_NAMES = (
    *FRONTEND_OS_ENV_NAMES,
    "PLAYWRIGHT_BROWSERS_PATH",
    "PLAYWRIGHT_NODEJS_PATH",
)


class _StoppablePlaywright(Protocol):
    def stop(self) -> None: ...


_PlaywrightT = TypeVar("_PlaywrightT", bound=_StoppablePlaywright, covariant=True)


class _PlaywrightManager(Protocol[_PlaywrightT]):
    def start(self) -> _PlaywrightT: ...


def build_secret_free_browser_environment(
    environ: Mapping[str, str],
) -> dict[str, str]:
    return {name: environ[name] for name in FRONTEND_OS_ENV_NAMES if name in environ}


@contextmanager
def secret_free_playwright_driver_environment(
    environ: MutableMapping[str, str],
) -> Iterator[None]:
    original_environment = dict(environ)
    driver_environment = {
        name: original_environment[name]
        for name in PLAYWRIGHT_DRIVER_OS_ENV_NAMES
        if name in original_environment
    }
    environ.clear()
    environ.update(driver_environment)
    try:
        yield
    finally:
        environ.clear()
        environ.update(original_environment)


@contextmanager
def secret_free_sync_playwright(
    playwright_factory: Callable[[], _PlaywrightManager[_PlaywrightT]],
    environ: MutableMapping[str, str],
) -> Iterator[_PlaywrightT]:
    playwright = start_secret_free_playwright(playwright_factory, environ)
    try:
        yield playwright
    finally:
        playwright.stop()


def start_secret_free_playwright(
    playwright_factory: Callable[[], _PlaywrightManager[_PlaywrightT]],
    environ: MutableMapping[str, str],
) -> _PlaywrightT:
    with secret_free_playwright_driver_environment(environ):
        return playwright_factory().start()


class RealLlmConfigurationError(ValueError):
    def __init__(
        self,
        missing_names: tuple[str, ...] = (),
        *,
        invalid_names: tuple[str, ...] = (),
    ):
        self.missing_names = missing_names
        self.invalid_names = invalid_names
        if missing_names:
            message = "missing required real-model configuration: " + ", ".join(
                missing_names
            )
        else:
            message = "invalid real-model configuration: " + ", ".join(invalid_names)
        super().__init__(message)


def _is_loopback_host(hostname: str | None) -> bool:
    if hostname == "localhost":
        return True
    try:
        return hostname is not None and ip_address(hostname).is_loopback
    except ValueError:
        return False


def _validate_base_url(base_url: str) -> None:
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError:
        parsed = None
        port = None
    if (
        parsed is None
        or parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or (parsed.scheme == "http" and not _is_loopback_host(parsed.hostname))
        or parsed.username is not None
        or parsed.password is not None
        or "?" in base_url
        or "#" in base_url
        or parsed.query
        or parsed.fragment
        or (parsed.netloc.endswith(":") and port is None)
    ):
        raise RealLlmConfigurationError(invalid_names=(REAL_LLM_ENV_NAMES[1],))


class RealLlmConfig:
    __slots__ = ("_api_key", "base_url", "model")

    def __init__(self, api_key: str, base_url: str, model: str):
        _validate_base_url(base_url)
        self._api_key = api_key
        self.base_url = base_url
        self.model = model

    def __repr__(self) -> str:
        return (
            "RealLlmConfig(api_key='<redacted>', "
            "base_url='<configured>', model='<configured>')"
        )

    def backend_environment(self) -> dict[str, str]:
        return {
            BACKEND_LLM_ENV_NAMES[0]: self._api_key,
            BACKEND_LLM_ENV_NAMES[1]: self.base_url,
            BACKEND_LLM_ENV_NAMES[2]: self.model,
        }

    def uses_api_key(self, candidate: str) -> bool:
        return bool(candidate) and hmac.compare_digest(self._api_key, candidate)

    def real_test_environment(self) -> dict[str, str]:
        return {
            REAL_LLM_ENV_NAMES[0]: self._api_key,
            REAL_LLM_ENV_NAMES[1]: self.base_url,
            REAL_LLM_ENV_NAMES[2]: self.model,
        }

    def redaction_secrets(self) -> tuple[str, ...]:
        return tuple(sorted({self._api_key, self.base_url}, key=len, reverse=True))


def load_real_llm_config(
    root: Path,
    environ: Mapping[str, str],
) -> RealLlmConfig:
    file_values = {
        key: str(value)
        for key, value in dotenv_values(root / ".env").items()
        if value is not None
    }
    values = {**file_values, **dict(environ)}
    normalized = {
        name: str(values.get(name, "")).strip() for name in REAL_LLM_ENV_NAMES
    }
    missing = tuple(name for name, value in normalized.items() if not value)
    if missing:
        raise RealLlmConfigurationError(missing)
    return RealLlmConfig(
        api_key=normalized[REAL_LLM_ENV_NAMES[0]],
        base_url=normalized[REAL_LLM_ENV_NAMES[1]],
        model=normalized[REAL_LLM_ENV_NAMES[2]],
    )


def build_child_environments(
    config: RealLlmConfig,
    environ: Mapping[str, str],
) -> tuple[dict[str, str], dict[str, str]]:
    frontend_environment = {
        name: environ[name] for name in FRONTEND_OS_ENV_NAMES if name in environ
    }
    backend_environment = {
        **{name: environ[name] for name in BACKEND_OS_ENV_NAMES if name in environ},
        "FLASK_SKIP_DOTENV": "1",
        **config.backend_environment(),
    }
    return backend_environment, frontend_environment
