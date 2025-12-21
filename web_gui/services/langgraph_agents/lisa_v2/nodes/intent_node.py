"""
意图识别节点 - LLM 驱动的对话式版本（使用 HTML 注释标记）
"""

from typing import Dict, Optional
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..state import LisaState
from ..prompts.intent_chat import INTENT_CHAT_PROMPT
from ..utils.logger import get_lisa_logger, log_node_entry, log_node_exit, log_node_error
from ..utils.llm_factory import get_llm_from_db

logger = get_lisa_logger()


def intent_node(state: LisaState, config: Optional[RunnableConfig] = None) -> Dict:
    """
    意图识别节点 - 纯 LLM 对话驱动版
    
    核心逻辑：
    1. LLM 自由对话，直到它认为意图明确
    2. LLM 添加隐藏标记 <!-- INTENT: X --> 来锁定意图
    3. Python 提取标记，设置门控状态
    """
    session_id = state.get("session_id", "")
    log_node_entry(logger, "intent_node", session_id, "intent")
    
    try:
        # 获取 LLM
        llm = get_llm_from_db()
        if not llm:
            logger.error("LLM 未配置！")
            return {
                "messages": [AIMessage(content="抱歉，AI 服务未配置。请联系管理员。")],
                "current_stage": "intent",
                "gate_passed": False,
            }
        
        messages = state.get("messages", [])
        is_activated = state.get("is_activated", False)
        
        logger.info(f"[{session_id[:8]}] is_activated={is_activated}, messages_count={len(messages)}")
        
        # 首次交互：直接返回欢迎语，不调用 LLM
        if not is_activated:
            response = """您好！我是 **Lisa Song**，您的首席测试领域专家，拥有15年跨行业测试经验。

**我能为您提供以下专业服务：**

- **A. 新需求/功能测试设计** - 为全新功能设计完整的测试方案
- **B. 需求评审与可测试性分析** - 审查需求文档，识别逻辑漏洞
- **C. 生产缺陷分析与回归策略** - 分析线上问题并设计回归测试
- **D. 专项测试策略规划** - 性能、安全、自动化测试策略
- **E. 产品测试现状评估** - 评估和优化现有测试体系
- **F. 通用测试咨询** - 其他测试相关问题

💡 **您可以：**
- 直接输入字母（如 A）快速选择
- 或者直接描述您的测试需求，我会为您匹配

请问今天有什么测试任务需要我帮忙规划吗？"""
            
            log_node_exit(logger, "intent_node", session_id, False, {"action": "welcome"})
            
            return {
                "messages": [AIMessage(content=response)],
                "current_stage": "intent",
                "gate_passed": False,
                "is_activated": True,
            }
        
        # 构建对话上下文
        system_msg = SystemMessage(content=INTENT_CHAT_PROMPT)
        conversation = [system_msg] + messages[-20:]  # 最近 20 轮
        
        logger.info(f"[{session_id[:8]}] 调用 LLM，上下文消息数: {len(conversation)}")
        
        # 调用 LLM
        try:
            ai_response = llm.invoke(conversation, config=config)
            
            if not ai_response or not hasattr(ai_response, 'content'):
                logger.error(f"[{session_id[:8]}] LLM 返回无效响应")
                return {
                    "messages": [AIMessage(content="抱歉，我暂时无法理解。请再说一次？")],
                    "current_stage": "intent",
                    "gate_passed": False,
                }
            
            response_content = ai_response.content
            
            if not response_content or not response_content.strip():
                logger.error(f"[{session_id[:8]}] LLM 返回空内容")
                return {
                    "messages": [AIMessage(content="请问您有什么测试相关的需求吗？")],
                    "current_stage": "intent",
                    "gate_passed": False,
                }
            
            logger.info(f"[{session_id[:8]}] LLM 响应长度: {len(response_content)}")
            
        except Exception as llm_error:
            logger.error(f"[{session_id[:8]}] LLM 调用失败: {llm_error}")
            return {
                "messages": [AIMessage(content="抱歉，我现在遇到了技术问题。请稍后再试或换个方式描述您的需求。")],
                "current_stage": "intent",
                "gate_passed": False,
            }
        
        # 检查是否包含意图确认标记
        import re
        intent_match = re.search(r'<!--\s*INTENT:\s*([A-F])\s*-->', response_content)
        
        if intent_match:
            # LLM 锁定了意图
            intent_code = intent_match.group(1)
            
            # 移除标记，只保留给用户看的内容
            clean_content = re.sub(r'<!--\s*INTENT:\s*[A-F]\s*-->', '', response_content).strip()
            
            from ..prompts.intent import WORKFLOW_MAP
            workflow_info = WORKFLOW_MAP.get(intent_code, WORKFLOW_MAP.get("F", {}))
            workflow_name = workflow_info.get("name", "未知工作流")
            
            logger.info(f"[{session_id[:8]}] ✅ 意图已锁定: {intent_code} - {workflow_name}")
            
            log_node_exit(logger, "intent_node", session_id, True, {"intent": intent_code})
            
            return {
                "messages": [AIMessage(content=clean_content)],
                "current_stage": "intent",
                "detected_intent": intent_code,
                "intent_confidence": 0.95,
                "gate_passed": True,  # 通过门控
            }
        else:
            # LLM 继续对话
            logger.info(f"[{session_id[:8]}] 💬 继续对话，未锁定意图")
            
            log_node_exit(logger, "intent_node", session_id, False, {"action": "continue_chat"})
            
            return {
                "messages": [ai_response],
                "current_stage": "intent",
                "gate_passed": False,  # 继续循环
            }
        
    except Exception as e:
        log_node_error(logger, "intent_node", session_id, e)
        return {
            "messages": [AIMessage(content=f"发生错误: {str(e)}")],
            "current_stage": "intent",
            "gate_passed": False,
        }
