"""
通用 OpenAI 兼容 LLM 模型适配器

用于替代 LiteLLM，提供更稳定、可控的流式输出（解决 Docker 缓冲问题和重复响应问题）。
"""

import sys
import logging
from typing import AsyncGenerator
from pydantic import Field
from google.adk.models import BaseLlm
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAICompatibleLlm(BaseLlm):
    """
    自定义 OpenAI 兼容 LLM 模型适配器
    
    目的：
    1. 替代 LiteLLM 以避免其默认行为（如发送重复的最终聚合文本）。
    2. 解决 Docker 环境下的 Python stdout 缓冲导致流式输出不流畅的问题。
    """
    
    api_key: str = Field(..., description="API 密钥")
    base_url: str = Field(..., description="API 基础 URL")
    
    _client: AsyncOpenAI = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        """
        生成内容（支持流式）
        """
        # 转换 ADK 请求到 OpenAI 格式
        messages = []
        
        # 处理 System Instruction (如果 wrapper 传递了)
        # 注意: BaseLlm 没有标准字段存储 system instruction，通常由 Agent 负责。
        # 这里只处理 LlmRequest 中的内容。
        
        for content in llm_request.contents:
            role = "user" if content.role == "user" else "assistant"
            # 简单的文本合并
            text_parts = [p.text for p in content.parts if p.text]
            if text_parts:
                messages.append({
                    "role": role,
                    "content": "".join(text_parts)
                })
                
        # 调用 OpenAI API
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream
            )
            
            if stream:
                async for chunk in response:
                    content = chunk.choices[0].delta.content
                    if content:
                        # 构造 ADK 响应
                        yield LlmResponse(
                            content=types.Content(
                                role="model", 
                                parts=[types.Part(text=content)]
                            ),
                            partial=True,
                            model_version=self.model
                        )
                        
                        # [Critical Fix] 强制刷新 stdout 解决 Docker 缓冲问题
                        try:
                            sys.stdout.write('.')
                            sys.stdout.flush()
                        except Exception:
                            pass
            else:
                # 非流式处理
                content = response.choices[0].message.content
                yield LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part(text=content)]
                    ),
                    partial=False,
                    model_version=self.model
                )
                
        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            raise
