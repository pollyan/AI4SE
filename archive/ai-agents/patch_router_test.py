import sys
# A small script to modify `tests/conftest.py` default config factory to use qwen-max directly if env fails
with open("backend/tests/conftest.py", "r") as f:
    text = f.read()

text = text.replace('"model_name": "gpt-4o-mini",', '"model_name": "qwen-max",')
with open("backend/tests/conftest.py", "w") as f:
    f.write(text)
