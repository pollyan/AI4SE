"""
JSON 输出解析器

使用 PydanticOutputParser 引导 LLM 输出结构化 JSON。
提供从 LLM 响应中提取和解析 JSON 的工具函数。
"""

import re
import json
import logging
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError
from langchain_core.output_parsers import PydanticOutputParser

from .schemas import LisaStructuredOutput, AlexStructuredOutput

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def create_lisa_parser() -> PydanticOutputParser[LisaStructuredOutput]:
    """
    创建 Lisa 智能体的输出解析器

    Returns:
        配置好的 PydanticOutputParser 实例
    """
    return PydanticOutputParser(pydantic_object=LisaStructuredOutput)


def create_alex_parser() -> PydanticOutputParser[AlexStructuredOutput]:
    """
    创建 Alex 智能体的输出解析器

    Returns:
        配置好的 PydanticOutputParser 实例
    """
    return PydanticOutputParser(pydantic_object=AlexStructuredOutput)


def extract_json_from_response(response: str) -> Optional[str]:
    """
    从 LLM 响应中提取 JSON 字符串

    支持以下格式：
    1. ```json ... ``` 代码块
    2. 纯 JSON 字符串（以 { 开头，以 } 结尾）

    Args:
        response: LLM 原始响应文本

    Returns:
        提取的 JSON 字符串，如果未找到则返回 None
    """
    if not response:
        return None

    # 尝试匹配 ```json ... ``` 代码块
    json_block_pattern = r"```json\s*([\s\S]*?)\s*```"
    match = re.search(json_block_pattern, response)
    if match:
        return match.group(1).strip()

    # 尝试匹配纯 JSON（从第一个 { 到最后一个 }）
    stripped = response.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    # 尝试在文本中找到 JSON 对象
    brace_pattern = r"\{[\s\S]*\}"
    match = re.search(brace_pattern, response)
    if match:
        candidate = match.group(0)
        # 验证是否为有效 JSON
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    return None


def parse_structured_output(
    json_str: str,
    schema_class: Type[T]
) -> Optional[T]:
    """
    解析 JSON 字符串为 Pydantic 模型实例

    Args:
        json_str: JSON 字符串
        schema_class: 目标 Pydantic 模型类

    Returns:
        解析后的模型实例，解析失败返回 None
    """
    if not json_str:
        return None

    try:
        data = json.loads(json_str)
        return schema_class.model_validate(data)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析失败: {e}")
        return None
    except ValidationError as e:
        logger.warning(f"Schema 验证失败: {e}")
        return None


def split_message_and_json(response: str) -> tuple[str, Optional[str]]:
    """
    将 LLM 响应拆分为 Message 和 JSON 部分

    Args:
        response: 原始响应字符串

    Returns:
        (message, json_str): message 是移除 JSON 后的文本，json_str 是提取的 JSON（未找到为 None）
    """
    json_str = extract_json_from_response(response)
    if not json_str:
        return response, None

    # 简单策略：移除 JSON 字符串所在的块
    # 注意：extract_json_from_response 可能会返回去除了 markdown 标记的纯 JSON
    # 我们需要找到它在原始字符串中的位置并移除
    
    # 1. 尝试移除 ```json ... ``` 块
    pattern = r"```json\s*[\s\S]*?```"
    match = re.search(pattern, response)
    if match:
        # 验证这个块里的内容是否就是我们要的 json_str
        # 这里简化处理：假定只要有代码块，就是它
        message = response[:match.start()] + response[match.end():]
        return message.strip(), json_str
    
    # 2. 如果是纯 JSON 对象在末尾
    if response.strip().endswith("}"):
        # 尝试从后往前找最后一个 JSON 块
        # 这是一个简化的启发式方法
        try:
            # 找到 json_str 在 response 中的位置
            idx = response.rfind(json_str)
            if idx != -1:
                message = response[:idx]
                return message.strip(), json_str
        except Exception:
            pass

    # 如果无法精确定位移除，就返回原始内容（兜底）
    # 但由于这是结构化输出，最好还是尝试移除
    return response.replace(json_str, "").strip(), json_str
