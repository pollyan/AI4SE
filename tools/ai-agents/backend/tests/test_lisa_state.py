"""
Lisa State 单元测试

测试 LisaState 类型定义和相关函数。
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from backend.agents.lisa.state import (
    LisaState,
    get_initial_state,
    clear_workflow_state,
    ArtifactKeys,
)


class TestLisaStateDefinition:
    """测试 LisaState 类型定义"""
    
    def test_initial_state_has_all_required_fields(self):
        """初始状态应包含所有必需字段"""
        state = get_initial_state()
        
        assert "messages" in state
        assert "current_workflow" in state
        assert "workflow_stage" in state
        assert "artifacts" in state
        assert "pending_clarifications" in state
        assert "consensus_items" in state
    
    def test_initial_state_values_are_empty(self):
        """初始状态各字段应为预期初始值 - plan 由 LLM 动态生成"""
        state = get_initial_state()
        
        assert state["messages"] == []
        assert state["current_workflow"] is None
        # workflow_stage 和 current_stage_id 现在初始化为 None
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
# 需求分析文档

## 功能概述

```mermaid
mindmap
  root((需求))
    功能A
    功能B
```
"""
        state["artifacts"][ArtifactKeys.TEST_DESIGN_REQUIREMENTS] = markdown_content
        
        assert ArtifactKeys.TEST_DESIGN_REQUIREMENTS in state["artifacts"]
        assert "mermaid" in state["artifacts"][ArtifactKeys.TEST_DESIGN_REQUIREMENTS]


class TestClearWorkflowState:
    """测试工作流状态清空函数"""
    
    def test_clear_preserves_messages(self):
        """清空工作流状态应保留消息历史"""
        state = get_initial_state()
        state["messages"].append(HumanMessage(content="历史消息"))
        state["current_workflow"] = "test_design"
        state["artifacts"]["test_design_requirements"] = "内容"
        
        cleared = clear_workflow_state(state)
        
        # 消息应保留
        assert len(cleared["messages"]) == 1
        assert cleared["messages"][0].content == "历史消息"
    
    def test_clear_removes_workflow_data(self):
        """清空工作流状态应移除工作流相关数据"""
        state = get_initial_state()
        state["current_workflow"] = "test_design"
        state["workflow_stage"] = "clarify"
        state["artifacts"]["test_design_requirements"] = "内容"
        state["pending_clarifications"] = ["问题1"]
        state["consensus_items"] = [{"question": "Q", "answer": "A"}]
        
        cleared = clear_workflow_state(state)
        
        assert cleared["current_workflow"] is None
        assert cleared["workflow_stage"] is None
        assert cleared["artifacts"] == {}
        assert cleared["pending_clarifications"] == []
        assert cleared["consensus_items"] == []
    
    def test_clear_does_not_mutate_original(self):
        """清空函数不应修改原状态"""
        state = get_initial_state()
        state["current_workflow"] = "test_design"
        state["artifacts"]["key"] = "value"
        
        cleared = clear_workflow_state(state)
        
        # 原状态不变
        assert state["current_workflow"] == "test_design"
        assert state["artifacts"]["key"] == "value"
        # 新状态已清空
        assert cleared["current_workflow"] is None


class TestArtifactKeys:
    """测试产出物 Key 常量"""
    
    def test_test_design_keys_have_semantic_prefix(self):
        """测试设计工作流的 Key 应有语义前缀"""
        assert ArtifactKeys.TEST_DESIGN_REQUIREMENTS.startswith("test_design_")
        assert ArtifactKeys.TEST_DESIGN_STRATEGY.startswith("test_design_")
        assert ArtifactKeys.TEST_DESIGN_CASES.startswith("test_design_")
        assert ArtifactKeys.TEST_DESIGN_FINAL.startswith("test_design_")
    
    def test_all_keys_are_unique(self):
        """所有 Key 应唯一"""
        keys = [
            ArtifactKeys.TEST_DESIGN_REQUIREMENTS,
            ArtifactKeys.TEST_DESIGN_STRATEGY,
            ArtifactKeys.TEST_DESIGN_CASES,
            ArtifactKeys.TEST_DESIGN_FINAL,
        ]
        assert len(keys) == len(set(keys))
