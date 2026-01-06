"""
LangChain LLM 适配器

提供基于 LangChain ChatOpenAI 的 LLM 封装，支持流式输出。
"""

import logging
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


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
            base_url: API 基础 URL
            api_key: API 密钥
        """
        logger.info(f"初始化 LangChain LLM: {model_name}, base_url: {base_url[:30]}...")
        
        self._chat_model = ChatOpenAI(
            model=model_name,
            openai_api_base=base_url,
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
