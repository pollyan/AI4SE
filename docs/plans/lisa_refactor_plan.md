# Lisa 智能体架构迁移计划 (Regex → Structured Output)

**版本**: v1.0
**日期**: 2026-01-18
**目标**: 将 Lisa 智能体的产出物管理从“正则提取”迁移到“结构化工具调用 (Hybrid Tool Calling)”，同时保持前端流式渲染体验。

---

## 1. 核心架构变更

### 1.1 当前状态 (Current)
- **生成**: LLM 在对话中直接输出 Markdown 代码块。
- **提取**: 后端使用 `re.finditer` 扫描回复，提取代码块。
- **流式**: `StreamWriter` 推送原始文本，前端解析。

### 1.2 目标状态 (Target)
- **生成**: LLM 显式调用 `UpdateArtifact` 工具。
- **提取**: 后端监听 `tool_calls`，直接获取结构化参数。
- **流式**: 后端通过 **Streaming Adapter** 实时解包工具参数，模拟文本流推送给前端。

---

## 2. TDD 实施策略 (Strict Red-Green-Refactor)

本次重构将严格遵循 TDD 流程：

1.  **Red**: 先编写测试用例，断言 Agent **会调用工具** (但目前还没实现，所以会失败)。
2.  **Green**: 实现工具定义和绑定，让测试通过。
3.  **Refactor**: 优化流式处理逻辑。

---

## 3. 详细执行阶段

### Phase 1: 基础设施 (Infrastructure)
**目标**: 定义数据结构，准备 Mock 环境。

1.  **定义 Schema (`schemas.py`)**
    - 创建 `UpdateArtifact` Pydantic 模型。
    - 字段: `key` (Enum), `markdown_body` (Str), `metadata` (Dict).
2.  **创建测试基座 (`tests/unit/test_artifact_tool.py`)**
    - 编写测试: 模拟 LLM 输出 ToolCall，验证 Schema 校验逻辑是否正确。

### Phase 2: 核心逻辑切换 (Core Logic)
**目标**: 让 Agent 学会使用工具，而不是直接写 Markdown。

3.  **TDD 测试 (`tests/integration/test_workflow_node.py`)**
    - **Red**: 构造一个 System Prompt，告诉 LLM "要更新文档必须用工具"。输入 "请更新需求文档"，断言 `response.tool_calls` 不为空。
4.  **实现逻辑 (`workflow_test_design.py`)**
    - 使用 `llm.bind_tools([UpdateArtifact])`。
    - 修改 Prompt，移除 "请按 Markdown 格式输出" 的指令，改为 "请调用工具更新文档"。
    - **Green**: 运行测试，确认 Agent 成功发起工具调用。

### Phase 3: 流式适配器 (Streaming Adapter)
**目标**: 解决 Tool Call 导致的前端空白问题。

5.  **TDD 测试 (`tests/unit/test_streaming.py`)**
    - **Red**: 模拟 LLM 的 `stream` 输出 (Chunk 包含 partial tool args)。
    - 断言: `StreamWriter` 能够收到连续的 `progress` 事件，且 content 是逐渐累加的。
6.  **实现 Adapter**
    - 在 `workflow_execution_node` 中引入 `async for chunk in llm.stream()`。
    - 编写 `ToolArgumentParser`，实时解析 JSON 片段。
    - 转发解析出的 `markdown_body` 给 `StreamWriter`。
    - **Green**: 验证流式输出是否连贯。

### Phase 4: 清理与验收 (Cleanup)
7.  **移除旧代码**
    - 删除 `extract_artifact_from_response` 正则函数。
    - 删除旧的 Prompt 模板中关于 Markdown 格式的硬编码说明。
8.  **全链路回归**
    - 运行所有现有测试，确保无回归。

---

## 4. 数据结构定义预览

```python
class UpdateArtifact(BaseModel):
    """更新工作流产出物。当用户确认或有新内容时调用此工具。"""
    
    key: Literal[
        "test_design_requirements",
        "test_design_strategy",
        "test_design_cases"
    ] = Field(description="产出物的唯一标识符")
    
    markdown_body: str = Field(description="完整的文档内容 (Markdown 格式)")
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="可选的元数据，如 risk_level, status 等"
    )
```

## 5. 验收标准
- [ ] 单元测试通过率 100%。
- [ ] 产出物不再通过 Regex 提取，而是通过 ToolCall 触发。
- [ ] 前端看到的流式效果与重构前一致（无长时间 Loading）。
