from flask import current_app
from flask.typing import ResponseReturnValue

from api_responses import default_llm_config_missing_response
from config_service import get_active_default_llm_config
from models import LlmConfig


def require_default_llm_config(
    request_id: str,
    *,
    context: str,
) -> tuple[LlmConfig | None, ResponseReturnValue | None]:
    config = get_active_default_llm_config()

    if config:
        return config, None

    current_app.logger.warning(f"[{request_id}] No LLM config found for {context}")
    return None, default_llm_config_missing_response()
