# 产出物状态同步修复实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 ReasoningNode → ArtifactNode 之间的状态同步问题，确保用户在对话中确认了待澄清问题后，产出物的 `assumptions` 状态能从 `pending` 正确更新为 `confirmed`。

**Architecture:** 采用"方案2为主 + 方案1兜底"策略。ReasoningNode 通过 `artifact_update_hint` 传递精确的操作级指引（如"将 Q-001 的 status 改为 confirmed"），ArtifactNode 的 Prompt 增加通用兜底规则。同步在 AGENTS.md 中沉淀最佳实践。

**Tech Stack:** Python, Pydantic, LangGraph, pytest

**依据:**
- LangGraph 官方推荐通过 State 在节点间传递私有上下文
- 业界共识："先推理再结构化"（Separate Reasoning and Structuring）模式
- Context Engineering：上游节点精简上下文，下游节点只处理必要信息

---

## Task 1: 增强 ReasoningNode Prompt 中 artifact_update_hint 的状态变更指引

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py:90-99`

**Goal:** 在 `artifact_update_hint` 的 Prompt 说明中，增加明确的操作级指引规则——当用户回复确认了某个待确认问题时，hint 必须包含该问题 ID 及其新的 status 和 note。

**Step 1: 修改 test_design.py 中 artifact_update_hint 的 Prompt 指引**

将 `test_design.py` 第 90-99 行的 `artifact_update_hint` 说明替换为更具操作性的版本：

```python
4. **artifact_update_hint** (optional string):
    - **全量推理结论交接 (Full Reasoning Handoff)**:
    - 当 `should_update_artifact=True` 时，**必须**填写此字段。
    - 这是一个给"产出物更新智能体"的直接指令。
    - **必须包含**:
      a. 用户确认的关键决策 (Decisions)
      b. 你在思考过程中发现的新风险或洞察 (New Insights & Risks)
      c. 具体的行动项 (Action Items: Add/Modify/Delete)
      d. **[关键] 待澄清问题状态变更 (Assumption Status Changes)**:
         - 当用户的回复回答或确认了 assumptions 列表中的某个问题时，
           **必须**在 hint 中明确列出该问题的 ID 和新状态。
         - 格式: "**状态变更**: Q-001 → confirmed (note: 用户确认xxx); Q-003 → confirmed (note: xxx)"
         - 即使用户一次性确认多个问题，也必须逐一列出每个 ID。
    - **示例**: "用户确认库存并发使用数据库乐观锁。**风险提示**: 高并发下失败率上升。**状态变更**: Q-001 → confirmed (note: 采用乐观锁); Q-003 → confirmed (note: 无需特殊字符)。**行动项**: 更新需求规则章节，明确乐观锁机制。"
```

**Step 2: 验证修改**

Run: `python -c "from tools.ai_agents.backend.agents.lisa.prompts.workflows.test_design import build_test_design_prompt; print('OK')"`
Expected: OK（无导入错误）

**Step 3: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py
git commit -m "feat(lisa): enhance artifact_update_hint with explicit assumption status change instructions"
```

---

## Task 2: 在 ArtifactNode Prompt 中增加通用兜底规则

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/artifacts.py:399-407`

**Goal:** 在 `build_artifact_update_prompt` 的 `reasoning_context` 区块中增加通用兜底规则，确保即使 hint 中没有精确列出状态变更，ArtifactNode 也能根据对话上下文更新 assumptions 的状态。

**Step 1: 修改 artifacts.py 中 reasoning_context 的构建**

将 `artifacts.py` 第 399-407 行替换为增强版本：

```python
    # [新增] 注入 Reasoning Hint
    reasoning_context = ""
    if reasoning_hint:
        reasoning_context = f"""
**来自推理智能体的重要上下文 (CONTEXT FROM REASONING AGENT)**:
{reasoning_hint}

请务必根据上述上下文更新文档，尤其是其中提到的风险、决策和**状态变更**。
如果上下文中包含"状态变更"指令（如 "Q-001 → confirmed"），你**必须**在 `assumptions` 列表中找到对应 ID 的条目，
将其 `status` 更新为 `confirmed`，并在 `note` 字段中填写确认结论。
"""
    else:
        # 兜底规则：即使没有 hint，也提醒 LLM 关注对话中的状态变更
        reasoning_context = """
**通用规则 (FALLBACK RULE)**:
如果对话历史中用户已经明确回答或确认了 `assumptions` 列表中的某个待确认问题（status 为 "pending"），
你**必须**将对应条目的 `status` 更新为 `confirmed`，并在 `note` 字段中记录用户的确认结论。
不要遗漏任何已在对话中被回答的问题。
"""
```

**Step 2: 验证修改**

Run: `python -c "from tools.ai_agents.backend.agents.lisa.prompts.artifacts import build_artifact_update_prompt; print(build_artifact_update_prompt('test_key', 'clarify', '', None, None)[:100])"`
Expected: 输出包含"通用规则"

**Step 3: Commit**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/artifacts.py
git commit -m "feat(lisa): add fallback rule for assumption status sync in artifact update prompt"
```

---

## Task 3: 编写单元测试验证 hint 传递机制

**Files:**
- Create: `tools/ai-agents/backend/tests/test_artifact_hint_sync.py`

**Goal:** 验证 `build_artifact_update_prompt` 在有/无 `reasoning_hint` 时的行为差异，以及 hint 中包含状态变更指令时 Prompt 的正确性。

**Step 1: 编写失败的测试**

```python
"""
测试产出物更新 Prompt 的 hint 注入机制
"""
import pytest
from tools.ai_agents.backend.agents.lisa.prompts.artifacts import (
    build_artifact_update_prompt,
)


class TestArtifactHintSync:
    """验证 artifact_update_hint 在 Prompt 中的注入行为"""

    def test_prompt_includes_hint_when_provided(self):
        """有 hint 时，Prompt 中应包含 hint 内容和状态变更指令"""
        hint = "用户确认密码不需要特殊字符。**状态变更**: Q-003 → confirmed (note: 无需特殊字符)"
        
        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="# 模板",
            existing_artifact=None,
            reasoning_hint=hint,
        )
        
        assert "Q-003 → confirmed" in prompt
        assert "状态变更" in prompt
        assert "status" in prompt.lower() or "confirmed" in prompt

    def test_prompt_includes_fallback_when_no_hint(self):
        """无 hint 时，Prompt 中应包含通用兜底规则"""
        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="# 模板",
            existing_artifact=None,
            reasoning_hint=None,
        )
        
        assert "通用规则" in prompt or "FALLBACK" in prompt
        assert "confirmed" in prompt

    def test_prompt_includes_hint_but_not_fallback(self):
        """有 hint 时，不应出现兜底规则"""
        hint = "**状态变更**: Q-001 → confirmed"
        
        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="# 模板",
            existing_artifact=None,
            reasoning_hint=hint,
        )
        
        assert "FALLBACK" not in prompt
        assert "通用规则" not in prompt
```

**Step 2: 运行测试验证失败**

Run: `cd tools/ai-agents && pytest backend/tests/test_artifact_hint_sync.py -v`
Expected: FAIL（因为当前代码中无 hint 时不输出兜底规则）

**Step 3: 确认 Task 2 的修改使测试通过**

Run: `cd tools/ai-agents && pytest backend/tests/test_artifact_hint_sync.py -v`
Expected: 3 tests PASSED

**Step 4: Commit**

```bash
git add tools/ai-agents/backend/tests/test_artifact_hint_sync.py
git commit -m "test(lisa): add unit tests for artifact hint sync mechanism"
```

---

## Task 4: 在 AGENTS.md 沉淀最佳实践

**Files:**
- Modify: `AGENTS.md:210-216`

**Goal:** 在 "AI Agents 架构策略" 章节中，增加"节点间上下文传递"最佳实践的描述。

**Step 1: 在 AGENTS.md 的"产出物更新流程"后追加最佳实践**

在 `AGENTS.md` 第 216 行（`> **禁止** 直接在节点中修改...`）后追加：

```markdown
### 节点间上下文传递 (Inter-Node Context Passing)

**核心原则**: 推理节点负责"理解和决策"，执行节点负责"执行"——通过 State 传递结构化操作指引。

| 原则 | 说明 |
|------|------|
| **先推理再结构化** | ReasoningNode 深度分析对话上下文后，在 `artifact_update_hint` 中生成精确的操作级指引，ArtifactNode 只需执行 |
| **操作级 Hint > 通用规则** | hint 中应包含具体的 ID、状态变更、字段值，而非模糊的"请更新文档" |
| **兜底防御** | ArtifactNode 的 Prompt 中保留通用兜底规则，确保即使 hint 缺失也有最低保障 |
| **Token 效率** | 由上游精简上下文，下游不重复推理全部对话历史 |

**`artifact_update_hint` 格式规范**:
```
"用户确认了xxx。**风险提示**: yyy。**状态变更**: Q-001 → confirmed (note: 结论); Q-003 → confirmed (note: 结论)。**行动项**: 更新zzz章节。"
```

> **依据**: LangGraph 官方推荐通过 State 键在节点间传递私有上下文（Private State 模式）；业界共识"先推理再结构化"（Separate Reasoning and Structuring）是多步 Agent 工作流最佳实践。
```

**Step 2: 验证 Markdown 格式**

目视检查 AGENTS.md 的新增内容是否格式正确，无嵌套代码块错误。

**Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add inter-node context passing best practice to AGENTS.md"
```

---

## Task 5: 运行全量测试并推送

**Step 1: 运行本地测试**

Run: `./scripts/test/test-local.sh`
Expected: 所有测试通过

**Step 2: 推送代码**

```bash
git push
```
