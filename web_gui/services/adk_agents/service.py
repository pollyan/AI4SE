"""
ADK Assistant Service

提供统一的服务接口，与原 LangGraphAssistantService 保持相同签名。
"""

import logging
from typing import AsyncIterator, Optional
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import RunConfig
from google.adk.agents.run_config import StreamingMode
from google.genai import types

logger = logging.getLogger(__name__)


class AdkAssistantService:
    """
    Google ADK 智能体服务
    
    替代 LangGraphAssistantService，提供相同的接口。
    """
    
    def __init__(self, assistant_type: str, config: Optional[dict] = None):
        """
        初始化 ADK 服务
        
        Args:
            assistant_type: 智能体类型 ('alex' 或 'lisa')
            config: 可选的配置字典 (用于测试连接或覆盖默认配置)
        """
        self.assistant_type = assistant_type
        self.config = config
        self.runner = None
        self.session_service = InMemorySessionService()
        
        logger.info(f"初始化 ADK 智能体服务: {assistant_type}")
    
    async def initialize(self):
        """异步初始化服务"""
        logger.info(f"异步初始化 {self.assistant_type} 智能体")
        
        model_config = None
        
        if self.config:
            # 使用传入的配置
            logger.info("使用传入的配置初始化")
            model_config = self.config
        else:
            # 获取默认配置
            from ...models import RequirementsAIConfig
            
            config = RequirementsAIConfig.get_default_config()
            if not config:
                raise ValueError("未找到 AI 配置，请先在系统中配置 AI 服务")
            
            model_config = config.get_config_for_ai_service()
        
        # 创建对应的 Agent
        if self.assistant_type == "alex":
            from .alex import create_alex_agent
            agent = create_alex_agent(model_config)
        elif self.assistant_type in ("lisa", "song"):
            from .lisa import create_lisa_agent
            agent = create_lisa_agent(model_config)
        else:
            raise ValueError(f"未知的智能体类型: {self.assistant_type}")
        
        # 创建 Runner
        self.runner = Runner(
            agent=agent,
            app_name="intent-test-framework",
            session_service=self.session_service
        )
        
        logger.info(f"{self.assistant_type} 智能体初始化完成")

    async def analyze_user_requirement(self, 
                                user_message: str, 
                                session_context: dict = None,
                                project_name: str = None,
                                current_stage: str = "initial",
                                session_id: str = None) -> dict:
        """
        处理非流式消息 (兼容 RequirementsAIService 接口)
        """
        if not self.runner:
            await self.initialize()

        logger.info(f"非流式处理消息 - 会话: {session_id}, 消息长度: {len(user_message)}")

        try:
            # 创建或获取 session
            session = await self.session_service.get_session(
                app_name="intent-test-framework",
                user_id="default",
                session_id=session_id
            )
            
            if not session:
                session = await self.session_service.create_session(
                    app_name="intent-test-framework",
                    user_id="default",
                    session_id=session_id
                )
            
            # 构建消息
            content = types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )
            
            # 运行 (非流式)
            # ADK 的 run_async 默认返回 stream，我们需要根据 run_config 控制或手动收集
            # 此处我们收集流式响应组合成完整文本
            
            full_response_text = ""
            
            async for event in self.runner.run_async(
                user_id="default",
                session_id=session_id,
                new_message=content
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            # 注意：ADK v1 可能是累积的也可能是增量的，取决于具体实现
                            # 但根据 stream_message 的实现，我们假设需要处理
                            # 观察 stream_message 逻辑，event.content.parts[0].text似乎是累积的？
                            # 在 stream_message 中：
                            # if current_text.startswith(previous_text): delta = ...
                            # 这意味着 event.content 是累积的。
                            # 所以最后一个 event 包含完整文本。
                            pass
                
                # 我们只关心最终状态，或者简单的覆盖
                # 如果是累积的，只需保留最新的 text
                if event.content and event.content.parts:
                     for part in event.content.parts:
                        if part.text:
                            # 假设是累积的，且只有一段文本
                            if len(part.text) > len(full_response_text):
                                full_response_text = part.text

            return {
                'ai_response': full_response_text,
                'stage': current_stage,
                'ai_context': {}, # ADK 管理状态，不需要返回给前端/DB存储
                'consensus_content': {}
            }

        except Exception as e:
            logger.error(f"非流式处理失败: {str(e)}")
            raise

    async def test_connection(self, messages: list) -> str:
        """
        测试连接
        """
        if not self.runner:
            await self.initialize()
            
        user_msg = messages[-1]['content']
        
        # 使用临时 session ID
        session_id = "test_connection_session"
        
        # 确保 session 存在 (InMemory)
        await self.session_service.create_session(
            app_name="intent-test-framework",
            user_id="default",
            session_id=session_id
        )

        content = types.Content(
            role="user",
            parts=[types.Part(text=user_msg)]
        )

        full_response_text = ""
        async for event in self.runner.run_async(
            user_id="default",
            session_id=session_id,
            new_message=content
        ):
             if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and len(part.text) > len(full_response_text):
                        full_response_text = part.text
        
        return full_response_text
    
    async def stream_message(
        self,
        session_id: str,
        user_message: str,
        project_name: Optional[str] = None,
        is_activated: bool = False
    ) -> AsyncIterator[str]:
        """
        流式处理消息
        
        接口与 LangGraphAssistantService.stream_message 保持一致。
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息内容
            project_name: 可选的项目名称
            is_activated: 会话是否已激活（保留参数，兼容接口）
            
        Yields:
            AI 回复的文本片段
        """
        if not self.runner:
            await self.initialize()
        
        logger.info(f"流式处理消息 - 会话: {session_id}, 消息长度: {len(user_message)}")
        
        try:
            # 创建或获取 session
            session = await self.session_service.get_session(
                app_name="intent-test-framework",
                user_id="default",
                session_id=session_id
            )
            
            if not session:
                session = await self.session_service.create_session(
                    app_name="intent-test-framework",
                    user_id="default",
                    session_id=session_id
                )
                logger.info(f"创建新会话: {session_id}")
            
            # 构建消息
            content = types.Content(
                role="user",
                parts=[types.Part(text=user_message)]
            )
            
            # 流式运行 - ADK 会产生多个增量事件
            logger.info(f"开始流式运行 ADK agent...")
            previous_text = ""
            event_count = 0
            
            async for event in self.runner.run_async(
                user_id="default",
                session_id=session_id,
                new_message=content,
                run_config=RunConfig(streaming_mode=StreamingMode.SSE)
            ):
                event_count += 1
                
                # ADK 事件包含累积的完整文本，需要提取增量部分
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            current_text = part.text
                            # 提取新增的文本（增量）
                            if current_text.startswith(previous_text):
                                delta = current_text[len(previous_text):]
                                if delta:
                                    logger.debug(f"流式输出增量: {len(delta)} 字符")
                                    yield delta
                                    previous_text = current_text
                            else:
                                # 如果文本不是累积的，直接输出
                                logger.debug(f"流式输出完整: {len(current_text)} 字符")
                                yield current_text
                                previous_text = current_text
            
            logger.info(f"流式消息处理完成，总计: {len(previous_text)} 字符")
            
        except Exception as e:
            logger.error(f"流式处理消息失败: {str(e)}")
            yield f"\n\n错误: {str(e)}"


