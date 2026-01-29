from typing import Dict, Any, List

def convert_list_to_markdown(items: List[str]) -> str:
    return "\n".join([f"- {item}" for item in items]) if items else "(无)"

def convert_requirement_doc(content: Dict[str, Any]) -> str:
    """将 RequirementDoc 结构转换为 Markdown"""
    md = []
    
    # 1. Scope
    if "scope" in content:
        md.append("## 项目范围 (Scope)")
        md.append(convert_list_to_markdown(content["scope"]))
        md.append("")
        
    # 2. Mermaid Flow
    if "flow_mermaid" in content and content["flow_mermaid"]:
        md.append("## 业务流程 (Flow)")
        md.append("```mermaid")
        md.append(content["flow_mermaid"])
        md.append("```")
        md.append("")
        
    # 3. Rules
    if "rules" in content:
        md.append("## 业务规则 (Rules)")
        md.append(convert_list_to_markdown(content["rules"]))
        md.append("")
        
    # 4. Assumptions
    if "assumptions" in content:
        md.append("## 假设与约束 (Assumptions)")
        md.append(convert_list_to_markdown(content["assumptions"]))
        md.append("")
        
    # 5. NFR
    if "nfr_markdown" in content and isinstance(content["nfr_markdown"], dict):
        md.append("## 非功能需求 (NFR)")
        for category, desc in content["nfr_markdown"].items():
            md.append(f"### {category}")
            md.append(desc)
            md.append("")
            
    return "\n".join(md)

def convert_to_markdown(content: Dict[str, Any], artifact_type: str) -> str:
    """通用转换入口"""
    if artifact_type == "requirement":
        return convert_requirement_doc(content)
    
    # Fallback: 如果是其他类型或未知结构，尝试通用的 key-value 渲染
    # TODO: 实现 Design 和 Cases 的转换
    md = []
    for k, v in content.items():
        md.append(f"## {k}")
        md.append(str(v))
        md.append("")
    return "\n".join(md)
