"""
Lisa Graph - LangGraph 状态图实现

基于 LangGraph StateGraph 的 Lisa 智能体图结构。
包含意图路由和测试设计工作流节点。
"""

import logging
from typing import Dict, Literal

from langgraph.graph import StateGraph, START, END

from .state import LisaState, get_initial_state
from .nodes import intent_router_node, workflow_test_design_node, clarify_intent_node
from ..llm import create_llm_from_config

logger = logging.getLogger(__name__)


def route_by_intent(state: LisaState) -> Literal["test_design", "requirement_review", "clarify"]:
    """
    根据意图路由到对应节点
    
    基于 state 中的 current_workflow 字段进行路由。
    intent_router_node 会在 LLM 判断后设置此字段。
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    current_workflow = state.get("current_workflow")
    
    logger.info(f"路由决策 - current_workflow: {current_workflow}")
    
    if current_workflow == "test_design":
        return "test_design"
    
    if current_workflow == "requirement_review":
        return "requirement_review"
    
    # 无工作流或工作流未识别，进入澄清
    return "clarify"


def create_lisa_graph(model_config: Dict[str, str]):
    """
    创建 Lisa LangGraph 图
    
    构建包含意图路由和测试设计工作流的状态图。
    
    图结构：
    START -> intent_router -> [test_design -> END]
                           -> [clarify -> END]
    
    每次用户消息都从 START 开始，避免循环。
    
    Args:
        model_config: 包含 model_name, base_url, api_key 的配置字典
        
    Returns:
        CompiledStateGraph: 编译后的图实例
    """
    logger.info("创建 Lisa Graph...")
    
    # 创建 LLM
    llm = create_llm_from_config(model_config)
    
    # 创建图
    graph = StateGraph(LisaState)
    
    # 添加节点 (使用闭包传递 llm)
    graph.add_node("intent_router", lambda state: intent_router_node(state, llm))
    graph.add_node("clarify_intent", lambda state: clarify_intent_node(state, llm))
    graph.add_node("workflow_test_design", lambda state: workflow_test_design_node(state, llm))
    # 需求评审使用与测试设计同样的工作流节点，区别在于 plan 不同
    graph.add_node("workflow_requirement_review", lambda state: workflow_test_design_node(state, llm))
    
    # 添加边 - 简化结构，避免循环
    graph.add_edge(START, "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "test_design": "workflow_test_design",
            "requirement_review": "workflow_requirement_review",
            "clarify": "clarify_intent",
        }
    )
    # clarify_intent 直接结束，等待用户下一次输入
    graph.add_edge("clarify_intent", END)
    graph.add_edge("workflow_test_design", END)
    graph.add_edge("workflow_requirement_review", END)
    
    # 编译图
    compiled = graph.compile()
    
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
