# Lisa 智能体架构审查与最佳实践差距分析报告

**日期**: 2026-01-17
**审查对象**: `tools/ai-agents/backend/agents/lisa`
**审查目标**: 对照 LangChain 1.x / LangGraph 最佳实践，评估架构合理性与改进空间。

## 1. 总体评价

Lisa 智能体目前采用了 **LangGraph StateGraph** 架构，这是符合当前 AI 工程化趋势的先进模式。其核心的状态管理、路由分发、流式响应机制均设计得当，符合现代 Agent 的标准。

然而，在 **产出物管理 (Artifact Management)** 这一具体环节，目前采用了 "Prompt + Regex Parsing" 的传统模式，这与 LangChain 1.x 推崇的 "Structured Output" 最佳实践存在差距，是系统稳定性的潜在短板。

## 2. 现状分析 (Current State)

### 2.1 架构亮点
- **LangGraph 状态机**: 正确使用了 `StateGraph`、`TypedDict` 和 `add_messages` reducer，状态流转清晰。
- **流式响应**: 通过 `StreamWriter` 实现了细腻的进度推送，用户体验优秀。
- **模块化**: 节点 (`nodes/`)、提示词 (`prompts/`)、状态 (`state.py`) 职责分离清晰。

### 2.2 核心问题：产出物生成机制
目前 `workflow_test_design.py` 中的产出物提取逻辑如下：

1. **隐式生成**: 在 System Prompt 中注入 Markdown 模板，要求 LLM 在对话中"顺便"生成文档。
2. **正则提取**: 使用正则表达式 (`re.finditer`) 从 LLM 的自然语言回复中提取 ` ```markdown ... ``` ` 代码块。
3. **脆弱性**:
   - 如果 LLM 忘记写闭合的 ` ``` `，提取失败。
   - 如果 LLM 在代码块前加了无关字符，提取可能截断。
   - 无法强制校验产出物内部结构的完整性（例如：无法确保"风险评估"表格一定包含"影响等级"列）。

## 3. 最佳实践差距分析 (Gap Analysis)

| 维度 | Lisa 当前实现 (Current) | LangChain 1.x 最佳实践 (Target) | 风险/影响 |
|------|-------------------------|---------------------------------|-----------|
| **生成方式** | **Text Parsing (Regex)**<br>依赖 LLM 遵守文本格式约定。 | **Structured Output / Tool Calling**<br>使用 `llm.with_structured_output(Schema)`。 | 解析失败率高，不仅导致产出物丢失，还可能让用户看到未渲染的 Markdown 源码。 |
| **类型安全** | **String (Dict[str, str])**<br>产出物仅被视为文本块。 | **Pydantic Model**<br>产出物由类定义，具备字段级验证。 | 无法在 Runtime 拦截不合规的产出物，错误会一直传递到前端展示层。 |
| **交互模式** | **Chat-based**<br>生成文档和聊天混在一起。 | **Action-based**<br>生成文档是一个显式的 Tool Call 动作。 | LLM 容易混淆"解释文档"和"生成文档"，导致意图漂移。 |

## 4. 改进建议 (Recommendations)

建议将 Lisa 的产出物管理逐步迁移到 **Structured Output** 模式。

### 4.1 推荐方案：混合模式 (Hybrid Tool Calling)

保留聊天的灵活性，但将"保存产出物"这一动作封装为工具。

**重构前 (Prompt 驱动):**
```text
(System): 请按照以下格式生成文档：```markdown...```
(AI): 好的，这是文档：
```markdown
# 需求分析...
```
```

**重构后 (Tool 驱动):**
```python
class UpdateArtifact(BaseModel):
    """更新当前阶段的产出物文档"""
    content: str = Field(description="完整的 Markdown 文档内容")
    key: str = Field(description="产出物 ID")

# 绑定工具
llm_with_tools = llm.bind_tools([UpdateArtifact])
```

**优势**:
1. **准确性**: LLM 必须调用 `UpdateArtifact` 才能修改文档，意图极其明确。
2. **稳定性**: 不再依赖正则表达式去"猜"哪一段是文档。
3. **前端友好**: `ToolCall` 事件可以直接映射为前端的"正在保存..."状态。

### 4.2 迁移路线图

1. **Phase 1 (Schema 定义)**: 为每个阶段的产出物定义 Pydantic Model（目前全是 Markdown 字符串，可以先定义一个通用的 `MarkdownArtifact`）。
2. **Phase 2 (节点重构)**: 修改 `workflow_execution_node`，不再使用 `extract_artifact_from_response`，而是检查 `response.tool_calls`。
3. **Phase 3 (前端适配)**: 确保前端能处理新的 Tool Call 产生的状态更新（目前通过 StreamWriter 推送，可以在后端做适配层，保持前端协议不变）。

## 5. 结论

Lisa 的地基非常稳固。通过采纳 **Structured Output**，我们可以将其从一个"聪明的聊天机器人"升级为一个"严谨的工程助手"，彻底消除产出物生成过程中的随机性。
