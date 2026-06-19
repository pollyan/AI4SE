from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from api_responses import json_error_response
from config_service import (
    build_default_llm_config_payload,
    check_default_llm_config,
    get_default_llm_config_payload,
    upsert_default_llm_config,
)
from mermaid_repair_service import MermaidRepairError, repair_mermaid_code
from route_guards import require_default_llm_config
from run_persistence import (
    AgentRunPersistence,
    ArtifactVersionConflictError,
    get_run_snapshot,
    get_runtime_observability_summary,
    list_agent_runs,
    replace_artifact_collaboration_state,
    update_context_summary,
    update_run_artifact,
    upsert_manual_decision_summary,
)
from request_schemas import (
    RequestValidationError,
    map_json_request_error,
    parse_default_llm_config_update_request,
    parse_agent_run_stream_request,
    parse_mermaid_repair_request,
    read_json_request_body,
)
from sse_response import build_sse_response
from stream_services import stream_agent_run_events
from test_assets import (
    create_lisa_test_asset_risk,
    delete_lisa_test_asset_risk,
    export_lisa_test_assets,
    get_lisa_test_asset_collection,
    materialize_lisa_test_assets,
    record_lisa_test_asset_intent_tester_case,
    record_lisa_test_asset_intent_tester_execution,
    record_lisa_test_asset_intent_tester_result,
    update_lisa_test_asset_issue_status,
    update_lisa_test_asset_risk,
    update_lisa_test_asset_risk_by_id,
    update_lisa_test_case_asset,
    update_lisa_test_point_asset,
)
from workflow_handoffs import export_run_handoffs, start_workflow_handoff


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


@api_bp.route("/config", methods=["POST"])
def update_default_config():
    """维护系统默认模型配置（不返回 API Key）。"""
    try:
        update = parse_default_llm_config_update_request(_read_json_body())
        config = upsert_default_llm_config(update)
        return jsonify(build_default_llm_config_payload(config)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        return json_error_response(str(e), 400)
    except SQLAlchemyError as e:
        current_app.logger.error(f"[{g.request_id}] Error updating config: {str(e)}")
        return json_error_response("更新配置失败", 500)


@api_bp.route("/config/check", methods=["POST"])
def check_default_config():
    """Check whether the default LLM config can reach the configured model."""
    config, error_response = require_default_llm_config(
        g.request_id,
        context="config check",
    )
    if error_response:
        return error_response
    return jsonify(check_default_llm_config(config)), 200


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
            persistence=AgentRunPersistence(),
        )
    )


@api_bp.route("/agent/runs", methods=["GET"])
def agent_runs_list():
    """Return recent persisted Agent Runtime runs."""
    workflow_id = request.args.get("workflowId")
    limit_arg = request.args.get("limit", "20")
    offset_arg = request.args.get("offset", "0")
    query_text = request.args.get("query")
    try:
        limit = int(limit_arg)
    except ValueError:
        return json_error_response("limit 必须是整数", 400)
    try:
        offset = int(offset_arg)
    except ValueError:
        return json_error_response("offset 必须是整数", 400)
    try:
        return jsonify(
            list_agent_runs(
                workflow_id=workflow_id,
                limit=limit,
                offset=offset,
                query_text=query_text,
            )
        ), 200
    except ValueError as e:
        return json_error_response(str(e), 400)


@api_bp.route("/agent/observability", methods=["GET"])
def agent_observability():
    """Return basic Agent Runtime observability metrics."""
    limit_arg = request.args.get("limit", "20")
    workflow_id = request.args.get("workflowId")
    stage_id = request.args.get("stageId")
    try:
        limit = int(limit_arg)
    except ValueError:
        return json_error_response("limit 必须是整数", 400)
    try:
        return jsonify(
            get_runtime_observability_summary(
                limit=limit,
                workflow_id=workflow_id,
                stage_id=stage_id,
            )
        ), 200
    except ValueError as e:
        return json_error_response(str(e), 400)


@api_bp.route("/agent/runs/<run_id>", methods=["GET"])
def agent_run_snapshot(run_id: str):
    """Return a persisted Agent Runtime run snapshot."""
    try:
        return jsonify(get_run_snapshot(run_id)), 200
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route("/agent/runs/<run_id>/context-summaries", methods=["PATCH"])
def agent_run_context_summary_update(run_id: str):
    """Update an existing persisted context summary for a run."""
    try:
        patch = _read_json_body()
        return jsonify(update_context_summary(run_id, patch)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        status_code = 404 if (
            message.startswith("未知 runId:")
            or message.startswith("未知上下文摘要:")
        ) else 400
        return json_error_response(message, status_code)


@api_bp.route("/agent/runs/<run_id>/artifacts", methods=["POST"])
def agent_run_artifact_update(run_id: str):
    """Create a new editable artifact version for a persisted run."""
    try:
        patch = _read_json_body()
        return jsonify(update_run_artifact(run_id, patch)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ArtifactVersionConflictError as e:
        return jsonify({
            "error": str(e),
            "currentArtifact": e.current_artifact,
        }), 409
    except ValueError as e:
        message = str(e)
        status_code = 404 if message.startswith("未知 runId:") else 400
        return json_error_response(message, status_code)


@api_bp.route("/agent/runs/<run_id>/artifact-collaboration", methods=["PUT"])
def agent_run_artifact_collaboration_update(run_id: str):
    """Replace artifact collaboration metadata for a persisted run."""
    try:
        patch = _read_json_body()
        return jsonify(replace_artifact_collaboration_state(run_id, patch)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        status_code = 404 if message.startswith("未知 runId:") else 400
        return json_error_response(message, status_code)


@api_bp.route("/agent/runs/<run_id>/context-summaries/decisions", methods=["POST"])
def agent_run_decision_summary_create(run_id: str):
    """Create or update the current run's manual decision summary."""
    try:
        patch = _read_json_body()
        return jsonify(upsert_manual_decision_summary(run_id, patch)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        status_code = 404 if message.startswith("未知 runId:") else 400
        return json_error_response(message, status_code)


@api_bp.route("/agent/runs/<run_id>/test-assets", methods=["GET"])
def agent_run_test_assets(run_id: str):
    """Return Lisa test assets exported from a TEST_DESIGN/CASES artifact."""
    try:
        return jsonify(export_lisa_test_assets(run_id)), 200
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route("/agent/runs/<run_id>/test-assets/materialize", methods=["POST"])
def agent_run_test_assets_materialize(run_id: str):
    """Persist Lisa test assets from the current TEST_DESIGN/CASES artifact."""
    try:
        return jsonify(materialize_lisa_test_assets(run_id)), 200
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route("/agent/test-assets/<int:collection_id>", methods=["GET"])
def agent_test_assets_collection(collection_id: int):
    """Return a materialized Lisa test asset collection."""
    try:
        return jsonify(get_lisa_test_asset_collection(collection_id)), 200
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/test-cases/<case_id>",
    methods=["PATCH"],
)
def agent_test_assets_case_update(collection_id: int, case_id: str):
    """Create a new editable version for a materialized Lisa test case."""
    try:
        patch = _read_json_body()
        return jsonify(update_lisa_test_case_asset(collection_id, case_id, patch)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/issues/<int:issue_id>",
    methods=["PATCH"],
)
def agent_test_assets_issue_status_update(collection_id: int, issue_id: int):
    """Update a persisted Lisa test asset issue triage status."""
    try:
        patch = _read_json_body()
        return jsonify(
            update_lisa_test_asset_issue_status(collection_id, issue_id, patch)
        ), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        return json_error_response(str(e), 404)


def _test_asset_intent_tester_error_status(message: str) -> int:
    if (
        message.startswith("未知测试资产集:")
        or message.startswith("未知测试用例:")
        or message.startswith("测试用例尚未导入 intent-tester:")
    ):
        return 404
    return 400


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/intent-tester/cases/<case_id>",
    methods=["PATCH"],
)
def agent_test_assets_intent_tester_case_record(collection_id: int, case_id: str):
    """Persist the intent-tester testcase mapped to a Lisa source case."""
    try:
        patch = _read_json_body()
        return jsonify(
            record_lisa_test_asset_intent_tester_case(
                collection_id,
                case_id,
                patch,
            )
        ), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        return json_error_response(
            message,
            _test_asset_intent_tester_error_status(message),
        )


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/intent-tester/cases/<case_id>/execution",
    methods=["PATCH"],
)
def agent_test_assets_intent_tester_execution_record(collection_id: int, case_id: str):
    """Persist the latest intent-tester execution summary for a Lisa source case."""
    try:
        patch = _read_json_body()
        return jsonify(
            record_lisa_test_asset_intent_tester_execution(
                collection_id,
                case_id,
                patch,
            )
        ), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        return json_error_response(
            message,
            _test_asset_intent_tester_error_status(message),
        )


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/intent-tester/cases/<case_id>/result",
    methods=["PATCH"],
)
def agent_test_assets_intent_tester_result_record(collection_id: int, case_id: str):
    """Persist a compact intent-tester execution result snapshot for a Lisa source case."""
    try:
        patch = _read_json_body()
        return jsonify(
            record_lisa_test_asset_intent_tester_result(
                collection_id,
                case_id,
                patch,
            )
        ), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        return json_error_response(
            message,
            _test_asset_intent_tester_error_status(message),
        )


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/test-points/<path:test_point>",
    methods=["PATCH"],
)
def agent_test_assets_test_point_update(collection_id: int, test_point: str):
    """Update a persisted Lisa test point calibration."""
    try:
        patch = _read_json_body()
        return jsonify(
            update_lisa_test_point_asset(collection_id, test_point, patch)
        ), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        return json_error_response(str(e), 404)


def _test_asset_risk_error_status(message: str) -> int:
    if (
        message.startswith("未知测试资产集:")
        or message.startswith("未知风险:")
    ):
        return 404
    return 400


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/risks",
    methods=["POST"],
)
def agent_test_assets_risk_create(collection_id: int):
    """Create a manual Lisa risk in a materialized test asset collection."""
    try:
        patch = _read_json_body()
        return jsonify(create_lisa_test_asset_risk(collection_id, patch)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        return json_error_response(message, _test_asset_risk_error_status(message))


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/risks/by-id/<int:risk_id>",
    methods=["PATCH"],
)
def agent_test_assets_risk_update_by_id(collection_id: int, risk_id: int):
    """Update a persisted Lisa risk by stable risk id."""
    try:
        patch = _read_json_body()
        return jsonify(
            update_lisa_test_asset_risk_by_id(collection_id, risk_id, patch)
        ), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        return json_error_response(message, _test_asset_risk_error_status(message))


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/risks/by-id/<int:risk_id>",
    methods=["DELETE"],
)
def agent_test_assets_risk_delete(collection_id: int, risk_id: int):
    """Delete an unlinked Lisa risk by stable risk id."""
    try:
        return jsonify(delete_lisa_test_asset_risk(collection_id, risk_id)), 200
    except ValueError as e:
        message = str(e)
        return json_error_response(message, _test_asset_risk_error_status(message))


@api_bp.route(
    "/agent/test-assets/<int:collection_id>/risks/<path:risk>",
    methods=["PATCH"],
)
def agent_test_assets_risk_update(collection_id: int, risk: str):
    """Update a persisted Lisa risk lifecycle state."""
    try:
        patch = _read_json_body()
        return jsonify(update_lisa_test_asset_risk(collection_id, risk, patch)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route("/agent/runs/<run_id>/handoffs", methods=["GET"])
def agent_run_handoffs(run_id: str):
    """Return configured workflow handoff contexts for a persisted run."""
    try:
        return jsonify(export_run_handoffs(run_id)), 200
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route(
    "/agent/runs/<run_id>/handoffs/<handoff_id>/start",
    methods=["POST"],
)
def agent_run_handoff_start(run_id: str, handoff_id: str):
    """Create a persisted target run from a configured workflow handoff."""
    try:
        return jsonify(start_workflow_handoff(run_id, handoff_id)), 200
    except ValueError as e:
        return json_error_response(str(e), 404)


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
