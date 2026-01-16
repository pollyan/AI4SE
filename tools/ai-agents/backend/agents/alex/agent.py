"""
Alex ADK Agent 实现

使用 Google ADK + LiteLLM 构建，通过 Tool Calling 管理工作流状态。
集成状态管理器，在 Tool 调用时自动更新状态并发送 SSE 事件。
"""

import logging
from typing import AsyncIterator, Dict, Any, Union, Optional

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .prompts import LISA_V5_2_INSTRUCTION, TOOL_USAGE_PROMPT
from .tools import ALEX_TOOLS
from .state_manager import AlexStateManager

logger = logging.getLogger(__name__)

APP_NAME = "ai4se_alex"


def create_alex_agent(model_config: Dict[str, str]) -> LlmAgent:
    """
    创建 Alex ADK Agent
    
    Args:
        model_config: 模型配置，包含 model_name, base_url, api_key
        
    Returns:
        配置好的 LlmAgent 实例
    """
    model_name = model_config.get("model_name", "deepseek-chat")
    base_url = model_config.get("base_url", "https://api.deepseek.com/v1")
    api_key = model_config.get("api_key", "")

    litellm_model = LiteLlm(
        model=f"openai/{model_name}",
        api_base=base_url,
        api_key=api_key,
    )

    # 组合完整的 instruction
    full_instruction = LISA_V5_2_INSTRUCTION + "\n\n" + TOOL_USAGE_PROMPT

    agent = LlmAgent(
        name="alex",
        model=litellm_model,
        instruction=full_instruction,
        description="基于 Lisa v5.2 提示词的测试领域专家，专注于测试策略设计与需求评审",
        tools=ALEX_TOOLS,  # 注入 Tools
    )

    logger.info(f"Alex ADK Agent 创建完成 - 模型: {model_name}, Tools: {len(ALEX_TOOLS)} 个")
    return agent


class AlexAdkRunner:
    """
    Alex ADK Runner
    
    封装 ADK Runner，处理 Tool 调用事件，管理工作流状态。
    """
    
    def __init__(self, model_config: Dict[str, str]):
        self.model_config = model_config
        self.agent = create_alex_agent(model_config)
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=self.agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        self._initialized_sessions: set = set()
        
        # 状态管理器
        self.state_manager = AlexStateManager()
        
        logger.info("AlexAdkRunner 初始化完成")

    async def _ensure_session(self, session_id: str, user_id: str = "default"):
        """确保会话存在"""
        if session_id not in self._initialized_sessions:
            try:
                existing = await self.session_service.get_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                )
                if not existing:
                    await self.session_service.create_session(
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id,
                    )
                    logger.info(f"创建新会话: {session_id}")
                self._initialized_sessions.add(session_id)
            except Exception as e:
                logger.warning(f"会话检查失败，尝试创建: {e}")
                try:
                    await self.session_service.create_session(
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id,
                    )
                    self._initialized_sessions.add(session_id)
                except Exception:
                    pass

    def _handle_tool_call(self, session_id: str, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """
        处理 Tool 调用，更新状态
        
        Args:
            session_id: 会话 ID
            tool_name: Tool 名称
            tool_args: Tool 参数
            
        Returns:
            是否需要发送 state 事件
        """
        try:
            if tool_name == "set_plan":
                stages = tool_args.get("stages", [])
                self.state_manager.handle_set_plan(session_id, stages)
                return True
                
            elif tool_name == "update_stage":
                stage_id = tool_args.get("stage_id", "")
                status = tool_args.get("status", "")
                self.state_manager.handle_update_stage(session_id, stage_id, status)
                return True
                
            elif tool_name == "save_artifact":
                key = tool_args.get("key", "")
                content = tool_args.get("content", "")
                self.state_manager.handle_save_artifact(session_id, key, content)
                return True
                
            else:
                logger.warning(f"未知的 Tool: {tool_name}")
                return False
                
        except Exception as e:
            logger.error(f"处理 Tool 调用失败: {tool_name}, 错误: {e}")
            return False

    async def stream_message(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "default",
    ) -> AsyncIterator[Union[str, Dict[str, Any]]]:
        """
        流式处理消息
        
        处理文本输出和 Tool 调用事件，在 Tool 调用后发送 state 事件。
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息
            user_id: 用户 ID
            
        Yields:
            str: 文本 chunk
            dict: state 事件，格式 {"type": "state", "progress": {...}}
        """
        await self._ensure_session(session_id, user_id)

        user_content = types.Content(
            role="user",
            parts=[types.Part(text=user_message)],
        )

        logger.info(f"Alex ADK 流式处理 - 会话: {session_id}, 消息长度: {len(user_message)}")

        try:
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # 处理 Tool 调用
                        if hasattr(part, "function_call") and part.function_call:
                            tool_name = part.function_call.name
                            tool_args = part.function_call.args or {}
                            
                            logger.debug(f"检测到 Tool 调用: {tool_name}, 参数: {tool_args}")
                            
                            # 更新状态
                            should_send_state = self._handle_tool_call(
                                session_id, tool_name, tool_args
                            )
                            
                            # 发送 state 事件
                            if should_send_state:
                                progress = self.state_manager.get_progress_info(session_id)
                                if progress:
                                    yield {"type": "state", "progress": progress}
                                    logger.debug(f"发送 state 事件: 阶段索引 {progress['currentStageIndex']}")
                        
                        # 处理文本输出
                        if hasattr(part, "text") and part.text:
                            yield part.text

        except Exception as e:
            logger.error(f"Alex ADK 流式处理失败: {e}")
            yield f"\n\n错误: {str(e)}"

    async def invoke(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "default",
    ) -> str:
        """
        非流式处理消息
        
        收集所有文本输出，忽略 state 事件。
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息
            user_id: 用户 ID
            
        Returns:
            完整的 AI 响应文本
        """
        chunks = []
        async for chunk in self.stream_message(session_id, user_message, user_id):
            if isinstance(chunk, str):
                chunks.append(chunk)
        return "".join(chunks)
    
    def get_progress_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取当前进度信息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            ProgressInfo 字典或 None
        """
        return self.state_manager.get_progress_info(session_id)


def create_alex_graph(model_config: Dict[str, str]) -> AlexAdkRunner:
    """
    创建 Alex ADK Runner
    
    保持与原有接口兼容。
    
    Args:
        model_config: 模型配置
        
    Returns:
        AlexAdkRunner 实例
    """
    return AlexAdkRunner(model_config)
