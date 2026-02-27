from langchain_openai import ChatOpenAI
from backend.agents.lisa.schemas import UpdateStructuredArtifact
import pprint
import asyncio
import os

async def test():
    llm = ChatOpenAI(model="qwen-plus", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=os.getenv("DASHSCOPE_API_KEY", "dummy"))
    bound = llm.bind_tools([UpdateStructuredArtifact], tool_choice="required")
    kwargs = bound.kwargs
    print("\nBOUND KWARGS >>> ")
    pprint.pprint(kwargs)

if __name__ == "__main__":
    asyncio.run(test())

if __name__ == "__main__":
    asyncio.run(test())
