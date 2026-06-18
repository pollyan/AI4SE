from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from api_responses import json_error_response
from config_service import get_default_llm_config_payload
from mermaid_repair_service import MermaidRepairError, repair_mermaid_code
from route_guards import require_default_llm_config
from request_schemas import (
    RequestValidationError,
    map_json_request_error,
    parse_agent_run_stream_request,
    parse_mermaid_repair_request,
    read_json_request_body,
)
from sse_response import build_sse_response
from stream_services import stream_agent_run_events


api_bp = Blueprint("new_agents_api", __name__, url_prefix="/api")


def _read_json_body():
    try:
        return read_json_request_body(
            request.get_data(cache=True),
            request.get_json,
        )
    except HTTPException as e:
        validation_error = map_json_request_error(e)
        if validation_error is not None:
            raise validation_error from e
        raise


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "new-agents-backend"})


@api_bp.route("/config", methods=["GET"])
def get_default_config():
    """获取系统默认模型配置（不返回 API Key）"""
    try:
        return jsonify(get_default_llm_config_payload()), 200
    except SQLAlchemyError as e:
        current_app.logger.error(f"[{g.request_id}] Error getting config: {str(e)}")
        return json_error_response("获取配置失败", 500)


@api_bp.route("/agent/runs/stream", methods=["POST"])
def agent_runs_stream():
    """Experimental structured Agent Runtime endpoint."""
    request_id = g.request_id
    try:
        agent_request = parse_agent_run_stream_request(_read_json_body())
    except RequestValidationError as e:
        return json_error_response(str(e), 400)

    config, error_response = require_default_llm_config(
        request_id,
        context="agent runtime",
    )
    if error_response:
        return error_response

    return build_sse_response(
        stream_agent_run_events(
            agent_request,
            api_key=config.api_key,
            base_url=config.base_url,
            model_name=config.model,
        )
    )


@api_bp.route("/utils/mermaid/repair", methods=["POST"])
def mermaid_repair():
    """Repair a Mermaid code block through the configured LLM."""
    request_id = g.request_id
    try:
        repair_request = parse_mermaid_repair_request(_read_json_body())
    except RequestValidationError as e:
        return json_error_response(str(e), 400)

    config, error_response = require_default_llm_config(
        request_id,
        context="mermaid repair",
    )
    if error_response:
        return error_response

    try:
        repaired_code = repair_mermaid_code(
            repair_request,
            api_key=config.api_key,
            base_url=config.base_url,
            model_name=config.model,
        )
    except MermaidRepairError as e:
        current_app.logger.warning(
            f"[{request_id}] Mermaid repair failed validation: {str(e)}"
        )
        return json_error_response(str(e), 502)

    return jsonify({"repairedCode": repaired_code}), 200
