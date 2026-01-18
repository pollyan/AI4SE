import pytest
from langchain_core.tools import tool
from backend.agents.lisa.tools import ask_confirmation

def test_ask_confirmation_tool_schema():
    """Verify tool schema matches frontend expectation"""
    schema = ask_confirmation.args_schema.schema()
    assert "message" in schema["properties"]
    assert schema["properties"]["message"]["type"] == "string"

def test_ask_confirmation_execution():
    """
    Test execution (simulated).
    In real flow, this tool creates an interrupt.
    Here we test the function itself returns a structured result or raises interrupt?
    
    Actually, for client-side tools, the backend 'execute' function is often a placeholder 
    or returns a special value indicating "Waiting for client".
    """
    # Verify it's callable
    result = ask_confirmation.invoke({"message": "Proceed?"})
    # What should it return?
    # Ideally, it should return something that LangGraph persists.
    # But usually the client INTERCEPTS the call.
    # The backend sees the RESULT when client sends it back.
    # So the tool implementation on backend might be minimal.
    assert result is not None
