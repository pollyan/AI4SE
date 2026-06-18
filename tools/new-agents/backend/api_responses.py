from flask import Response, jsonify


DEFAULT_LLM_CONFIG_MISSING_MESSAGE = (
    "系统未配置默认 LLM，请维护后端默认 LLM 配置后重试"
)


def json_error_response(message: str, status_code: int) -> tuple[Response, int]:
    return jsonify({"error": message}), status_code


def default_llm_config_missing_response() -> tuple[Response, int]:
    return json_error_response(DEFAULT_LLM_CONFIG_MISSING_MESSAGE, 503)
