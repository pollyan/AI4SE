# Lisa 架构迁移代码评审报告

**日期**: 2026-01-18
**评审人**: Sisyphus (AI Architect)
**评审对象**: Lisa 智能体产出物管理重构 (Regex -> Structured Output)

---

## 1. 总体评估 (Overall Assessment)

代码改动严格遵循了 **TDD (测试驱动开发)** 流程，所有新增功能均通过了单元测试和集成测试的验证。核心目标（引入 Tool Calling、保持流式体验）已达成。

| 维度 | 评分 | 说明 |
|------|------|------|
| **架构一致性** | ✅ Pass | 成功迁移到 Hybrid Tool Calling 模式，移除了 Regex 依赖。 |
| **测试覆盖率** | ✅ Pass | 新增了针对 Tool Call 和 Streaming Parsing 的专用测试用例。 |
| **代码质量** | ✅ Pass | `workflow_test_design.py` 经过重构，移除了冗余代码，逻辑清晰。 |
| **遗留风险** | ⚠️ Warning | **Prompt 尚未更新**，仍包含旧的 Regex 输出指令。 |

---

## 2. 详细发现 (Findings)

### 2.1 亮点 (Strengths)
1.  **Streaming Adapter 实现精妙**: 通过实时解析部分 JSON (`accumulated_tool_args`)，成功在后端模拟了流式 Markdown 推送。这确保了前端用户体验不受 Tool Calling "等待闭合" 特性的影响。
2.  **Mock 策略严谨**: 测试代码中对 `bind_tools` 和 `stream` 的 Mock 非常到位，准确模拟了 LangChain Runnable 的行为链。
3.  **回退机制移除**: 果断移除了 Regex Fallback 代码，避免了维护两套逻辑的长期债务。

### 2.2 发现的问题 (Issues)

**[CRITICAL] Prompt 指令冲突**
在 `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py` 中，System Prompt 依然包含以下指令：

```markdown
## 产出物输出规范 (Critical)
你必须在每次回复的最后... 请务必使用以下格式输出...
```markdown
[此处为更新后的产出物全量内容]
```
```

**风险**:
- LLM 会收到冲突的指令：一方面被要求调用 `UpdateArtifact` 工具，另一方面被 System Prompt 强迫输出 Markdown 代码块。
- 这可能导致 **"双重输出"** (Double Output)：模型既调用了工具，又在回复里把文档打印了一遍，造成 Token 浪费和用户困惑。

---

## 3. 改进建议 (Action Items)

虽然代码逻辑已就绪，但为了系统稳定性，建议立即执行以下 **Prompt 清理**：

1.  **修改 `test_design.py`**:
    - 删除 "产出物输出规范 (Critical)" 章节。
    - 替换为简短指令："当需要更新产出物时，请务必调用 `UpdateArtifact` 工具。不要在对话中直接输出文档内容。"
2.  **验证**:
    - 再次运行集成测试，确保 Prompt 修改后模型依然能正确触发工具（通常会更稳定）。

**下一步建议**: 请授权我执行 Prompt 清理工作，以完成本次迁移的最后一块拼图。
