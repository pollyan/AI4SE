"""
Alex Agent - LangChain/LangGraph 实现

基于 LangGraph create_react_agent 的需求分析专家智能体。
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

# Bundle 文件路径
BUNDLE_PATH = Path(__file__).parent / "alex_v1_bundle.txt"

# 类型别名 (向后兼容)
AlexAgent = object


def load_alex_persona() -> str:
    """
    加载 Alex 的 persona 定义
    
    Returns:
        Persona 内容字符串
    """
    if BUNDLE_PATH.exists():
        logger.info(f"从 Bundle 文件加载 Alex persona: {BUNDLE_PATH}")
        return BUNDLE_PATH.read_text(encoding="utf-8")
    
    # Fallback
    logger.warning(f"Bundle 文件不存在: {BUNDLE_PATH}，使用 fallback persona")
    return """你是 AI 需求分析师 Alex Chen，专门帮助用户澄清和完善项目需求。

你的职责：
1. 理解用户需求，识别信息缺口
2. 通过专业问题引导澄清
3. 提取已确认的需求要点
4. 生成结构化的共识内容

请始终以专业、友好的方式与用户交互。"""


def create_alex_agent(model_config: Dict[str, str]):
    """
    创建 Alex Agent
    
    Args:
        model_config: 包含以下键的字典：
            - model_name: 模型名称（如 "qwen-plus"）
            - base_url: API 基础 URL
            - api_key: API 密钥
    
    Returns:
        配置好的 LangGraph Agent 实例
    """
    logger.info(f"创建 Alex Agent，模型: {model_config['model_name']}")
    
    # 使用 LangChain LLM
    llm = create_llm_from_config(model_config)
    
    # 加载 persona
    persona = load_alex_persona()
    
    # 创建 Agent
    # V1: create_agent(model, tools, system_prompt=...)
    # 旧版: create_react_agent(model, tools, prompt=...)
    try:
        # 尝试新 API (LangChain V1)
        agent = create_agent(
            llm.model,
            tools=[],
            system_prompt=persona
        )
    except TypeError:
        # 回退到旧 API (LangGraph < V1)
        agent = create_agent(
            llm.model,
            tools=[],
            prompt=persona
        )
    
    logger.info("Alex Agent (LangGraph) 创建成功")
    return agent
