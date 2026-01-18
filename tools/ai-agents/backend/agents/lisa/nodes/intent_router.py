"""
Intent Router Node - 意图路由节点

使用 LLM with_structured_output 进行语义意图识别，将用户请求路由到对应工作流。
"""

import logging
from typing import Any, Literal
from functools import lru_cache

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command

from ..state import LisaState
from ..schemas import IntentResult
from ..prompts import INTENT_ROUTING_PROMPT
from ..routing.hybrid_router import HybridRouter, RoutingDecision
from ..routing.observability import log_routing_decision

logger = logging.getLogger(__name__)


def format_messages_for_context(messages: list, max_messages: int = 10) -> str:
    """格式化消息列表供上下文使用"""
    recent = messages[-max_messages:] if len(messages) > max_messages else messages
    
    formatted = []
    for msg in recent:
        role = "用户" if isinstance(msg, HumanMessage) else "Lisa"
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        formatted.append(f"[{role}]: {content}")
    
    return "\n".join(formatted) if formatted else "(无历史消息)"


def summarize_artifacts(artifacts: dict) -> str:
    """生成产出物摘要"""
    if not artifacts:
        return "(无产出物)"
    
    summaries = []
    for key, value in artifacts.items():
        length = len(value) if value else 0
        summaries.append(f"- {key}: {length} 字符")
    
    return "\n".join(summaries)


@lru_cache(maxsize=1)
def get_hybrid_router() -> HybridRouter:
    """获取混合路由器单例（缓存）"""
    return HybridRouter()


def fallback_intent_routing(state: LisaState, llm: Any) -> IntentResult:
    """LLM 降级路由逻辑 - 当语义路由不确定时调用"""
    messages = state.get("messages", [])
    
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
            
    if not last_user_message:
        return IntentResult(intent=None, confidence=0.0, reason="无用户消息")
        
    recent_messages = format_messages_for_context(messages)
    artifacts_summary = summarize_artifacts(state.get("artifacts", {}))
    
    system_prompt = INTENT_ROUTING_PROMPT.format(
        current_workflow=state.get("current_workflow") or "未开始",
        workflow_stage=state.get("workflow_stage") or "无",
        artifacts_summary=artifacts_summary,
        recent_messages=recent_messages,
    )
    
    structured_llm = llm.model.with_structured_output(
        IntentResult,
        method="function_calling"
    )
    
    result: IntentResult = structured_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"请分析用户意图：{last_user_message}")
    ])
    
    return result


RouterCommand = Command[Literal["workflow_test_design", "workflow_requirement_review", "clarify_intent"]]


def intent_router_node(state: LisaState, llm: Any) -> RouterCommand:
    logger.info("执行意图路由...")
    
    messages = state.get("messages", [])
    if not messages:
        logger.warning("无用户消息，跳过路由")
        return Command(update={}, goto="clarify_intent")
    
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
    
    if not last_user_message:
        logger.warning("未找到用户消息，跳过路由")
        return Command(update={}, goto="clarify_intent")
    
    # 使用 HybridRouter
    router = get_hybrid_router()
    
    # 定义 LLM 回调 (闭包捕获 state 和 llm)
    def llm_fallback_fn(input_text: str, context: dict) -> IntentResult:
        return fallback_intent_routing(state, llm)
    
    try:
        decision = router.route(
            user_input=last_user_message,
            llm_router_fn=llm_fallback_fn
        )
        
        # 记录可观测性日志
        log_routing_decision(decision, logger)
        
        # 意图映射到 Command
        if decision.intent == "START_TEST_DESIGN":
            return Command(
                update={"current_workflow": "test_design"},
                goto="workflow_test_design"
            )
        elif decision.intent == "START_REQUIREMENT_REVIEW":
            return Command(
                update={"current_workflow": "requirement_review"},
                goto="workflow_requirement_review"
            )
        elif decision.intent == "CONTINUE_WORKFLOW":
            current_workflow = state.get("current_workflow")
            if current_workflow == "test_design":
                return Command(update={}, goto="workflow_test_design")
            elif current_workflow == "requirement_review":
                return Command(update={}, goto="workflow_requirement_review")
            return Command(update={}, goto="clarify_intent")
        else:
            update = {}
            if decision.metadata and decision.metadata.get("clarification"):
                update["clarification"] = decision.metadata["clarification"]
            
            # 粘性逻辑：如果已经在工作流中，且意图不明，默认继续工作流
            # 防止用户回复简单的确认词（如"好的"）导致会话重置
            current_workflow = state.get("current_workflow")
            if current_workflow == "test_design":
                logger.info("意图不明，但处于 test_design 工作流中 -> 继续工作流 (粘性)")
                return Command(update=update, goto="workflow_test_design")
            elif current_workflow == "requirement_review":
                logger.info("意图不明，但处于 requirement_review 工作流中 -> 继续工作流 (粘性)")
                return Command(update=update, goto="workflow_requirement_review")
                
            return Command(update=update, goto="clarify_intent")
            
    except Exception as e:
        logger.error(f"意图路由失败: {e}", exc_info=True)
        return Command(update={}, goto="clarify_intent")

