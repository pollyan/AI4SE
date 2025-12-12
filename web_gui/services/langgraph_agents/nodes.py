"""
LangGraph 节点定义

定义 LangGraph 图中的节点函数。
"""

import logging
import os
from pathlib import Path
from typing import Optional
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from .state import AssistantState

logger = logging.getLogger(__name__)

# Bundle 文件目录
BUNDLE_DIR = Path(__file__).parent.parent.parent.parent / "assistant-bundles"

# 助手别名映射
ASSISTANT_ALIASES = {
    'alex': 'alex',
    'lisa': 'lisa',
    'song': 'lisa',  # 兼容旧名称
}


def load_assistant_persona(assistant_type: str) -> str:
    """
    加载智能体的完整 persona 定义
    
    Args:
        assistant_type: 智能体类型（alex 或 lisa）
        
    Returns:
        Persona 内容字符串
    """
    # 规范化助手类型名称
    normalized_type = ASSISTANT_ALIASES.get(assistant_type, assistant_type)
    
    bundle_files = {
        'alex': 'intelligent-requirements-analyst-bundle.txt',
        'lisa': 'testmaster-song-bundle.txt'
    }
    
    try:
        bundle_file = bundle_files.get(normalized_type)
        if not bundle_file:
            raise ValueError(f"未知的智能体类型: {assistant_type}")
        
        bundle_path = BUNDLE_DIR / bundle_file
        if bundle_path.exists():
            with open(bundle_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning(f"Bundle 文件不存在: {bundle_path}")
            return get_fallback_persona(normalized_type)
    except Exception as e:
        logger.error(f"加载 persona 失败: {e}")
        return get_fallback_persona(normalized_type)


def get_fallback_persona(assistant_type: str) -> str:
    """获取备用的基础 persona"""
    if assistant_type == 'alex':
        return """你是 AI 需求分析师 Alex Chen，专门帮助用户澄清和完善项目需求。

你的职责：
1. 理解用户需求，识别信息缺口
2. 通过专业问题引导澄清
3. 提取已确认的需求要点
4. 生成结构化的共识内容

请始终以专业、友好的方式与用户交互。"""
    elif assistant_type == 'lisa':
        return """你是 AI 测试分析师 Lisa Song，专门帮助用户进行测试策略分析和测试用例设计。

你的职责：
1. 分析功能需求，确定测试范围
2. 设计测试策略和优先级
3. 生成具体的测试用例
4. 输出完整的测试计划文档

请始终以专业、友好的方式与用户交互。"""
    else:
        return "你是一个专业的 AI 助手。"


def chat_node(state: AssistantState, config: Optional[RunnableConfig] = None) -> AssistantState:
    """
    执行 AI 对话节点
    
    Args:
        state: 当前状态
        config: LangGraph 运行时配置（可包含 callbacks）
        
    Returns:
        更新后的状态（包含 AI 回复）
    """
    # 规范化助手类型
    assistant_type = ASSISTANT_ALIASES.get(state['assistant_type'], state['assistant_type'])
    
    logger.info(f"执行 chat_node，助手类型: {assistant_type}, 会话: {state['session_id']}")
    
    try:
        # 获取 AI 配置
        from ...models import RequirementsAIConfig
        config_obj = RequirementsAIConfig.get_default_config()
        
        if not config_obj:
            raise ValueError("未找到 AI 配置，请先在系统中配置 AI 服务")
        
        # 获取 callbacks（从 LangGraph config）
        callbacks = []
        if config and 'callbacks' in config.get('configurable', {}):
            callbacks = config['configurable']['callbacks']
            logger.info(f"使用 Langfuse callbacks: {len(callbacks)} 个")
        
        # 初始化 LLM（启用流式响应）
        llm = ChatOpenAI(
            api_key=config_obj.api_key,
            base_url=config_obj.base_url,
            model=config_obj.model_name,
            temperature=0.7,
            streaming=True,
            callbacks=callbacks  # 传递 Langfuse callbacks
        )
        
        # 准备消息列表
        messages = list(state["messages"])
        
        # 如果没有系统消息，添加 persona
        if not any(isinstance(msg, SystemMessage) for msg in messages):
            persona = load_assistant_persona(assistant_type)
            system_prompt = f"""你的关键操作指令已附在下方，请严格按照指令中的 persona 执行，不要打破角色设定。

{persona}"""
            messages.insert(0, SystemMessage(content=system_prompt))
        
        # 调用 LLM
        response = llm.invoke(messages)
        
        # 更新状态
        new_state = state.copy()
        new_state["messages"] = messages + [response]
        new_state["is_turn_complete"] = True
        
        logger.info(f"chat_node 完成，生成回复长度: {len(response.content)}")
        return new_state
        
    except Exception as e:
        logger.error(f"chat_node 执行失败: {str(e)}")
        new_state = state.copy()
        new_state["error_message"] = f"对话处理失败: {str(e)}"
        new_state["is_turn_complete"] = True
        return new_state
