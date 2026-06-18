MERMAID_REPAIR_SYSTEM_PROMPT = """你是 Mermaid 图表修正专家。用户给你一段有语法错误的 Mermaid 代码和验证器抛出的错误信息。
请分析错误并修复语法。
必须遵循以下原则：
1. 仅输出修正后的完整 Mermaid 代码，不要附带任何解释文字。
2. 不要包含 ```mermaid 围栏标记，仅输出纯文本代码。
3. 确保特殊字符（如 <>()[]{}"）在节点文本中被合法转义或用双引号包裹。"""


def build_mermaid_repair_user_prompt(
    *,
    first_line: str,
    error_message: str,
    broken_code: str,
    block_index: int | None,
) -> str:
    position = block_index + 1 if block_index is not None else "未知"
    return f"""【图表预期类型上下文】：{first_line}
【当前位置】：第 {position} 个图表
【错误信息】：
{error_message}

【错误代码】：
{broken_code}"""
