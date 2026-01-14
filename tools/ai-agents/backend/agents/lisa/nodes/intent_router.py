"""
Intent Router Node - 意图路由节点

使用 LLM with_structured_output 进行语义意图识别，将用户请求路由到对应工作流。
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..state import LisaState
from ..schemas import IntentResult
from ..prompts import INTENT_ROUTING_PROMPT

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


def intent_router_node(state: LisaState, llm: Any) -> LisaState:
    logger.info("执行意图路由...")
    
    messages = state.get("messages", [])
    if not messages:
        logger.warning("无用户消息，跳过路由")
        return state
    
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
    
    if not last_user_message:
        logger.warning("未找到用户消息，跳过路由")
        return state
    
    recent_messages = format_messages_for_context(messages)
    artifacts_summary = summarize_artifacts(state.get("artifacts", {}))
    
    system_prompt = INTENT_ROUTING_PROMPT.format(
        current_workflow=state.get("current_workflow") or "未开始",
        workflow_stage=state.get("workflow_stage") or "无",
        artifacts_summary=artifacts_summary,
        recent_messages=recent_messages,
    )
    
    try:
        structured_llm = llm.model.with_structured_output(
            IntentResult,
            method="function_calling"
        )
        
        result: IntentResult = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请分析用户意图：{last_user_message}")
        ])
        
        logger.info(f"意图识别结果: {result.intent} (置信度: {result.confidence})")
        
        if result.intent == "START_TEST_DESIGN":
            return {
                **state,
                "current_workflow": "test_design",
            }
        elif result.intent == "START_REQUIREMENT_REVIEW":
            return {
                **state,
                "current_workflow": "requirement_review",
            }
        else:
            return {
                **state,
                "clarification": result.clarification,
            }
            
    except Exception as e:
        logger.error(f"意图路由失败: {e}")
        return state

