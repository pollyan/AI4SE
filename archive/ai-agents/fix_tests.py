import glob, os

def replace_in_file(filepath, replacements):
    with open(filepath, 'r') as f:
        content = f.read()
    
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
            
    if modified:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Updated {filepath}")

# Find all test files
test_files = glob.glob('backend/tests/**/*.py', recursive=True)

replacements = [
    ("artifact_node(cast(LisaState, mock_state), original_llm)", "artifact_node(cast(LisaState, mock_state), None, original_llm)"),
    ("artifact_node(cast(LisaState, state_after_init), original_llm)", "artifact_node(cast(LisaState, state_after_init), None, original_llm)"),
    ("artifact_node(cast(LisaState, state_after_update_1), original_llm)", "artifact_node(cast(LisaState, state_after_update_1), None, original_llm)"),
    ("artifact_node(state, mock_llm)", "artifact_node(state, None, mock_llm)"),
    ("artifact_node(cast(LisaState, state_after_1), mock_llm)", "artifact_node(cast(LisaState, state_after_1), None, mock_llm)"),
    ("reasoning_node(cast(LisaState, mock_state), mock_llm)", "reasoning_node(cast(LisaState, mock_state), None, mock_llm)"),
    ("reasoning_node(cast(LisaState, state), mock_llm)", "reasoning_node(cast(LisaState, state), None, mock_llm)"),
]

for filepath in test_files:
    replace_in_file(filepath, replacements)
