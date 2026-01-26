"""测试 Artifact 数据模型的序列化和验证"""
import pytest
from backend.agents.lisa.artifact_models import (
    ArtifactPhase,
    RuleItem,
    AssumptionItem,
    RequirementDoc,
    DesignNode,
    DesignDoc,
    CaseStep,
    CaseItem,
    CaseDoc,
    AgentArtifact,
)


class TestRequirementDoc:
    """Phase 1: 需求文档模型测试"""

    def test_requirement_doc_basic_creation(self):
        """测试基本创建"""
        doc = RequirementDoc(
            scope=["登录页面", "POST /api/login"],
            flow_mermaid="graph LR; A-->B",
            rules=[
                RuleItem(id="R1", desc="密码不能为空", source="user")
            ],
            assumptions=[
                AssumptionItem(id="Q1", question="是否支持第三方登录?", status="pending")
            ],
        )
        assert doc.scope == ["登录页面", "POST /api/login"]
        assert len(doc.rules) == 1
        assert doc.rules[0].source == "user"

    def test_assumption_status_validation(self):
        """测试假设状态枚举验证"""
        item = AssumptionItem(id="Q1", question="问题", status="assumed")
        assert item.status == "assumed"

    def test_requirement_doc_with_nfr(self):
        """测试非功能需求字段"""
        doc = RequirementDoc(
            scope=["API"],
            flow_mermaid="",
            rules=[],
            assumptions=[],
            nfr_markdown="## 性能要求\n- QPS > 1000",
        )
        assert doc.nfr_markdown is not None
        assert "性能要求" in doc.nfr_markdown


class TestDesignDocModel:
    """Phase 2: 测试设计文档模型测试"""

    def test_test_node_tree_structure(self):
        """测试树形结构"""
        child = DesignNode(
            id="TP-001",
            label="密码为空校验",
            type="point",
            method="等价类",
            priority="P0",
        )
        parent = DesignNode(
            id="GRP-001",
            label="登录表单校验",
            type="group",
            children=[child],
        )
        assert parent.children is not None
        assert parent.children[0].id == "TP-001"
        assert parent.children[0].method == "等价类"

    def test_design_doc_with_strategy(self):
        """测试完整设计文档"""
        doc = DesignDoc(
            strategy_markdown="## 测试策略\n- 边界值分析\n- 安全测试",
            test_points=DesignNode(
                id="ROOT",
                label="登录模块",
                type="group",
                children=[],
            ),
        )
        assert "边界值" in doc.strategy_markdown

    def test_test_node_is_new_flag(self):
        """测试 is_new 标记用于 Diff"""
        node = DesignNode(
            id="TP-NEW",
            label="新增测试点",
            type="point",
            is_new=True,
        )
        assert node.is_new is True


class TestCaseDocModel:
    """Phase 3: 测试用例文档模型测试"""

    def test_case_with_steps(self):
        """测试用例步骤"""
        case = CaseItem(
            id="TC-001",
            title="验证有效登录",
            precondition="用户已注册",
            steps=[
                CaseStep(action="访问登录页", expect="页面加载"),
                CaseStep(action="输入账密", expect="输入成功"),
            ],
            tags=["Smoke", "P0"],
        )
        assert len(case.steps) == 2
        assert case.steps[0].action == "访问登录页"

    def test_case_with_script(self):
        """测试自动化脚本字段"""
        case = CaseItem(
            id="TC-002",
            title="自动化用例",
            steps=[CaseStep(action="点击", expect="响应")],
            tags=[],
            script="await page.click('#btn')",
        )
        assert case.script is not None
        assert "page.click" in case.script

    def test_case_doc_with_stats(self):
        """测试用例集统计信息"""
        doc = CaseDoc(
            cases=[],
            stats={"total": 24, "p0_count": 5, "auto_ready": 10},
        )
        assert doc.stats is not None
        assert doc.stats["total"] == 24


class TestAgentArtifact:
    """通用 Artifact 信封测试"""

    def test_artifact_phase_enum(self):
        """测试阶段枚举"""
        artifact = AgentArtifact(
            phase="requirement",
            version="1.0",
            content=RequirementDoc(
                scope=["test"],
                flow_mermaid="",
                rules=[],
                assumptions=[],
            ),
        )
        assert artifact.phase == "requirement"

    def test_artifact_json_serialization(self):
        """测试 JSON 序列化"""
        doc = RequirementDoc(
            scope=["test"],
            flow_mermaid="graph LR; A-->B",
            rules=[RuleItem(id="R1", desc="规则1", source="default")],
            assumptions=[],
        )
        artifact = AgentArtifact(phase="requirement", version="1.0", content=doc)
        json_str = artifact.model_dump_json()
        assert '"phase":"requirement"' in json_str
        assert '"source":"default"' in json_str

    def test_artifact_with_design_content(self):
        """测试设计阶段内容"""
        design = DesignDoc(
            strategy_markdown="策略",
            test_points=DesignNode(id="ROOT", label="Root", type="group"),
        )
        artifact = AgentArtifact(phase="design", version="1.0", content=design)
        assert artifact.phase == "design"

    def test_artifact_with_cases_content(self):
        """测试用例阶段内容"""
        cases = CaseDoc(cases=[])
        artifact = AgentArtifact(phase="cases", version="1.0", content=cases)
        assert artifact.phase == "cases"
