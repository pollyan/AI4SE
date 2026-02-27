import pytest
from backend.agents.shared.utils import extract_json_from_markdown
import json

def test_clean_json():
    text = '{"key": "value", "list": [1, 2, 3]}'
    result = extract_json_from_markdown(text)
    assert result == {"key": "value", "list": [1, 2, 3]}

def test_markdown_json():
    text = '''```json
{
    "nested": {"id": 1}
}
```'''
    result = extract_json_from_markdown(text)
    assert result == {"nested": {"id": 1}}

def test_markdown_no_lang():
    text = '''```
{
    "pure": "json"
}
```'''
    result = extract_json_from_markdown(text)
    assert result == {"pure": "json"}

def test_dirty_json():
    text = '''好的，这是你的提取结果：
```json
{
    "key": "success"
}
```
希望对你有帮助！'''
    result = extract_json_from_markdown(text)
    assert result == {"key": "success"}

def test_chatty_json_no_markdown():
    text = '''Sure, here is the JSON you requested:
{
    "some": "data",
    "number": 42
}
Let me know if you need anything else.'''
    result = extract_json_from_markdown(text)
    assert result == {"some": "data", "number": 42}

def test_invalid_json_throws_error():
    # Only curly braces but invalid structure
    text = "```json\n{ key: no quotes }\n```"
    with pytest.raises(json.JSONDecodeError):
        extract_json_from_markdown(text)

def test_no_braces_throws_error():
    text = "Just some text without braces."
    with pytest.raises(ValueError, match="No JSON object structure"):
        extract_json_from_markdown(text)
