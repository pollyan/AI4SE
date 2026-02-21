"""
Agent Smoke Test Fixtures

提供真实 LLM 配置和 LangSmith 可观测性。
API Key 必须存在，否则测试直接 FAIL（不是 skip）。
"""

import os
import pytest
from dotenv import load_dotenv

# 加载项目根目录的 .env
# （向上回溯 5 层: agent_smoke -> tests -> backend -> ai-agents -> tools -> 项目根）
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../../../")
)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


@pytest.fixture(autouse=True)
def enable_langsmith_tracing():
    """
    Smoke test 运行时自动开启 LangSmith tracing（如果配置了 key）。

    使用独立的 project 名称 "ai4se-smoke-test"，不与开发/生产 trace 混淆。
    测试结束后恢复原始环境变量。
    """
    langsmith_key = os.getenv("LANGCHAIN_API_KEY")
    old_project = os.environ.get("LANGCHAIN_PROJECT")
    old_tracing = os.environ.get("LANGCHAIN_TRACING_V2")

    if langsmith_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "ai4se-smoke-test"

    yield

    # 恢复原始值
    if old_project is not None:
        os.environ["LANGCHAIN_PROJECT"] = old_project
    elif "LANGCHAIN_PROJECT" in os.environ:
        del os.environ["LANGCHAIN_PROJECT"]

    if old_tracing is not None:
        os.environ["LANGCHAIN_TRACING_V2"] = old_tracing
    elif "LANGCHAIN_TRACING_V2" in os.environ:
        del os.environ["LANGCHAIN_TRACING_V2"]


@pytest.fixture
def real_ai_config(create_ai_config):
    """
    使用 .env 中的真实 LLM API Key 在数据库中创建 AI 配置。

    必须配置 OPENAI_API_KEY，否则测试 FAIL（不是 skip）。
    结合 create_ai_config fixture 写入 SQLite in-memory 数据库。
    """
    api_key = os.getenv("OPENAI_API_KEY")
    assert api_key, (
        "OPENAI_API_KEY 未设置！Agent Smoke Test 需要真实的 LLM API Key。\n"
        "请确保项目根目录的 .env 中配置了 OPENAI_API_KEY。\n"
        f"（当前搜索路径: {PROJECT_ROOT}/.env）"
    )

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    # 默认用 qwen-plus，可通过环境变量覆盖为更轻量的模型
    model_name = os.getenv("SMOKE_TEST_MODEL", "qwen-plus")

    return create_ai_config(
        config_name="smoke_test_config",
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        is_default=True,
        is_active=True
    )


@pytest.fixture
def lisa_session(client, real_ai_config):
    """
    创建一个 Lisa 会话，返回 session_id。

    依赖 real_ai_config 确保数据库中有有效的 AI 配置，
    才能让 LangchainAssistantService.initialize() 找到配置。
    """
    response = client.post(
        "/ai-agents/api/requirements/sessions",
        json={"assistant_type": "lisa", "project_name": "冒烟测试项目"},
        content_type="application/json"
    )
    data = response.get_json()
    assert response.status_code == 200, (
        f"创建 Lisa 会话失败: HTTP {response.status_code}\n响应: {data}"
    )
    return data["data"]["id"]

@pytest.fixture
def lisa_graph(real_ai_config):
    """
    暴露 Lisa 的 LangGraph 实例，用于测试中读取 State 快照。
    
    使用方式: state = lisa_graph.get_state({"configurable": {"thread_id": session_id}})
    """
    import asyncio
    from backend.agents.service import LangchainAssistantService
    
    service = LangchainAssistantService("lisa")
    asyncio.get_event_loop().run_until_complete(service.initialize())
    return service.agent

@pytest.fixture
def lisa_graph(real_ai_config):
    """
    暴露 Lisa 的 LangGraph 实例，用于测试中读取 State 快照。
    
    使用方式: state = lisa_graph.get_state({"configurable": {"thread_id": session_id}})
    """
    import asyncio
    from backend.agents.service import LangchainAssistantService
    
    service = LangchainAssistantService("lisa")
    asyncio.get_event_loop().run_until_complete(service.initialize())
    return service.agent
