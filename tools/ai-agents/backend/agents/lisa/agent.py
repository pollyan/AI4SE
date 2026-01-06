"""
Lisa Song Agent - LangChain/LangGraph 实现

基于 LangGraph create_react_agent 的测试专家智能体。
依靠 "Pure Prompt" (v5.0 Bundle) 的完全体系统提示词。
"""

import logging
from pathlib import Path
from typing import Dict

# 优先使用新 API，回退到旧 API
try:
    from langchain.agents import create_agent
except ImportError:
    from langgraph.prebuilt import create_react_agent as create_agent

from ..llm import create_llm_from_config

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


def create_lisa_agent(model_config: Dict[str, str]):
    """
    创建 Lisa Agent
    
    使用 LangGraph create_react_agent。
    核心逻辑完全由 instruction (bundle.txt) 驱动。
    
    Args:
        model_config: 包含 model_name, base_url, api_key 的配置字典
    
    Returns:
        配置好的 LangGraph Agent 实例
    """
    logger.info(f"创建 Lisa Agent，模型: {model_config['model_name']}")
    
    # 使用 LangChain LLM
    llm = create_llm_from_config(model_config)
    
    # 加载 Pure Prompt
    instruction = load_instruction()
    
    # 创建 Agent
    try:
        # 尝试新 API (LangChain V1)
        agent = create_agent(
            llm.model,
            tools=[],
            system_prompt=instruction
        )
    except TypeError:
        # 回退到旧 API (LangGraph < V1)
        agent = create_agent(
            llm.model,
            tools=[],
            prompt=instruction
        )
    
    logger.info("Lisa Agent (LangGraph) 创建成功")
    return agent
