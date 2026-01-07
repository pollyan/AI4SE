"""
Lisa Prompts 单元测试

测试 Prompt 共享模块的内容和组合函数。
"""

import pytest

from backend.agents.lisa.prompts import (
    LISA_IDENTITY,
    LISA_STYLE,
    LISA_PRINCIPLES,
    LISA_SKILLS,
    PROTOCOL_PANORAMA_FOCUS,
    PROTOCOL_TECH_SELECTION,
    RESPONSE_TEMPLATE,
)
from backend.agents.lisa.prompts.shared import (
    build_base_prompt,
    build_full_prompt_with_protocols,
)


class TestPromptComponents:
    """测试各 Prompt 组件内容"""
    
    def test_identity_contains_name_and_title(self):
        """身份组件应包含姓名和职位"""
        assert "Lisa Song" in LISA_IDENTITY
        assert "测试领域专家" in LISA_IDENTITY
    
    def test_style_contains_key_characteristics(self):
        """风格组件应包含关键特征"""
        assert "专注" in LISA_STYLE
        assert "沟通" in LISA_STYLE
        assert "简洁" in LISA_STYLE
    
    def test_principles_contains_core_values(self):
        """原则组件应包含核心价值观"""
        assert "规划优先" in LISA_PRINCIPLES
        assert "风险驱动" in LISA_PRINCIPLES
        assert "可视化" in LISA_PRINCIPLES
        assert "信息澄清" in LISA_PRINCIPLES
        assert "动态规划" in LISA_PRINCIPLES
    
    def test_skills_contains_tool_categories(self):
        """技能组件应包含工具类别"""
        assert "分析与思维框架" in LISA_SKILLS
        assert "测试策略与规划" in LISA_SKILLS
        assert "测试设计技术" in LISA_SKILLS
    
    def test_skills_contains_specific_techniques(self):
        """技能组件应包含具体技术"""
        assert "思维导图" in LISA_SKILLS
        assert "FMEA" in LISA_SKILLS
        assert "等价类划分" in LISA_SKILLS
        assert "Mermaid" in LISA_PRINCIPLES  # 可视化原则中提及
    
    def test_panorama_focus_protocol_has_steps(self):
        """全景-聚焦协议应包含执行步骤"""
        assert "宣布与范围界定" in PROTOCOL_PANORAMA_FOCUS
        assert "呈现议程" in PROTOCOL_PANORAMA_FOCUS
        assert "执行聚焦讨论" in PROTOCOL_PANORAMA_FOCUS
    
    def test_tech_selection_protocol_has_steps(self):
        """技术选型协议应包含执行步骤"""
        assert "技术决策" in PROTOCOL_TECH_SELECTION
        assert "交付告知" in PROTOCOL_TECH_SELECTION
    
    def test_response_template_has_structure(self):
        """响应模板应包含结构定义"""
        assert "任务进展" in RESPONSE_TEMPLATE
        assert "共识总结" in RESPONSE_TEMPLATE
        assert "[-] 进行中" in RESPONSE_TEMPLATE


class TestPromptCombination:
    """测试 Prompt 组合函数"""
    
    def test_base_prompt_includes_identity_and_style(self):
        """基础 Prompt 应包含身份和风格"""
        base = build_base_prompt()
        
        assert "Lisa Song" in base
        assert "专注" in base
        assert "规划优先" in base
        assert "思维导图" in base
    
    def test_base_prompt_excludes_protocols(self):
        """基础 Prompt 不应包含协议"""
        base = build_base_prompt()
        
        assert "全景-聚焦" not in base
        assert "技术选型协议" not in base
    
    def test_full_prompt_includes_all_components(self):
        """完整 Prompt 应包含所有组件"""
        full = build_full_prompt_with_protocols()
        
        # 身份
        assert "Lisa Song" in full
        # 风格
        assert "专注" in full
        # 原则
        assert "规划优先" in full
        # 技能
        assert "FMEA" in full
        # 协议
        assert "全景-聚焦" in full
        assert "技术选型协议" in full
        # 响应模板
        assert "任务进展" in full
    
    def test_full_prompt_has_section_separators(self):
        """完整 Prompt 应有分节符"""
        full = build_full_prompt_with_protocols()
        
        assert "---" in full


class TestPromptQuality:
    """测试 Prompt 质量"""
    
    def test_no_trailing_whitespace_in_components(self):
        """组件不应有尾部空白"""
        components = [
            LISA_IDENTITY,
            LISA_STYLE,
            LISA_PRINCIPLES,
            LISA_SKILLS,
            PROTOCOL_PANORAMA_FOCUS,
            PROTOCOL_TECH_SELECTION,
            RESPONSE_TEMPLATE,
        ]
        
        for component in components:
            assert component == component.strip(), "组件有尾部空白"
    
    def test_components_are_not_empty(self):
        """组件不应为空"""
        components = [
            LISA_IDENTITY,
            LISA_STYLE,
            LISA_PRINCIPLES,
            LISA_SKILLS,
            PROTOCOL_PANORAMA_FOCUS,
            PROTOCOL_TECH_SELECTION,
            RESPONSE_TEMPLATE,
        ]
        
        for component in components:
            assert len(component) > 50, "组件内容过短"
