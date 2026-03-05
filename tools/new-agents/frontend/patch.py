import re

with open('/Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/src/core/workflows.ts', 'r') as f:
    text = f.read()

# Replace STRATEGY
strategy_pattern = re.compile(r"id: 'STRATEGY',\n\s+name: '策略制定',\n\s+description: `基于需求.*?预估总用例 \[M\] 条`", re.DOTALL)
text = strategy_pattern.sub("id: 'STRATEGY',\n                name: '策略制定',\n                description: STRATEGY_PROMPT", text)

# Replace REPORT
report_pattern = re.compile(r"id: 'REPORT',\n\s+name: '评审报告',\n\s+description: `整合深度评审阶段.*?评审结论已同步至相关干系人`", re.DOTALL)
text = report_pattern.sub("id: 'REPORT',\n                name: '评审报告',\n                description: REPORT_PROMPT", text)

with open('/Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/src/core/workflows.ts', 'w') as f:
    f.write(text)
