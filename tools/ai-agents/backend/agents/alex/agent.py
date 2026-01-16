"""
Alex ADK Agent 实现

使用 Google ADK + LiteLLM 构建，通过 Tool Calling 管理工作流状态。
集成状态管理器，在 Tool 调用时自动更新状态并发送 SSE 事件。
"""

import logging
import os
from typing import AsyncIterator, Dict, Any, Union, Optional

from langsmith import traceable

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .prompts import LISA_V5_2_INSTRUCTION
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
    full_instruction = LISA_V5_2_INSTRUCTION

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
            if tool_name == "update_progress":
                self.state_manager.handle_update_progress(
                    session_id,
                    stages=tool_args.get("stages", []),
                    current_stage_id=tool_args.get("current_stage_id", ""),
                    current_task=tool_args.get("current_task", "")
                )
                return True
                
            elif tool_name == "update_artifact":
                self.state_manager.handle_update_artifact(
                    session_id,
                    artifact_key=tool_args.get("artifact_key", ""),
                    section_id=tool_args.get("section_id", ""),
                    content=tool_args.get("content", "")
                )
                return True
                
            else:
                logger.warning(f"未知的 Tool: {tool_name}")
                return False
                
        except Exception as e:
            logger.error(f"处理 Tool 调用失败: {tool_name}, 错误: {e}")
            return False

    @traceable(name="alex_stream_message", run_type="chain")
    async def stream_message(
        self,
        session_id: str,
        user_message: str,
        user_id: str = "default",
    ) -> AsyncIterator[Union[str, Dict[str, Any]]]:
        """
        流式处理消息
        
        处理文本输出和 Tool 调用事件，在 Tool 调用后发送 state 事件。
        流结束后强制推送最终状态。
        
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

        # 记录上一次发送的状态，用于去重
        last_sent_progress = None
        
        # 辅助函数：发送状态并更新记录
        def _should_send(new_progress: Dict) -> bool:
            nonlocal last_sent_progress
            import json
            # 简单比较：转换为 JSON 字符串比较 (确保顺序一致性可能需要 sort_keys=True，但 dict 比较通常足够)
            # 这里直接比较 dict 对象
            if new_progress != last_sent_progress:
                last_sent_progress = new_progress
                return True
            return False

        try:
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_content,
            ):
                if event.content and event.content.parts:
                    
                    # 标志：当前 Event 中是否有状态更新
                    state_updated_in_event = False
                    
                    for part in event.content.parts:
                        # 处理 Tool 调用
                        if hasattr(part, "function_call") and part.function_call:
                            tool_name = part.function_call.name
                            tool_args = part.function_call.args or {}
                            
                            logger.debug(f"检测到 Tool 调用: {tool_name}, 参数: {tool_args}")
                            
                            # 更新状态 (不立即发送，而是标记)
                            updated = self._handle_tool_call(
                                session_id, tool_name, tool_args
                            )
                            if updated:
                                state_updated_in_event = True
                        
                        # 处理文本输出 (实时发送)
                        if hasattr(part, "text") and part.text:
                            yield part.text
                    
                    # 历史遗留注释：原本在此处会根据 state_updated_in_event 发送状态
                    # 现在改为：仅记录 updated 状态，不发送中间状态，改为在流结束后统一发送 (finally 块)
                    if state_updated_in_event:
                        logger.debug("检测到状态更新 (已抑制中间推送，等待流结束)")

        except Exception as e:
            logger.error(f"Alex ADK 流式处理失败: {e}")
            yield f"\n\n错误: {str(e)}"
            
        finally:
            # 流式处理结束（或异常退出）后，强制发送一次最终状态 (仅在有变更时)
            try:
                final_progress = self.state_manager.get_progress_info(session_id)
                if final_progress and _should_send(final_progress):
                    yield {"type": "state", "progress": final_progress}
                    logger.debug(f"发送最终 state 事件 (去重后发送): 阶段索引 {final_progress['currentStageIndex']}")
                else:
                    logger.debug("最终状态与最后一次发送一致，跳过冗余推送")
            except Exception as e:
                logger.error(f"发送最终 state 事件失败: {e}")

    @traceable(name="alex_invoke", run_type="chain")
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
