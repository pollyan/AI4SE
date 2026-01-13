"""
Schema 单元测试

TDD Red Phase: 验证 Pydantic Schema 和 to_progress_info 转换逻辑
"""

import pytest
from backend.agents.shared.schemas import (
    WorkflowStage,
    Artifact,
    LisaStructuredOutput,
    AlexStructuredOutput,
    to_progress_info,
)


class TestWorkflowStage:
    
    def test_valid_stage_pending(self):
        stage = WorkflowStage(id="clarify", name="需求澄清", status="pending")
        assert stage.id == "clarify"
        assert stage.name == "需求澄清"
        assert stage.status == "pending"

    def test_valid_stage_active(self):
        stage = WorkflowStage(id="strategy", name="策略制定", status="active")
        assert stage.status == "active"

    def test_valid_stage_completed(self):
        stage = WorkflowStage(id="cases", name="用例设计", status="completed")
        assert stage.status == "completed"

    def test_invalid_status_raises_error(self):
        with pytest.raises(ValueError):
            WorkflowStage(id="test", name="测试", status="invalid_status")


class TestArtifact:

    def test_artifact_with_content(self):
        artifact = Artifact(
            stage_id="clarify",
            key="requirements",
            name="需求分析文档",
            content="# 需求分析\n\n## 功能需求\n- 用户登录"
        )
        assert artifact.stage_id == "clarify"
        assert artifact.key == "requirements"
        assert artifact.name == "需求分析文档"
        assert artifact.content is not None
        assert "需求分析" in artifact.content

    def test_artifact_without_content(self):
        artifact = Artifact(
            stage_id="strategy",
            key="test_strategy",
            name="测试策略",
            content=None
        )
        assert artifact.content is None

    def test_artifact_content_default_none(self):
        artifact = Artifact(
            stage_id="cases",
            key="test_cases",
            name="测试用例集"
        )
        assert artifact.content is None


class TestLisaStructuredOutput:

    @pytest.fixture
    def sample_output(self):
        return LisaStructuredOutput(
            plan=[
                WorkflowStage(id="clarify", name="需求澄清", status="completed"),
                WorkflowStage(id="strategy", name="策略制定", status="active"),
                WorkflowStage(id="cases", name="用例设计", status="pending"),
            ],
            current_stage_id="strategy",
            artifacts=[
                Artifact(
                    stage_id="clarify",
                    key="requirements",
                    name="需求分析文档",
                    content="# 需求分析完成"
                ),
                Artifact(
                    stage_id="strategy",
                    key="test_strategy",
                    name="测试策略",
                    content=None
                ),
            ],
            # message 字段已移除
        )

    def test_output_structure(self, sample_output):
        assert len(sample_output.plan) == 3
        assert sample_output.current_stage_id == "strategy"
        assert len(sample_output.artifacts) == 2
        # message 断言已移除

    def test_output_json_serialization(self, sample_output):
        json_str = sample_output.model_dump_json()
        assert "clarify" in json_str
        assert "strategy" in json_str
        assert "需求澄清" in json_str
        assert "message" not in json_str

    def test_output_from_json(self):
        json_data = {
            "plan": [
                {"id": "clarify", "name": "需求澄清", "status": "active"}
            ],
            "current_stage_id": "clarify",
            "artifacts": [],
            # message 字段不应包含在 JSON 中
        }
        output = LisaStructuredOutput.model_validate(json_data)
        assert output.plan[0].id == "clarify"


class TestToProgressInfo:

    @pytest.fixture
    def lisa_output(self):
        return LisaStructuredOutput(
            plan=[
                WorkflowStage(id="clarify", name="需求澄清", status="completed"),
                WorkflowStage(id="strategy", name="策略制定", status="active"),
                WorkflowStage(id="cases", name="用例设计", status="pending"),
                WorkflowStage(id="delivery", name="交付确认", status="pending"),
            ],
            current_stage_id="strategy",
            artifacts=[
                Artifact(
                    stage_id="clarify",
                    key="requirements",
                    name="需求分析文档",
                    content="# 需求分析内容"
                ),
                Artifact(
                    stage_id="strategy",
                    key="test_strategy",
                    name="测试策略",
                    content=None
                ),
                Artifact(
                    stage_id="cases",
                    key="test_cases",
                    name="测试用例集",
                    content=None
                ),
            ],
            # message 字段已移除
        )

    def test_progress_info_stages(self, lisa_output):
        progress = to_progress_info(lisa_output)
        
        assert len(progress["stages"]) == 4
        assert progress["stages"][0]["id"] == "clarify"
        assert progress["stages"][0]["status"] == "completed"
        assert progress["stages"][1]["status"] == "active"

    def test_progress_info_current_stage_index(self, lisa_output):
        progress = to_progress_info(lisa_output)
        
        assert progress["currentStageIndex"] == 1

    def test_progress_info_current_task(self, lisa_output):
        progress = to_progress_info(lisa_output)
        
        assert "策略制定" in progress["currentTask"]

    def test_progress_info_artifacts_dict(self, lisa_output):
        progress = to_progress_info(lisa_output)
        
        assert "requirements" in progress["artifacts"]
        assert progress["artifacts"]["requirements"] == "# 需求分析内容"
        assert "test_strategy" not in progress["artifacts"]

    def test_progress_info_artifact_progress_template(self, lisa_output):
        progress = to_progress_info(lisa_output)
        
        template = progress["artifactProgress"]["template"]
        assert len(template) == 3
        assert template[0]["artifactKey"] == "requirements"
        assert template[0]["stageId"] == "clarify"
        assert template[0]["name"] == "需求分析文档"

    def test_progress_info_artifact_progress_completed(self, lisa_output):
        progress = to_progress_info(lisa_output)
        
        completed = progress["artifactProgress"]["completed"]
        assert "requirements" in completed
        assert "test_strategy" not in completed

    def test_progress_info_artifact_progress_generating(self, lisa_output):
        progress = to_progress_info(lisa_output)
        
        generating = progress["artifactProgress"]["generating"]
        assert generating == "test_strategy"

    def test_progress_info_no_generating_when_all_done(self):
        output = LisaStructuredOutput(
            plan=[
                WorkflowStage(id="clarify", name="需求澄清", status="completed"),
            ],
            current_stage_id="clarify",
            artifacts=[
                Artifact(
                    stage_id="clarify",
                    key="requirements",
                    name="需求分析文档",
                    content="已完成"
                ),
            ],
            # message 字段已移除
        )
        progress = to_progress_info(output)
        
        assert progress["artifactProgress"]["generating"] is None

    def test_progress_info_empty_artifacts(self):
        output = LisaStructuredOutput(
            plan=[
                WorkflowStage(id="clarify", name="需求澄清", status="active"),
            ],
            current_stage_id="clarify",
            artifacts=[],
            # message 字段已移除
        )
        progress = to_progress_info(output)
        
        assert progress["artifacts"] == {}
        assert progress["artifactProgress"]["template"] == []
        assert progress["artifactProgress"]["completed"] == []
        assert progress["artifactProgress"]["generating"] is None
