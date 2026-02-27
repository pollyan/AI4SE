"""
共享 State 模块单元测试 (TDD Red Phase)

测试 shared/state.py 中的 BaseAgentState 和相关工具函数。
"""

from langchain_core.messages import HumanMessage


class TestBaseAgentState:
    """测试 BaseAgentState 基类"""
    
    def test_base_state_has_required_fields(self):
        """BaseAgentState 应包含所有智能体共用的字段"""
        from backend.agents.shared.state import BaseAgentState
        
        # 验证 TypedDict 包含必要的字段
        annotations = BaseAgentState.__annotations__
        
        assert "messages" in annotations
        assert "current_workflow" in annotations
        assert "workflow_stage" in annotations
        assert "plan" in annotations
        assert "current_stage_id" in annotations
        assert "artifacts" in annotations
        assert "pending_clarifications" in annotations
        assert "consensus_items" in annotations


class TestGetBaseInitialState:
    """测试 get_base_initial_state 函数"""
    
    def test_returns_valid_state_dict(self):
        """应返回有效的状态字典"""
        from backend.agents.shared.state import get_base_initial_state
        
        state = get_base_initial_state()
        
        assert isinstance(state, dict)
        assert "messages" in state
        assert "current_workflow" in state
        assert "plan" in state
    
    def test_initial_state_has_correct_defaults(self):
        """初始状态应有正确的默认值"""
        from backend.agents.shared.state import get_base_initial_state
        
        state = get_base_initial_state()
        
        assert state["messages"] == []
        assert state["current_workflow"] is None
        assert state["workflow_stage"] is None
        assert state["plan"] == []
        assert state["current_stage_id"] is None
        assert state["artifacts"] == {}
        assert state["pending_clarifications"] == []
        assert state["consensus_items"] == []


class TestClearWorkflowState:
    """测试 clear_workflow_state 函数"""
    
    def test_clears_workflow_fields_but_keeps_messages(self):
        """应清空工作流字段但保留消息历史"""
        from backend.agents.shared.state import get_base_initial_state, clear_workflow_state
        
        # 准备一个有内容的状态
        state = get_base_initial_state()
        state["messages"] = [HumanMessage(content="hello")]
        state["current_workflow"] = "test_design"
        state["plan"] = [{"id": "step1", "name": "Step 1"}]
        state["artifacts"] = {"key": "value"}
        
        # 清空工作流状态
        cleared = clear_workflow_state(state)
        
        # 消息应保留
        assert len(cleared["messages"]) == 1
        assert cleared["messages"][0].content == "hello"
        
        # 工作流相关字段应清空
        assert cleared["current_workflow"] is None
        assert cleared["plan"] == []
        assert cleared["artifacts"] == {}
    
    def test_returns_new_dict_not_mutate_original(self):
        """应返回新字典，不修改原对象"""
        from backend.agents.shared.state import get_base_initial_state, clear_workflow_state
        
        state = get_base_initial_state()
        state["current_workflow"] = "test_design"
        
        cleared = clear_workflow_state(state)
        
        # 原对象不应被修改
        assert state["current_workflow"] == "test_design"
        assert cleared["current_workflow"] is None


class TestLisaStateCompatibility:
    """测试 Lisa 状态与 BaseAgentState 的兼容性"""
    
    def test_lisa_state_inherits_base_fields(self):
        """LisaState 应包含 BaseAgentState 的所有字段"""
        from backend.agents.shared.state import BaseAgentState
        from backend.agents.lisa.state import LisaState
        
        base_fields = set(BaseAgentState.__annotations__.keys())
        lisa_fields = set(LisaState.__annotations__.keys())
        
        # Lisa 应包含所有 base 字段
        assert base_fields.issubset(lisa_fields)
    
    def test_lisa_get_initial_state_compatible(self):
        """Lisa 的 get_initial_state 应与 base 兼容"""
        from backend.agents.shared.state import get_base_initial_state
        from backend.agents.lisa.state import get_initial_state
        
        base_state = get_base_initial_state()
        lisa_state = get_initial_state()
        
        # Lisa 状态应包含所有 base 字段
        for key in base_state.keys():
            assert key in lisa_state




