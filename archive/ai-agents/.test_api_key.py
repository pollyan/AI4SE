import os
import asyncio
from backend.app import create_app
from backend.agents.service import LangchainAssistantService

async def main():
    app = create_app()
    with app.app_context():
        # Override env vars
        os.environ['OPENAI_API_KEY'] = "sk-0b7ca376cfce4e2f82986eb5fea5124d"
        os.environ['OPENAI_BASE_URL'] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        os.environ['MODEL_NAME'] = "deepseek-v3.2"
        os.environ['SMOKE_TEST_MODEL'] = "deepseek-v3.2"
        os.environ['SMOKE_TEST_JUDGE_MODEL'] = "deepseek-v3.2"
        
        from backend.models import db, RequirementsAIConfig
        db.create_all()
        c = RequirementsAIConfig(
            config_name="test_config",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key="sk-0b7ca376cfce4e2f82986eb5fea5124d",
            model_name="deepseek-v3.2",
            is_default=True,
            is_active=True
        )
        db.session.add(c)
        db.session.commit()
        
        s = LangchainAssistantService('lisa')
        await s.initialize()
        
asyncio.run(main())
