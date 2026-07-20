import os
from typing import Any

from config_admin_auth import ensure_provider_api_key_is_independent
from llm_client import LlmClientError, stream_chat_completion_content
from models import LlmConfig, db
from openai import APIError, AuthenticationError, RateLimitError
from request_schemas import DefaultLlmConfigUpdateRequest

DEFAULT_LLM_CONFIG_KEY = "default"
DEFAULT_LLM_CONFIG_KEY_ENV = "NEW_AGENTS_DEFAULT_LLM_CONFIG_KEY"
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_DESCRIPTION = "Environment default LLM config"


def get_default_llm_config_key() -> str:
    return _read_env_value(DEFAULT_LLM_CONFIG_KEY_ENV) or DEFAULT_LLM_CONFIG_KEY


def get_active_default_llm_config() -> LlmConfig | None:
    config = LlmConfig.query.filter_by(
        config_key=get_default_llm_config_key(),
        is_active=True,
    ).first()
    if config is not None:
        ensure_provider_api_key_is_independent(config.api_key)
    return config


def _read_env_value(name: str) -> str:
    return os.environ.get(name, "").strip()


def upsert_default_llm_config_from_env() -> LlmConfig | None:
    api_key = _read_env_value("NEW_AGENTS_DEFAULT_LLM_API_KEY")
    model = _read_env_value("NEW_AGENTS_DEFAULT_LLM_MODEL")
    if not api_key or not model:
        return None
    ensure_provider_api_key_is_independent(api_key)

    base_url = (
        _read_env_value("NEW_AGENTS_DEFAULT_LLM_BASE_URL") or DEFAULT_LLM_BASE_URL
    )
    description = (
        _read_env_value("NEW_AGENTS_DEFAULT_LLM_DESCRIPTION") or DEFAULT_LLM_DESCRIPTION
    )

    config_key = get_default_llm_config_key()
    config = LlmConfig.query.filter_by(config_key=config_key).first()
    if config is None:
        config = LlmConfig(config_key=config_key)
        db.session.add(config)

    config.api_key = api_key
    config.base_url = base_url
    config.model = model
    config.description = description
    config.is_active = True

    db.session.commit()
    return config


def build_default_llm_config_payload(
    config: LlmConfig | None,
) -> dict[str, Any]:
    if not config:
        return {"hasDefault": False}
    return {
        "hasDefault": True,
        "baseUrl": config.base_url,
        "model": config.model,
        "description": config.description,
    }


def get_default_llm_config_payload() -> dict[str, Any]:
    return build_default_llm_config_payload(get_active_default_llm_config())


def upsert_default_llm_config(
    update: DefaultLlmConfigUpdateRequest,
) -> LlmConfig:
    config_key = get_default_llm_config_key()
    config = LlmConfig.query.filter_by(config_key=config_key).first()
    if config is None:
        if not update.api_key:
            raise ValueError("apiKey 不能为空")
        config = LlmConfig(config_key=config_key)
        db.session.add(config)
    effective_api_key = update.api_key or config.api_key
    ensure_provider_api_key_is_independent(effective_api_key)
    if update.api_key:
        config.api_key = update.api_key

    config.base_url = update.base_url
    config.model = update.model
    config.description = update.description or DEFAULT_LLM_DESCRIPTION
    config.is_active = True

    db.session.commit()
    return config


def build_llm_config_check_candidate(
    update: DefaultLlmConfigUpdateRequest,
    saved_config: LlmConfig | None = None,
) -> LlmConfig:
    api_key = update.api_key or (saved_config.api_key if saved_config else None)
    if not api_key:
        raise ValueError("apiKey 不能为空")
    ensure_provider_api_key_is_independent(api_key)
    return LlmConfig(
        config_key=(
            saved_config.config_key if saved_config else get_default_llm_config_key()
        ),
        api_key=api_key,
        base_url=update.base_url,
        model=update.model,
        description=update.description or DEFAULT_LLM_DESCRIPTION,
        is_active=True,
    )


def build_default_llm_config_check_candidate(
    update: DefaultLlmConfigUpdateRequest,
) -> LlmConfig:
    return build_llm_config_check_candidate(
        update,
        get_active_default_llm_config(),
    )


def check_default_llm_config(config: LlmConfig) -> dict[str, Any]:
    try:
        response = "".join(
            stream_chat_completion_content(
                api_key=config.api_key,
                base_url=config.base_url,
                model=config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are checking whether the configured model is reachable.",
                    },
                    {
                        "role": "user",
                        "content": "Reply with ok.",
                    },
                ],
                temperature=0,
            )
        ).strip()
    except (LlmClientError, AuthenticationError, RateLimitError, APIError):
        return {
            "ok": False,
            "baseUrl": config.base_url,
            "model": config.model,
            "message": "模型连接检测失败",
        }

    if not response:
        return {
            "ok": False,
            "baseUrl": config.base_url,
            "model": config.model,
            "message": "模型返回为空",
        }

    return {
        "ok": True,
        "baseUrl": config.base_url,
        "model": config.model,
        "message": "模型配置可用",
    }
