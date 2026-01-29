import logging
from typing import Any, cast

from langchain_core.messages import SystemMessage

from langgraph.config import get_stream_writer

from ..state import LisaState
from ..tools import update_artifact
from ..schemas import UpdateStructuredArtifact
from ..prompts.artifacts import build_artifact_update_prompt
from ..utils.markdown_generator import convert_to_markdown
from ...shared.progress import get_progress_info

logger = logging.getLogger(__name__)


def artifact_node(state: LisaState, llm: Any) -> LisaState:
    """
    产出物更新节点 (Artifact Node)

    负责：
    1. 强制调用 update_artifact 工具
    2. 执行工具调用并更新 State 中的 artifacts
    3. 推送 tool-call 和 progress 事件
    """
    logger.info("Entering ArtifactNode...")

    current_stage = cast(str, state.get("current_stage_id", "clarify"))
    artifacts = state.get("artifacts", {})

    writer = get_stream_writer()

    # [新增] 初始化模版注入逻辑 (Deterministic Initialization)
    # 如果是初始化阶段，直接构造工具调用而不经过 LLM，确保 100% 成功率
    templates = state.get("artifact_templates", [])
    current_template = next(
        (t for t in templates if t.get("stage") == current_stage), None
    )

    mock_tool_calls_for_init = []

    if current_template:
        key = current_template["key"]
        if key not in artifacts:
            outline = current_template.get("outline", "")
            logger.info(
                f"ArtifactNode: DETECTED MISSING ARTIFACT {key}. "
                "Using deterministic initialization."
            )

            # 手动构造一个"虚拟"的 tool calls 列表
            mock_tool_calls_for_init = [
                {
                    "name": "update_artifact",
                    "args": {"key": key, "markdown_body": outline},
                    "id": f"call_init_{current_stage}",
                }
            ]

    # 3. 执行逻辑分叉
    tool_calls = []

    if mock_tool_calls_for_init:
        # A. 确定性初始化路径
        tool_calls = mock_tool_calls_for_init
    else:
        # B. 正常的 LLM 生成路径
        # 绑定工具并强制调用
        # 同时绑定旧版(Markdown)和新版(Structured)工具，让 LLM 根据 Prompt 决定
        llm_with_tools = llm.model.bind_tools(
            [update_artifact, UpdateStructuredArtifact],
            tool_choice="auto",  # 允许 LLM 自动选择合适的工具
        )

        # 获取当前阶段对应的 artifact key
        current_template = next(
            (t for t in templates if t.get("stage") == current_stage), None
        )
        artifact_key = (
            current_template["key"]
            if current_template
            else f"{current_stage}_output"
        )
        template_outline = (
            current_template.get("outline", "") if current_template else ""
        )

        # 构建 Prompt（使用动态 Schema 生成）
        artifact_prompt_text = build_artifact_update_prompt(
            artifact_key=artifact_key,
            current_stage=current_stage,
            template_outline=template_outline,
        )

        # 使用 state 中的 messages + 指令
        messages = state["messages"] + [
            SystemMessage(content=artifact_prompt_text)
        ]

        try:
            response = llm_with_tools.invoke(messages)
            tool_calls = response.tool_calls
        except Exception as e:
            logger.error(f"Artifact LLM call failed: {e}", exc_info=True)
            return state

    # 4. 处理工具调用
    # tool_calls 已经在上面被正确赋值了 (无论来自 mock 还是 response)
    if not tool_calls:
        logger.warning("ArtifactNode: No tool calls generated!")
        return state

    new_artifacts = dict(artifacts)

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        key = args.get("key")

        # 标准化工具名称比较（忽略大小写和下划线）
        normalized_tool_name = tool_name.lower().replace("_", "")

        if normalized_tool_name == "updateartifact":
            content = args.get("markdown_body")
            if key and content:
                new_artifacts[key] = content
                logger.info(f"ArtifactNode: Updated artifact {key} (markdown)")

        elif normalized_tool_name == "updatestructuredartifact":
            content = args.get("content")
            artifact_type = args.get("artifact_type", "requirement")
            
            if key and content:
                # 将结构化数据转换为 Markdown 字符串
                # 前端组件期望 artifacts 的值为 Markdown 字符串，否则会直接渲染 JSON
                markdown_content = convert_to_markdown(content, artifact_type)
                new_artifacts[key] = markdown_content
                logger.info(
                    f"ArtifactNode: Updated artifact {key} (structured -> markdown)"
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

            temp_state = {**state, "artifacts": new_artifacts}
            progress_info = get_progress_info(temp_state)

            if progress_info:
                completed = progress_info.get("artifactProgress", {}).get(
                    "completed"
                )
                logger.info(
                    "ArtifactNode: Generated progress info. Completed keys: "
                    f"{completed}"
                )
                progress_info["currentTask"] = f"已更新产出物: {key}"

                writer({"type": "progress", "progress": progress_info})
                logger.info("ArtifactNode: Sent progress event via writer")

    return {**state, "artifacts": new_artifacts}
