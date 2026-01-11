"""
LangChain Assistant Service

提供统一的服务接口。
使用 LangChain V1 的 create_agent 实现。
Lisa 智能体使用 LangGraph StateGraph 实现。
"""

import logging
from typing import AsyncIterator, Optional, Dict, List, Any, Union
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
        self._lisa_session_states: Dict[str, Any] = {}  # Lisa Graph 专用状态存储
        
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
        # 创建对应的 Agent
        if self.assistant_type == "alex":
            # Alex 现在也使用 LangGraph 实现
            from .alex import create_alex_graph
            self.agent = create_alex_graph(model_config)
        elif self.assistant_type in ("lisa", "song"):
            # Lisa 使用 LangGraph 实现
            from .lisa import create_lisa_graph
            self.agent = create_lisa_graph(model_config)
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
        
        向 AI 模型发送测试请求并验证响应有效性。
        如果连接失败会抛出异常，调用方需要处理。
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            
        Returns:
            str: AI 模型的有效响应内容
            
        Raises:
            Exception: 连接失败、超时、响应无效等各种错误
        """
        import asyncio
        
        if not self.agent:
            await self.initialize()
            
        user_msg = messages[-1]['content']
        
        # 构建消息
        input_messages = [HumanMessage(content=user_msg)]
        
        # 记录测试开始（脱敏配置信息）
        config_info = {
            "model": self.config.get("model_name", "N/A") if self.config else "使用默认配置",
            "base_url": self.config.get("base_url", "N/A")[:50] + "..." if self.config else "N/A"
        }
        logger.info(f"开始测试连接 - 配置: {config_info}")
        
        try:
            # 添加 30 秒超时控制
            result = await asyncio.wait_for(
                self.agent.ainvoke({"messages": input_messages}),
                timeout=30.0
            )
            
            # 提取响应
            if result and "messages" in result:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    content = last_message.content
                    
                    # 验证响应非空
                    if not content or len(content.strip()) == 0:
                        raise Exception("LLM 返回了空响应")
                    
                    # 验证响应不是常见的错误信息
                    content_lower = content.lower()
                    error_indicators = [
                        "error", "错误", "failed", "失败",
                        "invalid", "无效", "unauthorized", "未授权",
                        "forbidden", "禁止", "not found", "找不到",
                        "timeout", "超时", "quota", "配额",
                        "rate limit", "限流", "insufficient", "余额不足"
                    ]
                    
                    if any(indicator in content_lower for indicator in error_indicators):
                        logger.warning(f"疑似错误响应: {content[:200]}")
                        raise Exception(f"LLM 返回了错误响应: {content[:200]}")
                    
                    # 验证响应长度合理（至少应该有几个字符）
                    if len(content.strip()) < 2:
                        raise Exception(f"LLM 响应过短，疑似无效: '{content}'")
                    
                    logger.info(f"测试连接成功 - 响应长度: {len(content)} 字符")
                    return content
            
            # 如果没有有效响应，抛出异常
            raise Exception("LLM 未返回有效的消息格式")
            
        except asyncio.TimeoutError:
            logger.error(f"测试连接超时（30秒）- 配置: {config_info}")
            raise Exception("连接超时：AI 服务在 30 秒内未响应，请检查网络连接和 Base URL 配置")
        except Exception as e:
            # 记录详细错误信息并向上抛出
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"测试连接失败 [{error_type}]: {error_msg} - 配置: {config_info}")
            
            # 如果是我们自己抛出的异常，直接向上传递
            if "LLM" in error_msg or "连接超时" in error_msg:
                raise
            
            # 对于其他异常，提供更友好的错误信息
            if "api" in error_msg.lower() and "key" in error_msg.lower():
                raise Exception(f"API 密钥验证失败: {error_msg}")
            elif "connection" in error_msg.lower() or "网络" in error_msg:
                raise Exception(f"网络连接失败: {error_msg}")
            elif "404" in error_msg or "not found" in error_msg.lower():
                raise Exception(f"API 端点不存在，请检查 Base URL 配置: {error_msg}")
            else:
                raise Exception(f"连接测试失败: {error_msg}")
    
    async def stream_message(
        self,
        session_id: str,
        user_message: str,
        project_name: Optional[str] = None,
        is_activated: bool = False
    ) -> AsyncIterator[Union[str, dict]]:
        """
        流式处理消息
        
        使用 LangChain V1 的 .astream() 实现真正的增量流式。
        Lisa 和 Alex 智能体均使用 LangGraph StateGraph 管理状态。
        
        Args:
            session_id: 会话 ID
            user_message: 用户消息内容
            project_name: 可选的项目名称
            is_activated: 会话是否已激活（保留参数，兼容接口）
            
        Yields:
            str: AI 回复的文本片段
            dict: state 事件，格式 {"type": "state", "progress": {...}}
        """
        if not self.agent:
            await self.initialize()
        
        logger.info(f"流式处理消息 - 会话: {session_id}, 消息长度: {len(user_message)}")
        
        try:
            # 所有智能体现在都使用 LangGraph 状态管理
            # 统一使用 _stream_graph_message
            async for chunk in self._stream_graph_message(session_id, user_message):
                yield chunk
                    
        except Exception as e:
            logger.error(f"流式处理消息失败: {str(e)}")
            yield f"\n\n错误: {str(e)}"
    
    async def _stream_graph_message(
        self,
        session_id: str,
        user_message: str
    ) -> AsyncIterator[Union[str, dict]]:
        """
        通用 Graph 专用流式处理
        
        使用 StateGraph 管理会话状态，支持工作流控制和产出物存储。
        使用 stream_mode="messages" 获取真正的 token 级流式输出。
        
        Yields:
            str: 文本内容片段
            dict: state 事件 {"type": "state", "progress": {...}}
        """
        
        # 获取或初始化 Graph 状态
        if session_id not in self._lisa_session_states:
            # 根据类型获取初始状态
            if self.assistant_type in ("lisa", "song"):
                from .lisa import get_initial_state
                self._lisa_session_states[session_id] = get_initial_state()
            elif self.assistant_type == "alex":
                from .alex.state import get_initial_state
                self._lisa_session_states[session_id] = get_initial_state()
        
        state = self._lisa_session_states[session_id]
        
        # 添加用户消息到状态
        state["messages"].append(HumanMessage(content=user_message))
        
        # 记录日志 (Alex 可能没有 workflow 字段)
        workflow_info = state.get('current_workflow', 'N/A')
        logger.info(f"Graph 流式处理 - 智能体: {self.assistant_type}, 工作流: {workflow_info}")
        
        # 注意: 不再使用关键词检测工作流类型
        # 工作流类型由 intent_router 节点基于语义判断设置
        
        # 注意: 不在此处发送初始进度事件
        # 进度条应该在 LLM 响应中解析到 <plan> 后才显示
        # 这样可以避免第二轮对话时显示上一轮的旧进度
        
        full_response = ""
        
        # 用户输出节点（需要流式输出的节点）
        # Lisa 需要过滤 intent_router，Alex 主要是 workflow_product_design
        user_facing_nodes = {
            "clarify_intent", 
            "workflow_test_design", 
            "workflow_requirement_review", 
            "workflow_product_design", # Alex
            "model"
        }
        
        # 使用 stream_mode="messages" 获取真正的 token 级增量
        # 导入清理函数用于流式过滤
        from .shared.progress_utils import clean_response_streaming
        
        # 记录已输出的清理后的文本长度
        yielded_len = 0
        
        async for event in self.agent.astream(
            state,
            stream_mode="messages"
        ):
            # event 格式: (message, metadata) 元组
            if isinstance(event, tuple) and len(event) >= 2:
                message, metadata = event[0], event[1]
                
                # 从 metadata 获取当前节点名（langgraph_node）
                node_name = metadata.get("langgraph_node", "")
                
                if node_name in user_facing_nodes:
                    if hasattr(message, 'content') and message.content:
                        content = message.content
                        
                        # 增量输出逻辑：
                        # 基于全量内容进行清理，然后计算新增的 delta
                        # 这种方式可以处理跨 chunk 的 XML 标签，以及临时隐藏未完成的标签
                        
                        if content.startswith(full_response):
                             # Case 1: content 是累积的完整响应 (LangGraph 默认行为)
                             # 无需额外拼接
                             full_response = content
                        else:
                             # Case 2: content 只是增量 chunk (某些 LLM 的行为)
                             # 需要累积到 full_response
                             # 注意：这里假设 content 确实是增量，不包含之前的 duplicated 内容
                             # LangGraph stream_mode="messages" 通常返回的是 MessageChunk，会自动合并
                             # 如果这里返回的是增量 chunk，我们需要自己拼接
                             # 但根据之前的代码，似乎之前的 content 包含了 full_response
                             # 为了安全，我们只信任 MessageChunk 的累积能力，或者只处理 case 1
                             if not full_response.endswith(content):
                                 full_response += content

                        # 核心逻辑：对当前完整的 full_response 进行智能流式清理
                        cleaned_full = clean_response_streaming(full_response)
                        
                        # 计算需要输出的 delta
                        if len(cleaned_full) > yielded_len:
                            delta = cleaned_full[yielded_len:]
                            yield delta
                            yielded_len += len(delta)
            
        # Lisa/Alex: 解析 XML 进度更新指令和动态 Plan，并清理响应
        cleaned_response = full_response
        if self.assistant_type in ("lisa", "song", "alex", "chen") and full_response:
            from .shared.progress_utils import parse_progress_update, parse_plan, clean_response_text
            from .shared.artifact_utils import parse_all_artifacts

            # 解析动态 Plan (LLM 首次规划工作阶段)
            parsed_plan = parse_plan(full_response)
            if parsed_plan:
                state["plan"] = parsed_plan
                state["current_stage_id"] = parsed_plan[0]["id"] if parsed_plan else None
                logger.info(f"动态 Plan 已更新: {len(parsed_plan)} 个阶段")
                logger.info(f"Plan 内容: {parsed_plan}")
            else:
                logger.warning(f"未能解析到 Plan 标签。响应前200字符: {full_response[:200]}")
            
            # 解析进度更新指令 (阶段切换)
            update_result = parse_progress_update(full_response)
            if update_result:
                stage_id, new_status = update_result
                state["current_stage_id"] = stage_id
                logger.info(f"进度更新: current_stage_id -> {stage_id}")
            
            # 解析产出物 (统一处理 <artifact> 标签)
            artifacts = parse_all_artifacts(full_response)
            if artifacts:
                if "artifacts" not in state:
                    state["artifacts"] = {}
                for artifact in artifacts:
                    state["artifacts"][artifact["key"]] = artifact["content"]
                    logger.info(f"产出物已保存: {artifact['key']} ({len(artifact['content'])} 字符)")
            
            # 清理 XML 标签 (包括 plan, update_status, artifact)
            cleaned_response = clean_response_text(full_response)
        
        # 将清理后的响应添加到消息历史
        if cleaned_response:
            state["messages"].append(AIMessage(content=cleaned_response))
        
        # 保存更新后的状态
        self._lisa_session_states[session_id] = state
        
        # Lisa/Alex: 发送最终 state 事件（进度条在 LLM 响应完成后显示）
        if self.assistant_type in ("lisa", "song", "alex", "chen"):
            from .shared.progress import get_progress_info
            progress = get_progress_info(state)
            if progress:
                yield {"type": "state", "progress": progress}
                logger.info(f"进度事件已发送: 当前阶段索引 {progress['currentStageIndex']}")
                logger.info(f"进度事件内容: stages={len(progress['stages'])}, currentTask={progress['currentTask']}")
            else:
                logger.warning(f"未发送进度事件 - plan: {state.get('plan')}, current_stage_id: {state.get('current_stage_id')}")
        
        # 同时保存到传统历史记录（用于兼容）
        self._add_to_history(session_id, "user", user_message)
        self._add_to_history(session_id, "assistant", cleaned_response)
        
        logger.info(f"Graph 流式消息处理完成，总计: {len(cleaned_response)} 字符")
        
    
    async def _stream_legacy_message(
        self,
        session_id: str,
        user_message: str
    ) -> AsyncIterator[str]:
        """
        传统智能体流式处理（Alex 等）
        """
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



