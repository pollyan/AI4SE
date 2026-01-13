"""
Alex Nodes 单元测试

测试 Alex 智能体的节点逻辑。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from langchain_core.messages import AIMessage

from backend.agents.alex.state import get_initial_state, ArtifactKeys
from backend.agents.alex.nodes.workflow_product_design import (
    get_artifacts_summary,
    determine_stage,
    extract_artifact_from_response,
    workflow_product_design_node,
)


class TestGetArtifactsSummary:
    """测试产出物摘要生成"""

    def test_empty_artifacts(self):
        """空产出物应返回(无)"""
        result = get_artifacts_summary({})

        assert result == "(无)"

    def test_single_artifact(self):
        """单个产出物应显示名称和长度"""
        artifacts = {
            ArtifactKeys.PRODUCT_ELEVATOR: "电梯演讲内容"
        }

        result = get_artifacts_summary(artifacts)

        assert "电梯演讲" in result
        assert "6" in result  # "电梯演讲内容" 长度为6
        assert "字符" in result

    def test_multiple_artifacts(self):
        """多个产出物应分行显示"""
        artifacts = {
            ArtifactKeys.PRODUCT_ELEVATOR: "内容1",
            ArtifactKeys.PRODUCT_PERSONA: "内容2",
        }

        result = get_artifacts_summary(artifacts)

        assert "电梯演讲" in result
        assert "用户画像" in result
        assert result.count("\n") == 1  # 应该有1个换行符

    def test_all_artifact_types(self):
        """所有类型的产出物都应正确显示"""
        artifacts = {
            ArtifactKeys.PRODUCT_ELEVATOR: "内容1",
            ArtifactKeys.PRODUCT_PERSONA: "内容2",
            ArtifactKeys.PRODUCT_JOURNEY: "内容3",
            ArtifactKeys.PRODUCT_BRD: "内容4",
        }

        result = get_artifacts_summary(artifacts)

        assert "电梯演讲" in result
        assert "用户画像" in result
        assert "用户旅程" in result
        assert "业务需求文档" in result


class TestDetermineStage:
    """测试阶段判断逻辑"""

    def test_no_artifacts_returns_elevator(self):
        """无产出物时应返回elevator"""
        state = get_initial_state()

        result = determine_stage(state)

        assert result == "elevator"

    def test_elevator_complete_returns_persona(self):
        """有elevator时应返回persona"""
        state = get_initial_state()
        state["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR] = "内容"

        result = determine_stage(state)

        assert result == "persona"

    def test_persona_complete_returns_journey(self):
        """有persona时应返回journey"""
        state = get_initial_state()
        state["artifacts"][ArtifactKeys.PRODUCT_PERSONA] = "内容"

        result = determine_stage(state)

        assert result == "journey"

    def test_journey_complete_returns_brd(self):
        """有journey时应返回brd"""
        state = get_initial_state()
        state["artifacts"][ArtifactKeys.PRODUCT_JOURNEY] = "内容"

        result = determine_stage(state)

        assert result == "brd"

    def test_brd_complete_returns_brd(self):
        """有brd时应返回brd（已完成）"""
        state = get_initial_state()
        state["artifacts"][ArtifactKeys.PRODUCT_BRD] = "内容"

        result = determine_stage(state)

        assert result == "brd"

    def test_priority_order(self):
        """应按优先级检查：brd > journey > persona > elevator"""
        state = get_initial_state()
        # 添加多个产出物
        state["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR] = "内容1"
        state["artifacts"][ArtifactKeys.PRODUCT_PERSONA] = "内容2"
        state["artifacts"][ArtifactKeys.PRODUCT_JOURNEY] = "内容3"

        result = determine_stage(state)

        # journey 完成后应进入 brd
        assert result == "brd"


class TestExtractArtifact:
    """测试产出物提取"""

    def test_extract_elevator_from_markdown(self):
        """应能从markdown代码块中提取elevator"""
        response = '''```markdown
# 电梯演讲

这是一个很好的产品。
```'''

        artifact_key, content = extract_artifact_from_response(response, "elevator")

        assert artifact_key == ArtifactKeys.PRODUCT_ELEVATOR
        assert "电梯演讲" in content
        assert "这是一个很好的产品" in content

    def test_extract_persona_from_markdown(self):
        """应能从markdown代码块中提取persona"""
        response = '''```markdown
# 用户画像

目标用户：开发者
```'''

        artifact_key, content = extract_artifact_from_response(response, "persona")

        assert artifact_key == ArtifactKeys.PRODUCT_PERSONA
        assert "用户画像" in content

    def test_extract_journey_from_markdown(self):
        """应能从markdown代码块中提取journey"""
        response = '''```markdown
# 用户旅程

发现 -> 使用 -> 推荐
```'''

        artifact_key, content = extract_artifact_from_response(response, "journey")

        assert artifact_key == ArtifactKeys.PRODUCT_JOURNEY
        assert "用户旅程" in content

    def test_extract_brd_from_markdown(self):
        """应能从markdown代码块中提取brd"""
        response = '''```markdown
# BRD

产品需求文档内容
```'''

        artifact_key, content = extract_artifact_from_response(response, "brd")

        assert artifact_key == ArtifactKeys.PRODUCT_BRD
        assert "BRD" in content

    def test_no_markdown_returns_none(self):
        """没有markdown代码块时应返回None"""
        response = "这是一段普通的文本，没有代码块。"

        artifact_key, content = extract_artifact_from_response(response, "elevator")

        assert artifact_key is None
        assert content is None

    def test_malformed_markdown_returns_none(self):
        """格式错误的markdown应返回None"""
        response = "```markdown\n未闭合的代码块"

        artifact_key, content = extract_artifact_from_response(response, "elevator")

        assert artifact_key is None
        assert content is None

    def test_unknown_stage_returns_none(self):
        """未知阶段应返回None"""
        response = '```markdown\n内容\n```'

        artifact_key, content = extract_artifact_from_response(response, "unknown")

        assert artifact_key is None
        assert content is None


class TestWorkflowProductDesignNode:
    """测试产品设计工作流节点"""

    def test_adds_ai_message_to_history(self):
        """应将AI消息添加到历史"""
        state = get_initial_state()
        state["messages"] = []
        mock_llm = MagicMock()

        mock_response = AIMessage(content="AI回复")
        mock_llm.model.invoke.return_value = mock_response

        result = workflow_product_design_node(state, mock_llm)

        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "AI回复"

    def test_extracts_and_stores_artifact(self):
        """应提取并存储产出物"""
        state = get_initial_state()
        mock_llm = MagicMock()

        response_content = '''这是回复内容。

```markdown
# 电梯演讲

产品价值主张
```'''

        mock_response = AIMessage(content=response_content)
        mock_llm.model.invoke.return_value = mock_response

        result = workflow_product_design_node(state, mock_llm)

        assert ArtifactKeys.PRODUCT_ELEVATOR in result["artifacts"]
        assert "电梯演讲" in result["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR]

    def test_updates_workflow_stage(self):
        """应更新工作流阶段"""
        state = get_initial_state()
        state["current_stage_id"] = "elevator"
        mock_llm = MagicMock()

        mock_response = AIMessage(content="回复")
        mock_llm.model.invoke.return_value = mock_response

        result = workflow_product_design_node(state, mock_llm)

        assert result["workflow_stage"] == "elevator"
        assert result["current_workflow"] == "product_design"

    def test_handles_llm_error_gracefully(self):
        """应优雅处理LLM错误"""
        state = get_initial_state()
        mock_llm = MagicMock()

        mock_llm.model.invoke.side_effect = Exception("LLM错误")

        result = workflow_product_design_node(state, mock_llm)

        # 应返回错误消息
        assert len(result["messages"]) == 1
        assert "抱歉" in result["messages"][0].content or "问题" in result["messages"][0].content

    def test_preserves_existing_artifacts(self):
        """应保留已有的产出物"""
        state = get_initial_state()
        state["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR] = "已有内容"
        mock_llm = MagicMock()

        mock_response = AIMessage(content="新回复")
        mock_llm.model.invoke.return_value = mock_response

        result = workflow_product_design_node(state, mock_llm)

        # 已有的产出物应该还在
        assert ArtifactKeys.PRODUCT_ELEVATOR in result["artifacts"]
        assert result["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR] == "已有内容"

    def test_uses_current_stage_id(self):
        """应使用current_stage_id作为当前阶段"""
        state = get_initial_state()
        state["current_stage_id"] = "persona"
        mock_llm = MagicMock()

        mock_response = AIMessage(content="回复")
        mock_llm.model.invoke.return_value = mock_response

        result = workflow_product_design_node(state, mock_llm)

        assert result["workflow_stage"] == "persona"

    def test_falls_back_to_determine_stage(self):
        """当没有current_stage_id时，应使用determine_stage"""
        state = get_initial_state()
        # 不设置current_stage_id
        mock_llm = MagicMock()

        mock_response = AIMessage(content="回复")
        mock_llm.model.invoke.return_value = mock_response

        result = workflow_product_design_node(state, mock_llm)

        # 应该通过determine_stage判断为elevator
        assert result["workflow_stage"] == "elevator"
