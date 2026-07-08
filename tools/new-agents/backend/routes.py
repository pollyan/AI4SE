import re

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from agent_contracts import AgentTurnOutput, validate_agent_turn
from api_responses import DEFAULT_LLM_CONFIG_MISSING_CODE, json_error_response
from config_service import (
    build_default_llm_config_payload,
    build_default_llm_config_check_candidate,
    check_default_llm_config,
    get_default_llm_config_payload,
    upsert_default_llm_config,
)
from mermaid_repair_service import MermaidRepairError, repair_mermaid_code
from models import db
from route_guards import require_default_llm_config
from run_persistence import (
    AgentRunPersistence,
    ArtifactVersionConflictError,
    clone_agent_run,
    get_run_snapshot,
    get_runtime_observability_summary,
    list_agent_runs,
    record_runtime_config_issue,
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
from routes_test_assets import register_test_asset_routes
from story_handoff_packets import (
    create_story_handoff_packet,
    list_story_handoff_candidates,
    list_story_handoff_packets,
)
from workflow_handoffs import (
    export_run_handoffs,
    export_target_workflow_handoffs,
    start_workflow_handoff,
)


api_bp = Blueprint("new_agents_api", __name__, url_prefix="/api")
register_test_asset_routes(api_bp)

MERMAID_CODE_BLOCK_PATTERN = re.compile(
    r"```mermaid(?:[ \t].*)?\n[\s\S]*?```",
)


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


def _replace_mermaid_block_at_index(
    markdown: str,
    block_index: int,
    new_code: str,
) -> str | None:
    matches = list(MERMAID_CODE_BLOCK_PATTERN.finditer(markdown))
    if block_index < 0 or block_index >= len(matches):
        return None

    target = matches[block_index]
    replacement = f"```mermaid\n{new_code.strip()}\n```"
    if replacement == target.group(0):
        return markdown
    return (
        f"{markdown[:target.start()]}"
        f"{replacement}"
        f"{markdown[target.end():]}"
    )


def _validate_mermaid_repair_artifact_contract(
    repair_request,
    repaired_code: str,
) -> None:
    if not (
        repair_request.workflow_id
        and repair_request.stage_id
        and repair_request.current_artifact
        and repair_request.block_index is not None
    ):
        return

    candidate_artifact = _replace_mermaid_block_at_index(
        repair_request.current_artifact,
        repair_request.block_index,
        repaired_code,
    )
    if candidate_artifact is None:
        raise MermaidRepairError(
            "Mermaid repair artifact contract validation failed: "
            "target Mermaid block not found"
        )

    try:
        output = AgentTurnOutput.model_validate({
            "chat": "已完成 Mermaid 图表修复校验。",
            "artifact_update": {
                "type": "replace",
                "markdown": candidate_artifact,
            },
            "stage_action": None,
            "warnings": [],
        })
        validate_agent_turn(
            output,
            workflow_id=repair_request.workflow_id,
            current_stage_id=repair_request.stage_id,
        )
    except ValueError as e:
        raise MermaidRepairError(
            "Mermaid repair artifact contract validation failed: "
            f"{str(e)}"
        ) from e


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
    try:
        request_body = _read_json_body()
    except RequestValidationError as e:
        return json_error_response(str(e), 400)

    if request_body is not None:
        try:
            update = parse_default_llm_config_update_request(request_body)
            config = build_default_llm_config_check_candidate(update)
            return jsonify(check_default_llm_config(config)), 200
        except RequestValidationError as e:
            return json_error_response(str(e), 400)
        except ValueError as e:
            return json_error_response(str(e), 400)
        except SQLAlchemyError as e:
            current_app.logger.error(
                f"[{g.request_id}] Error checking temporary config: {str(e)}"
            )
            return json_error_response("模型检测失败", 500)

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
        try:
            record_runtime_config_issue(
                workflow_id=agent_request.workflow_id,
                stage_id=agent_request.stage_id,
                error_code=DEFAULT_LLM_CONFIG_MISSING_CODE,
                issue_scope="default_llm_config",
                route="/api/agent/runs/stream",
                request_id=request_id,
            )
        except SQLAlchemyError as e:
            current_app.logger.error(
                f"[{request_id}] Error recording runtime config issue: {str(e)}"
            )
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
    reuse_status = request.args.get("reuseStatus")
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
                reuse_status=reuse_status,
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


@api_bp.route("/agent/runs/<run_id>/clone", methods=["POST"])
def agent_run_clone(run_id: str):
    """Clone a persisted Agent Runtime run as a new active run."""
    try:
        cloned_run = clone_agent_run(run_id)
        return jsonify(get_run_snapshot(cloned_run.id)), 200
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
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(
            f"[{g.request_id}] Error updating artifact collaboration "
            f"for run {run_id}: {str(e)}"
        )
        return json_error_response("协作状态保存失败", 500)


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


@api_bp.route("/agent/runs/<run_id>/handoffs", methods=["GET"])
def agent_run_handoffs(run_id: str):
    """Return configured workflow handoff contexts for a persisted run."""
    try:
        return jsonify(export_run_handoffs(run_id)), 200
    except ValueError as e:
        return json_error_response(str(e), 404)


@api_bp.route("/agent/workflow-handoff-candidates", methods=["GET"])
def agent_workflow_handoff_candidates():
    """Return persisted upstream handoff candidates for a target workflow."""
    target_workflow_id = (request.args.get("targetWorkflowId") or "").strip()
    target_stage_id = (request.args.get("targetStageId") or "").strip() or None
    if not target_workflow_id:
        return json_error_response("targetWorkflowId 不能为空", 400)

    try:
        return jsonify(
            export_target_workflow_handoffs(
                target_workflow_id,
                target_stage_id,
            )
        ), 200
    except ValueError as e:
        return json_error_response(str(e), 400)


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


@api_bp.route("/agent/runs/<run_id>/story-handoff-candidates", methods=["GET"])
def agent_run_story_handoff_candidates(run_id: str):
    """Return ready stories that can generate single-story handoff packets."""
    stage_id = (request.args.get("stageId") or "SPRINT_PLAN").strip()
    try:
        return jsonify(list_story_handoff_candidates(run_id, stage_id)), 200
    except ValueError as e:
        message = str(e)
        status_code = 404 if message.startswith("未知 runId:") else 400
        return json_error_response(message, status_code)


@api_bp.route("/agent/runs/<run_id>/story-handoff-packets", methods=["GET"])
def agent_run_story_handoff_packets(run_id: str):
    """Return persisted single-story handoff packets for a run."""
    stage_id = (request.args.get("stageId") or "SPRINT_PLAN").strip()
    try:
        return jsonify(list_story_handoff_packets(run_id, stage_id)), 200
    except ValueError as e:
        message = str(e)
        status_code = 404 if message.startswith("未知 runId:") else 400
        return json_error_response(message, status_code)


@api_bp.route("/agent/runs/<run_id>/story-handoff-packets", methods=["POST"])
def agent_run_story_handoff_packet_create(run_id: str):
    """Create a persisted requirement-only packet for one ready story."""
    try:
        payload = _read_json_body()
        if not isinstance(payload, dict):
            return json_error_response("请求体必须是 JSON 对象", 400)
        stage_id = str(payload.get("stageId") or "SPRINT_PLAN").strip()
        story_id = str(payload.get("storyId") or "").strip()
        if not story_id:
            return json_error_response("storyId 不能为空", 400)
        return jsonify(create_story_handoff_packet(run_id, stage_id, story_id)), 200
    except RequestValidationError as e:
        return json_error_response(str(e), 400)
    except ValueError as e:
        message = str(e)
        status_code = 404 if message.startswith("未知 runId:") else 400
        return json_error_response(message, status_code)


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
        _validate_mermaid_repair_artifact_contract(
            repair_request,
            repaired_code,
        )
    except MermaidRepairError as e:
        current_app.logger.warning(
            f"[{request_id}] Mermaid repair failed validation: {str(e)}"
        )
        return json_error_response(str(e), 502)

    return jsonify({"repairedCode": repaired_code}), 200
