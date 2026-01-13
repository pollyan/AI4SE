"""
产出物解析工具模块

提供 artifact 标签解析、Markdown 代码块提取等功能。
Lisa 和 Alex 智能体共用此模块。
"""

import re
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


# Artifact 标签正则表达式
# 匹配: <artifact key="xxx">内容</artifact> 或 <artifact key='xxx'>内容</artifact>
ARTIFACT_PATTERN = re.compile(
    r'<artifact\s+key=["\']([^"\']+)["\']\s*>(.*?)</artifact>',
    re.IGNORECASE | re.DOTALL
)


def parse_artifact(text: str) -> Optional[Dict[str, str]]:
    """
    解析响应文本中的第一个 artifact 标签
    
    Args:
        text: LLM 响应文本
        
    Returns:
        {"key": "artifact_key", "content": "内容"} 或 None
        
    Example:
        >>> parse_artifact('<artifact key="requirements">需求文档</artifact>')
        {"key": "requirements", "content": "需求文档"}
    """
    match = ARTIFACT_PATTERN.search(text)
    if match:
        key = match.group(1)
        content = match.group(2).strip()
        logger.info(f"解析到产出物: key={key}, length={len(content)}")
        return {"key": key, "content": content}
    return None


def parse_all_artifacts(text: str) -> List[Dict[str, str]]:
    """
    解析响应文本中的所有 artifact 标签
    
    Args:
        text: LLM 响应文本
        
    Returns:
        [{"key": "...", "content": "..."}, ...] 列表
    """
    results = []
    for match in ARTIFACT_PATTERN.finditer(text):
        key = match.group(1)
        content = match.group(2).strip()
        results.append({"key": key, "content": content})
    
    if results:
        logger.info(f"解析到 {len(results)} 个产出物")
    
    return results


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
