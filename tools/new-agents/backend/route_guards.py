from flask import current_app
from flask.typing import ResponseReturnValue

from api_responses import default_llm_config_missing_response
from api_responses import json_error_response
from config_admin_auth import ServiceCredentialCollisionError
from config_service import get_active_default_llm_config
from models import LlmConfig


def require_default_llm_config(
    request_id: str,
    *,
    context: str,
) -> tuple[LlmConfig | None, ResponseReturnValue | None]:
    try:
        config = get_active_default_llm_config()
    except ServiceCredentialCollisionError:
        current_app.logger.error(
            f"[{request_id}] Service credentials collide for {context}"
        )
        return None, json_error_response("服务认证未正确配置", 503)

    if config:
        return config, None

    current_app.logger.warning(f"[{request_id}] No LLM config found for {context}")
    return None, default_llm_config_missing_response()
