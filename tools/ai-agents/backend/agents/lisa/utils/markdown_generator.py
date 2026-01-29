from typing import Dict, Any, List, Union

def convert_list_to_markdown(items: List[Any]) -> str:
    return "\n".join([f"- {item}" for item in items]) if items else "(无)"

def convert_requirement_doc(content: Dict[str, Any]) -> str:
    """
    将 RequirementDoc 结构转换为符合 ARTIFACT_CLARIFY_REQUIREMENTS 模板的 Markdown
    兼容 strict schema (objects) 和 simplified schema (strings)
    """
    md = ["# 需求分析文档\n"]
    
    # 1. 需求全景图 (Scope)
    md.append("## 1. 需求全景图")
    if "scope" in content:
        scope = content["scope"]
        md.append("> 核心需求与范围：")
        if isinstance(scope, list):
            md.append(convert_list_to_markdown(scope))
        elif isinstance(scope, str):
            md.append(scope)
    md.append("")

    # 2. 功能详细规格 (Rules / Scope Detail)
    md.append("## 2. 功能详细规格")
    if "rules" in content:
        rules = content["rules"]
        if isinstance(rules, list) and rules:
            if isinstance(rules[0], dict):
                # Schema: RuleItem(id, desc, source)
                md.append("| ID | 规则描述 | 来源 |")
                md.append("|---|---|---|")
                for r in rules:
                    rid = r.get('id', '-')
                    desc = r.get('desc', '')
                    source = r.get('source', '')
                    md.append(f"| {rid} | {desc} | {source} |")
            else:
                # Fallback: list of strings
                md.append(convert_list_to_markdown(rules))
    md.append("")

    # 3. 业务流程图
    md.append("## 3. 业务流程图")
    if content.get("flow_mermaid"):
        md.append("```mermaid")
        md.append(content["flow_mermaid"])
        md.append("```")
    md.append("")

    # 4. 非功能需求 (NFR)
    md.append("## 4. 非功能需求 (NFR)")
    nfr = content.get("nfr_markdown")
    if nfr:
        if isinstance(nfr, str):
            md.append(nfr)
        elif isinstance(nfr, dict):
            for k, v in nfr.items():
                md.append(f"- **{k}**: {v}")
    md.append("")

    # 5 & 6. 待澄清问题 & 已确认信息 (Assumptions)
    assumptions = content.get("assumptions", [])
    pending = []
    confirmed = []
    
    if isinstance(assumptions, list) and assumptions:
        if isinstance(assumptions[0], dict):
            # Schema: AssumptionItem(id, question, status, note)
            for a in assumptions:
                if a.get('status') == 'confirmed':
                    confirmed.append(a)
                else:
                    pending.append(a)
        else:
            # Fallback: list of strings (treat all as pending)
            pending = [{'question': str(a)} for a in assumptions]

    md.append("## 5. 待澄清问题")
    if pending:
        md.append("| ID | 问题描述 | 状态 |")
        md.append("|---|---|---|")
        for i, p in enumerate(pending):
            qid = p.get('id', f'Q{i+1}')
            qtext = p.get('question', '')
            status = p.get('status', '待确认')
            md.append(f"| {qid} | {qtext} | {status} |")
    else:
        md.append("(无)")
    md.append("")

    md.append("## 6. 已确认信息")
    if confirmed:
        for c in confirmed:
            note = c.get('note', '')
            md.append(f"- ✅ {c.get('question')}：{note}")
    else:
        md.append("(无)")
        
    return "\n".join(md)

def convert_to_markdown(content: Dict[str, Any], artifact_type: str) -> str:
    """通用转换入口"""
    if artifact_type == "requirement":
        return convert_requirement_doc(content)
    
    # Fallback for other types (Design, Cases) - simple dump for now
    # Improvement: Implement specific converters for them later
    md = [f"# {artifact_type.title()} Document\n"]
    for k, v in content.items():
        md.append(f"## {k}")
        md.append(str(v))
        md.append("")
    return "\n".join(md)
