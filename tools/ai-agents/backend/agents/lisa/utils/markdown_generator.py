from typing import Dict, Any, List

from ..artifact_models import RequirementDoc


def convert_list_to_markdown(items: List[Any]) -> str:
    return "\n".join([f"- {item}" for item in items]) if items else "(无)"


def sanitize_mermaid_node(text: str) -> str:
    text = text.replace("(", "（").replace(")", "）")
    text = text.replace("[", "【").replace("]", "】")
    text = text.replace("\n", " ").strip()
    return text


def generate_mindmap(items: List[str], root_name: str = "需求全景") -> str:
    lines = ["mindmap"]
    lines.append(f"  root(({root_name}))")
    for item in items:
        sanitized = sanitize_mermaid_node(str(item))
        lines.append(f"    {sanitized}")
    return "\n".join(lines)


def create_empty_requirement_doc() -> RequirementDoc:
    return RequirementDoc(
        scope=[],
        out_of_scope=[],
        scope_mermaid=None,
        features=[],
        flow_mermaid="",
        rules=[],
        assumptions=[],
        nfr_markdown=None,
    )


def convert_requirement_doc(content: Dict[str, Any]) -> str:
    md = ["# 需求分析文档\n"]

    # Section 1: 测试范围
    md.append("## 1. 测试范围")
    scope = content.get("scope", [])
    out_of_scope = content.get("out_of_scope", [])

    scope_mermaid = content.get("scope_mermaid")
    if scope_mermaid and not isinstance(scope_mermaid, str):
        scope_mermaid = str(scope_mermaid)

    if out_of_scope or scope or scope_mermaid:
        md.append("### 范围内")
        if scope_mermaid:
            md.append("```mermaid")
            md.append(scope_mermaid)
            md.append("```")
        elif scope:
            md.append("```mermaid")
            md.append(generate_mindmap(scope))
            md.append("```")
            md.append(convert_list_to_markdown(scope))
        else:
            md.append("(无)")

        if out_of_scope:
            md.append("\n### 范围外")
            md.append(convert_list_to_markdown(out_of_scope))
    else:
        md.append(
            "> **说明**：在此描述本次测试覆盖的功能模块、接口范围及明确排除在外的（Out-of-Scope）内容。"
        )
    md.append("")

    # Section 2: 功能详细规格
    md.append("## 2. 功能详细规格")
    features = content.get("features", [])
    if features:
        md.append("| ID | 名称 | 描述 | 验收标准 | 优先级 |")
        md.append("|---|---|---|---|---|")
        for f in features:
            fid = f.get("id", "-")
            name = f.get("name", "")
            desc = f.get("desc", "")
            acceptance = f.get("acceptance", [])
            acc_str = "; ".join(acceptance) if acceptance else "-"
            priority = f.get("priority", "P1")
            md.append(f"| {fid} | {name} | {desc} | {acc_str} | {priority} |")
    else:
        md.append(
            "> **说明**：在此详细列出功能点、验收标准（Acceptance Criteria）及优先级（P0-P2）。"
        )
    md.append("")

    # Section 3: 核心业务规则
    md.append("## 3. 核心业务规则")
    rules = content.get("rules", [])
    if rules:
        if isinstance(rules[0], dict):
            md.append("| ID | 规则描述 | 来源 |")
            md.append("|---|---|---|")
            for r in rules:
                rid = r.get("id", "-")
                desc = r.get("desc", "")
                source = r.get("source", "")
                md.append(f"| {rid} | {desc} | {source} |")
        else:
            md.append(convert_list_to_markdown(rules))
    else:
        md.append(
            "> **说明**：在此记录关键业务逻辑、状态机流转规则、权限校验等核心规则。"
        )
    md.append("")

    # Section 4: 业务流程图
    md.append("## 4. 业务流程图")
    if content.get("flow_mermaid"):
        mermaid_code = content["flow_mermaid"]
        if not isinstance(mermaid_code, str):
            mermaid_code = str(mermaid_code)
        md.append("```mermaid")
        md.append(mermaid_code)
        md.append("```")
    else:
        md.append(
            "> **说明**：在此补充核心业务流程图（Mermaid）或时序图，展示数据流转路径。"
        )
    md.append("")

    # Section 5: 非功能需求
    md.append("## 5. 非功能需求")
    nfr = content.get("nfr_markdown")
    if nfr:
        if isinstance(nfr, str):
            md.append(nfr)
        elif isinstance(nfr, dict):
            for k, v in nfr.items():
                md.append(f"- **{k}**: {v}")
    else:
        md.append(
            "> **说明**：在此记录性能（QPS/RT）、安全（鉴权/加密）、兼容性等非功能需求。"
        )
    md.append("")

    # Split assumptions into pending and confirmed
    assumptions = content.get("assumptions", [])
    pending = []
    confirmed = []

    if isinstance(assumptions, list) and assumptions:
        for a in assumptions:
            if isinstance(a, dict):
                if a.get("status") == "confirmed":
                    confirmed.append(a)
                else:
                    pending.append(a)
            else:
                pending.append(
                    {
                        "id": "-",
                        "question": str(a),
                        "priority": "P1",
                        "status": "pending",
                    }
                )

    # Section 6: 待澄清问题
    md.append("## 6. 待澄清问题")
    if pending:
        p0_items = [p for p in pending if p.get("priority") == "P0"]
        p1_items = [p for p in pending if p.get("priority", "P1") == "P1"]
        p2_items = [p for p in pending if p.get("priority") == "P2"]

        def render_priority_section(items: list, header: str) -> None:
            if not items:
                return
            md.append(f"\n{header}")
            md.append("| ID | 问题描述 | 状态 |")
            md.append("|---|---|---|")
            for p in items:
                qid = p.get("id", "-")
                qtext = p.get("question", "")
                status = p.get("status", "待确认")
                md.append(f"| {qid} | {qtext} | {status} |")

        render_priority_section(p0_items, "### [P0] 阻塞性问题 (必须解决)")
        render_priority_section(p1_items, "### [P1] 建议澄清 (推荐解决)")
        render_priority_section(p2_items, "### [P2] 可选细化 (后续补充)")
    else:
        md.append(
            "> **说明**：在此记录需求分析过程中发现的疑问、假设及跟进状态（待确认/已确认）。"
        )
    md.append("")

    # Section 7: 已确认信息
    md.append("## 7. 已确认信息")
    if confirmed:
        for c in confirmed:
            note = c.get("note", "")
            md.append(f"- ✅ {c.get('question')}：{note}")
    else:
        md.append("> **说明**：在此记录已与产品/开发确认的关键信息或决策结论。")
    md.append("")

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
