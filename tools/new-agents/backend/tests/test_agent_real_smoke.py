import os
import re

import pytest

from agent_runtime import build_pydantic_agent_runtime


pytestmark = pytest.mark.slow

REQUIRED_ENV_VARS = (
    "NEW_AGENTS_SMOKE_API_KEY",
    "NEW_AGENTS_SMOKE_BASE_URL",
    "NEW_AGENTS_SMOKE_MODEL",
)

SMOKE_SYSTEM_PROMPT = """
你是 Lisa 测试专家。请严格输出符合 AgentTurnOutput 的结构化结果。
本次只验证 TEST_DESIGN/CLARIFY 阶段，不要请求进入下一阶段。
chat 只返回给用户看的简短说明，禁止包含 Markdown 标题、表格、代码块或完整文档正文。
artifact_update 必须是 replace，markdown 必须包含需求分析文档的全部关键章节。
markdown 中必须逐字包含以下标题，不能改写、不能增加前缀序号样式、不能使用三级标题替代:
# 需求分析文档
## 文档信息
## 1. 需求事实清单
## 2. 被测系统与边界
## 3. 业务规则与数据状态
## 4. 核心链路与异常链路
## 5. 待澄清问题
## 6. 隐式质量需求
## 7. 后续测试设计输入
## 8. 阶段门禁
markdown 必须包含 fenced Mermaid flowchart。
""".strip()

SMOKE_USER_PROMPT = """
请为一个登录功能生成需求澄清阶段的需求分析文档。
功能包括账号密码登录、短信验证码登录、第三方登录、失败重试、账号锁定和安全审计。
""".strip()


def _load_required_env() -> dict[str, str]:
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        pytest.skip(
            "real PydanticAI smoke requires env vars: "
            + ", ".join(missing)
        )

    return {name: os.environ[name] for name in REQUIRED_ENV_VARS}


def _contains_artifact_markdown(text: str) -> bool:
    return any(
        [
            bool(re.search(r"^#{1,6}\s+\S", text, re.MULTILINE)),
            bool(re.search(r"^\|?\s*-{3,}\s*\|", text, re.MULTILINE)),
            "```" in text,
            "sequenceDiagram" in text,
            "flowchart " in text,
            "graph " in text,
        ]
    )


def test_real_pydantic_ai_runtime_returns_valid_clarify_artifact():
    env = _load_required_env()
    runtime = build_pydantic_agent_runtime(
        api_key=env["NEW_AGENTS_SMOKE_API_KEY"],
        base_url=env["NEW_AGENTS_SMOKE_BASE_URL"],
        model_name=env["NEW_AGENTS_SMOKE_MODEL"],
        system_prompt=SMOKE_SYSTEM_PROMPT,
    )

    output = runtime.run_turn(
        SMOKE_USER_PROMPT,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )

    assert output.chat.strip()
    assert not _contains_artifact_markdown(output.chat)
    assert output.artifact_update.type == "replace"
    assert output.artifact_update.markdown is not None
    assert "# 需求分析文档" in output.artifact_update.markdown
    assert "## 文档信息" in output.artifact_update.markdown
    assert "## 1. 需求事实清单" in output.artifact_update.markdown
    assert "## 2. 被测系统与边界" in output.artifact_update.markdown
    assert "## 3. 业务规则与数据状态" in output.artifact_update.markdown
    assert "## 4. 核心链路与异常链路" in output.artifact_update.markdown
    assert "## 5. 待澄清问题" in output.artifact_update.markdown
    assert "## 6. 隐式质量需求" in output.artifact_update.markdown
    assert "## 7. 后续测试设计输入" in output.artifact_update.markdown
    assert "## 8. 阶段门禁" in output.artifact_update.markdown
    assert "flowchart" in output.artifact_update.markdown
    assert output.stage_action is None
