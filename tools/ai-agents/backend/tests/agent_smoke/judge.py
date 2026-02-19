"""
轻量 LLM-as-Judge

使用一个独立的 LLM 调用评估 Agent 输出的语义正确性。
弥补 Pydantic 结构验证无法覆盖的"结构对了但内容离谱"的场景。

复用 .env 中的阿里云 DashScope API 配置（OPENAI_API_KEY + OPENAI_BASE_URL）。
"""

import os
import logging
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class JudgeResult(BaseModel):
    """Judge 评估结果"""
    passed: bool = Field(description="是否通过")
    reason: str = Field(description="简要评估理由（中文）")


JUDGE_PROMPT = """你是一个严格的测试评估专家。请判断 AI 智能体的输出是否满足预期。

## 用户输入
{user_input}

## 预期行为
{expected_behavior}

## 实际输出
{actual_output}

## 评估标准
评估实际输出是否在语义上满足预期行为。不要求文字完全匹配，但内容必须与用户输入的主题相关。
如果输出主题完全偏离用户需求，或者内容为空/无意义，则判定为不通过。"""


def judge_output(
    user_input: str,
    expected_behavior: str,
    actual_output: str,
) -> JudgeResult:
    """
    用 LLM 评估 agent 输出的语义正确性。

    复用 .env 中配置的阿里云 DashScope API，不引入新的 Key。
    使用 temperature=0 确保判断稳定。

    Args:
        user_input: 用户发送给 Lisa 的原始消息。
        expected_behavior: 用自然语言描述的预期行为（语义层面，不是精确匹配）。
        actual_output: Agent 实际回复的文本。

    Returns:
        JudgeResult: 包含 passed（bool）和 reason（str）。
    """
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    # 可以通过环境变量选择更轻量的 Judge 模型以节省成本
    model = os.getenv("SMOKE_TEST_JUDGE_MODEL", "qwen-plus")

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=0
    )
    structured_llm = llm.with_structured_output(JudgeResult)

    result = structured_llm.invoke(
        JUDGE_PROMPT.format(
            user_input=user_input,
            expected_behavior=expected_behavior,
            actual_output=actual_output
        )
    )
    logger.info(f"Judge 结果: passed={result.passed}, reason={result.reason}")
    return result
