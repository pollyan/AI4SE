import os
from typing import Any

from models import LlmConfig, db


DEFAULT_LLM_CONFIG_KEY = "default"
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_DESCRIPTION = "Environment default LLM config"


def get_active_default_llm_config() -> LlmConfig | None:
    return LlmConfig.query.filter_by(
        config_key=DEFAULT_LLM_CONFIG_KEY,
        is_active=True,
    ).first()


def _read_env_value(name: str) -> str:
    return os.environ.get(name, "").strip()


def upsert_default_llm_config_from_env() -> LlmConfig | None:
    api_key = _read_env_value("NEW_AGENTS_DEFAULT_LLM_API_KEY")
    model = _read_env_value("NEW_AGENTS_DEFAULT_LLM_MODEL")
    if not api_key or not model:
        return None

    base_url = (
        _read_env_value("NEW_AGENTS_DEFAULT_LLM_BASE_URL") or DEFAULT_LLM_BASE_URL
    )
    description = (
        _read_env_value("NEW_AGENTS_DEFAULT_LLM_DESCRIPTION")
        or DEFAULT_LLM_DESCRIPTION
    )

    config = LlmConfig.query.filter_by(config_key=DEFAULT_LLM_CONFIG_KEY).first()
    if config is None:
        config = LlmConfig(config_key=DEFAULT_LLM_CONFIG_KEY)
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
