import pytest

from request_schemas import (
    RequestValidationError,
    map_json_request_error,
    parse_mermaid_repair_request,
    parse_agent_run_stream_request,
    read_json_request_body,
)


class FakeHttpException(Exception):
    def __init__(self, code: int):
        self.code = code


def test_parse_agent_run_stream_request_accepts_alias_fields() -> None:
    parsed = parse_agent_run_stream_request({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "requestId": "req-alias",
    })

    assert parsed.prompt == "用户需求"
    assert parsed.system_prompt == "你是 Lisa。"
    assert parsed.workflow_id == "TEST_DESIGN"
    assert parsed.stage_id == "CLARIFY"
    assert parsed.run_id is None
    assert parsed.request_id


def test_parse_agent_run_stream_request_accepts_optional_run_id() -> None:
    parsed = parse_agent_run_stream_request({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "runId": " existing-run ",
        "requestId": "req-run",
    })

    assert parsed.run_id == "existing-run"


def test_parse_agent_run_stream_request_normalizes_client_request_identity() -> None:
    parsed = parse_agent_run_stream_request({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "requestId": " request-login-001 ",
    })

    assert parsed.request_id == "request-login-001"


def test_read_json_request_body_returns_none_for_empty_raw_body() -> None:
    assert read_json_request_body(b"", lambda: {"ignored": True}) is None


def test_read_json_request_body_delegates_non_empty_body_to_json_reader() -> None:
    assert read_json_request_body(b"{}", lambda: {"ok": True}) == {"ok": True}


def test_read_json_request_body_leaves_json_reader_exceptions_to_http_layer() -> None:
    def get_json():
        raise FakeHttpException(400)

    with pytest.raises(FakeHttpException) as exc_info:
        read_json_request_body(b"{broken", get_json)

    assert exc_info.value.code == 400


def test_map_json_request_error_maps_malformed_json_to_validation_error() -> None:
    mapped = map_json_request_error(FakeHttpException(400))

    assert isinstance(mapped, RequestValidationError)
    assert str(mapped) == "请求体不是合法 JSON"


def test_map_json_request_error_maps_non_json_content_type_to_validation_error() -> None:
    mapped = map_json_request_error(FakeHttpException(415))

    assert isinstance(mapped, RequestValidationError)
    assert str(mapped) == "请求体必须是 JSON 对象"


def test_map_json_request_error_ignores_unknown_http_errors() -> None:
    assert map_json_request_error(FakeHttpException(418)) is None


def test_parse_agent_run_stream_request_normalizes_workflow_and_stage_ids() -> None:
    parsed = parse_agent_run_stream_request({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": " TEST_DESIGN ",
        "stageId": " CLARIFY ",
        "requestId": "req-normalize",
    })

    assert parsed.workflow_id == "TEST_DESIGN"
    assert parsed.stage_id == "CLARIFY"


def test_parse_agent_run_stream_request_rejects_missing_request_identity() -> None:
    with pytest.raises(RequestValidationError, match="requestId 不能为空"):
        parse_agent_run_stream_request({
            "prompt": "用户需求",
            "systemPrompt": "你是 Lisa。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        })


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "prompt": "用户需求",
                "systemPrompt": "你是 Lisa。",
                    "workflowId": "UNKNOWN_WORKFLOW",
                    "stageId": "CLARIFY",
                    "requestId": "req-unknown-workflow",
            },
            "未知 workflowId: UNKNOWN_WORKFLOW",
        ),
        (
            {
                "prompt": "用户需求",
                "systemPrompt": "你是 Lisa。",
                    "workflowId": "TEST_DESIGN",
                    "stageId": "REPORT",
                    "requestId": "req-unknown-stage",
            },
            "workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT",
        ),
    ],
)
def test_parse_agent_run_stream_request_rejects_unknown_workflow_or_stage(
    payload: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(RequestValidationError) as exc_info:
        parse_agent_run_stream_request(payload)

    assert str(exc_info.value) == message


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "systemPrompt": "你是 Lisa。",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
            },
            "prompt 不能为空",
        ),
        (
            {
                "prompt": "用户需求",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
            },
            "systemPrompt 不能为空",
        ),
        (
            {
                "prompt": "用户需求",
                "systemPrompt": "你是 Lisa。",
                "stageId": "CLARIFY",
            },
            "workflowId 不能为空",
        ),
        (
            {
                "prompt": "用户需求",
                "systemPrompt": "你是 Lisa。",
                "workflowId": "TEST_DESIGN",
            },
            "stageId 不能为空",
        ),
        (
            {
                "prompt": "用户需求",
                "systemPrompt": "你是 Lisa。",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
                "runId": "   ",
            },
            "runId 不能为空",
        ),
    ],
)
def test_parse_agent_run_stream_request_rejects_missing_required_fields(
    payload: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(RequestValidationError) as exc_info:
        parse_agent_run_stream_request(payload)

    assert str(exc_info.value) == message


@pytest.mark.parametrize("payload", [[{}], "not-object"])
def test_parse_agent_run_stream_request_rejects_non_object_json(payload: object) -> None:
    with pytest.raises(RequestValidationError) as exc_info:
        parse_agent_run_stream_request(payload)  # type: ignore[arg-type]

    assert str(exc_info.value) == "请求体必须是 JSON 对象"


def test_parse_mermaid_repair_request_accepts_required_fields() -> None:
    parsed = parse_mermaid_repair_request({
        "brokenCode": "graph TD\nA-->",
        "errorMessage": "Syntax error",
        "blockIndex": 2,
    })

    assert parsed.broken_code == "graph TD\nA-->"
    assert parsed.error_message == "Syntax error"
    assert parsed.block_index == 2


def test_parse_mermaid_repair_request_accepts_artifact_contract_context() -> None:
    parsed = parse_mermaid_repair_request({
        "brokenCode": "graph TD\nA-->",
        "errorMessage": "Syntax error",
        "blockIndex": 0,
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "currentArtifact": "# 需求分析文档\n\n```mermaid\ngraph TD\nA-->\n```",
    })

    assert parsed.workflow_id == "TEST_DESIGN"
    assert parsed.stage_id == "CLARIFY"
    assert parsed.current_artifact.startswith("# 需求分析文档")


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (
            {
                "brokenCode": "graph TD\nA-->",
                "errorMessage": "Syntax error",
                "blockIndex": 0,
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
            },
            "artifact contract context 必须同时包含 workflowId、stageId、currentArtifact 和 blockIndex",
        ),
        (
            {
                "brokenCode": "graph TD\nA-->",
                "errorMessage": "Syntax error",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
                "currentArtifact": "# 需求分析文档",
            },
            "artifact contract context 必须同时包含 workflowId、stageId、currentArtifact 和 blockIndex",
        ),
        (
            {
                "brokenCode": "graph TD\nA-->",
                "errorMessage": "Syntax error",
                "blockIndex": 0,
                "workflowId": "TEST_DESIGN",
                "stageId": "UNKNOWN",
                "currentArtifact": "# 需求分析文档",
            },
            "workflowId 与 stageId 不匹配: TEST_DESIGN/UNKNOWN",
        ),
    ],
)
def test_parse_mermaid_repair_request_requires_complete_artifact_contract_context(
    payload: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(RequestValidationError, match=message):
        parse_mermaid_repair_request(payload)


def test_parse_mermaid_repair_request_rejects_negative_block_index() -> None:
    with pytest.raises(RequestValidationError) as exc_info:
        parse_mermaid_repair_request({
            "brokenCode": "graph TD\nA-->",
            "errorMessage": "Syntax error",
            "blockIndex": -1,
        })

    assert str(exc_info.value) == "blockIndex 不能为负数"


def test_parse_mermaid_repair_request_rejects_boolean_block_index() -> None:
    with pytest.raises(RequestValidationError) as exc_info:
        parse_mermaid_repair_request({
            "brokenCode": "graph TD\nA-->",
            "errorMessage": "Syntax error",
            "blockIndex": True,
        })

    assert str(exc_info.value) == "blockIndex 必须为整数"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"errorMessage": "Syntax error"}, "brokenCode 不能为空"),
        ({"brokenCode": "graph TD"}, "errorMessage 不能为空"),
    ],
)
def test_parse_mermaid_repair_request_rejects_missing_required_fields(
    payload: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(RequestValidationError) as exc_info:
        parse_mermaid_repair_request(payload)

    assert str(exc_info.value) == message


@pytest.mark.parametrize("payload", [[{}], "not-object"])
def test_parse_mermaid_repair_request_rejects_non_object_json(payload: object) -> None:
    with pytest.raises(RequestValidationError) as exc_info:
        parse_mermaid_repair_request(payload)  # type: ignore[arg-type]

    assert str(exc_info.value) == "请求体必须是 JSON 对象"
