from langchain_core.tools import tool
from .schemas import UpdateArtifact

@tool(args_schema=UpdateArtifact)
def update_artifact(key: str, markdown_body: str, metadata: dict = None) -> str:
    """
    更新工作流产出物。
    
    当需要保存或更新文档内容时调用此工具。
    严禁在普通对话中直接输出 Markdown 代码块，必须通过此工具提交。
    """
    return f"Artifact '{key}' updated successfully."


@tool
def ask_confirmation(message: str) -> str:
    """
    Ask the user for confirmation.
    
    Args:
        message: The confirmation message to display to the user.
    """
    # This tool is intended for client-side interaction.
    # The frontend intercepts this tool call, renders a UI, and sends back the result.
    # The result sent back by frontend should be a string ("Confirmed" or "Denied" or JSON).
    return "Waiting for user confirmation..."
