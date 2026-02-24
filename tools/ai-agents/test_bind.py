import asyncio
from backend.agents.lisa.schemas import UpdateStructuredArtifact
from backend.agents.shared.llm_factory import get_llm

async def main():
    llm = get_llm("qwen-plus")  # or whatever DashScope uses
    llm_with_tools = llm.bind_tools([UpdateStructuredArtifact], tool_choice="required")
    # let's trigger it with a dummy prompt
    resp = await llm_with_tools.ainvoke("Please update the artifact right now.")
    print(resp.tool_calls)

if __name__ == "__main__":
    asyncio.run(main())
