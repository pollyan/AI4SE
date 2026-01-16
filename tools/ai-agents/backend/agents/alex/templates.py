"""
Alex 智能体产出物模板定义

定义每个工作流各阶段的产出物骨架结构。
章节内容采用【全量替换】模式：LLM 每次调用 update_artifact 时传入章节的完整内容。
"""

from typing import Dict, List, Any

# ═══════════════════════════════════════════════════════════════════════════════
# 模板定义
# ═══════════════════════════════════════════════════════════════════════════════

ARTIFACT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ─────────────────────────────────────────────────────────────────────────────
    # 测试用例设计工作流 (Workflow: test_design)
    # ─────────────────────────────────────────────────────────────────────────────
    
    "test_design_requirements": {
        "name": "需求分析文档",
        "stage_id": "clarify",
        "sections": [
            {
                "id": "background",
                "title": "1. 背景与目标",
                "placeholder": "> *待分析...*"
            },
            {
                "id": "scope",
                "title": "2. 范围与边界",
                "placeholder": "**包含范围**:\\n> *待定义...*\\n\\n**排除范围**:\\n> *待定义...*"
            },
            {
                "id": "actors",
                "title": "3. 用户角色",
                "placeholder": "| 角色 | 描述 | 核心诉求 |\\n|------|------|----------|\\n| - | *待识别* | - |"
            },
            {
                "id": "functional",
                "title": "4. 功能需求",
                "placeholder": "| 编号 | 需求描述 | 优先级 |\\n|------|----------|--------|\\n| FR-01 | *待分析* | - |"
            },
            {
                "id": "non_functional",
                "title": "5. 非功能需求",
                "placeholder": "| 类型 | 需求描述 | 指标 |\\n|------|----------|------|\\n| 性能 | *待分析* | - |"
            },
            {
                "id": "constraints",
                "title": "6. 约束与假设",
                "placeholder": "**技术约束**:\\n> *待识别...*\\n\\n**业务假设**:\\n> *待识别...*"
            },
            {
                "id": "acceptance",
                "title": "7. 验收标准",
                "placeholder": "| 场景 | 给定条件 | 预期结果 |\\n|------|----------|----------|\\n| - | *待定义* | - |"
            },
        ]
    },
    
    "test_design_strategy": {
        "name": "测试策略蓝图",
        "stage_id": "strategy",
        "sections": [
            {
                "id": "risk_analysis",
                "title": "1. 风险分析",
                "placeholder": "> *待分析...*"
            },
            {
                "id": "strategy_matrix",
                "title": "2. 模块级策略矩阵",
                "placeholder": "| 模块 | 优先级 | 核心测试策略 |\\n|------|--------|-------------|\\n| - | - | *待定义* |"
            },
            {
                "id": "approach",
                "title": "3. 测试方法选型",
                "placeholder": "> *待确定...*"
            },
        ]
    },
    
    "test_design_cases": {
        "name": "测试用例集",
        "stage_id": "cases",
        "sections": [
            {
                "id": "mindmap",
                "title": "1. 测试点思维导图",
                "placeholder": "> *待设计...*"
            },
            {
                "id": "cases",
                "title": "2. 测试用例",
                "placeholder": "| 用例ID | 场景 | 步骤 | 预期结果 |\\n|--------|------|------|----------|\\n| - | *待生成* | - | - |"
            },
        ]
    },
    
    "test_design_final": {
        "name": "测试设计文档",
        "stage_id": "delivery",
        "sections": [
            {
                "id": "summary",
                "title": "1. 文档概述",
                "placeholder": "> *待汇总...*"
            },
            {
                "id": "full_content",
                "title": "2. 完整内容",
                "placeholder": "> *待整合...*"
            },
        ]
    },
    
    # ─────────────────────────────────────────────────────────────────────────────
    # 需求评审工作流 (Workflow: requirement_review)
    # ─────────────────────────────────────────────────────────────────────────────
    
    "requirement_review_report": {
        "name": "需求评审报告",
        "stage_id": "review",
        "sections": [
            {
                "id": "business_summary",
                "title": "1. 业务理解",
                "placeholder": "> *待理解...*"
            },
            {
                "id": "issues",
                "title": "2. 问题清单",
                "placeholder": "| # | 维度 | 问题描述 | 严重程度 | 建议 |\\n|---|------|----------|----------|------|\\n| - | - | *待评审* | - | - |"
            },
            {
                "id": "conclusion",
                "title": "3. 评审结论",
                "placeholder": "> *待总结...*"
            },
        ]
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_template(artifact_key: str) -> Dict[str, Any] | None:
    """获取指定 artifact_key 的模板定义"""
    return ARTIFACT_TEMPLATES.get(artifact_key)


def get_template_by_stage(stage_id: str) -> Dict[str, Any] | None:
    """根据 stage_id 获取对应的模板定义"""
    for key, template in ARTIFACT_TEMPLATES.items():
        if template.get("stage_id") == stage_id:
            return {"artifact_key": key, **template}
    return None


def render_template_skeleton(artifact_key: str) -> str | None:
    """
    渲染模板骨架为完整的 Markdown 字符串
    
    Returns:
        拼接好的 Markdown 骨架，各章节显示 placeholder
    """
    template = get_template(artifact_key)
    if not template:
        return None
    
    lines = [f"# {template['name']}", ""]
    
    for section in template.get("sections", []):
        lines.append(f"## {section['title']}")
        lines.append("")
        # 处理转义的换行符
        placeholder = section.get("placeholder", "> *待填充...*").replace("\\n", "\n")
        lines.append(placeholder)
        lines.append("")
    
    return "\n".join(lines)


def update_section_content(
    current_content: str,
    artifact_key: str,
    section_id: str,
    new_content: str
) -> str | None:
    """
    更新产出物中指定章节的内容（全量替换该章节）
    
    Args:
        current_content: 当前产出物的完整 Markdown 内容
        artifact_key: 产出物 key
        section_id: 要更新的章节 ID
        new_content: 新的章节内容
        
    Returns:
        更新后的完整 Markdown 内容
    """
    template = get_template(artifact_key)
    if not template:
        return None
    
    sections = template.get("sections", [])
    section_titles = {s["id"]: s["title"] for s in sections}
    
    if section_id not in section_titles:
        return None
    
    target_title = section_titles[section_id]
    
    # 找到下一个章节的标题（用于确定替换边界）
    section_ids = [s["id"] for s in sections]
    current_idx = section_ids.index(section_id)
    next_title = None
    if current_idx + 1 < len(sections):
        next_title = section_titles[section_ids[current_idx + 1]]
    
    # 使用正则替换章节内容
    import re
    
    # 构建匹配模式：从当前章节标题到下一个章节标题（或文档末尾）
    pattern_start = rf"(## {re.escape(target_title)}\n\n)"
    if next_title:
        pattern_end = rf"(\n\n## {re.escape(next_title)})"
        pattern = pattern_start + r".*?" + pattern_end
        replacement = rf"\g<1>{new_content}\g<2>"
    else:
        # 最后一个章节，匹配到文档末尾
        pattern = pattern_start + r".*$"
        replacement = rf"\g<1>{new_content}"
    
    updated = re.sub(pattern, replacement, current_content, flags=re.DOTALL)
    return updated
