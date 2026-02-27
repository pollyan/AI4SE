"""
Lisa Graph - LangGraph 状态图实现

基于 LangGraph StateGraph 的 Lisa 智能体图结构。
包含意图路由和测试设计工作流节点。
"""

import logging
from typing import Dict

from langgraph.graph import StateGraph, START, END

from .state import LisaState, get_initial_state
from .nodes.intent_router import intent_router_node
from .nodes.clarify_intent import clarify_intent_node
from .nodes.reasoning_node import reasoning_node
from .nodes.artifact_node import artifact_node
from ..llm import create_llm_from_config
from ..shared.checkpointer import get_checkpointer
from ..shared.retry_policy import get_llm_retry_policy

logger = logging.getLogger(__name__)


def create_lisa_graph(model_config: Dict[str, str]):
    """
    创建 Lisa LangGraph 图
    
    构建包含意图路由和测试设计工作流的状态图。
    使用 Command 模式进行路由，intent_router_node 直接返回 Command 对象
    指定下一个节点，无需 conditional_edges。
    
    图结构：
    START -> intent_router -> [workflow_test_design -> END]
                           -> [workflow_requirement_review -> END]
                           -> [clarify_intent -> END]
    
    Args:
        model_config: 包含 model_name, base_url, api_key 的配置字典
        
    Returns:
        CompiledStateGraph: 编译后的图实例
    """
    logger.info("创建 Lisa Graph...")
    
    llm = create_llm_from_config(model_config)
    
    graph = StateGraph(LisaState)
    
    from functools import partial
    
    llm_retry = get_llm_retry_policy()
    
    graph.add_node("intent_router", partial(intent_router_node, llm=llm), retry_policy=llm_retry)
    graph.add_node("clarify_intent", partial(clarify_intent_node, llm=llm), retry_policy=llm_retry)
    
    # 双节点架构
    graph.add_node("reasoning_node", partial(reasoning_node, llm=llm), retry_policy=llm_retry)
    graph.add_node("artifact_node", partial(artifact_node, llm=llm), retry_policy=llm_retry)
    
    graph.add_edge(START, "intent_router")
    graph.add_edge("clarify_intent", END)
    
    # 路由由 reasoning_node 的 Command 控制，artifact_node 执行完后结束
    graph.add_edge("artifact_node", END)
    # 显式添加 reasoning_node -> END (虽然 Command goto="artifact_node" 会覆盖，但作为静态图结构定义通常需要)
    # 但 LangGraph 的 Command 不强求预定义边，只要节点存在即可。
    # 为了可视化清晰，我们可以加边，或者保持 Command 动态路由。
    # 保持简单，不加显式边到 artifact_node，依靠 Command。
    
    compiled = graph.compile(checkpointer=get_checkpointer())
    
    logger.info("Lisa Graph 创建完成")
    return compiled


def get_graph_initial_state() -> LisaState:
    """
    获取 Graph 的初始状态
    
    为新会话提供初始状态。
    
    Returns:
        LisaState: 初始状态
    """
    return get_initial_state()
