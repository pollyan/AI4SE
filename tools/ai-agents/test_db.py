from pprint import pprint
import os
from backend.app import create_app
from backend.models import db, RequirementsAIConfig
import asyncio
app = create_app()
with app.app_context():
    db.create_all()
    c = RequirementsAIConfig(
        config_name="test_config",
        base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        api_key=os.getenv("OPENAI_API_KEY", "sk-0b7ca376cfce4e2f82986eb5fea5124d"),
        model_name=os.getenv("SMOKE_TEST_MODEL", "qwen-max"),
        is_default=True,
        is_active=True
    )
    db.session.add(c)
    db.session.commit()
    from backend.agents.service import LangchainAssistantService
    s = LangchainAssistantService('lisa')
    asyncio.run(s.initialize())
    print("Bound LLM config:", s.agent.bound)
