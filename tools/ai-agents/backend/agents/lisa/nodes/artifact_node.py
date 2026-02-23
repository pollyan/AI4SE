import logging
from typing import Any, cast, Dict

from pydantic import BaseModel
from langchain_core.messages import SystemMessage

from langgraph.config import get_stream_writer

from ..state import LisaState
from ..schemas import UpdateStructuredArtifact
from ..prompts.artifacts import build_artifact_update_prompt
from ..utils.markdown_generator import convert_to_markdown
from ..artifact_patch import merge_artifacts
from ...shared.progress import get_progress_info

logger = logging.getLogger(__name__)


def artifact_node(state: LisaState, llm: Any) -> LisaState:
    """
    产出物更新节点 (Artifact Node)

    负责：
    1. 强制调用 UpdateStructuredArtifact 工具
    2. 执行工具调用并更新 State 中的 artifacts
    3. 推送 tool-call 和 progress 事件
    """
    logger.info("Entering ArtifactNode...")

    current_stage = cast(str, state.get("current_stage_id", "clarify"))
    artifacts = state.get("artifacts", {})
    new_artifacts = dict(artifacts)
    new_structured_artifacts = dict(state.get("structured_artifacts", {}))

    writer = get_stream_writer()

    # [新增] 初始化模版注入逻辑 (Deterministic Initialization)
    # 如果是初始化阶段，直接构造工具调用而不经过 LLM，确保 100% 成功率
    templates = state.get("artifact_templates", [])
    current_template = next(
        (t for t in templates if t.get("stage") == current_stage), None
    )

    mock_tool_calls_for_init: list[dict[str, Any]] = []

    if current_template:
        key = current_template["key"]
        if key not in artifacts:
            outline = current_template.get("outline", "")
            logger.info(
                f"ArtifactNode: DETECTED MISSING ARTIFACT {key}. "
                "Using deterministic initialization."
            )

            # 手动构造一个"虚拟"的初始化列表（内部逻辑，不是工具调用）
            mock_tool_calls_for_init = [
                {
                    "name": "_deterministic_init",
                    "args": {"key": key, "markdown_body": outline},
                    "id": f"call_init_{current_stage}",
                }
            ]
            
            # [Fix Bug 3] 同时初始化结构化数据 - REMOVED
            # User Feedback: We want to show the Markdown template initially, 
            # so we DO NOT initialize structured data here.
            # state["structured_artifacts"] = state.get("structured_artifacts", {})
            # state["structured_artifacts"][key] = create_empty_requirement_doc().model_dump()

    # 3. 如果是初始化且需要发送前置进度事件，先发送
    if mock_tool_calls_for_init:
        init_key = current_template.get("key") if current_template else None
        if init_key:
            pre_state = {**state, "artifacts": artifacts}
            pre_progress = get_progress_info(pre_state)
            if pre_progress:
                pre_progress["currentTask"] = f"正在初始化{current_template.get('name', '产出物')}..."
                if pre_progress.get("artifactProgress"):
                    pre_progress["artifactProgress"]["generating"] = init_key
                    logger.info(f"[ArtifactNode] Init path: Setting generating to {init_key}")
                
                logger.info(f"[ArtifactNode] Sending pre-init progress: {pre_progress}")
                writer({"type": "progress", "progress": pre_progress})
                logger.info("ArtifactNode: Sent pre-init generating progress event")
        
        # 将骨架写入 artifacts，以此完成 INIT
        for init_call in mock_tool_calls_for_init:
            init_args = init_call["args"]
            init_k = init_args["key"]
            init_body = init_args["markdown_body"]
            if init_k and init_body:
                new_artifacts[init_k] = init_body
                writer({
                    "type": "tool-call",
                    "toolCallId": init_call["id"],
                    "toolName": "_deterministic_init",
                    "args": {"key": init_k, "markdown_body": init_body},
                    "result": "Initialized empty template."
                })

    # 现在执行真正的 LLM 更新逻辑
    # [新增] 在 LLM 调用前发送"生成中"状态事件，让前端立刻显示 loading
    generating_key = None
    if current_template:
        generating_key = current_template.get("key")

    if generating_key:
        pre_state = {**state, "artifacts": new_artifacts} # Use new_artifacts here to reflect any mock updates
        pre_progress = get_progress_info(pre_state)
        if pre_progress:
            pre_progress["currentTask"] = f"正在生成{current_template.get('name', '产出物')}..."
            # 确保 generating 字段被正确设置
            if pre_progress.get("artifactProgress"):
                pre_progress["artifactProgress"]["generating"] = generating_key
            writer({"type": "progress", "progress": pre_progress})
            logger.info("ArtifactNode: Sent pre-generation progress event")

    # 绑定工具并强制调用
    # 只绑定新版(Structured)工具，强制 LLM 输出结构化数据，避免回退到不可靠的纯 Markdown 工具
    llm_with_tools = llm.model.bind_tools(
        [UpdateStructuredArtifact],
        tool_choice="required",  # 强制调用工具：每轮对话都必须更新产出物
    )

    # 获取当前阶段对应的 artifact key
    current_template = next(
        (t for t in templates if t.get("stage") == current_stage), None
    )
    artifact_key = (
        current_template["key"] if current_template else f"{current_stage}_output"
    )
    template_outline = (
        current_template.get("outline", "") if current_template else ""
    )

    # 构建 Prompt（使用动态 Schema 生成）
    # [Fix Bug 1] 传递 existing_artifact
    structured_artifacts = state.get("structured_artifacts", {})
    existing_structured = structured_artifacts.get(artifact_key)

    # 获取 Reasoning Hint (Context-Aware Sync)
    latest_hint = cast(str | None, state.get("latest_artifact_hint"))
    if latest_hint:
        logger.info(f"ArtifactNode: Using reasoning hint: {latest_hint[:50]}...")

    artifact_prompt_text = build_artifact_update_prompt(
        artifact_key=artifact_key,
        current_stage=current_stage,
        template_outline=template_outline,
        existing_artifact=existing_structured,
        reasoning_hint=latest_hint,
    )

    # 使用 state 中的 messages + 指令
    messages = state["messages"] + [SystemMessage(content=artifact_prompt_text)]

    tool_calls: list[dict[str, Any]] = []
    try:
        response = llm_with_tools.invoke(messages)
        tool_calls = response.tool_calls
    except Exception as e:
        logger.error(f"Artifact LLM call failed: {e}", exc_info=True)
        # 即使 LLM 失败，也要保留确定性初始化写入的数据
        return {
            "artifacts": new_artifacts,
            "structured_artifacts": new_structured_artifacts
        }

    # 4. 处理工具调用
    if not tool_calls:
        logger.warning("ArtifactNode: No tool calls generated!")
        # 即使 LLM 没有生成工具调用，也要保留确定性初始化写入的骨架数据
        return {
            "artifacts": new_artifacts,
            "structured_artifacts": new_structured_artifacts
        }

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        key = args.get("key")

        # 标准化工具名称比较（只支持 UpdateStructuredArtifact）
        normalized_tool_name = tool_name.lower().replace("_", "")

        if normalized_tool_name == "updatestructuredartifact":
            patch = cast(Dict[str, Any], args.get("content"))
            artifact_type = args.get("artifact_type", "requirement")

            if key and patch:
                original = new_structured_artifacts.get(key, {})
                if hasattr(original, "model_dump"):
                    original = original.model_dump()
                elif isinstance(original, str):
                    original = {}

                if key == "test_design_cases":
                    logger.warning(f"DEBUG: R4 JSON ARGS: {args}")

                merged = merge_artifacts(cast(Dict[str, Any], original), patch)

                # Convert structured object back to Markdown string for frontend rendering
                markdown_content = convert_to_markdown(merged, artifact_type)
                new_artifacts[key] = markdown_content
                
                # 更新结构化数据
                new_structured_artifacts[key] = merged

                logger.info(
                    f"ArtifactNode: Updated artifact {key} (structured patch converted to markdown)"
                )

        else:
            logger.warning(f"ArtifactNode: Unknown tool name: {tool_name}")
            continue

        if key:
            writer(
                {
                    "type": "tool-call",
                    "toolCallId": tool_call.get("id", "call_unknown"),
                    "toolName": tool_name,
                    "args": {"key": key},
                    "result": f"Artifact '{key}' updated successfully.",
                }
            )

            temp_state = {**state, "artifacts": new_artifacts, "structured_artifacts": new_structured_artifacts}
            progress_info = get_progress_info(temp_state)

            if progress_info:
                completed = progress_info.get("artifactProgress", {}).get("completed")
                logger.info(
                    "ArtifactNode: Generated progress info. Completed keys: "
                    f"{completed}"
                )
                progress_info["currentTask"] = f"已更新产出物: {key}"

                writer({"type": "progress", "progress": progress_info})
                logger.info("ArtifactNode: Sent progress event via writer")

    return {
        "artifacts": new_artifacts,
        "structured_artifacts": new_structured_artifacts
    }
