from langchain_core.tools import tool

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
