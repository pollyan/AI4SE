from collections.abc import Callable
from typing import Any

from agent_contracts import WORKFLOW_STAGES
from pydantic import BaseModel, ConfigDict, Field


class RequestValidationError(ValueError):
    pass


class AgentRunStreamRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prompt: str = Field(min_length=1)
    system_prompt: str = Field(alias="systemPrompt", min_length=1)
    workflow_id: str = Field(alias="workflowId", min_length=1)
    stage_id: str = Field(alias="stageId", min_length=1)


class MermaidRepairRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    broken_code: str = Field(alias="brokenCode", min_length=1)
    error_message: str = Field(alias="errorMessage", min_length=1)
    block_index: int | None = Field(default=None, alias="blockIndex")


def _is_blank(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip()


def read_json_request_body(raw_body: bytes, get_json: Callable[[], Any]) -> Any:
    if not raw_body:
        return None
    return get_json()


def map_json_request_error(exc: BaseException) -> RequestValidationError | None:
    status_code = getattr(exc, "code", None)
    if status_code == 400:
        return RequestValidationError("请求体不是合法 JSON")
    if status_code == 415:
        return RequestValidationError("请求体必须是 JSON 对象")
    return None


def _ensure_request_object(data: Any) -> dict[str, Any]:
    if data is None:
        raise RequestValidationError("请求体为空")
    if not isinstance(data, dict):
        raise RequestValidationError("请求体必须是 JSON 对象")
    if not data:
        raise RequestValidationError("请求体为空")
    return data


def parse_agent_run_stream_request(
    data: dict[str, Any] | None,
) -> AgentRunStreamRequest:
    data = _ensure_request_object(data)
    if _is_blank(data.get("prompt")):
        raise RequestValidationError("prompt 不能为空")
    if _is_blank(data.get("systemPrompt")):
        raise RequestValidationError("systemPrompt 不能为空")
    if _is_blank(data.get("workflowId")):
        raise RequestValidationError("workflowId 不能为空")
    if _is_blank(data.get("stageId")):
        raise RequestValidationError("stageId 不能为空")
    workflow_id = data["workflowId"].strip()
    stage_id = data["stageId"].strip()
    workflow_stages = WORKFLOW_STAGES.get(workflow_id)
    if workflow_stages is None:
        raise RequestValidationError(f"未知 workflowId: {workflow_id}")
    if stage_id not in workflow_stages:
        raise RequestValidationError(
            f"workflowId 与 stageId 不匹配: {workflow_id}/{stage_id}"
        )
    normalized_data = {
        **data,
        "workflowId": workflow_id,
        "stageId": stage_id,
    }
    return AgentRunStreamRequest.model_validate(normalized_data)


def parse_mermaid_repair_request(
    data: dict[str, Any] | None,
) -> MermaidRepairRequest:
    data = _ensure_request_object(data)
    if _is_blank(data.get("brokenCode")):
        raise RequestValidationError("brokenCode 不能为空")
    if _is_blank(data.get("errorMessage")):
        raise RequestValidationError("errorMessage 不能为空")
    block_index = data.get("blockIndex")
    if block_index is not None:
        if isinstance(block_index, bool) or not isinstance(block_index, int):
            raise RequestValidationError("blockIndex 必须为整数")
        if block_index < 0:
            raise RequestValidationError("blockIndex 不能为负数")
    return MermaidRepairRequest.model_validate(data)
