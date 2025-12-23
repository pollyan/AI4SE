"""
Lisa Song Agent - Google ADK 实现

基于 "Pure Prompt" (v5.0 Bundle) 的完全体智能测试专家。
单体智能体架构，依靠通过强大的 System Prompt 管理意图识别与工作流执行。
"""

import logging
from pathlib import Path
from typing import Dict
from google.adk.agents import LlmAgent
from ..llm import OpenAICompatibleLlm

logger = logging.getLogger(__name__)

# Bundle 路径
BUNDLE_PATH = Path(__file__).parent / "lisa_v5_bundle.txt"

def load_instruction() -> str:
    """加载 Lisa 的完整 System Prompt"""
    if BUNDLE_PATH.exists():
        return BUNDLE_PATH.read_text(encoding="utf-8")
    else:
        logger.warning(f"Lisa bundle not found at {BUNDLE_PATH}")
        return "你是 Lisa Song，首席测试专家。"

def create_lisa_agent(model_config: Dict[str, str]) -> LlmAgent:
    """
    创建 Lisa Agent
    
    使用标准的 LlmAgent + OpenAICompatibleLlm (解决Streaming问题)。
    核心逻辑完全由 instruction (bundle.txt) 驱动。
    """
    
    # 1. 创建模型适配器 (使用共享的 OpenAICompatibleLlm)
    model = OpenAICompatibleLlm(
        model=model_config['model_name'],
        base_url=model_config['base_url'],
        api_key=model_config['api_key']
    )
    
    # 2. 加载 Pure Prompt
    instruction = load_instruction()
    
    # 3. 创建 Agent
    agent = LlmAgent(
        name="lisa_song",
        model=model,
        instruction=instruction,
        description="首席测试专家 (v5.0 Pure Prompt)"
    )
    
    return agent
