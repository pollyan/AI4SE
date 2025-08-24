"""
需求分析AI服务
基于已有的智能需求分析师Alex，使用完整的BMAD架构persona
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class RequirementsAIService:
    """需求分析AI服务 - 使用智能需求分析师Alex persona，完全基于真实AI模型"""

    def __init__(self, config=None):
        """
        初始化需求分析AI服务
        
        Args:
            config: 可选的AI配置字典，如果不提供则使用环境变量或默认配置
        """
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
            
        # 加载智能需求分析师Alex的完整persona
        self.alex_persona = self._load_alex_persona()
        
        logger.info(f"需求分析AI服务初始化完成，使用智能需求分析师Alex persona，模型: {self.model_name}")
    
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

    def _load_alex_persona(self) -> str:
        """加载智能需求分析师Alex的完整persona和指令"""
        try:
            # 读取完整的智能需求分析师bundle
            bundle_path = Path(__file__).parent.parent.parent / "intelligent-requirements-analyzer" / "dist" / "intelligent-requirements-analyst-bundle.txt"
            
            if bundle_path.exists():
                with open(bundle_path, 'r', encoding='utf-8') as f:
                    alex_content = f.read()
                logger.info("成功加载智能需求分析师Alex的完整persona")
                return alex_content
            else:
                logger.warning(f"未找到Alex persona文件: {bundle_path}")
                return self._get_fallback_persona()
                
        except Exception as e:
            logger.error(f"加载Alex persona失败: {e}")
            return self._get_fallback_persona()

    def _get_fallback_persona(self) -> str:
        """获取备用的基础persona"""
        return """你是AI需求分析师Alex，专门帮助用户澄清和完善项目需求。
        
你的职责：
1. 理解用户需求，识别信息缺口
2. 通过专业问题引导澄清
3. 提取已确认的需求要点
4. 生成结构化的共识内容

请始终以专业、友好的方式与用户交互。"""

    def analyze_user_requirement(self, 
                                user_message: str, 
                                session_context: Dict[str, Any],
                                project_name: str,
                                current_stage: str = "initial") -> Dict[str, Any]:
        """
        纯传输模式：直接转发用户消息给AI模型，让Alex完全自主处理
        
        Args:
            user_message: 用户输入的需求描述
            session_context: 会话上下文（在纯传输模式下基本不使用）
            project_name: 项目名称
            current_stage: 当前分析阶段
            
        Returns:
            Dict包含AI回应等基本信息
        """
        try:
            # 纯传输模式：不构建复杂的系统提示词，直接使用用户消息
            # 如果是激活消息（包含bundle），直接发送
            # 如果是普通消息，简单转发
            
            if "智能需求分析师" in user_message and "Bundle" in user_message:
                # 这是激活Alex的消息，直接发送
                ai_response = self._call_ai_model("", user_message)
            else:
                # 普通对话消息，简单转发
                ai_response = self._call_ai_model("", user_message)
            
            # 纯传输模式：最简化的返回结构
            result = {
                'ai_response': ai_response,
                'processing_time': datetime.utcnow().isoformat(),
                'model_used': self.model_name,
                'stage': current_stage,  # 保持当前阶段不变
                'alex_persona': True,
                # 简化的上下文信息
                'ai_context': session_context.get('ai_context', {}),
                'consensus_content': session_context.get('consensus_content', {})
            }
            
            logger.info(f"纯传输模式：消息已转发给Alex")
            
            return result
            
        except Exception as e:
            logger.error(f"Alex需求分析AI服务调用失败: {str(e)}")
            raise

    def _build_alex_system_prompt(self, project_name: str, current_stage: str) -> str:
        """构建Alex系统提示词"""
        # 将Alex的完整persona作为系统指令，同时添加项目特定上下文
        alex_instructions = f"""你的关键操作指令已附在下方，请严格按照指令中的persona执行，不要打破角色设定。

{self.alex_persona}

=== 当前项目上下文 ===
项目名称: {project_name}
当前阶段: {current_stage}

=== 特殊指令 ===
由于你现在是在Web应用中工作，而不是在聊天界面，请注意：
1. 请使用智能澄清方法分析用户需求
2. 生成的回应应该是自然的对话，但也要包含结构化的共识信息
3. 遵循BMAD架构原则，完全自主决策
4. 当需要澄清时，提供具体的澄清问题

请以Alex的身份响应用户需求，提供专业的需求分析和澄清引导。"""
        
        return alex_instructions

    def _build_alex_user_prompt(self, user_message: str, session_context: Dict[str, Any]) -> str:
        """构建Alex用户提示词"""
        context_str = ""
        
        # 添加会话历史上下文（以Alex可理解的方式）
        if session_context.get('user_context') or session_context.get('ai_context') or session_context.get('consensus_content'):
            context_str += "\n=== 对话历史上下文 ===\n"
            
            if session_context.get('consensus_content'):
                context_str += f"当前已达成的共识：\n{json.dumps(session_context['consensus_content'], ensure_ascii=False, indent=2)}\n"
            
            if session_context.get('user_context'):
                context_str += f"用户历史上下文：\n{json.dumps(session_context['user_context'], ensure_ascii=False, indent=2)}\n"
                
            if session_context.get('ai_context'):
                context_str += f"AI分析历史：\n{json.dumps(session_context['ai_context'], ensure_ascii=False, indent=2)}\n"

        return f"""用户当前输入：
{user_message}
{context_str}
请作为智能需求分析师Alex，分析这条用户输入，结合历史上下文，提供专业的需求分析和澄清引导。

请直接以对话方式回应，但同时识别和提取关键的需求信息。"""

    def _call_ai_model(self, system_prompt: str, user_prompt: str) -> str:
        """调用AI模型API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            # 处理base_url的尾部斜杠，避免双斜杠
            base_url = self.base_url.rstrip('/')
            api_url = f"{base_url}/chat/completions"
            
            logger.info(f"调用AI API: {api_url}, 模型: {self.model_name}")
            
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"AI API调用失败，状态码: {response.status_code}, 响应: {response.text}")
            
            result = response.json()
            ai_message = result['choices'][0]['message']['content'].strip()
            
            logger.info(f"AI模型调用成功，返回内容长度: {len(ai_message)}")
            return ai_message
            
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API网络请求失败: {str(e)}")
            raise Exception(f"AI服务网络异常: {str(e)}")
        except Exception as e:
            logger.error(f"AI API调用异常: {str(e)}")
            raise

    def _parse_alex_response(self, ai_response: str, user_message: str) -> Dict[str, Any]:
        """
        简化版Alex响应解析 - 专注于数据传输，所有逻辑由Alex persona处理
        
        按照纯传输模式，我们只负责将Alex的回应包装成前端需要的格式
        """
        try:
            # Alex的回应就是自然对话，直接传输
            ai_response_content = ai_response.strip()
            
            # 构建最简化的传输格式
            # 所有分析逻辑都在Alex persona中完成，Web层只做数据包装
            return {
                'ai_response': ai_response_content,
                'identified_requirements': [],  # Alex在对话中自然表达，不需要结构化提取
                'information_gaps': [],  # Alex在对话中自然询问，不需要预处理
                'clarification_questions': [],  # Alex在对话中自然提问，不需要单独提取  
                'consensus_content': {
                    'analysis_method': 'Alex智能需求分析师',
                    'last_user_input': user_message,
                    'conversation_active': True
                },
                'analysis_summary': 'Alex已处理用户输入'
            }
            
        except Exception as e:
            logger.error(f"Alex响应传输时出现异常: {str(e)}")
            # 返回安全的错误恢复结果
            return {
                'ai_response': ai_response if ai_response else "抱歉，我遇到了一些技术问题，请您重新发送消息。",
                'identified_requirements': [],
                'information_gaps': [],
                'clarification_questions': [],
                'consensus_content': {
                    'analysis_status': '传输异常，需要重新发送',
                    'error_info': str(e)
                },
                'analysis_summary': '传输过程中出现异常'
            }

    def _determine_next_stage(self, parsed_result: Dict[str, Any], current_stage: str) -> str:
        """
        简化版阶段判断 - Alex会在对话中自然体现进展，无需复杂逻辑
        """
        # 在纯传输模式下，阶段变更也应该由Alex在对话中自然表达
        # Web层只需保持一个简单的进展标记即可
        return current_stage  # 保持当前阶段，让Alex在对话中自然推进

    def generate_welcome_message(self, project_name: str) -> Dict[str, Any]:
        """
        使用Alex persona为新会话生成欢迎消息
        
        Args:
            project_name: 项目名称
            
        Returns:
            包含Alex欢迎消息和初始分析的字典
        """
        try:
            # 构建Alex的欢迎场景系统提示词
            system_prompt = f"""你的关键操作指令已附在下方，请严格按照指令中的persona执行。

{self.alex_persona}

=== 当前场景 ===
用户刚刚创建了一个名为"{project_name}"的需求分析会话，这是你们的第一次接触。

=== 特殊指令 ===
请以智能需求分析师Alex的身份：
1. 生成一个专业、温暖的欢迎消息
2. 简要介绍你的能力和分析方法
3. 引导用户开始描述需求
4. 体现出你的专业性和对需求分析的深度理解

请直接以对话方式回应，不要使用JSON格式。"""

            user_prompt = f"""用户创建了项目"{project_name}"的需求分析会话。

请作为智能需求分析师Alex，为这个新会话生成欢迎消息。"""
            
            # 调用Alex生成欢迎消息
            alex_welcome_response = self._call_ai_model(system_prompt, user_prompt)
            
            # 为欢迎场景构建结构化返回结果
            result = {
                'ai_response': alex_welcome_response,
                'identified_requirements': [],
                'information_gaps': [
                    '需要了解项目基本目标',
                    '需要了解目标用户群体', 
                    '需要了解功能需求范围',
                    '需要了解技术约束条件'
                ],
                'clarification_questions': [
                    '请简要描述这个项目想要解决什么核心问题？',
                    '项目的主要目标用户是谁？',
                    '您希望实现哪些主要功能？'
                ],
                'consensus_content': {
                    'project_name': project_name,
                    'analysis_method': 'Alex智能需求分析师',
                    'session_status': '已开始',
                    'understanding_level': 'initial'
                },
                'analysis_summary': 'Alex已准备好开始需求分析',
                'alex_persona': True
            }
            
            logger.info(f"Alex为项目 {project_name} 生成了欢迎消息")
            return result
            
        except Exception as e:
            logger.error(f"Alex生成欢迎消息失败: {str(e)}")
            # 返回Alex风格的默认欢迎消息
            return {
                'ai_response': f'你好！我是智能需求分析师Alex，专门帮助澄清和完善项目需求。很高兴为项目"{project_name}"提供需求分析服务。\n\n我会运用多维度分析方法，通过深入的专业提问来帮助你将模糊的想法逐步转化为清晰、可执行的需求规格。\n\n请告诉我，这个项目的核心目标是什么？你希望解决什么问题？',
                'identified_requirements': [],
                'information_gaps': [
                    '需要了解项目基本目标',
                    '需要了解目标用户群体',
                    '需要了解功能需求范围'
                ],
                'clarification_questions': [
                    '请简要描述这个项目想要解决什么核心问题？',
                    '项目的主要目标用户是谁？',
                    '您希望实现哪些主要功能？'
                ],
                'consensus_content': {
                    'project_name': project_name,
                    'analysis_method': 'Alex智能需求分析师',
                    'session_status': '已开始（默认模式）'
                },
                'analysis_summary': 'Alex默认欢迎模式（服务异常恢复）',
                'alex_persona': True
            }