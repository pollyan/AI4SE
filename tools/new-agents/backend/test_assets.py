import json

from models import (
    AgentTestAssetIntentTesterMapping,
    AgentRiskMatrixAsset,
    AgentTestAssetCollection,
    AgentTestAssetIssue,
    AgentTestCaseAsset,
    AgentTestCaseVersion,
    AgentTestPointAsset,
    db,
)
from run_persistence import get_run_snapshot


CASE_STAGE_ID = "CASES"
TEST_CASE_HEADERS = [
    "ID",
    "用例标题",
    "优先级",
    "测试维度",
    "关联测试点",
    "关联风险",
    "前置条件",
    "操作步骤",
    "测试数据",
    "预期结果",
]
COVERAGE_HEADERS = ["测试点", "优先级", "关联风险", "覆盖用例", "覆盖状态"]
TEST_CASE_PATCH_FIELDS = {
    "title",
    "priority",
    "dimension",
    "testPoint",
    "risk",
    "precondition",
    "steps",
    "testData",
    "expectedResult",
}
ISSUE_STATUSES = {"pending", "confirmed", "ignored"}
TEST_POINT_PATCH_FIELDS = {"priority", "risk", "status", "testCases"}
TEST_POINT_STATUSES = {"已覆盖", "部分覆盖", "未覆盖"}
RISK_PATCH_FIELDS = {"status", "owner", "note"}
RISK_CREATE_FIELDS = {"risk", "status", "owner", "note"}
RISK_BY_ID_PATCH_FIELDS = {"risk", "status", "owner", "note"}
RISK_STATUSES = {"open", "mitigating", "accepted", "closed"}
DEFAULT_RISK_LIFECYCLE = {"status": "open", "owner": "", "note": ""}
INTENT_TESTER_CASE_FIELDS = {"intentTesterCaseId", "intentTesterCaseName"}
INTENT_TESTER_EXECUTION_FIELDS = {
    "executionId",
    "status",
    "mode",
    "browser",
    "startTime",
    "endTime",
    "duration",
    "errorMessage",
}
INTENT_TESTER_RESULT_FIELDS = {
    "executionId",
    "status",
    "stepsTotal",
    "stepsPassed",
    "stepsFailed",
    "duration",
    "errorMessage",
    "steps",
}
INTENT_TESTER_RESULT_STEP_FIELDS = {
    "stepIndex",
    "description",
    "status",
    "errorMessage",
    "screenshotPath",
    "action",
}


def export_lisa_test_assets(run_id: str) -> dict:
    snapshot = get_run_snapshot(run_id)
    if snapshot["run"]["workflowId"] != "TEST_DESIGN":
        raise ValueError("仅支持 TEST_DESIGN workflow 导出 Lisa 测试资产")

    cases_artifact = next(
        (
            artifact
            for artifact in snapshot["artifacts"]
            if artifact["stageId"] == CASE_STAGE_ID
        ),
        None,
    )
    if cases_artifact is None:
        raise ValueError("缺少 TEST_DESIGN/CASES 测试用例集")

    markdown = cases_artifact["content"]
    case_rows = _parse_tables_with_headers(markdown, TEST_CASE_HEADERS)
    coverage_rows = _parse_tables_with_headers(markdown, COVERAGE_HEADERS)
    if not case_rows:
        raise ValueError("测试用例集缺少可解析的用例清单表格")
    test_cases = [_map_test_case(row) for row in case_rows]
    coverage_trace = [_map_coverage(row) for row in coverage_rows]

    return {
        "runId": snapshot["run"]["id"],
        "workflowId": snapshot["run"]["workflowId"],
        "sourceStageId": CASE_STAGE_ID,
        "sourceArtifactVersion": cases_artifact["versionNumber"],
        "testCases": test_cases,
        "coverageTrace": coverage_trace,
        "coverageSummary": _build_coverage_summary(test_cases, coverage_trace),
        "assetIssues": _build_asset_issues(test_cases, coverage_trace),
        "riskMatrix": _build_risk_matrix(test_cases, coverage_trace),
        "intentTesterDrafts": _build_intent_tester_drafts(test_cases),
    }


def materialize_lisa_test_assets(run_id: str) -> dict:
    exported = export_lisa_test_assets(run_id)
    collection = AgentTestAssetCollection.query.filter_by(
        run_id=run_id,
        source_stage_id=exported["sourceStageId"],
    ).first()
    if collection is None:
        collection = AgentTestAssetCollection(
            run_id=run_id,
            workflow_id=exported["workflowId"],
            source_stage_id=exported["sourceStageId"],
            source_artifact_version=exported["sourceArtifactVersion"],
        )
        db.session.add(collection)
        db.session.flush()
    else:
        collection.workflow_id = exported["workflowId"]
        collection.source_artifact_version = exported["sourceArtifactVersion"]
        collection.test_cases.clear()
        collection.test_points.clear()
        collection.issues.clear()
        db.session.flush()

    for test_case in exported["testCases"]:
        case_asset = AgentTestCaseAsset(
            collection_id=collection.id,
            case_id=test_case["id"],
        )
        db.session.add(case_asset)
        db.session.flush()
        version = _create_test_case_version(case_asset.id, 1, test_case)
        db.session.add(version)
        db.session.flush()
        case_asset.current_version_id = version.id

    for trace in exported["coverageTrace"]:
        db.session.add(
            AgentTestPointAsset(
                collection_id=collection.id,
                test_point=trace["testPoint"],
                priority=trace["priority"],
                risk=trace["risk"],
                test_cases_json=json.dumps(trace["testCases"], ensure_ascii=False),
                status=trace["status"],
            )
        )

    _sync_risk_matrix(collection, exported["riskMatrix"])

    for issue in exported["assetIssues"]:
        db.session.add(
            AgentTestAssetIssue(
                collection_id=collection.id,
                issue_type=issue["type"],
                case_id=issue.get("caseId"),
                test_point=issue.get("testPoint"),
                message=issue["message"],
                status="pending",
            )
        )

    _delete_stale_intent_tester_mappings(
        collection,
        {test_case["id"] for test_case in exported["testCases"]},
    )

    db.session.commit()
    return get_lisa_test_asset_collection(collection.id)


def get_lisa_test_asset_collection(collection_id: int) -> dict:
    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    return _serialize_collection(collection)


def update_lisa_test_case_asset(
    collection_id: int,
    case_id: str,
    patch: dict,
) -> dict:
    unknown_fields = sorted(set(patch) - TEST_CASE_PATCH_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知测试用例字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    test_case = AgentTestCaseAsset.query.filter_by(
        collection_id=collection_id,
        case_id=case_id,
    ).first()
    if test_case is None:
        raise ValueError(f"未知测试用例: {case_id}")

    current = _serialize_test_case(test_case)
    next_payload = {
        key: current[key]
        for key in [
            "title",
            "priority",
            "dimension",
            "testPoint",
            "risk",
            "precondition",
            "steps",
            "testData",
            "expectedResult",
        ]
    }
    for field, value in patch.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} 不能为空")
        next_payload[field] = value.strip()

    next_version_number = max(version.version_number for version in test_case.versions) + 1
    version = _create_test_case_version(
        test_case.id,
        next_version_number,
        {"id": case_id, **next_payload},
    )
    db.session.add(version)
    db.session.flush()
    test_case.current_version_id = version.id
    db.session.commit()
    return _serialize_test_case(test_case)


def update_lisa_test_asset_issue_status(
    collection_id: int,
    issue_id: int,
    patch: dict,
) -> dict:
    if set(patch) != {"status"}:
        raise ValueError("资产问题状态更新只支持 status 字段")
    status = patch["status"]
    if status not in ISSUE_STATUSES:
        raise ValueError(f"未知资产问题状态: {status}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    issue = AgentTestAssetIssue.query.filter_by(
        collection_id=collection_id,
        id=issue_id,
    ).first()
    if issue is None:
        raise ValueError(f"未知资产问题: {issue_id}")

    issue.status = status
    db.session.commit()
    return _serialize_asset_issue(issue)


def update_lisa_test_point_asset(
    collection_id: int,
    test_point: str,
    patch: dict,
) -> dict:
    unknown_fields = sorted(set(patch) - TEST_POINT_PATCH_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知测试点字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    point_asset = AgentTestPointAsset.query.filter_by(
        collection_id=collection_id,
        test_point=test_point,
    ).first()
    if point_asset is None:
        raise ValueError(f"未知测试点: {test_point}")

    for field in ["priority", "risk"]:
        if field in patch:
            value = patch[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} 不能为空")
            setattr(point_asset, field if field != "risk" else "risk", value.strip())

    if "status" in patch:
        status = patch["status"]
        if status not in TEST_POINT_STATUSES:
            raise ValueError(f"未知测试点覆盖状态: {status}")
        point_asset.status = status

    if "testCases" in patch:
        test_cases = patch["testCases"]
        if not isinstance(test_cases, list):
            raise ValueError("testCases 必须是字符串列表")
        normalized_cases = []
        for case_id in test_cases:
            if not isinstance(case_id, str) or not case_id.strip():
                raise ValueError("testCases 必须是字符串列表")
            normalized_cases.append(case_id.strip())
        point_asset.test_cases_json = json.dumps(normalized_cases, ensure_ascii=False)

    _rebuild_risk_matrix(collection)
    db.session.commit()
    return _serialize_test_point(point_asset)


def update_lisa_test_asset_risk(
    collection_id: int,
    risk: str,
    patch: dict,
) -> dict:
    unknown_fields = sorted(set(patch) - RISK_PATCH_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知风险字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    risk_asset = AgentRiskMatrixAsset.query.filter_by(
        collection_id=collection_id,
        risk=risk,
    ).first()
    if risk_asset is None:
        raise ValueError(f"未知风险: {risk}")

    _apply_risk_lifecycle_patch(risk_asset, patch)
    db.session.commit()
    return _serialize_risk_matrix_item(risk_asset)


def create_lisa_test_asset_risk(collection_id: int, patch: dict) -> dict:
    unknown_fields = sorted(set(patch) - RISK_CREATE_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知风险字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    risk_name = _require_risk_name(patch.get("risk"))
    existing = AgentRiskMatrixAsset.query.filter_by(
        collection_id=collection_id,
        risk=risk_name,
    ).first()
    if existing is not None:
        raise ValueError(f"风险已存在: {risk_name}")

    risk_asset = AgentRiskMatrixAsset(
        collection_id=collection.id,
        risk=risk_name,
        test_cases_json=json.dumps([], ensure_ascii=False),
        test_points_json=json.dumps([], ensure_ascii=False),
        priorities_json=json.dumps([], ensure_ascii=False),
        dimensions_json=json.dumps([], ensure_ascii=False),
        coverage_statuses_json=json.dumps([], ensure_ascii=False),
        is_manual=True,
        status=DEFAULT_RISK_LIFECYCLE["status"],
        owner=DEFAULT_RISK_LIFECYCLE["owner"],
        note=DEFAULT_RISK_LIFECYCLE["note"],
    )
    _apply_risk_lifecycle_patch(risk_asset, patch)
    db.session.add(risk_asset)
    db.session.commit()
    return _serialize_risk_matrix_item(risk_asset)


def update_lisa_test_asset_risk_by_id(
    collection_id: int,
    risk_id: int,
    patch: dict,
) -> dict:
    unknown_fields = sorted(set(patch) - RISK_BY_ID_PATCH_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知风险字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    risk_asset = AgentRiskMatrixAsset.query.filter_by(
        collection_id=collection_id,
        id=risk_id,
    ).first()
    if risk_asset is None:
        raise ValueError(f"未知风险: {risk_id}")

    if "risk" in patch:
        new_risk = _require_risk_name(patch["risk"])
        duplicate = AgentRiskMatrixAsset.query.filter_by(
            collection_id=collection_id,
            risk=new_risk,
        ).first()
        if duplicate is not None and duplicate.id != risk_asset.id:
            raise ValueError(f"风险已存在: {new_risk}")
        old_risk = risk_asset.risk
        if new_risk != old_risk:
            risk_asset.risk = new_risk
            _rename_risk_sources(collection, old_risk, new_risk)

    _apply_risk_lifecycle_patch(risk_asset, patch)
    _rebuild_risk_matrix(collection)
    db.session.commit()
    return _serialize_risk_matrix_item(risk_asset)


def delete_lisa_test_asset_risk(collection_id: int, risk_id: int) -> dict:
    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    risk_asset = AgentRiskMatrixAsset.query.filter_by(
        collection_id=collection_id,
        id=risk_id,
    ).first()
    if risk_asset is None:
        raise ValueError(f"未知风险: {risk_id}")

    if json.loads(risk_asset.test_cases_json) or json.loads(risk_asset.test_points_json):
        raise ValueError(f"风险仍有关联资产，无法删除: {risk_asset.risk}")

    db.session.delete(risk_asset)
    db.session.commit()
    return {"id": risk_id, "deleted": True}


def record_lisa_test_asset_intent_tester_case(
    collection_id: int,
    case_id: str,
    patch: dict,
) -> dict:
    unknown_fields = sorted(set(patch) - INTENT_TESTER_CASE_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知 intent-tester 映射字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    _require_test_case_asset(collection_id, case_id)

    intent_tester_case_id = patch.get("intentTesterCaseId")
    if not isinstance(intent_tester_case_id, int) or intent_tester_case_id <= 0:
        raise ValueError("intentTesterCaseId 必须是正整数")
    intent_tester_case_name = patch.get("intentTesterCaseName")
    if not isinstance(intent_tester_case_name, str) or not intent_tester_case_name.strip():
        raise ValueError("intentTesterCaseName 不能为空")

    mapping = AgentTestAssetIntentTesterMapping.query.filter_by(
        collection_id=collection_id,
        source_case_id=case_id,
    ).first()
    if mapping is None:
        mapping = AgentTestAssetIntentTesterMapping(
            collection_id=collection_id,
            source_case_id=case_id,
            intent_tester_case_id=intent_tester_case_id,
            intent_tester_case_name=intent_tester_case_name.strip(),
        )
        db.session.add(mapping)
    else:
        mapping.intent_tester_case_id = intent_tester_case_id
        mapping.intent_tester_case_name = intent_tester_case_name.strip()

    db.session.commit()
    return _serialize_intent_tester_mapping(mapping)


def record_lisa_test_asset_intent_tester_execution(
    collection_id: int,
    case_id: str,
    patch: dict,
) -> dict:
    unknown_fields = sorted(set(patch) - INTENT_TESTER_EXECUTION_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知 intent-tester 执行字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    _require_test_case_asset(collection_id, case_id)

    mapping = AgentTestAssetIntentTesterMapping.query.filter_by(
        collection_id=collection_id,
        source_case_id=case_id,
    ).first()
    if mapping is None:
        raise ValueError(f"测试用例尚未导入 intent-tester: {case_id}")

    execution_id = patch.get("executionId")
    status = patch.get("status")
    mode = patch.get("mode")
    browser = patch.get("browser")
    for field, value in [
        ("executionId", execution_id),
        ("status", status),
        ("mode", mode),
        ("browser", browser),
    ]:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} 不能为空")

    mapping.latest_execution_id = execution_id.strip()
    mapping.latest_execution_status = status.strip()
    mapping.latest_execution_mode = mode.strip()
    mapping.latest_execution_browser = browser.strip()
    mapping.latest_execution_start_time = _optional_string(
        patch.get("startTime"),
        "startTime",
    )
    mapping.latest_execution_end_time = _optional_string(
        patch.get("endTime"),
        "endTime",
    )
    duration = patch.get("duration")
    if duration is not None and not isinstance(duration, (int, float)):
        raise ValueError("duration 必须是数字")
    mapping.latest_execution_duration = duration
    mapping.latest_execution_error_message = _optional_string(
        patch.get("errorMessage"),
        "errorMessage",
    )

    db.session.commit()
    return _serialize_intent_tester_mapping(mapping)


def record_lisa_test_asset_intent_tester_result(
    collection_id: int,
    case_id: str,
    patch: dict,
) -> dict:
    unknown_fields = sorted(set(patch) - INTENT_TESTER_RESULT_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知 intent-tester 结果字段: {', '.join(unknown_fields)}")

    collection = db.session.get(AgentTestAssetCollection, collection_id)
    if collection is None:
        raise ValueError(f"未知测试资产集: {collection_id}")
    _require_test_case_asset(collection_id, case_id)

    mapping = AgentTestAssetIntentTesterMapping.query.filter_by(
        collection_id=collection_id,
        source_case_id=case_id,
    ).first()
    if mapping is None:
        raise ValueError(f"测试用例尚未导入 intent-tester: {case_id}")

    result_snapshot = _normalize_intent_tester_result_snapshot(patch)
    mapping.latest_execution_result_json = json.dumps(
        result_snapshot,
        ensure_ascii=False,
    )
    mapping.latest_execution_id = result_snapshot["executionId"]
    mapping.latest_execution_status = result_snapshot["status"]
    mapping.latest_execution_duration = result_snapshot["duration"]
    mapping.latest_execution_error_message = result_snapshot["errorMessage"]

    db.session.commit()
    return _serialize_intent_tester_mapping(mapping)


def _normalize_intent_tester_result_snapshot(patch: dict) -> dict:
    execution_id = patch.get("executionId")
    status = patch.get("status")
    for field, value in [("executionId", execution_id), ("status", status)]:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} 不能为空")

    duration = patch.get("duration")
    if duration is not None and not isinstance(duration, (int, float)):
        raise ValueError("duration 必须是数字")
    error_message = _optional_string(patch.get("errorMessage"), "errorMessage")

    steps = patch.get("steps", [])
    if not isinstance(steps, list):
        raise ValueError("steps 必须是列表")
    normalized_steps = [_normalize_intent_tester_result_step(step) for step in steps]
    failed_steps = [
        step for step in normalized_steps if step["status"] == "failed"
    ]
    screenshots = []
    for step in normalized_steps:
        screenshot_path = step["screenshotPath"]
        if screenshot_path and screenshot_path not in screenshots:
            screenshots.append(screenshot_path)

    steps_total = _optional_non_negative_integer(
        patch.get("stepsTotal"),
        "stepsTotal",
    )
    steps_passed = _optional_non_negative_integer(
        patch.get("stepsPassed"),
        "stepsPassed",
    )
    steps_failed = _optional_non_negative_integer(
        patch.get("stepsFailed"),
        "stepsFailed",
    )

    return {
        "executionId": execution_id.strip(),
        "status": status.strip(),
        "stepsTotal": len(normalized_steps) if steps_total is None else steps_total,
        "stepsPassed": (
            sum(1 for step in normalized_steps if step["status"] == "success")
            if steps_passed is None
            else steps_passed
        ),
        "stepsFailed": len(failed_steps) if steps_failed is None else steps_failed,
        "duration": duration,
        "errorMessage": error_message,
        "screenshots": screenshots,
        "failedSteps": failed_steps,
    }


def _normalize_intent_tester_result_step(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("steps 必须是对象列表")
    unknown_fields = sorted(set(value) - INTENT_TESTER_RESULT_STEP_FIELDS)
    if unknown_fields:
        raise ValueError(f"未知 intent-tester 步骤字段: {', '.join(unknown_fields)}")

    step_index = value.get("stepIndex")
    if not isinstance(step_index, int) or step_index < 0:
        raise ValueError("stepIndex 必须是非负整数")
    status = value.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ValueError("步骤 status 不能为空")
    description = value.get("description")
    if not isinstance(description, str):
        raise ValueError("description 必须是字符串")
    action = value.get("action")
    if action is not None and not isinstance(action, str):
        raise ValueError("action 必须是字符串")

    return {
        "stepIndex": step_index,
        "description": description,
        "status": status.strip(),
        "errorMessage": _optional_string(value.get("errorMessage"), "errorMessage"),
        "screenshotPath": _optional_string(
            value.get("screenshotPath"),
            "screenshotPath",
        ),
        "action": action,
    }


def _optional_non_negative_integer(value: object, field: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} 必须是非负整数")
    return value


def _require_test_case_asset(
    collection_id: int,
    case_id: str,
) -> AgentTestCaseAsset:
    test_case = AgentTestCaseAsset.query.filter_by(
        collection_id=collection_id,
        case_id=case_id,
    ).first()
    if test_case is None:
        raise ValueError(f"未知测试用例: {case_id}")
    return test_case


def _optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是字符串")
    return value


def _require_risk_name(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("risk 不能为空")
    normalized = _normalize_risk(value)
    if normalized is None:
        raise ValueError("risk 不能为空")
    return normalized


def _apply_risk_lifecycle_patch(
    risk_asset: AgentRiskMatrixAsset,
    patch: dict,
) -> None:
    if "status" in patch:
        status = patch["status"]
        if status not in RISK_STATUSES:
            raise ValueError(f"未知风险状态: {status}")
        risk_asset.status = status

    for field in ["owner", "note"]:
        if field not in patch:
            continue
        value = patch[field]
        if not isinstance(value, str):
            raise ValueError(f"{field} 必须是字符串")
        setattr(risk_asset, field, value.strip())


def _rename_risk_sources(
    collection: AgentTestAssetCollection,
    old_risk: str,
    new_risk: str,
) -> None:
    for point_asset in collection.test_points:
        if point_asset.risk == old_risk:
            point_asset.risk = new_risk

    for test_case in collection.test_cases:
        current = _serialize_test_case(test_case)
        if current["risk"] != old_risk:
            continue
        next_payload = {
            key: current[key]
            for key in [
                "title",
                "priority",
                "dimension",
                "testPoint",
                "risk",
                "precondition",
                "steps",
                "testData",
                "expectedResult",
            ]
        }
        next_payload["risk"] = new_risk
        next_version_number = max(
            version.version_number for version in test_case.versions
        ) + 1
        version = _create_test_case_version(
            test_case.id,
            next_version_number,
            {"id": test_case.case_id, **next_payload},
        )
        db.session.add(version)
        db.session.flush()
        test_case.current_version_id = version.id


def _create_test_case_version(
    test_case_id: int,
    version_number: int,
    test_case: dict,
) -> AgentTestCaseVersion:
    return AgentTestCaseVersion(
        test_case_id=test_case_id,
        version_number=version_number,
        title=test_case["title"],
        priority=test_case["priority"],
        dimension=test_case["dimension"],
        test_point=test_case["testPoint"],
        risk=test_case["risk"],
        precondition=test_case["precondition"],
        steps=test_case["steps"],
        test_data=test_case["testData"],
        expected_result=test_case["expectedResult"],
    )


def _serialize_collection(collection: AgentTestAssetCollection) -> dict:
    test_cases = [_serialize_test_case(test_case) for test_case in collection.test_cases]
    test_points = [_serialize_test_point(test_point) for test_point in collection.test_points]
    risk_matrix = [_serialize_risk_matrix_item(risk) for risk in collection.risk_matrix]
    issues = [_serialize_asset_issue(issue) for issue in collection.issues]
    intent_tester_mappings = [
        _serialize_intent_tester_mapping(mapping)
        for mapping in collection.intent_tester_mappings
    ]

    return {
        "id": collection.id,
        "runId": collection.run_id,
        "workflowId": collection.workflow_id,
        "sourceStageId": collection.source_stage_id,
        "sourceArtifactVersion": collection.source_artifact_version,
        "testCases": test_cases,
        "testPoints": test_points,
        "coverageTrace": test_points,
        "coverageSummary": _build_coverage_summary(test_cases, test_points),
        "assetIssues": issues,
        "riskMatrix": risk_matrix,
        "intentTesterDrafts": _build_intent_tester_drafts(test_cases),
        "intentTesterMappings": intent_tester_mappings,
    }


def _serialize_asset_issue(issue: AgentTestAssetIssue) -> dict:
    return {
        "id": issue.id,
        "type": issue.issue_type,
        **({"caseId": issue.case_id} if issue.case_id is not None else {}),
        **({"testPoint": issue.test_point} if issue.test_point is not None else {}),
        "message": issue.message,
        "status": issue.status,
    }


def _serialize_test_point(test_point: AgentTestPointAsset) -> dict:
    return {
        "testPoint": test_point.test_point,
        "priority": test_point.priority,
        "risk": test_point.risk,
        "testCases": json.loads(test_point.test_cases_json),
        "status": test_point.status,
    }


def _serialize_risk_matrix_item(risk: AgentRiskMatrixAsset) -> dict:
    return {
        "id": risk.id,
        "risk": risk.risk,
        "isManual": bool(risk.is_manual),
        "testCases": json.loads(risk.test_cases_json),
        "testPoints": json.loads(risk.test_points_json),
        "priorities": json.loads(risk.priorities_json),
        "dimensions": json.loads(risk.dimensions_json),
        "coverageStatuses": json.loads(risk.coverage_statuses_json),
        "status": risk.status,
        "owner": risk.owner,
        "note": risk.note,
    }


def _serialize_test_case(test_case: AgentTestCaseAsset) -> dict:
    current_version = db.session.get(
        AgentTestCaseVersion,
        test_case.current_version_id,
    )
    if current_version is None:
        raise ValueError(f"测试用例当前版本不存在: {test_case.case_id}")
    return {
        "id": test_case.case_id,
        **_serialize_test_case_version(current_version),
        "versionNumber": current_version.version_number,
        "versions": [
            _serialize_test_case_version(version)
            for version in test_case.versions
        ],
    }


def _serialize_test_case_version(version: AgentTestCaseVersion) -> dict:
    return {
        "versionNumber": version.version_number,
        "title": version.title,
        "priority": version.priority,
        "dimension": version.dimension,
        "testPoint": version.test_point,
        "risk": version.risk,
        "precondition": version.precondition,
        "steps": version.steps,
        "testData": version.test_data,
        "expectedResult": version.expected_result,
    }


def _serialize_intent_tester_mapping(
    mapping: AgentTestAssetIntentTesterMapping,
) -> dict:
    latest_execution = None
    if mapping.latest_execution_id is not None:
        latest_execution = {
            "executionId": mapping.latest_execution_id,
            "testCaseId": mapping.intent_tester_case_id,
            "status": mapping.latest_execution_status,
            "mode": mapping.latest_execution_mode,
            "browser": mapping.latest_execution_browser,
            "startTime": mapping.latest_execution_start_time,
            "endTime": mapping.latest_execution_end_time,
            "duration": mapping.latest_execution_duration,
            "errorMessage": mapping.latest_execution_error_message,
        }

    return {
        "sourceCaseId": mapping.source_case_id,
        "intentTesterCaseId": mapping.intent_tester_case_id,
        "intentTesterCaseName": mapping.intent_tester_case_name,
        "latestExecution": latest_execution,
        "latestResult": (
            json.loads(mapping.latest_execution_result_json)
            if mapping.latest_execution_result_json
            else None
        ),
    }


def _delete_stale_intent_tester_mappings(
    collection: AgentTestAssetCollection,
    source_case_ids: set[str],
) -> None:
    for mapping in list(collection.intent_tester_mappings):
        if mapping.source_case_id not in source_case_ids:
            db.session.delete(mapping)


def _rebuild_risk_matrix(collection: AgentTestAssetCollection) -> None:
    test_cases = [_serialize_test_case(test_case) for test_case in collection.test_cases]
    test_points = [_serialize_test_point(test_point) for test_point in collection.test_points]
    _sync_risk_matrix(collection, _build_risk_matrix(test_cases, test_points))


def _sync_risk_matrix(
    collection: AgentTestAssetCollection,
    derived_risks: list[dict],
) -> None:
    existing_by_name = {risk.risk: risk for risk in collection.risk_matrix}
    derived_names = set()

    for risk in derived_risks:
        derived_names.add(risk["risk"])
        risk_asset = existing_by_name.get(risk["risk"])
        if risk_asset is None:
            risk_asset = AgentRiskMatrixAsset(
                collection_id=collection.id,
                risk=risk["risk"],
                status=DEFAULT_RISK_LIFECYCLE["status"],
                owner=DEFAULT_RISK_LIFECYCLE["owner"],
                note=DEFAULT_RISK_LIFECYCLE["note"],
                is_manual=False,
            )
            db.session.add(risk_asset)
        _apply_risk_matrix_payload(risk_asset, risk)

    for risk_asset in list(collection.risk_matrix):
        if risk_asset.risk in derived_names:
            continue
        if risk_asset.is_manual:
            _apply_risk_matrix_payload(
                risk_asset,
                {
                    "risk": risk_asset.risk,
                    "testCases": [],
                    "testPoints": [],
                    "priorities": [],
                    "dimensions": [],
                    "coverageStatuses": [],
                },
            )
            continue
        db.session.delete(risk_asset)


def _apply_risk_matrix_payload(
    risk_asset: AgentRiskMatrixAsset,
    risk: dict,
) -> None:
    risk_asset.risk = risk["risk"]
    risk_asset.test_cases_json = json.dumps(risk["testCases"], ensure_ascii=False)
    risk_asset.test_points_json = json.dumps(risk["testPoints"], ensure_ascii=False)
    risk_asset.priorities_json = json.dumps(risk["priorities"], ensure_ascii=False)
    risk_asset.dimensions_json = json.dumps(risk["dimensions"], ensure_ascii=False)
    risk_asset.coverage_statuses_json = json.dumps(
        risk["coverageStatuses"],
        ensure_ascii=False,
    )


def _parse_tables_with_headers(markdown: str, required_headers: list[str]) -> list[dict]:
    rows = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        if not _is_table_row(lines[index]):
            index += 1
            continue

        headers = _split_table_row(lines[index])
        if not all(header in headers for header in required_headers):
            index += 1
            continue
        if index + 1 >= len(lines) or not _is_separator_row(lines[index + 1]):
            raise ValueError(f"Markdown 表格缺少分隔行: {', '.join(required_headers)}")

        index += 2
        while index < len(lines) and _is_table_row(lines[index]):
            values = _split_table_row(lines[index])
            if len(values) != len(headers):
                raise ValueError("Markdown 表格列数与表头不一致")
            rows.append(dict(zip(headers, values, strict=True)))
            index += 1
        continue
    return rows


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator_row(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(set(cell.replace(":", "").strip()) <= {"-"} for cell in cells)


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _map_test_case(row: dict) -> dict:
    return {
        "id": row["ID"],
        "title": row["用例标题"],
        "priority": row["优先级"],
        "dimension": row["测试维度"],
        "testPoint": row["关联测试点"],
        "risk": row["关联风险"],
        "precondition": row["前置条件"],
        "steps": row["操作步骤"],
        "testData": row["测试数据"],
        "expectedResult": row["预期结果"],
    }


def _map_coverage(row: dict) -> dict:
    return {
        "testPoint": row["测试点"],
        "priority": row["优先级"],
        "risk": row["关联风险"],
        "testCases": [
            item.strip()
            for item in row["覆盖用例"].split(",")
            if item.strip()
        ],
        "status": row["覆盖状态"],
    }


def _build_coverage_summary(
    test_cases: list[dict],
    coverage_trace: list[dict],
) -> dict:
    total_points = len(coverage_trace)
    covered = sum(1 for row in coverage_trace if row["status"] == "已覆盖")
    partial = sum(1 for row in coverage_trace if row["status"] == "部分覆盖")
    uncovered = sum(1 for row in coverage_trace if row["status"] == "未覆盖")

    return {
        "totalTestCases": len(test_cases),
        "totalTestPoints": total_points,
        "coveredTestPoints": covered,
        "partiallyCoveredTestPoints": partial,
        "uncoveredTestPoints": uncovered,
        "coverageRate": _coverage_rate(covered, total_points),
        "byPriority": _build_priority_coverage(coverage_trace),
    }


def _build_priority_coverage(coverage_trace: list[dict]) -> list[dict]:
    priorities = sorted({row["priority"] for row in coverage_trace})
    summary = []
    for priority in priorities:
        rows = [row for row in coverage_trace if row["priority"] == priority]
        covered = sum(1 for row in rows if row["status"] == "已覆盖")
        partial = sum(1 for row in rows if row["status"] == "部分覆盖")
        uncovered = sum(1 for row in rows if row["status"] == "未覆盖")
        summary.append(
            {
                "priority": priority,
                "total": len(rows),
                "covered": covered,
                "partial": partial,
                "uncovered": uncovered,
                "coverageRate": _coverage_rate(covered, len(rows)),
            }
        )
    return summary


def _coverage_rate(covered: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((covered / total) * 100, 2)


def _build_asset_issues(test_cases: list[dict], coverage_trace: list[dict]) -> list[dict]:
    issues = []
    known_case_ids = {test_case["id"] for test_case in test_cases}
    referenced_case_ids = set()

    for trace in coverage_trace:
        for case_id in trace["testCases"]:
            referenced_case_ids.add(case_id)
            if case_id not in known_case_ids:
                issues.append(
                    {
                        "type": "unknown_coverage_case",
                        "testPoint": trace["testPoint"],
                        "caseId": case_id,
                        "message": f"覆盖追溯引用了不存在的测试用例 {case_id}",
                    }
                )

    for case_id in sorted(known_case_ids - referenced_case_ids):
        issues.append(
            {
                "type": "orphan_test_case",
                "caseId": case_id,
                "message": f"测试用例 {case_id} 未被任何测试点覆盖追溯引用",
            }
        )

    return issues


def _build_risk_matrix(test_cases: list[dict], coverage_trace: list[dict]) -> list[dict]:
    risk_index: dict[str, dict[str, set[str]]] = {}

    for test_case in test_cases:
        risk = _normalize_risk(test_case["risk"])
        if risk is None:
            continue
        entry = _risk_entry(risk_index, risk)
        entry["testCases"].add(test_case["id"])
        entry["testPoints"].add(test_case["testPoint"])
        entry["priorities"].add(test_case["priority"])
        entry["dimensions"].add(test_case["dimension"])

    for trace in coverage_trace:
        risk = _normalize_risk(trace["risk"])
        if risk is None:
            continue
        entry = _risk_entry(risk_index, risk)
        entry["testPoints"].add(trace["testPoint"])
        entry["priorities"].add(trace["priority"])
        entry["coverageStatuses"].add(trace["status"])
        for case_id in trace["testCases"]:
            entry["testCases"].add(case_id)

    return [
        {
            "risk": risk,
            "testCases": sorted(entry["testCases"]),
            "testPoints": sorted(entry["testPoints"]),
            "priorities": sorted(entry["priorities"]),
            "dimensions": sorted(entry["dimensions"]),
            "coverageStatuses": sorted(entry["coverageStatuses"]),
        }
        for risk, entry in sorted(risk_index.items())
    ]


def _risk_entry(risk_index: dict[str, dict[str, set[str]]], risk: str) -> dict[str, set[str]]:
    if risk not in risk_index:
        risk_index[risk] = {
            "testCases": set(),
            "testPoints": set(),
            "priorities": set(),
            "dimensions": set(),
            "coverageStatuses": set(),
        }
    return risk_index[risk]


def _normalize_risk(risk: str) -> str | None:
    normalized = risk.strip()
    if not normalized or normalized in {"-", "无", "N/A", "n/a"}:
        return None
    return normalized


def _build_intent_tester_drafts(test_cases: list[dict]) -> list[dict]:
    return [_build_intent_tester_draft(test_case) for test_case in test_cases]


def _build_intent_tester_draft(test_case: dict) -> dict:
    return {
        "sourceCaseId": test_case["id"],
        "name": f"{test_case['id']} {test_case['title']}",
        "description": "\n".join(
            [
                "来源: New Agents Lisa TEST_DESIGN/CASES",
                f"测试点: {test_case['testPoint']}",
                f"关联风险: {test_case['risk']}",
                f"前置条件: {test_case['precondition']}",
                f"测试数据: {test_case['testData']}",
                f"预期结果: {test_case['expectedResult']}",
            ]
        ),
        "category": test_case["dimension"],
        "priority": _intent_tester_priority(test_case["priority"]),
        "tags": _intent_tester_tags(test_case),
        "steps": [
            {
                "action": "ai_assert",
                "params": {"prompt": f"确认前置条件成立：{test_case['precondition']}"},
            },
            {
                "action": "ai_assert",
                "params": {
                    "prompt": (
                        f"按自然语言测试步骤执行并观察：{test_case['steps']}；"
                        f"测试数据：{test_case['testData']}"
                    )
                },
            },
            {
                "action": "ai_assert",
                "params": {"prompt": f"验证预期结果：{test_case['expectedResult']}"},
            },
        ],
        "draftWarnings": [
            "该草稿由 Lisa Markdown 用例派生，导入 intent-tester 前需要人工校准页面 URL、定位语义和可执行步骤。"
        ],
    }


def _intent_tester_priority(priority: str) -> int:
    return {"P0": 1, "P1": 2, "P2": 3}.get(priority, 3)


def _intent_tester_tags(test_case: dict) -> list[str]:
    tags = ["lisa", "new-agents", test_case["id"], test_case["priority"]]
    risk = _normalize_risk(test_case["risk"])
    if risk is not None:
        tags.append(risk)
    return tags
