import json
import os
import re

import pytest

from agent_contracts import validate_agent_turn
from agent_runtime import build_pydantic_agent_runtime
from test_artifact_data_renderers import VALID_CLARIFY_ARTIFACT_DATA


pytestmark = pytest.mark.slow

REQUIRED_ENV_VARS = (
    "NEW_AGENTS_SMOKE_API_KEY",
    "NEW_AGENTS_SMOKE_BASE_URL",
    "NEW_AGENTS_SMOKE_MODEL",
)

SMOKE_SYSTEM_PROMPT = """
你是 Lisa 测试专家。请严格输出一个 JSON object，用于验证 TEST_DESIGN/CLARIFY 的 artifact_data 结构化产物链路。
本次只验证 TEST_DESIGN/CLARIFY 阶段，不要请求进入下一阶段。
chat 只返回给用户看的简短说明，禁止包含 Markdown 标题、表格、代码块、Mermaid 或完整文档正文。
必须输出 artifact_data，不要输出完整 Markdown、Mermaid、表格或 ai4se-visual；后端会负责确定性渲染右侧 artifact。
artifact_data 必须包含 document_info、requirement_facts、system_boundaries、business_rules、flow_links、clarification_questions、quality_requirements、downstream_inputs 和 stage_gate。
stage_action 必须为 null，warnings 可以为空数组。
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


def _run_smoke_turn(runtime):
    outputs = list(
        runtime.stream_turn(
            SMOKE_USER_PROMPT,
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )
    assert outputs
    output = outputs[-1]
    return validate_agent_turn(
        output,
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    )


def test_smoke_system_prompt_requests_artifact_data_not_markdown_protocol():
    assert "artifact_data" in SMOKE_SYSTEM_PROMPT
    assert "artifact_update" not in SMOKE_SYSTEM_PROMPT
    assert "不要输出完整 Markdown" in SMOKE_SYSTEM_PROMPT


def test_deepseek_smoke_gate_uses_artifact_data_renderer_and_json_object_mode(
    monkeypatch,
):
    emitted_calls = []

    def fake_stream_chat_completion_content(**kwargs):
        emitted_calls.append(kwargs)
        yield json.dumps(
            {
                "chat": "已完成登录需求澄清，右侧产物由结构化数据渲染。",
                "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
                "stage_action": None,
                "warnings": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )
    runtime = build_pydantic_agent_runtime(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model_name="deepseek-v4-flash",
        system_prompt=SMOKE_SYSTEM_PROMPT,
    )

    output = _run_smoke_turn(runtime)

    assert emitted_calls[0]["response_format"] == {"type": "json_object"}
    assert emitted_calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    system_content = emitted_calls[0]["messages"][0]["content"]
    assert "artifact_data" in system_content
    assert "artifact_update" not in system_content
    assert output.artifact_update.markdown is not None
    assert "# 需求分析文档" in output.artifact_update.markdown
    assert "flowchart" in output.artifact_update.markdown
    assert not _contains_artifact_markdown(output.chat)


def test_real_pydantic_ai_runtime_returns_valid_clarify_artifact():
    env = _load_required_env()
    runtime = build_pydantic_agent_runtime(
        api_key=env["NEW_AGENTS_SMOKE_API_KEY"],
        base_url=env["NEW_AGENTS_SMOKE_BASE_URL"],
        model_name=env["NEW_AGENTS_SMOKE_MODEL"],
        system_prompt=SMOKE_SYSTEM_PROMPT,
    )

    output = _run_smoke_turn(runtime)

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
