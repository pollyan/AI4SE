# AI 交互设计规则

## 核心原则：零硬编码逻辑，纯语义理解

### 规则 1: 禁止关键词匹配
**不要做：**
- ❌ 使用关键词列表匹配用户输入（如 `if "测试用例" in user_input`）
- ❌ 用正则表达式提取意图
- ❌ 硬编码的命令判断（如 `if input == "帮助"`）

**要做：**
- ✅ 将完整的用户原始输入传递给 LLM
- ✅ 让 LLM 通过语义理解判断用户意图
- ✅ 通过 prompt engineering 引导 LLM 输出结构化的意图识别结果

### 规则 2: LLM 优先原则
所有需要"理解"用户意图的场景，必须使用 LLM，包括但不限于：
- 意图识别
- 确认判断（"可以"、"好的"、"是的"等各种表达方式）
- 阶段切换判断
- 异常输入处理

### 规则 3: 快速响应的误导性
如果 AI 助手的响应速度异常快（< 500ms），通常意味着：
- 使用了硬编码逻辑而非 LLM
- 这是一个需要重构的信号

### 规则 4: 结构化输出
当需要从 LLM 获取决策信息时：
- 在 prompt 中明确要求 JSON 格式输出
- 使用 LangChain 的 `with_structured_output()` 或类似机制
- 提取决策字段（如 intent, confidence, action）

### 实施示例

**❌ 错误示例（硬编码关键词）：**
```python
def analyze_intent(user_message: str):
    if "测试用例" in user_message or "测试设计" in user_message:
        return "A", 0.9
    return "F", 0.3
```

**✅ 正确示例（LLM 语义理解）：**
```python
async def analyze_intent(user_message: str, llm):
    prompt = f"""
分析用户意图，从以下选项选择：
A. 新需求/功能测试设计
B. 需求评审与可测试性分析
...

用户输入: {user_message}

输出 JSON:
{{"intent": "A/B/C/D/E/F", "confidence": 0.0-1.0, "reasoning": "..."}}
"""
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    result = json.loads(extract_json(response.content))
    return result["intent"], result["confidence"]
```

## 适用范围
本规则适用于所有 LangGraph 智能体的实现，特别是：
- Lisa v2 (测试分析师)
- Alex (需求分析师)
- 未来的所有对话式智能体

## 例外情况
以下场景可以使用简单逻辑判断（不需要 LLM）：
- 空消息检查（`if not message.strip()`）
- 会话状态标志位（`if is_activated`）
- 长度验证（`if len(message) > 10000`）

## 更新日志
- 2025-12-21: 初始版本，基于 Lisa v2 意图识别重构经验总结
