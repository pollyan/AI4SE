import logging
from dataclasses import dataclass
from typing import List, Any
from langchain_core.messages import SystemMessage
from .schemas import UserIntentInClarify

logger = logging.getLogger(__name__)


@dataclass
class ClarifyContext:
    blocking_questions: List[str]
    optional_questions: List[str]


INTENT_PARSING_PROMPT = """
你是一个意图分析专家。请分析用户在需求澄清阶段的回复意图。

## 当前上下文
- 待解决的阻塞性问题: {blocking_questions}
- 待解决的建议澄清问题: {optional_questions}

## 用户回复
"{user_message}"

## 意图类型
- provide_material: 提供需求材料
- answer_question: 回答具体问题
- confirm_proceed: 确认继续 (如"好的", "继续")
- need_more_clarify: 需要更多澄清
- accept_risk: 接受风险继续 (如"先这样吧")
- change_scope: 调整范围
- off_topic: 离题

使用语义理解，不要依赖关键字匹配。
"""


def parse_user_intent(
    user_message: str,
    context: ClarifyContext,
    llm: Any
) -> UserIntentInClarify:
    prompt = INTENT_PARSING_PROMPT.format(
        blocking_questions=context.blocking_questions,
        optional_questions=context.optional_questions,
        user_message=user_message
    )
    import json
    from backend.agents.shared.utils import extract_json_from_markdown
    
    prompt += "\n\n[CRITICAL INSTRUCTION]\n"
    prompt += "你必须并且只能返回一个完全符合 `UserIntentInClarify` Schema 描述的 JSON 对象字符串。不要添加 Markdown 代码块标记（如 ```json），绝不能输出无关的解释或回复。\n"
    prompt += UserIntentInClarify.schema_json()
    
    try:
        raw_msg = llm.model.invoke([SystemMessage(content=prompt)])
        text_content = raw_msg.content.strip()

        data = extract_json_from_markdown(text_content)
        result = UserIntentInClarify(**data)
        
        logger.info(f"意图解析: intent={result.intent}, confidence={result.confidence}")
        return result
        
    except Exception as e:
        logger.error(f"意图解析失败: {e}", exc_info=True)
        return UserIntentInClarify(intent="need_more_clarify", confidence=0.5)
