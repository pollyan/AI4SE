from backend.agents.lisa.tools import ask_confirmation


def test_ask_confirmation_tool():
    """Test the ask_confirmation tool execution"""
    result = ask_confirmation.invoke({"message": "Do you confirm?"})
    assert result == "Waiting for user confirmation..."
    assert "ask_confirmation" == ask_confirmation.name
