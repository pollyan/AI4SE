from backend.agents.lisa.artifact_models import (
    RequirementDoc,
    DesignDoc,
    DesignNode,
    CaseDoc,
    CaseItem,
    CaseStep,
    RuleItem,
    AssumptionItem,
    AgentArtifact,
)
from backend.agents.lisa.artifact_patch import merge_artifacts
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
                assumptions=[
                    AssumptionItem(
                        id="Q1", question="支持第三方登录?", status="pending"
                    )
                ],
            ),
        )
        assert phase1.phase == "requirement"

        phase2 = AgentArtifact(
            phase="design",
            version="1.0",
            content=DesignDoc(
                strategy_markdown="## 策略\n- 边界值分析",
                test_points=DesignNode(
                    id="ROOT",
                    label="登录测试",
                    type="group",
                    children=[
                        DesignNode(
                            id="TP-001",
                            label="密码边界",
                            type="point",
                            method="边界值",
                            priority="P0",
                        )
                    ],
                ),
            ),
        )
        assert phase2.phase == "design"

        phase3 = AgentArtifact(
            phase="cases",
            version="1.0",
            content=CaseDoc(
                cases=[
                    CaseItem(
                        id="TC-001",
                        title="密码5位验证",
                        steps=[CaseStep(action="输入5位密码", expect="提示错误")],
                        tags=["P0", "Smoke"],
                    )
                ],
                stats={"total": 1, "p0_count": 1},
            ),
        )
        assert phase3.phase == "cases"

    def test_patch_integration_with_artifact(self):
        original_design = {
            "strategy_markdown": "策略",
            "test_points": {
                "id": "ROOT",
                "label": "Root",
                "type": "group",
                "children": [],
            },
        }

        patch1 = {
            "test_points": {
                "children": [
                    {"id": "GRP-1", "label": "功能组", "type": "group", "children": []}
                ]
            }
        }

        state1 = merge_artifacts(original_design, patch1)
        assert len(state1["test_points"]["children"]) == 1
        assert state1["test_points"]["children"][0]["id"] == "GRP-1"

        patch2 = {
            "test_points": {
                "children": [
                    {
                        "id": "GRP-1",
                        "children": [
                            {
                                "id": "TP-1",
                                "label": "测试点1",
                                "type": "point",
                                "method": "等价类",
                            }
                        ],
                    }
                ]
            }
        }

        final_state = merge_artifacts(state1, patch2)

        grp1 = final_state["test_points"]["children"][0]
        assert grp1["id"] == "GRP-1"
        assert len(grp1["children"]) == 1
        assert grp1["children"][0]["id"] == "TP-1"

    def test_structured_artifact_schema_validation(self):
        schema = UpdateStructuredArtifact(
            key="test_design_requirements",
            artifact_type="requirement",
            content={
                "scope": ["测试"],
                "flow_mermaid": "graph LR; A-->B",
                "rules": [],
                "assumptions": [],
            },
        )
        assert schema.artifact_type == "requirement"

        doc = RequirementDoc(**schema.content)
        assert doc.scope == ["测试"]
