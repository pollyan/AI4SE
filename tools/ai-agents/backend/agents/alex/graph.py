"""
Alex Graph - LangGraph 状态图实现

基于 LangGraph StateGraph 的 Alex 智能体图结构。
"""

import logging
from typing import Dict

from langgraph.graph import StateGraph, START, END


from pathlib import Path
from .state import AlexState, get_initial_state
from ..llm import create_llm_from_config

logger = logging.getLogger(__name__)

# Bundle 文件路径
BUNDLE_PATH = Path(__file__).parent / "alex_v1_bundle.txt"


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



def create_alex_graph(model_config: Dict[str, str]):
    """
    创建 Alex LangGraph 图
    
    结构简单：START -> model -> END
    所有的对话逻辑由 System Prompt (Persona) 驱动。
    
    Args:
        model_config: 模型配置
        
    Returns:
        CompiledStateGraph: 编译后的图实例
    """
    logger.info("创建 Alex Graph...")
    
    # 1. 创建 LLM
    llm = create_llm_from_config(model_config)
    
    # 加载 Persona
    persona = load_alex_persona()
    
    
    # 2. 定义节点
    def model_node(state: AlexState):
        """核心模型节点"""
        messages = state["messages"]
        
        # 构造带有 system prompt 的调用
        from langchain_core.messages import SystemMessage
        
        prompt_messages = [SystemMessage(content=persona)] + messages
        
        # llm 是 LangchainLlm 包装器，需要调用 .model 获取底层 ChatModel
        response = llm.model.invoke(prompt_messages)
        
        # 返回更新 (LangGraph 会自动 append 到 messages)
        return {"messages": [response]}

    # 3. 创建图
    graph = StateGraph(AlexState)
    
    graph.add_node("model", model_node)
    
    graph.add_edge(START, "model")
    graph.add_edge("model", END)
    
    compiled = graph.compile()
    
    logger.info("Alex Graph 创建完成")
    return compiled

