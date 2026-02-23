"""
轻量 LLM-as-Judge

使用一个独立的 LLM 调用评估 Agent 输出的语义正确性。
弥补 Pydantic 结构验证无法覆盖的"结构对了但内容离谱"的场景。

复用 .env 中的阿里云 DashScope API 配置（OPENAI_API_KEY + OPENAI_BASE_URL）。
"""

import os
import logging
from typing import cast
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)


class JudgeResult(BaseModel):
    """Judge 评估结果"""
    passed: bool = Field(description="是否通过")
    reason: str = Field(description="简要评估理由（中文）")

    def __repr__(self) -> str:
        return f"JudgeResult(passed={self.passed}, reason='{self.reason}')"

    def __str__(self) -> str:
        return self.__repr__()


JUDGE_SYSTEM = (
    "你是一个严格的测试评估专家，负责评估 AI 智能体的输出质量。\n"
    "请根据用户输入、预期行为和实际输出来判断测试是否通过。\n"
    "你必须只返回一个 JSON 对象，包含 passed (bool) 和 reason (string) 两个字段。\n"
    "禁止输出 Markdown 代码块、引言或任何额外文字。"
)

JUDGE_USER = """请判断以下 AI 智能体的输出是否满足预期。

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
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("SMOKE_TEST_JUDGE_MODEL", "deepseek-v3.2")

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,  # type: ignore[arg-type]
        temperature=0
    )
    response = llm.invoke([
        SystemMessage(content=JUDGE_SYSTEM),
        HumanMessage(content=JUDGE_USER.format(
            user_input=user_input,
            expected_behavior=expected_behavior,
            actual_output=actual_output
        ))
    ])
    
    import json
    try:
        content = str(response.content).strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        data = json.loads(content)
        result = JudgeResult(**data)
        logger.info(f"Judge 结果: passed={result.passed}, reason={result.reason}")
        return result
    except Exception as e:
        logger.error(f"解析 Judge JSON 失败: {e}\nRaw={response.content}")
        return JudgeResult(passed=False, reason=f"Judge failed to parse JSON: {e}")

ARTIFACT_JUDGE_SYSTEM = (
    "你是一个严格的测试评估专家，负责评估 AI 智能体生成的结构化产出物是否符合预期。\n"
    "你会收到一段 JSON 格式的产出物切片和预期行为描述。\n"
    "请判断该 JSON 切片是否在语义上满足预期行为。\n"
    "你必须只返回一个 JSON 对象，包含 passed (bool) 和 reason (string) 两个字段。\n"
    "禁止输出 Markdown 代码块、引言或任何额外文字。"
)

ARTIFACT_JUDGE_USER = """请判断以下产出物 JSON 切片是否满足预期。

## 对话背景
{conversation_context}

## 预期行为
{expected_behavior}

## 产出物 JSON 切片
```json
{artifact_slice}
```

## 评估标准
1. JSON 切片中的字段值必须与对话背景中的信息语义一致。
2. 如果预期行为中要求某些字段状态变化（如 status 从 pending 变为 confirmed），必须验证是否已变化。
3. 不要求文字完全匹配，但内容的业务含义必须正确。
4. 如果 JSON 切片为空或缺少关键字段，判定为不通过。"""


def judge_artifact_slice(
    conversation_context: str,
    expected_behavior: str,
    artifact_slice: str,
) -> JudgeResult:
    """
    用 LLM 评估产出物 JSON 切片的语义正确性。

    Args:
        conversation_context: 对话背景摘要（如"用户确认了密码不需要特殊字符"）。
        expected_behavior: 用自然语言描述的预期行为。
        artifact_slice: 产出物 JSON 切片（字符串）。

    Returns:
        JudgeResult: 包含 passed（bool）和 reason（str）。
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.getenv("SMOKE_TEST_JUDGE_MODEL", "deepseek-v3.2")

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,  # type: ignore[arg-type]
        temperature=0
    )
    response = llm.invoke([
        SystemMessage(content=ARTIFACT_JUDGE_SYSTEM),
        HumanMessage(content=ARTIFACT_JUDGE_USER.format(
            conversation_context=conversation_context,
            expected_behavior=expected_behavior,
            artifact_slice=artifact_slice
        ))
    ])
    
    import json as json_module
    try:
        content = str(response.content).strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        data = json_module.loads(content)
        result = JudgeResult(**data)
        logger.info(
            f"Artifact Judge 结果: passed={result.passed}, "
            f"reason={result.reason}"
        )
        return result
    except Exception as e:
        logger.error(
            f"解析 Artifact Judge JSON 失败: {e}\n"
            f"Raw={response.content}"
        )
        return JudgeResult(
            passed=False,
            reason=f"Artifact Judge failed to parse JSON: {e}"
        )
