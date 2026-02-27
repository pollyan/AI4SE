from backend.agents.lisa.utils.markdown_generator import convert_to_markdown


class TestConvertRequirementDocBasic:
    def test_convert_requirement_doc(self):
        content = {
            "scope": ["模块A", "模块B"],
            "flow_mermaid": "graph TD\nA-->B",
            "rules": ["规则1"],
            "assumptions": ["假设1"],
            "nfr_markdown": {"性能": "很快", "安全": "很安全"},
        }

        md = convert_to_markdown(content, "requirement")

        assert "## 1. 测试范围" in md
        assert "```mermaid" in md
        assert "mindmap" in md
        assert "root((需求全景))" in md
        assert "模块A" in md
        assert "模块B" in md

        assert "## 4. 业务流程图" in md
        assert "graph TD" in md
        assert "## 3. 核心业务规则" in md
        assert "## 5. 非功能需求" in md
        assert "**性能**" in md
        assert "很快" in md

    def test_convert_requirement_doc_with_scope_mermaid(self):
        content = {
            "scope": ["Old List"],
            "scope_mermaid": "mindmap\n  root((New Mindmap))",
            "flow_mermaid": "",
            "rules": [],
            "assumptions": [],
        }

        md = convert_to_markdown(content, "requirement")
        assert "New Mindmap" in md

    def test_convert_unsupported_type_raises_error(self):
        """确定性优先: 不支持的类型直接报错，不做静默降级"""
        import pytest
        with pytest.raises(ValueError, match="unsupported artifact_type"):
            convert_to_markdown({"key": "value"}, "unknown")


class TestConvertDesignDoc:
    """测试策略文档（design）的 Markdown 转换"""

    def test_renders_strategy_markdown(self):
        content = {
            "strategy_markdown": "## 1. 风险分析\n\n| 风险项 | 影响 |\n|---|---|\n| R1 | 高 |",
            "test_points": {"id": "ROOT", "label": "根节点", "type": "group"},
        }
        md = convert_to_markdown(content, "design")
        assert "# 测试策略蓝图" in md
        assert "## 1. 风险分析" in md
        assert "风险项" in md

    def test_renders_test_points_tree(self):
        content = {
            "strategy_markdown": "策略文档内容",
            "test_points": {
                "id": "GRP-001",
                "label": "带验证码用户登录",
                "type": "group",
                "priority": "P0",
                "method": "混合策略",
                "children": [
                    {
                        "id": "TP-001",
                        "label": "核心登录功能验证",
                        "type": "group",
                        "priority": "P0",
                        "method": "功能测试",
                        "children": [
                            {
                                "id": "TP-001-01",
                                "label": "正向登录流程",
                                "type": "point",
                                "priority": "P0",
                                "method": "黑盒测试",
                            }
                        ],
                    }
                ],
            },
        }
        md = convert_to_markdown(content, "design")
        assert "## 测试点拓扑" in md
        assert "带验证码用户登录" in md
        assert "核心登录功能验证" in md
        assert "正向登录流程" in md
        # 验证层级缩进
        lines = md.split("\n")
        tp_lines = [l for l in lines if "正向登录流程" in l]
        assert len(tp_lines) == 1
        assert tp_lines[0].startswith("    ")  # level 2 = 4 spaces indent

    def test_empty_design_doc(self):
        content = {
            "strategy_markdown": "",
            "test_points": None,
        }
        md = convert_to_markdown(content, "design")
        assert "策略文档待生成" in md
        assert "测试点结构待生成" in md


class TestConvertRequirementDoc7Sections:
    def test_section_1_scope_with_out_of_scope(self):
        content = {
            "scope": ["登录功能", "注销功能"],
            "out_of_scope": ["注册功能"],
            "flow_mermaid": "",
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 1. 测试范围" in result
        assert "### 范围内" in result
        assert "### 范围外" in result
        assert "登录功能" in result
        assert "注册功能" in result

    def test_section_2_features_table(self):
        content = {
            "scope": ["测试"],
            "flow_mermaid": "",
            "features": [
                {
                    "id": "F1",
                    "name": "登录",
                    "desc": "用户登录",
                    "acceptance": ["能登录", "有提示"],
                    "priority": "P0",
                }
            ],
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 2. 功能详细规格" in result
        assert "| F1 |" in result
        assert "登录" in result
        assert "能登录" in result

    def test_section_3_rules_table(self):
        content = {
            "scope": ["测试"],
            "flow_mermaid": "",
            "rules": [{"id": "R1", "desc": "密码不能为空", "source": "user"}],
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 3. 核心业务规则" in result
        assert "R1" in result

    def test_section_7_confirmed_from_assumptions(self):
        content = {
            "scope": ["测试"],
            "flow_mermaid": "",
            "assumptions": [
                {
                    "id": "Q1",
                    "question": "问题1",
                    "status": "pending",
                    "priority": "P0",
                },
                {
                    "id": "Q2",
                    "question": "问题2",
                    "status": "confirmed",
                    "note": "答案",
                },
            ],
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 6. 待澄清问题" in result
        assert "## 7. 已确认信息" in result
        section_7 = result.split("## 7.")[1] if "## 7." in result else ""
        assert "问题2" in section_7
        assert "答案" in section_7

    def test_all_7_sections_present(self):
        content = {
            "scope": ["测试"],
            "out_of_scope": [],
            "features": [],
            "flow_mermaid": "graph TD; A-->B",
            "rules": [],
            "assumptions": [],
            "nfr_markdown": "性能要求",
        }
        result = convert_to_markdown(content, "requirement")
        assert "## 1. 测试范围" in result
        assert "## 2. 功能详细规格" in result
        assert "## 3. 核心业务规则" in result
        assert "## 4. 业务流程图" in result
        assert "## 5. 非功能需求" in result
        assert "## 6. 待澄清问题" in result
        assert "## 7. 已确认信息" in result


class TestCreateEmptyRequirementDoc:
    def test_returns_requirement_doc(self):
        from backend.agents.lisa.utils.markdown_generator import (
            create_empty_requirement_doc,
        )
        from backend.agents.lisa.artifact_models import RequirementDoc

        doc = create_empty_requirement_doc()
        assert isinstance(doc, RequirementDoc)

    def test_all_lists_empty(self):
        from backend.agents.lisa.utils.markdown_generator import (
            create_empty_requirement_doc,
        )

        doc = create_empty_requirement_doc()
        assert doc.scope == []
        assert doc.out_of_scope == []
        assert doc.features == []
        assert doc.rules == []
        assert doc.assumptions == []

    def test_converts_to_markdown(self):
        from backend.agents.lisa.utils.markdown_generator import (
            create_empty_requirement_doc,
            convert_to_markdown,
        )

        doc = create_empty_requirement_doc()
        result = convert_to_markdown(doc.model_dump(), "requirement")
        assert "## 1. 测试范围" in result
from backend.agents.lisa.utils.markdown_generator import (
    convert_to_markdown,
    create_empty_requirement_doc,
)


class TestMarkdownDescriptions:
    def test_empty_doc_shows_descriptions(self):
        empty_doc = create_empty_requirement_doc().model_dump()
        md = convert_to_markdown(empty_doc, "requirement")

        # Verify descriptions exist for each section
        assert "> **说明**：在此描述本次测试覆盖的功能模块" in md
        assert "> **说明**：在此详细列出功能点" in md
        assert "> **说明**：在此记录关键业务逻辑" in md
        assert "> **说明**：在此补充核心业务流程图" in md
        assert "> **说明**：在此记录性能（QPS/RT）" in md
        assert "> **说明**：在此记录需求分析过程中发现的疑问" in md
        assert "> **说明**：在此记录已与产品/开发确认的关键信息" in md

    def test_populated_doc_hides_descriptions(self):
        # Create doc with content for Section 2 (Features)
        doc = create_empty_requirement_doc().model_dump()
        doc["features"] = [
            {"id": "F1", "name": "Feature 1", "desc": "Desc", "priority": "P1"}
        ]

        md = convert_to_markdown(doc, "requirement")

        # Verify description is NOT present for populated section
        assert "> **说明**：在此详细列出功能点" not in md
        assert "| F1 | Feature 1 | Desc | - | P1 |" in md

        # Verify other empty sections STILL have descriptions
        assert "> **说明**：在此描述本次测试覆盖的功能模块" in md
