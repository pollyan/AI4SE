"""
LangChain Assistant Service

提供统一的服务接口。
使用 LangChain V1 的 create_agent 实现。
Lisa 智能体使用 LangGraph StateGraph 实现。
Alex 智能体使用 Google ADK 实现。
"""

import logging
import json
import re
from typing import AsyncIterator, Optional, Dict, List, Any, Union, TYPE_CHECKING
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)


class LangchainAssistantService:
    """
    LangChain 智能体服务
    
    """
    
    SUPPORTED_ASSISTANTS = {
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
            assistant_type: 智能体类型 ('lisa')
            config: 可选的配置字典 (用于测试连接或覆盖默认配置)
        """
        self.assistant_type = assistant_type
        self.config = config
        self.agent = None
        self._session_histories: Dict[str, List[dict]] = {}
        
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
        if self.assistant_type == "lisa":
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
            messages = self._build_messages(session_id, user_message)
            result = await self.agent.ainvoke({"messages": messages})
            ai_response = ""
            if result and "messages" in result:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    ai_response = last_message.content
            
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
        
        config_info = {
            "model": self.config.get("model_name", "N/A") if self.config else "使用默认配置",
            "base_url": self.config.get("base_url", "N/A")[:50] + "..." if self.config else "N/A"
        }
        logger.info(f"开始测试连接 - 配置: {config_info}")
        
        try:
            input_messages = [HumanMessage(content=user_msg)]
            test_config = {"configurable": {"thread_id": "test-connection"}}
            result = await asyncio.wait_for(
                self.agent.ainvoke({"messages": input_messages}, config=test_config),
                timeout=30.0
            )
            content = ""
            if result and "messages" in result:
                last_message = result["messages"][-1]
                if hasattr(last_message, "content"):
                    content = last_message.content
            
            if not content or len(content.strip()) == 0:
                raise Exception("LLM 返回了空响应")
            
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
            
            if len(content.strip()) < 2:
                raise Exception(f"LLM 响应过短，疑似无效: '{content}'")
            
            logger.info(f"测试连接成功 - 响应长度: {len(content)} 字符")
            return content
            
        except asyncio.TimeoutError:
            logger.error(f"测试连接超时（30秒）- 配置: {config_info}")
            raise Exception("连接超时：AI 服务在 30 秒内未响应，请检查网络连接和 Base URL 配置")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"测试连接失败 [{error_type}]: {error_msg} - 配置: {config_info}")
            
            if "LLM" in error_msg or "连接超时" in error_msg:
                raise
            
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
            # Lisa 继续使用 LangGraph 状态管理
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
        
        使用 Checkpointer 自动管理会话状态，通过 thread_id 追踪会话。
        使用 stream_mode="messages" 获取真正的 token 级流式输出。
        """
        
        config = {"configurable": {"thread_id": session_id}}
        
        logger.info(f"Graph 流式处理 - 智能体: {self.assistant_type}, 会话: {session_id}")
        
        full_response = ""
        
        user_facing_nodes = {
            "clarify_intent", 
            "workflow_test_design", 
            "workflow_requirement_review", 
            "workflow_product_design",
            "model"
        }
        
        # 仅对这些节点启用 AIMessage 过滤（因为它们使用流式输出）
        streaming_nodes = {
            "workflow_test_design",
            "workflow_requirement_review",
            "workflow_product_design",
            "model"
        }
        
        # from .shared.progress_utils import clean_response_streaming  # Removed
        processed_templates = set()
        plan_parsed = False
        json_parsed = False

        from .shared.progress_utils import (
            clean_response_text,
            get_current_stage_id,
            parse_structured_json,
            extract_plan_from_structured,
            extract_artifacts_from_structured,
        )
        # from .shared.artifact_utils import parse_all_artifacts (Removed)
        from .shared.output_parser import split_message_and_json
        
        yielded_len = 0
        
        current_state = {}
        
        async for chunk in self.agent.astream(
            {"messages": [HumanMessage(content=user_message)]},
            config=config,
            stream_mode=["messages", "updates", "custom"]  # 添加 custom 模式接收 StreamWriter 数据
        ):
            if isinstance(chunk, tuple) and len(chunk) == 2:
                mode, payload = chunk
                
                # ════════════════════════════════════════════════════════════
                # 处理 custom 模式 (来自 get_stream_writer)
                # ════════════════════════════════════════════════════════════
                if mode == "custom":
                    if isinstance(payload, dict):
                        data_type = payload.get("type")
                        
                        if data_type == "progress":
                            # 直接使用 StreamWriter 发送的进度数据
                            progress_data = payload.get("progress", {})
                            current_state["plan"] = progress_data.get("stages", [])
                            idx = progress_data.get("currentStageIndex", 0)
                            current_state["currentStageIndex"] = idx
                            current_state["currentTask"] = progress_data.get("currentTask", "")
                            
                            # Ensure current_stage_id is set for get_progress_info
                            if current_state["plan"] and 0 <= idx < len(current_state["plan"]):
                                current_state["current_stage_id"] = current_state["plan"][idx].get("id")
                            
                            # 提取并保存产出物模板元数据
                            if "artifact_templates" in progress_data:
                                current_state["artifact_templates"] = progress_data["artifact_templates"]
                            
                            # 提取并保存产出物内容 (模板初始化或增量更新)
                            if "artifacts" in progress_data:
                                if "artifacts" not in current_state:
                                    current_state["artifacts"] = {}
                                current_state["artifacts"].update(progress_data["artifacts"])
                            
                            from .shared.progress import get_progress_info
                            progress_info = get_progress_info(current_state)
                            if progress_info:
                                yield {"type": "state", "progress": progress_info}
                            logger.info(f"StreamWriter 进度: stage={progress_data.get('currentStageIndex')}")
                        
                        elif data_type == "artifact":
                            # 处理 StreamWriter 发送的产出物数据
                            artifact_data = payload.get("artifact", {})
                            artifact_key = artifact_data.get("key")
                            artifact_content = artifact_data.get("content")
                            
                            if artifact_key and artifact_content:
                                if "artifacts" not in current_state:
                                    current_state["artifacts"] = {}
                                current_state["artifacts"][artifact_key] = artifact_content
                                
                                from .shared.progress import get_progress_info
                                progress_info = get_progress_info(current_state)
                                if progress_info:
                                    yield {"type": "state", "progress": progress_info}
                                logger.info(f"StreamWriter 产出物: {artifact_key}")
                        
                        elif data_type == "data_stream_event":
                            # 透传数据流事件 (如 progress data 等)
                            yield payload.get("event")
                        
                        elif data_type == "text_delta_chunk":
                            # 接收原始 delta，直接 yield 字符串，由 adapter 包装 ID
                            yield payload.get("delta")
                
                elif mode == "updates":
                    for node_name, update_content in payload.items():
                        if isinstance(update_content, dict):
                            current_state.update(update_content)
                            if "current_workflow" in update_content:
                                logger.info(f"状态更新 [{node_name}]: current_workflow -> {update_content['current_workflow']}")

                elif mode == "messages":
                    message, metadata = payload
                
                    node_name = metadata.get("langgraph_node", "")
                    
                    if node_name in user_facing_nodes:
                        # 只处理 AIMessageChunk（流式 token），忽略完整的 AIMessage（节点返回）
                        # 避免 LangGraph stream_mode="messages" 同时捕获流式和最终消息导致重复
                        # 注意：仅对流式节点应用此逻辑；静态节点（如 clarify_intent）没有 chunks，必须保留 AIMessage
                        if node_name in streaming_nodes:
                            if isinstance(message, AIMessage) and not isinstance(message, AIMessageChunk):
                                continue
                        
                        if hasattr(message, 'content') and message.content:
                            content = message.content
                            
                            # 直接追加内容，不做去重
                            # 之前的去重逻辑会导致 Markdown 格式（如 **）和重复词被吞噬
                            # 我们已经通过 AIMessageChunk 类型过滤解决了 LangGraph 重复推送的问题
                            full_response += content
    
                            if not json_parsed and not plan_parsed:
                                if '```json' in full_response and '```' in full_response[full_response.find('```json')+7:]:
                                    structured_data, _ = parse_structured_json(full_response)
                                    if structured_data:
                                        parsed_plan = extract_plan_from_structured(structured_data)
                                        if parsed_plan:
                                            current_state["plan"] = parsed_plan
                                            stage_id = structured_data.get("current_stage_id") or get_current_stage_id(parsed_plan) or ""
                                            current_state["current_stage_id"] = stage_id
                                            plan_parsed = True
                                            json_parsed = True
                                        
                                        templates, artifacts_dict = extract_artifacts_from_structured(structured_data)
                                        if templates:
                                            if "artifact_templates" not in current_state:
                                                current_state["artifact_templates"] = []
                                            existing_keys = {t.get("artifact_key") for t in current_state["artifact_templates"]}
                                            for tmpl in templates:
                                                if tmpl.get("artifact_key") not in existing_keys:
                                                    current_state["artifact_templates"].append(tmpl)
                                        
                                        if artifacts_dict:
                                            if "artifacts" not in current_state:
                                                current_state["artifacts"] = {}
                                            current_state["artifacts"].update(artifacts_dict)
                                        
                                        from .shared.progress import get_progress_info
                                        progress_info = get_progress_info(current_state)
                                    yield {"type": "state", "progress": progress_info}
                                    logger.info("JSON 结构化输出解析成功")

                        # [REMOVED] Legacy XML Artifact Parsing
                        # if "<artifact" in full_response.lower() and "</artifact>" in full_response.lower():
                        #     ... (removed) ...

                        # temp_cleaned = clean_response_streaming(full_response)
                        temp_cleaned = full_response
                        message_part, _ = split_message_and_json(temp_cleaned)
                        
                        if len(message_part) > yielded_len:
                            delta = message_part[yielded_len:]
                            yielded_len += len(delta)
                            yield delta
            
        final_message, final_json = split_message_and_json(full_response)
        cleaned_response = clean_response_text(final_message)

        if self.assistant_type == "lisa" and full_response:
            
            if not json_parsed and not plan_parsed:
                structured_data = None
                parsed_plan = None
                
                if final_json:
                    from .shared.output_parser import parse_structured_output
                    from .shared.schemas import LisaStructuredOutput
                    
                    structured_obj = parse_structured_output(final_json, LisaStructuredOutput)
                    
                    if structured_obj:
                        structured_data = structured_obj.model_dump()
                        
                        parsed_plan = extract_plan_from_structured(structured_data)
                        if parsed_plan:
                            current_state["plan"] = parsed_plan
                            stage_id = structured_data.get("current_stage_id") or get_current_stage_id(parsed_plan) or ""
                            current_state["current_stage_id"] = stage_id
                        
                        templates, artifacts_dict = extract_artifacts_from_structured(structured_data)
                        
                        if templates:
                            if "artifact_templates" not in current_state:
                                current_state["artifact_templates"] = []
                            existing_keys = {t.get("artifact_key") for t in current_state["artifact_templates"]}
                            for tmpl in templates:
                                if tmpl.get("artifact_key") not in existing_keys:
                                    current_state["artifact_templates"].append(tmpl)
                        
                        if artifacts_dict:
                            if "artifacts" not in current_state:
                                current_state["artifacts"] = {}
                            current_state["artifacts"].update(artifacts_dict)
                        
                        json_parsed = True
            
            from .shared.progress import get_progress_info
            progress_info = get_progress_info(current_state)
            if progress_info:
                yield {"type": "state", "progress": progress_info}
        
        if self.assistant_type == "lisa":
            from .shared.progress import get_progress_info
            progress = get_progress_info(current_state)
            if progress:
                yield {"type": "state", "progress": progress}
                logger.info(f"进度事件已发送: 当前阶段索引 {progress['currentStageIndex']}")
            else:
                logger.warning(f"未发送进度事件 - plan: {current_state.get('plan')}, current_stage_id: {current_state.get('current_stage_id')}")
        
        self._add_to_history(session_id, "user", user_message)
        self._add_to_history(session_id, "assistant", cleaned_response)
        
        logger.info(f"Graph 流式消息处理完成，总计: {len(cleaned_response)} 字符")
