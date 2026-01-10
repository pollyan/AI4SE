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
from .nodes.workflow_product_design import workflow_product_design_node

logger = logging.getLogger(__name__)

def setup_node(state: AlexState) -> AlexState:
    """初始化节点：设置默认工作流"""
    # 如果没设置工作流，默认为 product_design
    if not state.get("current_workflow"):
        return {
            **state,
            "current_workflow": "product_design",
            "plan": []  # 确保 plan 存在（空列表触发动态生成）
        }
    return state

def create_alex_graph(model_config: Dict[str, str]):
    """
    创建 Alex LangGraph 图 (新版)
    
    结构：START -> setup -> workflow_product_design -> END
    """
    logger.info("创建 Alex Graph (Dynamic Plan)...")
    
    # 1. 创建 LLM
    llm = create_llm_from_config(model_config)
    
    # 2. 定义图
    graph = StateGraph(AlexState)
    
    # 添加节点
    graph.add_node("setup", setup_node)
    graph.add_node("workflow_product_design", lambda state: workflow_product_design_node(state, llm))
    
    # 添加边
    graph.add_edge(START, "setup")
    graph.add_edge("setup", "workflow_product_design")
    graph.add_edge("workflow_product_design", END)
    
    compiled = graph.compile()
    
    logger.info("Alex Graph 创建完成")
    return compiled

