"""
智能助手AI服务
支持多种AI助手类型：需求分析师Alex、测试分析师Song等
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class IntelligentAssistantService:
    """智能助手AI服务 - 支持多种助手类型的统一服务"""

    # 支持的助手类型
    SUPPORTED_ASSISTANTS = {
        'alex': {
            'name': 'Alex Chen',
            'title': '需求分析师',
            'bundle_file': 'intelligent-requirements-analyst-bundle.txt'
        },
        'song': {
            'name': 'Song Liu', 
            'title': '测试分析师',
            'bundle_file': 'testmaster-song-bundle.txt'
        }
    }

    def __init__(self, config=None, assistant_type='alex'):
        """
        初始化智能助手AI服务
        
        Args:
            config: 可选的AI配置字典，如果不提供则使用环境变量或默认配置
            assistant_type: 助手类型，默认为'alex'（需求分析师）
        """
        self.assistant_type = assistant_type
        
        if assistant_type not in self.SUPPORTED_ASSISTANTS:
            raise ValueError(f"不支持的助手类型: {assistant_type}。支持的类型: {list(self.SUPPORTED_ASSISTANTS.keys())}")
        
        self.assistant_info = self.SUPPORTED_ASSISTANTS[assistant_type]
        
        if config:
            # 使用传入的配置
            self.api_key = config.get("api_key")
            self.base_url = config.get("base_url")
            self.model_name = config.get("model_name")
        else:
            # 尝试从数据库获取默认配置
            self.api_key, self.base_url, self.model_name = self._load_config_from_db()
        
        if not self.api_key:
            raise ValueError("缺少AI服务配置，请配置API密钥")
            
        # 加载指定助手的完整persona
        self.assistant_persona = self._load_assistant_persona()
        
        logger.info(f"智能助手AI服务初始化完成，使用{self.assistant_info['title']}{self.assistant_info['name']}，模型: {self.model_name}")
    
    def _load_config_from_db(self):
        """从数据库加载默认AI配置，如果失败则使用环境变量"""
        try:
            from ..models import RequirementsAIConfig
            
            default_config = RequirementsAIConfig.get_default_config()
            
            if default_config:
                config_data = default_config.get_config_for_ai_service()
                return (
                    config_data["api_key"],
                    config_data["base_url"], 
                    config_data["model_name"]
                )
            else:
                # 回退到环境变量
                logger.warning("未找到默认AI配置，使用环境变量")
                return (
                    os.getenv("OPENAI_API_KEY"),
                    os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                    os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest")
                )
        
        except Exception as e:
            logger.warning(f"从数据库加载AI配置失败: {e}，使用环境变量")
            return (
                os.getenv("OPENAI_API_KEY"),
                os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"), 
                os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest")
            )

    def _load_assistant_persona(self) -> str:
        """加载指定助手的完整persona和指令"""
        try:
            # 读取指定助手的bundle文件
            bundle_file = self.assistant_info['bundle_file']
            bundle_path = Path(__file__).parent.parent.parent / "intelligent-requirements-analyzer" / "dist" / bundle_file
            
            if bundle_path.exists():
                with open(bundle_path, 'r', encoding='utf-8') as f:
                    persona_content = f.read()
                logger.info(f"成功加载{self.assistant_info['title']}{self.assistant_info['name']}的完整persona")
                return persona_content
            else:
                logger.warning(f"未找到{self.assistant_info['title']}persona文件: {bundle_path}")
                return self._get_fallback_persona()
                
        except Exception as e:
            logger.error(f"加载{self.assistant_info['title']}persona失败: {e}")
            return self._get_fallback_persona()

    def _get_fallback_persona(self) -> str:
        """获取备用的基础persona"""
        if self.assistant_type == 'alex':
            return """你是AI需求分析师Alex，专门帮助用户澄清和完善项目需求。
        
你的职责：
1. 理解用户需求，识别信息缺口
2. 通过专业问题引导澄清
3. 提取已确认的需求要点
4. 生成结构化的共识内容

请始终以专业、友好的方式与用户交互。"""
        
        elif self.assistant_type == 'song':
            return """你是AI测试分析师Song，专门帮助用户进行测试策略分析和测试用例设计。

你的职责：
1. 分析功能需求，确定测试范围
2. 设计测试策略和优先级
3. 生成具体的测试用例
4. 输出完整的测试计划文档

请始终以专业、友好的方式与用户交互。"""
        
        else:
            return f"""你是AI智能助手{self.assistant_info['name']}，请协助用户完成相关工作。"""

    def analyze_user_requirement(self, 
                                user_message: str, 
                                session_context: Dict[str, Any],
                                project_name: str,
                                current_stage: str = "initial",
                                session_id: str = None) -> Dict[str, Any]:
        """
        无状态方案：仅通过历史对话维持连续性
        
        Args:
            user_message: 用户输入的需求描述
            session_context: 会话上下文（此方案中基本不使用）
            project_name: 项目名称
            current_stage: 当前分析阶段
            session_id: 会话ID，用于获取历史消息
            
        Returns:
            Dict包含AI回应等基本信息
        """
        try:
            # 构建完整的对话历史（包括当前消息）
            ai_response = self._call_ai_with_full_history(user_message, session_id)
            
            # 返回简化的结果结构
            result = {
                'ai_response': ai_response,
                'processing_time': datetime.utcnow().isoformat(),
                'model_used': self.model_name,
                'stage': current_stage,  # 保持当前阶段不变
                'alex_persona': True,
                # 无状态方案：不使用复杂的上下文存储
                'ai_context': {},
                'consensus_content': {}
            }
            
            logger.info(f"无状态Alex消息处理完成，会话ID: {session_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Alex需求分析AI服务调用失败: {str(e)}")
            raise



    def _call_ai_with_full_history(self, user_message: str, session_id: str) -> str:
        """
        发送所有历史对话，完全无状态方案
        """
        try:
            # 获取会话历史消息
            messages = []
            
            if session_id:
                from ..models import RequirementsMessage
                # 获取所有历史消息，不限制条数
                history_messages = RequirementsMessage.get_by_session(session_id, limit=None)
                
                # 构建消息历史
                for msg in history_messages:
                    if msg.message_type == 'system' and "智能需求分析师" in msg.content:
                        # 激活消息作为系统提示词
                        assistant_name = self.assistant_info['name']
                        assistant_title = self.assistant_info['title']
                        system_prompt = f"你是{assistant_name}，{assistant_title}。请严格按照之前加载的指令和身份执行任务。保持专业的{assistant_name}身份，使用之前定义的命令和功能来帮助用户。"
                        messages.append({"role": "system", "content": system_prompt})
                        messages.append({"role": "user", "content": msg.content})
                    elif msg.message_type == 'user':
                        messages.append({"role": "user", "content": msg.content})
                    elif msg.message_type == 'ai':
                        messages.append({"role": "assistant", "content": msg.content})
            
            # 如果没有系统消息，使用带激活前缀的assistant persona
            if not any(msg["role"] == "system" for msg in messages):
                full_system_prompt = f"""你的关键操作指令已附在下方，请严格按照指令中的persona执行，不要打破角色设定。

{self.assistant_persona}"""
                messages.insert(0, {"role": "system", "content": full_system_prompt})
            
            # 检查当前用户消息是否已经是最后一条消息
            # 如果不是，说明需要添加（例如首次对话或者其他情况）
            if not messages or messages[-1]["role"] != "user" or messages[-1]["content"] != user_message:
                messages.append({"role": "user", "content": user_message})
            
            # 调用AI模型
            return self._call_ai_model_with_messages(messages)
            
        except Exception as e:
            logger.error(f"发送完整历史调用AI失败: {str(e)}")
            raise

    def _call_ai_model_with_messages(self, messages: List[Dict[str, str]]) -> str:
        """使用消息列表调用AI模型"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            # 处理base_url的尾部斜杠，避免双斜杠
            base_url = self.base_url.rstrip('/')
            api_url = f"{base_url}/chat/completions"
            
            logger.info(f"调用AI API with full history: {api_url}, 消息数: {len(messages)}")
            
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=180  # 增加到3分钟，避免长回复被截断
            )
            
            # 解析响应
            if response.status_code == 200:
                result = response.json()
                logger.info(f"AI API响应结构: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                # 统一的AI响应提取逻辑
                try:
                    # OpenAI格式
                    if 'choices' in result and result['choices'] and 'message' in result['choices'][0]:
                        message = result['choices'][0]['message']
                        if 'content' in message and message['content']:
                            ai_message = message['content'].strip()
                        else:
                            # Gemini API可能返回空content或缺少content字段
                            logger.warning(f"AI响应message缺少content或content为空: {message}")
                            ai_message = "AI响应内容为空，请重新尝试。"
                    elif 'candidates' in result:
                        # Google AI格式
                        ai_message = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    else:
                        # 未识别的格式
                        logger.error(f"未知的API响应格式: {result}")
                        raise Exception(f"无法解析AI响应格式，未找到choices或candidates字段")
                        
                    return ai_message
                    
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"解析AI响应时发生错误: {e}, 完整响应: {result}")
                    return "抱歉，AI响应格式解析失败。请检查API配置或稍后重试。"
            else:
                error_msg = f"AI API调用失败: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"AI API网络请求失败: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"调用AI模型失败: {str(e)}")
            raise


# 为了保持导入兼容，创建别名
RequirementsAIService = IntelligentAssistantService



