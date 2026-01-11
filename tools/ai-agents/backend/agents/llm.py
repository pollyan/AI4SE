"""
LangChain LLM 适配器

提供基于 LangChain ChatOpenAI 的 LLM 封装，支持流式输出。
"""

import logging
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def normalize_base_url(base_url: str) -> str:
    """
    规范化 API base_url
    
    LangChain 的 ChatOpenAI 会自动在 base_url 后追加 /chat/completions 路径。
    如果用户输入的 base_url 已经包含此路径，会导致重复路径错误（如 /v4/chat/completions/chat/completions）。
    
    此函数会：
    1. 去除尾部斜杠
    2. 去除常见的 API 路径后缀（/chat/completions, /completions, /v1/chat/completions 等）
    
    Args:
        base_url: 用户输入的 API 基础 URL
        
    Returns:
        规范化后的 base_url
    """
    if not base_url:
        return base_url
    
    # 去除尾部斜杠
    normalized = base_url.rstrip('/')
    
    # 需要去除的路径后缀列表（按长度降序排列，确保先匹配更长的）
    suffixes_to_remove = [
        '/chat/completions',
        '/completions',
    ]
    
    for suffix in suffixes_to_remove:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            logger.info(f"base_url 规范化: 已去除 '{suffix}' 后缀")
            break
    
    return normalized


class LangchainLlm:
    """
    LangChain LLM 封装
    
    封装 ChatOpenAI，提供统一的接口用于创建 Agent。
    支持 OpenAI 兼容的第三方 API 端点。
    """
    
    def __init__(self, model_name: str, base_url: str, api_key: str):
        """
        初始化 LLM
        
        Args:
            model_name: 模型名称（如 "qwen-plus"）
            base_url: API 基础 URL（会自动规范化）
            api_key: API 密钥
        """
        # 规范化 base_url，防止路径重复
        normalized_url = normalize_base_url(base_url)
        
        logger.info(f"初始化 LangChain LLM: {model_name}, base_url: {normalized_url[:30]}...")
        
        self._chat_model = ChatOpenAI(
            model=model_name,
            openai_api_base=normalized_url,
            openai_api_key=api_key,
            streaming=True
        )
    
    @property
    def model(self) -> BaseChatModel:
        """获取底层 ChatModel 实例"""
        return self._chat_model


def create_llm_from_config(config: Dict[str, str]) -> LangchainLlm:
    """
    从配置字典创建 LLM 实例
    
    Args:
        config: 包含 model_name, base_url, api_key 的配置字典
    
    Returns:
        LangchainLlm 实例
    """
    return LangchainLlm(
        model_name=config['model_name'],
        base_url=config['base_url'],
        api_key=config['api_key']
    )
