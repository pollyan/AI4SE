"""
Alex State 单元测试

测试 AlexState 类型定义和相关函数。
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from backend.agents.alex.state import (
    AlexState,
    get_initial_state,
    ArtifactKeys,
)


class TestAlexStateDefinition:
    """测试 AlexState 类型定义"""

    def test_initial_state_has_all_required_fields(self):
        """初始状态应包含所有必需字段"""
        state = get_initial_state()

        assert "messages" in state
        assert "current_workflow" in state
        assert "workflow_stage" in state
        assert "artifacts" in state
        assert "plan" in state
        assert "current_stage_id" in state
        assert "pending_clarifications" in state
        assert "consensus_items" in state

    def test_initial_state_values_are_empty(self):
        """初始状态各字段应为预期初始值 - plan 由 LLM 动态生成"""
        state = get_initial_state()

        assert state["messages"] == []
        assert state["current_workflow"] is None
        assert state["workflow_stage"] is None
        # plan 初始为空，由 LLM 在首次响应时动态生成
        assert state["plan"] == []
        assert state["current_stage_id"] is None
        assert state["artifacts"] == {}
        assert state["pending_clarifications"] == []
        assert state["consensus_items"] == []

    def test_state_can_store_messages(self):
        """状态应能存储消息"""
        state = get_initial_state()
        state["messages"].append(HumanMessage(content="测试消息"))
        state["messages"].append(AIMessage(content="AI回复"))

        assert len(state["messages"]) == 2
        assert state["messages"][0].content == "测试消息"
        assert state["messages"][1].content == "AI回复"

    def test_state_can_store_artifacts(self):
        """状态应能存储产出物 (Markdown 格式)"""
        state = get_initial_state()

        markdown_content = """
# 产品设计文档

## 价值主张

```mermaid
mindmap
  root((产品))
    用户价值
    商业价值
```
"""
        state["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR] = markdown_content

        assert ArtifactKeys.PRODUCT_ELEVATOR in state["artifacts"]
        assert "mermaid" in state["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR]

    def test_state_can_store_plan(self):
        """状态应能存储动态计划"""
        state = get_initial_state()

        plan = [
            {"id": "elevator", "name": "电梯演讲", "status": "pending"},
            {"id": "persona", "name": "用户画像", "status": "pending"},
            {"id": "journey", "name": "用户旅程", "status": "pending"},
            {"id": "brd", "name": "BRD文档", "status": "pending"},
        ]
        state["plan"] = plan

        assert len(state["plan"]) == 4
        assert state["plan"][0]["id"] == "elevator"

    def test_state_can_track_current_stage(self):
        """状态应能跟踪当前阶段"""
        state = get_initial_state()
        state["current_stage_id"] = "persona"

        assert state["current_stage_id"] == "persona"


class TestArtifactKeys:
    """测试产出物 Key 常量"""

    def test_product_design_keys_exist(self):
        """产品设计工作流的 Key 应存在"""
        assert hasattr(ArtifactKeys, "PRODUCT_ELEVATOR")
        assert hasattr(ArtifactKeys, "PRODUCT_PERSONA")
        assert hasattr(ArtifactKeys, "PRODUCT_JOURNEY")
        assert hasattr(ArtifactKeys, "PRODUCT_BRD")

    def test_artifact_keys_are_strings(self):
        """所有 Key 应为字符串"""
        assert isinstance(ArtifactKeys.PRODUCT_ELEVATOR, str)
        assert isinstance(ArtifactKeys.PRODUCT_PERSONA, str)
        assert isinstance(ArtifactKeys.PRODUCT_JOURNEY, str)
        assert isinstance(ArtifactKeys.PRODUCT_BRD, str)

    def test_all_keys_are_unique(self):
        """所有 Key 应唯一"""
        keys = [
            ArtifactKeys.PRODUCT_ELEVATOR,
            ArtifactKeys.PRODUCT_PERSONA,
            ArtifactKeys.PRODUCT_JOURNEY,
            ArtifactKeys.PRODUCT_BRD,
        ]
        assert len(keys) == len(set(keys))

    def test_keys_follow_naming_convention(self):
        """Key命名应遵循product_前缀约定"""
        assert ArtifactKeys.PRODUCT_ELEVATOR.startswith("product_")
        assert ArtifactKeys.PRODUCT_PERSONA.startswith("product_")
        assert ArtifactKeys.PRODUCT_JOURNEY.startswith("product_")
        assert ArtifactKeys.PRODUCT_BRD.startswith("product_")


class TestStateMutation:
    """测试状态变更"""

    def test_updating_workflow_stage(self):
        """应能更新工作流阶段"""
        state = get_initial_state()
        state["current_stage_id"] = "elevator"
        state["workflow_stage"] = "elevator"

        assert state["current_stage_id"] == "elevator"
        assert state["workflow_stage"] == "elevator"

    def test_adding_artifacts(self):
        """应能添加产出物"""
        state = get_initial_state()
        state["artifacts"][ArtifactKeys.PRODUCT_ELEVATOR] = "电梯演讲内容"

        assert ArtifactKeys.PRODUCT_ELEVATOR in state["artifacts"]
        assert len(state["artifacts"]) == 1

    def test_updating_plan(self):
        """应能更新计划"""
        state = get_initial_state()
        new_plan = [
            {"id": "elevator", "name": "电梯演讲", "status": "completed"},
            {"id": "persona", "name": "用户画像", "status": "active"},
        ]
        state["plan"] = new_plan

        assert len(state["plan"]) == 2
        assert state["plan"][1]["status"] == "active"

    def test_adding_pending_clarifications(self):
        """应能添加待澄清问题"""
        state = get_initial_state()
        state["pending_clarifications"].append("目标用户是谁？")

        assert len(state["pending_clarifications"]) == 1
        assert "目标用户" in state["pending_clarifications"][0]

    def test_adding_consensus_items(self):
        """应能添加共识项"""
        state = get_initial_state()
        state["consensus_items"].append("目标用户：中小企业")

        assert len(state["consensus_items"]) == 1
        assert "中小企业" in state["consensus_items"][0]
