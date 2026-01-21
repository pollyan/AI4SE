# AI-Agents 测试覆盖与技术债修复实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 补全 AI-Agents 后端所有关键组件的测试覆盖，并修复 `current_workflow` vs `workflow_type` 字段不一致的技术债。

**Architecture:** 采用 TDD 方式，先编写失败的测试，再修复代码使测试通过。按 Critical -> High -> Medium 优先级顺序执行。技术债修复需要同时修改 `reasoning_node.py` 和相关测试文件。

**Tech Stack:** Python 3.11+, pytest, unittest.mock, LangGraph, LangChain

---

## Phase 1: 技术债修复 (Critical)

### Task 1: 修复 current_workflow vs workflow_type 字段不一致

**问题分析:**
- `intent_router_node.py` 设置 `current_workflow` 字段
- `reasoning_node.py` 读取 `workflow_type` 字段 (默认 "test_design")
- 导致 `requirement_review` 工作流永远无法正确触发

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py:36`
- Modify: `tools/ai-agents/backend/tests/test_reasoning_node.py:20`
- Modify: `tools/ai-agents/backend/tests/test_artifact_node.py:20`

**Step 1: 查看当前 reasoning_node.py 中的 workflow_type 使用**

Run: `grep -n "workflow_type" tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py`
Expected: 找到多处 `workflow_type` 引用

**Step 2: 修改 reasoning_node.py 使用 current_workflow**

将 `reasoning_node.py` 中所有 `workflow_type` 替换为 `current_workflow`:

```python
# Line ~36: 修改前
workflow_type = state.get("workflow_type", "test_design")

# Line ~36: 修改后
workflow_type = state.get("current_workflow", "test_design")
```

同样修改其他引用位置 (约 Line 148-152):

```python
# 修改前
state_updates["workflow_type"] = workflow_type

# 修改后
state_updates["current_workflow"] = workflow_type
```

**Step 3: 更新 test_reasoning_node.py 的 mock_state fixture**

```python
# 修改前
@pytest.fixture
def mock_state():
    return {
        "messages": [],
        "artifacts": {"test_design_requirements": "existing content"},
        "current_stage_id": "clarify",
        "plan": [{"id": "clarify", "name": "Clarify"}]
    }

# 修改后 (添加 current_workflow)
@pytest.fixture
def mock_state():
    return {
        "messages": [],
        "artifacts": {"test_design_requirements": "existing content"},
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
        "plan": [{"id": "clarify", "name": "Clarify"}]
    }
```

**Step 4: 更新 test_artifact_node.py 的 mock_state fixture**

```python
# 修改前
@pytest.fixture
def mock_state():
    return {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "workflow_type": "test_design"
    }

# 修改后
@pytest.fixture
def mock_state():
    return {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "current_workflow": "test_design"
    }
```

**Step 5: 运行测试验证修复**

Run: `pytest tools/ai-agents/backend/tests/test_reasoning_node.py tools/ai-agents/backend/tests/test_artifact_node.py -v`
Expected: 所有测试 PASS

**Step 6: 提交修复**

```bash
git add tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py
git add tools/ai-agents/backend/tests/test_reasoning_node.py
git add tools/ai-agents/backend/tests/test_artifact_node.py
git commit -m "fix(agents): unify workflow field name to current_workflow

- Replace workflow_type with current_workflow in reasoning_node.py
- Update test fixtures to use current_workflow
- Fixes requirement_review workflow not being triggered correctly"
```

---

## Phase 2: Critical 测试补充

### Task 2: clarify_intent_node 完整测试

**Files:**
- Create: `tools/ai-agents/backend/tests/agents/lisa/nodes/test_clarify_intent_node.py`
- Reference: `tools/ai-agents/backend/agents/lisa/nodes/clarify_intent.py`

**Step 1: 创建测试目录结构**

Run: `mkdir -p tools/ai-agents/backend/tests/agents/lisa/nodes && touch tools/ai-agents/backend/tests/agents/lisa/nodes/__init__.py`

**Step 2: 编写 test_clarify_intent_node.py**

```python
"""
clarify_intent_node 单元测试

测试意图澄清节点的所有场景：
- 使用动态澄清问题
- 使用默认消息
- 消息历史更新
- 状态结构完整性
"""

import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage

from backend.agents.lisa.nodes.clarify_intent import clarify_intent_node
from backend.agents.lisa.prompts import CLARIFY_INTENT_MESSAGE


@pytest.fixture
def mock_llm():
    """Mock LLM (clarify_intent_node 不使用 LLM，但接口需要)"""
    return MagicMock()


@pytest.fixture
def base_state():
    """基础状态 fixture"""
    return {
        "messages": [HumanMessage(content="你好")],
        "artifacts": {},
        "current_stage_id": None,
        "current_workflow": None,
    }


@pytest.mark.unit
class TestClarifyIntentNode:
    """clarify_intent_node 测试套件"""

    def test_uses_dynamic_question_when_present(self, mock_llm, base_state):
        """当 state 中有 clarification 字段时，使用动态问题"""
        # Arrange
        dynamic_question = "请问您是想进行测试设计还是需求评审？"
        base_state["clarification"] = dynamic_question

        # Act
        result = clarify_intent_node(base_state, mock_llm)

        # Assert
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert last_message.content == dynamic_question

    def test_uses_default_message_when_no_clarification(self, mock_llm, base_state):
        """当 state 中没有 clarification 字段时，使用默认消息"""
        # Arrange - 确保没有 clarification 字段
        assert "clarification" not in base_state

        # Act
        result = clarify_intent_node(base_state, mock_llm)

        # Assert
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert last_message.content == CLARIFY_INTENT_MESSAGE

    def test_uses_default_when_clarification_is_none(self, mock_llm, base_state):
        """当 clarification 字段为 None 时，使用默认消息"""
        # Arrange
        base_state["clarification"] = None

        # Act
        result = clarify_intent_node(base_state, mock_llm)

        # Assert
        last_message = result["messages"][-1]
        assert last_message.content == CLARIFY_INTENT_MESSAGE

    def test_uses_default_when_clarification_is_empty(self, mock_llm, base_state):
        """当 clarification 字段为空字符串时，使用默认消息"""
        # Arrange
        base_state["clarification"] = ""

        # Act
        result = clarify_intent_node(base_state, mock_llm)

        # Assert
        last_message = result["messages"][-1]
        assert last_message.content == CLARIFY_INTENT_MESSAGE

    def test_appends_message_to_history(self, mock_llm, base_state):
        """验证澄清消息正确追加到历史记录"""
        # Arrange
        original_count = len(base_state["messages"])

        # Act
        result = clarify_intent_node(base_state, mock_llm)

        # Assert
        assert len(result["messages"]) == original_count + 1
        # 原始消息应该保持不变
        assert result["messages"][0].content == "你好"

    def test_preserves_existing_state_fields(self, mock_llm, base_state):
        """验证其他状态字段被保留"""
        # Arrange
        base_state["artifacts"] = {"some_key": "some_value"}
        base_state["current_stage_id"] = "clarify"

        # Act
        result = clarify_intent_node(base_state, mock_llm)

        # Assert
        assert result["artifacts"] == {"some_key": "some_value"}
        assert result["current_stage_id"] == "clarify"

    def test_handles_empty_messages_list(self, mock_llm):
        """处理空消息列表的情况"""
        # Arrange
        state = {"messages": []}

        # Act
        result = clarify_intent_node(state, mock_llm)

        # Assert
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)

    def test_handles_missing_messages_field(self, mock_llm):
        """处理缺少 messages 字段的情况"""
        # Arrange
        state = {}

        # Act
        result = clarify_intent_node(state, mock_llm)

        # Assert
        assert "messages" in result
        assert len(result["messages"]) == 1
```

**Step 3: 运行测试验证失败 (TDD Red)**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/nodes/test_clarify_intent_node.py -v`
Expected: 所有测试应该 PASS (因为代码已存在，这是补充测试)

**Step 4: 提交测试**

```bash
git add tools/ai-agents/backend/tests/agents/lisa/nodes/
git commit -m "test(agents): add comprehensive tests for clarify_intent_node

- Test dynamic question usage when clarification field present
- Test fallback to default message
- Test message history preservation
- Test edge cases (empty, None, missing fields)"
```

---

### Task 3: graph.py 编译与结构测试

**Files:**
- Create: `tools/ai-agents/backend/tests/agents/lisa/test_graph.py`
- Reference: `tools/ai-agents/backend/agents/lisa/graph.py`

**Step 1: 编写 test_graph.py**

```python
"""
Lisa Graph 单元测试

测试 LangGraph 图的构建、节点和边的正确性。
"""

import pytest
from unittest.mock import MagicMock, patch

from backend.agents.lisa.graph import create_lisa_graph, get_graph_initial_state
from backend.agents.lisa.state import LisaState


@pytest.fixture
def mock_model_config():
    """Mock 模型配置"""
    return {
        "model_name": "gpt-4",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key"
    }


@pytest.mark.unit
class TestCreateLisaGraph:
    """create_lisa_graph 测试套件"""

    @patch("backend.agents.lisa.graph.create_llm_from_config")
    @patch("backend.agents.lisa.graph.get_checkpointer")
    def test_graph_compilation_succeeds(self, mock_checkpointer, mock_llm, mock_model_config):
        """验证图能成功编译"""
        # Arrange
        mock_llm.return_value = MagicMock()
        mock_checkpointer.return_value = MagicMock()

        # Act
        graph = create_lisa_graph(mock_model_config)

        # Assert
        assert graph is not None
        # CompiledStateGraph 有 invoke 方法
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "stream")

    @patch("backend.agents.lisa.graph.create_llm_from_config")
    @patch("backend.agents.lisa.graph.get_checkpointer")
    def test_graph_has_all_required_nodes(self, mock_checkpointer, mock_llm, mock_model_config):
        """验证图包含所有必需节点"""
        # Arrange
        mock_llm.return_value = MagicMock()
        mock_checkpointer.return_value = MagicMock()

        # Act
        graph = create_lisa_graph(mock_model_config)

        # Assert - 检查节点存在
        # CompiledGraph 的节点可以通过 graph.nodes 访问
        node_names = list(graph.nodes.keys())
        
        required_nodes = ["intent_router", "clarify_intent", "reasoning_node", "artifact_node"]
        for node in required_nodes:
            assert node in node_names, f"Missing required node: {node}"

    @patch("backend.agents.lisa.graph.create_llm_from_config")
    @patch("backend.agents.lisa.graph.get_checkpointer")
    def test_graph_uses_checkpointer(self, mock_checkpointer, mock_llm, mock_model_config):
        """验证图使用了 checkpointer"""
        # Arrange
        mock_llm.return_value = MagicMock()
        mock_cp = MagicMock()
        mock_checkpointer.return_value = mock_cp

        # Act
        create_lisa_graph(mock_model_config)

        # Assert
        mock_checkpointer.assert_called_once()

    @patch("backend.agents.lisa.graph.create_llm_from_config")
    @patch("backend.agents.lisa.graph.get_checkpointer")
    def test_graph_creates_llm_with_config(self, mock_checkpointer, mock_llm, mock_model_config):
        """验证图使用配置创建 LLM"""
        # Arrange
        mock_llm.return_value = MagicMock()
        mock_checkpointer.return_value = MagicMock()

        # Act
        create_lisa_graph(mock_model_config)

        # Assert
        mock_llm.assert_called_once_with(mock_model_config)


@pytest.mark.unit
class TestGetGraphInitialState:
    """get_graph_initial_state 测试套件"""

    def test_returns_valid_initial_state(self):
        """验证返回有效的初始状态"""
        # Act
        state = get_graph_initial_state()

        # Assert
        assert isinstance(state, dict)
        assert "messages" in state
        assert isinstance(state["messages"], list)

    def test_initial_state_has_empty_messages(self):
        """验证初始状态的消息列表为空"""
        # Act
        state = get_graph_initial_state()

        # Assert
        assert len(state["messages"]) == 0

    def test_initial_state_has_empty_artifacts(self):
        """验证初始状态的 artifacts 为空"""
        # Act
        state = get_graph_initial_state()

        # Assert
        assert "artifacts" in state
        assert state["artifacts"] == {}
```

**Step 2: 运行测试**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/test_graph.py -v`
Expected: 所有测试 PASS

**Step 3: 提交测试**

```bash
git add tools/ai-agents/backend/tests/agents/lisa/test_graph.py
git commit -m "test(agents): add graph compilation and structure tests

- Verify graph compiles successfully
- Verify all required nodes exist
- Verify checkpointer integration
- Verify initial state structure"
```

---

## Phase 3: High 优先级测试

### Task 4: intent_router_node 边缘场景测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/agents/lisa/test_intent_router_node.py`

**Step 1: 扩展现有测试文件**

```python
"""
intent_router_node 完整测试套件

测试意图路由的所有场景：
- 明确意图路由
- 粘性工作流
- 高/低置信度处理
- 异常处理
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from backend.agents.lisa.nodes.intent_router import intent_router_node
from backend.agents.lisa.routing.hybrid_router import RoutingDecision


@pytest.fixture
def mock_llm():
    return MagicMock()


@pytest.mark.unit
class TestIntentRouterNode:
    """intent_router_node 测试套件"""

    def test_sticky_workflow_on_unknown_intent(self, mock_llm):
        """当在工作流中遇到不明意图时，应默认继续当前工作流（粘性）"""
        # Arrange
        state = {
            "messages": [HumanMessage(content="好的")],
            "current_workflow": "test_design",
            "artifacts": {}
        }

        with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
            mock_router = MagicMock()
            mock_get_router.return_value = mock_router
            mock_router.route.return_value = RoutingDecision(
                intent=None,
                confidence=0.0,
                source="llm",
                latency_ms=100,
                reason="Unclear"
            )

            # Act
            command = intent_router_node(state, mock_llm)

            # Assert
            assert command.goto == "reasoning_node"

    def test_route_to_test_design_on_explicit_intent(self, mock_llm):
        """明确的测试设计意图应路由到 reasoning_node"""
        # Arrange
        state = {
            "messages": [HumanMessage(content="我想做测试设计")],
            "current_workflow": None,
            "artifacts": {}
        }

        with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
            mock_router = MagicMock()
            mock_get_router.return_value = mock_router
            mock_router.route.return_value = RoutingDecision(
                intent="START_TEST_DESIGN",
                confidence=0.95,
                source="semantic",
                latency_ms=50,
                reason="High confidence match"
            )

            # Act
            command = intent_router_node(state, mock_llm)

            # Assert
            assert isinstance(command, Command)
            assert command.goto == "reasoning_node"
            assert command.update.get("current_workflow") == "test_design"

    def test_route_to_requirement_review_on_explicit_intent(self, mock_llm):
        """明确的需求评审意图应路由到 reasoning_node 并设置 requirement_review"""
        # Arrange
        state = {
            "messages": [HumanMessage(content="帮我评审这个需求")],
            "current_workflow": None,
            "artifacts": {}
        }

        with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
            mock_router = MagicMock()
            mock_get_router.return_value = mock_router
            mock_router.route.return_value = RoutingDecision(
                intent="START_REQUIREMENT_REVIEW",
                confidence=0.92,
                source="semantic",
                latency_ms=50,
                reason="Requirement review detected"
            )

            # Act
            command = intent_router_node(state, mock_llm)

            # Assert
            assert isinstance(command, Command)
            assert command.goto == "reasoning_node"
            assert command.update.get("current_workflow") == "requirement_review"

    def test_continue_workflow_without_current_goes_to_clarify(self, mock_llm):
        """CONTINUE_WORKFLOW 意图但没有当前工作流时，应请求澄清"""
        # Arrange
        state = {
            "messages": [HumanMessage(content="继续")],
            "current_workflow": None,
            "artifacts": {}
        }

        with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
            mock_router = MagicMock()
            mock_get_router.return_value = mock_router
            mock_router.route.return_value = RoutingDecision(
                intent="CONTINUE_WORKFLOW",
                confidence=0.85,
                source="semantic",
                latency_ms=50,
                reason="Continue detected"
            )

            # Act
            command = intent_router_node(state, mock_llm)

            # Assert
            assert command.goto == "clarify_intent"

    def test_exception_handling_returns_clarify_intent(self, mock_llm):
        """路由异常时应降级到 clarify_intent"""
        # Arrange
        state = {
            "messages": [HumanMessage(content="测试")],
            "current_workflow": None,
            "artifacts": {}
        }

        with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
            mock_router = MagicMock()
            mock_get_router.return_value = mock_router
            mock_router.route.side_effect = Exception("Router failed")

            # Act
            command = intent_router_node(state, mock_llm)

            # Assert
            assert command.goto == "clarify_intent"

    def test_low_confidence_with_no_workflow_goes_to_clarify(self, mock_llm):
        """低置信度且无当前工作流时，应请求澄清"""
        # Arrange
        state = {
            "messages": [HumanMessage(content="嗯")],
            "current_workflow": None,
            "artifacts": {}
        }

        with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
            mock_router = MagicMock()
            mock_get_router.return_value = mock_router
            mock_router.route.return_value = RoutingDecision(
                intent=None,
                confidence=0.1,
                source="llm",
                latency_ms=100,
                reason="Very unclear"
            )

            # Act
            command = intent_router_node(state, mock_llm)

            # Assert
            assert command.goto == "clarify_intent"
```

**Step 2: 运行测试**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/test_intent_router_node.py -v`
Expected: 所有测试 PASS

**Step 3: 提交测试**

```bash
git add tools/ai-agents/backend/tests/agents/lisa/test_intent_router_node.py
git commit -m "test(agents): expand intent_router_node tests

- Add tests for explicit intent routing
- Add tests for requirement_review workflow
- Add exception handling test
- Add low confidence scenario test"
```

---

### Task 5: reasoning_node 边缘场景测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/test_reasoning_node.py`

**Step 1: 扩展现有测试文件**

在现有测试文件末尾添加以下测试：

```python
@patch("backend.agents.lisa.nodes.reasoning_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_handles_llm_error(mock_prompt, mock_process, mock_writer, mock_llm):
    """Test graceful handling when LLM call fails"""
    
    state = {
        "messages": [],
        "artifacts": {"test_design_requirements": "content"},
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
        "plan": [{"id": "clarify", "name": "Clarify"}]
    }
    
    # Mock LLM failure
    mock_process.side_effect = Exception("LLM connection failed")
    
    command = reasoning_node(state, mock_llm)
    
    assert isinstance(command, Command)
    assert command.goto == "__end__"
    # Should contain error message
    assert len(command.update["messages"]) > 0
    assert "错误" in command.update["messages"][-1].content or "error" in command.update["messages"][-1].content.lower()


@patch("backend.agents.lisa.nodes.reasoning_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_stage_transition(mock_prompt, mock_process, mock_writer, mock_llm, mock_state):
    """Test that request_transition_to updates current_stage_id"""
    
    # Mock LLM response with transition request
    mock_process.return_value = ReasoningResponse(
        thought="需求已确认，准备进入策略阶段。",
        should_update_artifact=False,
        request_transition_to="strategy"
    )
    
    command = reasoning_node(mock_state, mock_llm)
    
    assert isinstance(command, Command)
    # Stage should be updated
    assert command.update.get("current_stage_id") == "strategy"


@patch("backend.agents.lisa.nodes.reasoning_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_requirement_review_prompt")
def test_reasoning_node_requirement_review_workflow(mock_prompt, mock_process, mock_writer, mock_llm):
    """Test that requirement_review workflow uses correct prompt builder"""
    
    state = {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "current_workflow": "requirement_review",
        "plan": [{"id": "clarify", "name": "Clarify"}]
    }
    
    mock_process.return_value = ReasoningResponse(
        thought="评审需求中...",
        should_update_artifact=False
    )
    
    reasoning_node(state, mock_llm)
    
    # Verify requirement_review prompt builder was called
    mock_prompt.assert_called_once()


@patch("backend.agents.lisa.nodes.reasoning_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_empty_messages(mock_prompt, mock_process, mock_writer, mock_llm):
    """Test handling of empty messages list"""
    
    state = {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "current_workflow": "test_design"
    }
    
    mock_process.return_value = ReasoningResponse(
        thought="Welcome!",
        should_update_artifact=False
    )
    
    command = reasoning_node(state, mock_llm)
    
    assert isinstance(command, Command)
    # Should still work without errors
    assert len(command.update["messages"]) > 0
```

**Step 2: 添加必要的导入**

在文件顶部添加 `build_requirement_review_prompt` 的 patch 路径（如果需要）

**Step 3: 运行测试**

Run: `pytest tools/ai-agents/backend/tests/test_reasoning_node.py -v`
Expected: 所有测试 PASS

**Step 4: 提交测试**

```bash
git add tools/ai-agents/backend/tests/test_reasoning_node.py
git commit -m "test(agents): add reasoning_node edge case tests

- Add LLM error handling test
- Add stage transition test (request_transition_to)
- Add requirement_review workflow test
- Add empty messages handling test"
```

---

## Phase 4: Medium 优先级测试

### Task 6: stream_utils.py 单元测试

**Files:**
- Create: `tools/ai-agents/backend/tests/agents/lisa/test_stream_utils.py`
- Reference: `tools/ai-agents/backend/agents/lisa/stream_utils.py`

**Step 1: 编写 test_stream_utils.py**

```python
"""
stream_utils 单元测试

测试流式处理工具函数。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.agents.lisa.stream_utils import get_stage_index


@pytest.mark.unit
class TestStreamUtils:
    """stream_utils 测试套件"""

    def test_get_stage_index_returns_correct_index(self):
        """验证阶段索引计算正确"""
        # Arrange
        plan = [
            {"id": "clarify", "name": "Clarify"},
            {"id": "strategy", "name": "Strategy"},
            {"id": "cases", "name": "Cases"}
        ]

        # Act & Assert
        assert get_stage_index("clarify", plan) == 0
        assert get_stage_index("strategy", plan) == 1
        assert get_stage_index("cases", plan) == 2

    def test_get_stage_index_returns_0_for_unknown_stage(self):
        """未知阶段返回 0"""
        # Arrange
        plan = [{"id": "clarify", "name": "Clarify"}]

        # Act
        result = get_stage_index("unknown", plan)

        # Assert
        assert result == 0

    def test_get_stage_index_handles_empty_plan(self):
        """空 plan 返回 0"""
        # Act
        result = get_stage_index("any", [])

        # Assert
        assert result == 0

    def test_get_stage_index_handles_none_plan(self):
        """None plan 返回 0"""
        # Act
        result = get_stage_index("any", None)

        # Assert
        assert result == 0
```

**Step 2: 运行测试**

Run: `pytest tools/ai-agents/backend/tests/agents/lisa/test_stream_utils.py -v`
Expected: 所有测试 PASS

**Step 3: 提交测试**

```bash
git add tools/ai-agents/backend/tests/agents/lisa/test_stream_utils.py
git commit -m "test(agents): add stream_utils unit tests

- Test get_stage_index with valid inputs
- Test edge cases (unknown stage, empty plan, None)"
```

---

### Task 7: artifact_node 边缘场景测试

**Files:**
- Modify: `tools/ai-agents/backend/tests/test_artifact_node.py`

**Step 1: 在现有测试文件末尾添加**

```python
@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_handles_llm_error(mock_writer_getter, mock_llm):
    """Test graceful handling when LLM call fails"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    state = {
        "messages": [],
        "artifacts": {"test_key": "existing"},
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
        "plan": [{"id": "clarify", "name": "Clarify", "status": "active"}],
        "artifact_templates": [
            {"key": "test_key", "stage": "clarify", "outline": "# Template"}
        ]
    }

    # Mock LLM failure
    bound_llm.invoke.side_effect = Exception("LLM failed")

    # Act - should not raise
    try:
        result = artifact_node(state, original_llm)
        # If it doesn't raise, verify it returns something sensible
        assert "artifacts" in result
    except Exception as e:
        # If it raises, that's also acceptable but should be logged
        pytest.fail(f"artifact_node should handle LLM errors gracefully, got: {e}")


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_handles_multiple_tool_calls(mock_writer_getter, mock_llm):
    """Test handling of multiple tool calls in single response"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    state = {
        "messages": [],
        "artifacts": {"key1": "content1"},
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
        "plan": [{"id": "clarify", "name": "Clarify", "status": "active"}],
        "artifact_templates": [
            {"key": "key1", "stage": "clarify", "outline": "# T1"},
            {"key": "key2", "stage": "clarify", "outline": "# T2"}
        ]
    }

    # Mock multiple tool calls
    mock_response = MagicMock()
    mock_response.tool_calls = [
        {"name": "update_artifact", "args": {"key": "key1", "markdown_body": "# Updated 1"}, "id": "1"},
        {"name": "update_artifact", "args": {"key": "key2", "markdown_body": "# Updated 2"}, "id": "2"}
    ]
    mock_response.content = ""
    bound_llm.invoke.return_value = mock_response

    # Act
    result = artifact_node(state, original_llm)

    # Assert - both artifacts should be updated
    assert result["artifacts"]["key1"] == "# Updated 1"
    assert result["artifacts"]["key2"] == "# Updated 2"


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_ignores_invalid_key(mock_writer_getter, mock_llm):
    """Test that invalid artifact keys are handled gracefully"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    state = {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
        "plan": [{"id": "clarify", "name": "Clarify", "status": "active"}],
        "artifact_templates": []  # No templates
    }

    # Mock tool call with unknown key
    mock_response = MagicMock()
    mock_response.tool_calls = [
        {"name": "update_artifact", "args": {"key": "unknown_key", "markdown_body": "# Content"}, "id": "1"}
    ]
    mock_response.content = ""
    bound_llm.invoke.return_value = mock_response

    # Act - should not raise
    result = artifact_node(state, original_llm)

    # Assert - unknown key should still be added (or ignored based on implementation)
    # At minimum, should not crash
    assert "artifacts" in result
```

**Step 2: 运行测试**

Run: `pytest tools/ai-agents/backend/tests/test_artifact_node.py -v`
Expected: 测试 PASS 或揭示需要修复的边缘情况

**Step 3: 提交测试**

```bash
git add tools/ai-agents/backend/tests/test_artifact_node.py
git commit -m "test(agents): add artifact_node edge case tests

- Add LLM error handling test
- Add multiple tool calls test
- Add invalid key handling test"
```

---

## Phase 5: 清理技术债

### Task 8: 删除废弃的 process_workflow_stream

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/stream_utils.py`

**Step 1: 检查 process_workflow_stream 是否被引用**

Run: `grep -r "process_workflow_stream" tools/ai-agents/backend --include="*.py"`
Expected: 仅在 stream_utils.py 中定义，无其他引用

**Step 2: 如果无引用，删除该函数**

删除 `stream_utils.py` 中标记为废弃的 `process_workflow_stream` 函数。

**Step 3: 运行测试确保无破坏**

Run: `pytest tools/ai-agents/backend/tests/ -v`
Expected: 所有测试 PASS

**Step 4: 提交清理**

```bash
git add tools/ai-agents/backend/agents/lisa/stream_utils.py
git commit -m "chore(agents): remove deprecated process_workflow_stream

- Function was marked deprecated and had no references
- Cleanup reduces code maintenance burden"
```

---

## Phase 6: 最终验证

### Task 9: 运行完整测试套件

**Step 1: 运行所有 ai-agents 测试**

Run: `pytest tools/ai-agents/backend/tests/ -v --tb=short`
Expected: 所有测试 PASS

**Step 2: 运行 lint 检查**

Run: `flake8 tools/ai-agents/backend --select=E9,F63,F7,F82 --show-source`
Expected: 无错误

**Step 3: 最终提交总结**

```bash
git log --oneline -10
```

---

## 总结

| Phase | 任务数 | 预计工时 |
|-------|--------|----------|
| Phase 1: 技术债修复 | 1 | 1h |
| Phase 2: Critical 测试 | 2 | 3h |
| Phase 3: High 测试 | 2 | 3h |
| Phase 4: Medium 测试 | 2 | 2h |
| Phase 5: 清理 | 1 | 0.5h |
| Phase 6: 验证 | 1 | 0.5h |
| **总计** | **9** | **~10h** |

---

**Plan complete and saved to `docs/plans/2026-01-21-ai-agents-test-coverage-techdebt.md`.**
