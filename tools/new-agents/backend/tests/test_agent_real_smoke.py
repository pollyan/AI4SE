import os
import re

import pytest

from agent_runtime import PydanticAgentRuntime, RawStreamingConfig

pytestmark = pytest.mark.slow

GENERIC_ENV_VARS = (
    "NEW_AGENTS_SMOKE_API_KEY",
    "NEW_AGENTS_SMOKE_BASE_URL",
    "NEW_AGENTS_SMOKE_MODEL",
)
DEEPSEEK_ENV_VARS = (
    "DEEPSEEK_V4_SMOKE_API_KEY",
    "DEEPSEEK_V4_SMOKE_BASE_URL",
    "DEEPSEEK_V4_SMOKE_MODEL",
)

SMOKE_SYSTEM_PROMPT = """
你是 Lisa 测试专家。请严格输出符合当前阶段 artifact_data schema 的 JSON object。
本次只验证 TEST_DESIGN/CLARIFY 阶段，不要请求进入下一阶段。
chat 只返回给用户看的简短说明，禁止包含 Markdown 标题、表格、代码块或完整文档正文。
artifact_data 必须包含登录功能澄清所需的业务事实、范围边界、业务规则、核心/异常链路、待澄清问题、隐式质量需求、后续测试设计输入和阶段门禁。
不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 fenced block；后端会根据 artifact_data 确定性渲染右侧产出物。
""".strip()

SMOKE_USER_PROMPT = """
请为一个登录功能生成需求澄清阶段的需求分析文档。
功能包括账号密码登录、短信验证码登录、第三方登录、失败重试、账号锁定和安全审计。
""".strip()


def _load_deepseek_smoke_env() -> dict[str, str]:
    values = {
        "api_key": (
            os.environ.get("DEEPSEEK_V4_SMOKE_API_KEY")
            or os.environ.get("NEW_AGENTS_SMOKE_API_KEY")
        ),
        "base_url": (
            os.environ.get("DEEPSEEK_V4_SMOKE_BASE_URL")
            or os.environ.get("NEW_AGENTS_SMOKE_BASE_URL")
        ),
        "model": (
            os.environ.get("DEEPSEEK_V4_SMOKE_MODEL")
            or os.environ.get("NEW_AGENTS_SMOKE_MODEL")
        ),
    }
    missing = [key for key, value in values.items() if not value]
    if missing:
        pytest.skip(
            "real DeepSeek V4 smoke requires env vars: "
            "DEEPSEEK_V4_SMOKE_API_KEY, DEEPSEEK_V4_SMOKE_BASE_URL, "
            "DEEPSEEK_V4_SMOKE_MODEL "
            "(or NEW_AGENTS_SMOKE_API_KEY, NEW_AGENTS_SMOKE_BASE_URL, "
            "NEW_AGENTS_SMOKE_MODEL)"
        )
    return {key: value for key, value in values.items() if value is not None}


def test_deepseek_smoke_env_prefers_deepseek_specific_values(monkeypatch):
    monkeypatch.setenv("NEW_AGENTS_SMOKE_API_KEY", "generic-key")
    monkeypatch.setenv("NEW_AGENTS_SMOKE_BASE_URL", "https://generic.example/v1")
    monkeypatch.setenv("NEW_AGENTS_SMOKE_MODEL", "generic-model")
    monkeypatch.setenv("DEEPSEEK_V4_SMOKE_API_KEY", "deepseek-key")
    monkeypatch.setenv("DEEPSEEK_V4_SMOKE_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setenv("DEEPSEEK_V4_SMOKE_MODEL", "deepseek-v4-flash")

    assert _load_deepseek_smoke_env() == {
        "api_key": "deepseek-key",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
    }


def test_deepseek_smoke_env_skips_when_required_values_are_missing(monkeypatch):
    for name in GENERIC_ENV_VARS + DEEPSEEK_ENV_VARS:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(pytest.skip.Exception) as exc_info:
        _load_deepseek_smoke_env()

    assert "real DeepSeek V4 smoke requires env vars" in str(exc_info.value)
    assert "DEEPSEEK_V4_SMOKE_API_KEY" in str(exc_info.value)


def test_deepseek_smoke_prompt_requests_artifact_data_not_markdown():
    assert "artifact_data" in SMOKE_SYSTEM_PROMPT
    assert "不要输出完整 Markdown" in SMOKE_SYSTEM_PROMPT
    assert "artifact_update 必须是 replace" not in SMOKE_SYSTEM_PROMPT
    assert "artifact_update.markdown" not in SMOKE_SYSTEM_PROMPT


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


def test_real_deepseek_v4_raw_json_runtime_returns_valid_clarify_artifact():
    env = _load_deepseek_smoke_env()
    runtime = PydanticAgentRuntime(
        agent=None,
        raw_streaming_config=RawStreamingConfig(
            api_key=env["api_key"],
            base_url=env["base_url"],
            model_name=env["model"],
            system_prompt=SMOKE_SYSTEM_PROMPT,
        ),
    )

    outputs = list(
        runtime.stream_turn(
            SMOKE_USER_PROMPT,
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )
    output = outputs[-1]

    assert output.chat.strip()
    assert not _contains_artifact_markdown(output.chat)
    assert output.artifact_data is not None
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
