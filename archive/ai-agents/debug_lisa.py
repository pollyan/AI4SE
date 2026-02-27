import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

from backend.agents.lisa.agent import create_lisa_graph
from langgraph.checkpoint.memory import MemorySaver

def main():
    graph = create_lisa_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test_123"}}
    
    # R1
    r1 = "帮我设计用户登录功能的测试用例。POST /api/login 参数：username: 手机号规则；password: 密码规则 (6-20位字符数字)。5次错误锁定"
    print("Sending R1...")
    res = graph.invoke({"messages": [("user", r1)]}, config=config)
    for m in res["messages"]:
        if hasattr(m, "tool_calls") and m.tool_calls:
            print("R1 Tool Calls:", m.tool_calls)
            
    # R2
    r2 = "需求确认：手机号11位。锁定针对用户名连续5次。可以流转。"
    print("Sending R2...")
    res = graph.invoke({"messages": [("user", r2)]}, config=config)
    for m in res["messages"]:
        if hasattr(m, "tool_calls") and m.tool_calls:
            print("R2 Tool Calls:", m.tool_calls)
            
    # R3
    r3 = "需求已全部明确。请流转到策略阶段。"
    print("Sending R3...")
    res = graph.invoke({"messages": [("user", r3)]}, config=config)
    for m in res["messages"]:
        if hasattr(m, "tool_calls") and m.tool_calls:
            print("R3 Tool Calls:", m.tool_calls)
            
    # R4
    r4 = "策略没问题，请开始编写用例。"
    print("Sending R4...")
    res = graph.invoke({"messages": [("user", r4)]}, config=config)
    for m in res["messages"]:
        if hasattr(m, "tool_calls") and m.tool_calls:
            print("R4 Tool Calls:", m.tool_calls)
            print("R4 cases output:", json.dumps(m.tool_calls[0].get("args", {}).get("content", {}), ensure_ascii=False, indent=2))
            
    state = graph.get_state(config)
    print("Structured Artifacts Keys:", state.values.get("structured_artifacts", {}).keys())
    if "test_design_cases" in state.values.get("structured_artifacts", {}):
        print("Cases artifact:", json.dumps(state.values["structured_artifacts"]["test_design_cases"], ensure_ascii=False, indent=2))
        
if __name__ == "__main__":
    main()
