from flask import Blueprint, jsonify, request
from werkzeug.exceptions import HTTPException

from api_responses import json_error_response
from request_schemas import (
    RequestValidationError,
    map_json_request_error,
    read_json_request_body,
)
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


def _test_asset_intent_tester_error_status(message: str) -> int:
    if (
        message.startswith("未知测试资产集:")
        or message.startswith("未知测试用例:")
        or message.startswith("测试用例尚未导入 intent-tester:")
    ):
        return 404
    return 400


def _test_asset_risk_error_status(message: str) -> int:
    if (
        message.startswith("未知测试资产集:")
        or message.startswith("未知风险:")
    ):
        return 404
    return 400


def register_test_asset_routes(api_bp: Blueprint) -> None:
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
    def agent_test_assets_intent_tester_execution_record(
        collection_id: int,
        case_id: str,
    ):
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
    def agent_test_assets_intent_tester_result_record(
        collection_id: int,
        case_id: str,
    ):
        """Persist a compact intent-tester execution result snapshot for a source case."""
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
