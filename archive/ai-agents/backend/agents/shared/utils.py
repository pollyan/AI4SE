import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def extract_json_from_markdown(text_content: str) -> Dict[str, Any]:
    """
    Safely extract and parse JSON from a markdown string.
    This handles LLM responses where the model includes chatty pre/post-ambles
    or explicitly wraps the JSON in ```json ... ``` blocks.
    
    Args:
        text_content: The raw text response from the LLM.
        
    Returns:
        dict: The parsed JSON object.
        
    Raises:
        json.decoder.JSONDecodeError: If JSON parsing fails even after cleanup.
        ValueError: If no parseable JSON block could be found.
    """
    text_content = text_content.strip()

    # Look for markdown code block markers
    if "```" in text_content:
        # It's possible the JSON block is wrapped anywhere in the text
        # Try to find the start of a JSON block
        start_idx = text_content.find("```json")
        if start_idx == -1:
            # fallback to generic code block
            start_idx = text_content.find("```")
            # advance past "```"
            start_idx += 3
        else:
            # advance past "```json"
            start_idx += 7
            
        end_idx = text_content.rfind("```")
        
        if 0 <= start_idx < end_idx:
            # Extract just the block content and clean it
            text_content = text_content[start_idx:end_idx].strip()

    # Sometimes the model still prefixes with "Here is your JSON:" without markdown blocks.
    # Look for the first '{' and the last '}'
    start_brace = text_content.find("{")
    end_brace = text_content.rfind("}")
    
    if start_brace != -1 and end_brace != -1 and end_brace >= start_brace:
        text_content = text_content[start_brace:end_brace+1].strip()
    else:
        raise ValueError("No JSON object structure '{...}' found in the response text.")

    try:
        data = json.loads(text_content)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extracted JSON: {text_content}")
        raise e
