
import json
import re
from backend.agents.shared.progress_utils import parse_plan

plan_json = json.dumps([
    {"id": "clarify", "name": "需求澄清", "status": "completed"},
    {"id": "strategy", "name": "策略制定", "status": "active"}
], ensure_ascii=False)

response_with_xml = f'<plan>{plan_json}</plan>\n\n接下来我们进入策略制定阶段。'

print(f"Input: {response_with_xml}")
parsed = parse_plan(response_with_xml)
print(f"Parsed: {parsed}")

if parsed:
    print("Success!")
else:
    print("Failed!")
