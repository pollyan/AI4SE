"""
LangChain Assistant Service

提供统一的服务接口。
使用 LangChain V1 的 create_agent 实现。
"""

import logging
from typing import AsyncIterator, Optional, Dict, List
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)


class LangchainAssistantService:
    """
    LangChain 智能体服务
    
    """
    
    SUPPORTED_ASSISTANTS = {
        "alex": {
            "name": "Alex",
            "title": "需求分析专家",
            "bundle_file": "alex_v1_bundle.txt",
            "description": "专业的软件需求分析师，擅长澄清需求、识别模糊点并生成详细的需求文档。"
        },
        "lisa": {
            "name": "Lisa",
            "title": "测试专家 (v5.0)",
            "bundle_file": "lisa_v5_bundle.txt",
            "description": "资深测试专家，专注于制定测试策略、设计测试用例和探索性测试。"
        }
    }
    
    def __init__(self, assistant_type: str, config: Optional[dict] = None):
        """
        初始化 LangChain 服务
        
        Args:
            assistant_type: 智能体类型 ('alex' 或 'lisa')
            config: 可选的配置字典 (用于测试连接或覆盖默认配置)
        """
        self.assistant_type = assistant_type
        self.config = config
        self.agent = None
        self._session_histories: Dict[str, List[dict]] = {}  # {session_id: [messages]}
        
        logger.info(f"初始化 LangChain 智能体服务: {assistant_type}")
    
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
            from ..models import RequirementsAIConfig
            
            config = RequirementsAIConfig.get_default_config()
            if not config:
                raise ValueError("未找到 AI 配置，请先在系统中配置 AI 服务")
            
            model_config = config.get_config_for_ai_service()
        
        # 创建对应的 Agent
        if self.assistant_type == "alex":
            from .alex import create_alex_agent
            self.agent = create_alex_agent(model_config)
        elif self.assistant_type in ("lisa", "song"):
            from .lisa import create_lisa_agent
            self.agent = create_lisa_agent(model_config)
        else:
            raise ValueError(f"未知的智能体类型: {self.assistant_type}")
        
        logger.info(f"{self.assistant_type} 智能体初始化完成")

    def _get_session_history(self, session_id: str) -> List[dict]:
        """获取或创建会话历史"""
        if session_id not in self._session_histories:
            self._session_histories[session_id] = []
        return self._session_histories[session_id]
    
    def _add_to_history(self, session_id: str, role: str, content: str):
        """添加消息到会话历史"""
        history = self._get_session_history(session_id)
        history.append({"role": role, "content": content})
    
    def _build_messages(self, session_id: str, user_message: str) -> list:
        """构建消息列表用于 Agent 调用"""
        history = self._get_session_history(session_id)
        
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # 添加当前用户消息
        messages.append(HumanMessage(content=user_message))
        
        return messages

    async def analyze_user_requirement(self, 
                                user_message: str, 
                                session_context: dict = None,
                                project_name: str = None,
                                current_stage: str = "initial",
                                session_id: str = None) -> dict:
        """
        处理非流式消息
        """
        if not self.agent:
            await self.initialize()

        logger.info(f"非流式处理消息 - 会话: {session_id}, 消息长度: {len(user_message)}")

        try:
            # 构建消息
            messages = self._build_messages(session_id, user_message)
            
            # 调用 Agent (非流式)
            result = await self.agent.ainvoke({"messages": messages})
            
            # 提取 AI 响应
            ai_response = ""
            if result and "messages" in result:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    ai_response = last_message.content
            
            # 保存到会话历史
            self._add_to_history(session_id, "user", user_message)
            self._add_to_history(session_id, "assistant", ai_response)

            return {
                'ai_response': ai_response,
                'stage': current_stage,
                'ai_context': {},
                'consensus_content': {}
            }

        except Exception as e:
            logger.error(f"非流式处理失败: {str(e)}")
            raise

    async def test_connection(self, messages: list) -> str:
        """
        测试连接
        """
        if not self.agent:
            await self.initialize()
            
        user_msg = messages[-1]['content']
        
        # 构建消息
        input_messages = [HumanMessage(content=user_msg)]
        
        # 调用 Agent
        result = await self.agent.ainvoke({"messages": input_messages})
        
        # 提取响应
        if result and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, "content"):
                return last_message.content
        
        return ""
    
    async def stream_message(
        self,
        session_id: str,
        user_message: str,
        project_name: Optional[str] = None,
        is_activated: bool = False
    ) -> AsyncIterator[str]:
        """
        流式处理消息
        
        使用 LangChain V1 的 .astream() 实现真正的增量流式。
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息内容
            project_name: 可选的项目名称
            is_activated: 会话是否已激活（保留参数，兼容接口）
            
        Yields:
            AI 回复的文本片段（真流式，每个 chunk 直接是增量内容）
        """
        if not self.agent:
            await self.initialize()
        
        logger.info(f"流式处理消息 - 会话: {session_id}, 消息长度: {len(user_message)}")
        
        try:
            # 构建消息
            messages = self._build_messages(session_id, user_message)
            
            logger.info(f"开始流式运行 LangChain agent...")
            full_response = ""
            
            # 真流式！使用 stream_mode="messages" 获取增量输出
            async for chunk in self.agent.astream(
                {"messages": messages},
                stream_mode="messages"
            ):
                # chunk 格式: (message, metadata) 元组
                if isinstance(chunk, tuple) and len(chunk) >= 1:
                    message = chunk[0]
                    if hasattr(message, 'content') and message.content:
                        content = message.content
                        # 直接输出增量内容
                        yield content
                        full_response += content
                elif hasattr(chunk, 'content') and chunk.content:
                    # 备用格式处理
                    yield chunk.content
                    full_response += chunk.content
            
            # 保存完整响应到会话历史
            self._add_to_history(session_id, "user", user_message)
            self._add_to_history(session_id, "assistant", full_response)
            
            logger.info(f"流式消息处理完成，总计: {len(full_response)} 字符")
            
        except Exception as e:
            logger.error(f"流式处理消息失败: {str(e)}")
            yield f"\n\n错误: {str(e)}"



