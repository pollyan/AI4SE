"""
产出物解析工具模块

提供 Markdown 代码块提取等功能。
(Artifact XML 标签解析功能已移除)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_markdown_block(text: str) -> Optional[str]:
    """
    从响应文本中提取第一个 ```markdown 代码块的内容
    
    此函数用于向后兼容旧的产出物提取方式。
    
    Args:
        text: LLM 响应文本
        
    Returns:
        Markdown 代码块内容，若无则返回 None
    """
    if "```markdown" not in text:
        return None
    
    start = text.find("```markdown") + 11
    end = text.find("```", start)
    
    if end > start:
        content = text[start:end].strip()
        logger.debug(f"提取到 markdown 代码块: {len(content)} 字符")
        return content
    
    return None
