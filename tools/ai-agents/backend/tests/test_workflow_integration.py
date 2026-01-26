import pytest
from backend.agents.lisa.artifact_models import (
    RequirementDoc, DesignDoc, DesignNode, CaseDoc, CaseItem, CaseStep,
    RuleItem, AssumptionItem, AgentArtifact
)
from backend.agents.lisa.artifact_patch import apply_patch, PatchOperation
from backend.agents.lisa.schemas import UpdateStructuredArtifact


class TestArtifactWorkflowIntegration:

    def test_full_workflow_phase_transitions(self):
        phase1 = AgentArtifact(
            phase="requirement",
            version="1.0",
            content=RequirementDoc(
                scope=["登录模块", "POST /api/login"],
                flow_mermaid="graph LR; A[用户]-->B[登录页]-->C[验证]",
                rules=[RuleItem(id="R1", desc="密码6-20位", source="user")],
                assumptions=[AssumptionItem(id="Q1", question="支持第三方登录?", status="pending")]
            )
        )
        assert phase1.phase == "requirement"
        
        phase2 = AgentArtifact(
            phase="design",
            version="1.0",
            content=DesignDoc(
                strategy_markdown="## 策略\n- 边界值分析",
                test_points=DesignNode(
                    id="ROOT", label="登录测试", type="group",
                    children=[
                        DesignNode(id="TP-001", label="密码边界", type="point", method="边界值", priority="P0")
                    ]
                )
            )
        )
        assert phase2.phase == "design"
        
        phase3 = AgentArtifact(
            phase="cases",
            version="1.0",
            content=CaseDoc(
                cases=[
                    CaseItem(
                        id="TC-001", title="密码5位验证",
                        steps=[CaseStep(action="输入5位密码", expect="提示错误")],
                        tags=["P0", "Smoke"]
                    )
                ],
                stats={"total": 1, "p0_count": 1}
            )
        )
        assert phase3.phase == "cases"

    def test_patch_integration_with_artifact(self):
        design = DesignDoc(
            strategy_markdown="策略",
            test_points=DesignNode(id="ROOT", label="Root", type="group", children=[])
        )
        
        patches = [
            PatchOperation(op="add", parent_id="ROOT", node=DesignNode(id="GRP-1", label="功能组", type="group", children=[])),
        ]
        
        new_tree = apply_patch(design.test_points, patches)
        assert new_tree.children is not None
        assert len(new_tree.children) == 1
        assert new_tree.children[0].is_new is True
        
        patches2 = [
            PatchOperation(op="add", parent_id="GRP-1", node=DesignNode(id="TP-1", label="测试点1", type="point", method="等价类")),
        ]
        final_tree = apply_patch(new_tree, patches2)
        assert final_tree.children is not None
        assert final_tree.children[0].children is not None
        assert final_tree.children[0].children[0].id == "TP-1"

    def test_structured_artifact_schema_validation(self):
        schema = UpdateStructuredArtifact(
            key="test_design_requirements",
            artifact_type="requirement",
            content={
                "scope": ["测试"],
                "flow_mermaid": "graph LR; A-->B",
                "rules": [],
                "assumptions": []
            }
        )
        assert schema.artifact_type == "requirement"
        
        doc = RequirementDoc(**schema.content)
        assert doc.scope == ["测试"]
