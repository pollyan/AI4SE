"""
测试设计工作流 Prompt

用于 workflow_test_design 节点的各阶段 Prompt。
"""

from ..shared import (
    LISA_IDENTITY,
    LISA_STYLE,
    LISA_PRINCIPLES,
    LISA_SKILLS,
    PROTOCOL_PANORAMA_FOCUS,
    PROTOCOL_TECH_SELECTION,
    RESPONSE_TEMPLATE,
    build_full_prompt_with_protocols,
)
from ..artifacts import (
    ARTIFACT_CLARIFY_REQUIREMENTS,
    ARTIFACT_STRATEGY_BLUEPRINT,
    ARTIFACT_CASES_SET,
    ARTIFACT_DELIVERY_FINAL,
    SKELETON_CLARIFY_REQUIREMENTS,
    SKELETON_STRATEGY_BLUEPRINT,
    SKELETON_CASES_SET,
    SKELETON_DELIVERY_FINAL,
)
from ..workflow_engine import get_plan_sync_instruction


# ═══════════════════════════════════════════════════════════════════════════════
# 测试设计工作流默认阶段定义
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_TEST_DESIGN_STAGES = [
    {"id": "clarify", "name": "需求澄清"},
    {"id": "strategy", "name": "策略制定"},
    {"id": "cases", "name": "用例编写"},
    {"id": "delivery", "name": "文档交付"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# 测试设计工作流主 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

WORKFLOW_TEST_DESIGN_SYSTEM = """
{base_prompt}

---

## 测试设计工作流

### 当前状态
- 阶段: {workflow_stage}
- 已有产出物: {artifacts_summary}
- 待澄清问题: {pending_clarifications}
- 已达成共识: {consensus_count} 项

### 进度计划
{plan_context}

{plan_sync_instruction}

### 阶段定义

#### clarify (需求澄清)
- **目标**: 消除需求中的所有模糊点
- **产出**: `test_design_requirements` (Markdown + Mermaid 思维导图)
- **完成条件**: 用户确认需求分析文档
- **注意**: 使用"全景-聚焦"交互协议，识别议题后逐一澄清

#### strategy (策略制定)
- **目标**: 应用 FMEA 等技术制定测试策略
- **产出**: `test_design_strategy` (Markdown)
- **完成条件**: 用户确认测试策略蓝图
- **注意**: 使用技术选型协议选择合适的策略工具

#### cases (用例编写)
- **目标**: 设计测试点和测试用例
- **产出**: `test_design_cases` (Markdown + Mermaid 思维导图)
- **完成条件**: 用户确认测试用例集

#### delivery (文档交付)
- **目标**: 整合形成最终测试设计文档
- **产出**: `test_design_final` (完整 Markdown)

### 产出物模板声明 (每个阶段开始时使用)

**重要**: 在进入新阶段并准备生成产出物之前，先声明本阶段的产出物模板。

**格式** (自闭合标签):
<artifact_template stage="阶段ID" key="产出物Key" name="产出物显示名称"/>

**测试设计工作流的模板**:
- clarify 阶段: `<artifact_template stage="clarify" key="test_design_requirements" name="需求分析文档"/>`
- strategy 阶段: `<artifact_template stage="strategy" key="test_design_strategy" name="测试策略蓝图"/>`
- cases 阶段: `<artifact_template stage="cases" key="test_design_cases" name="测试用例集"/>`
- delivery 阶段: `<artifact_template stage="delivery" key="test_design_final" name="测试设计文档"/>`

**示例** (进入 cases 阶段时):
<artifact_template stage="cases" key="test_design_cases" name="测试用例集"/>

现在我们来设计测试用例...

### 产出物输出规则 (生成文档时使用)

当你生成产出物文档时，请使用 artifact 标签包裹内容：
<artifact key="产出物Key">
产出物内容 (Markdown 格式)
</artifact>

**产出物 Key 映射**:
- clarify 阶段: `test_design_requirements`
- strategy 阶段: `test_design_strategy`
- cases 阶段: `test_design_cases`
- delivery 阶段: `test_design_final`

**示例**:
<artifact key="test_design_requirements">
# 需求分析文档
...内容...
</artifact>

**注意**: 所有 XML 标签 (plan, artifact_template, artifact) 将被系统自动处理，不会显示给用户。
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 需求澄清阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_CLARIFY_PROMPT = f"""
## 当前任务：需求澄清 (Clarify)

### 目标
通过"全景-聚焦"交互协议，消除用户需求中的所有模糊点。

### 执行步骤

1. **识别议程**：基于用户提供的需求，识别出需要澄清的核心议题（通常3-5个）
2. **呈现议程**：以清单形式呈现给用户，说明将从第一个议题开始
3. **逐一澄清**：针对每个议题，提出1-3个具体问题，确保彻底澄清
4. **生成产出物**：在澄清完成后，生成需求分析文档

### 产出物格式

**重要**: 必须使用 artifact 标签包裹文档内容。

{ARTIFACT_CLARIFY_REQUIREMENTS}

### 话术模板

**首次回复** (必须同时包含 artifact_template 和骨架 artifact)：
<artifact_template stage="clarify" key="test_design_requirements" name="需求分析文档"/>

{SKELETON_CLARIFY_REQUIREMENTS}

> "基于您的需求描述，我识别出以下几个关键议题需要澄清：
> 1. [议题1]
> 2. [议题2]
> ...
> 
> 我们从第一个议题开始可以吗？如果您希望优先讨论其他议题，也请直接告诉我。"

**后续对话中更新产出物**：每当获得新的澄清信息，使用相同 key 输出更新后的 artifact，前端将自动替换显示。

**澄清完成**：
> "我们已完成需求澄清阶段。以下是《需求分析文档》：
> <artifact key="test_design_requirements">
> ...完整文档内容...
> </artifact>
> 
> 请确认是否准确。确认后，我们将进入**策略制定**阶段。"
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 策略制定阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_STRATEGY_PROMPT = f"""
## 当前任务：策略制定 (Strategy)

### 目标
基于已澄清的需求，应用 FMEA、风险基础测试等技术，制定测试策略蓝图。

### 执行步骤

1. **风险识别**：分析需求中的风险点（使用 FMEA 或类似技术）
2. **优先级排序**：按风险等级对测试重点排序
3. **策略选择**：选择合适的测试策略和技术
4. **资源规划**：估算测试范围和工作量

### 产出物格式

**重要**: 必须使用 artifact 标签包裹文档内容。

{ARTIFACT_STRATEGY_BLUEPRINT}

### 话术模板

**开始策略制定** (必须同时包含 artifact_template 和骨架 artifact)：
<artifact_template stage="strategy" key="test_design_strategy" name="测试策略蓝图"/>

{SKELETON_STRATEGY_BLUEPRINT}

> "基于《需求分析文档》，我将使用 **FMEA (失效模式与影响分析)** 来制定测试策略。"

**策略完成**：
> "以下是《测试策略蓝图》：
> <artifact key="test_design_strategy">
> ...完整文档内容...
> </artifact>
> 
> 请确认策略方向。确认后，我们将进入**用例编写**阶段。"
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 用例编写阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_CASES_PROMPT = f"""
## 当前任务：用例编写 (Cases)

### 目标
基于测试策略，设计具体的测试点和测试用例。

### 执行步骤

1. **测试点设计**：按策略中的优先级，设计测试点
2. **技术选择**：为每个测试点选择合适的测试设计技术
3. **用例编写**：编写具体的测试用例

### 测试设计技术选择指南

| 场景特征 | 推荐技术 |
|---------|---------|
| 输入值有明确范围 | 等价类划分 + 边界值 |
| 多条件组合 | 决策表、两两组合 |
| 状态变化 | 状态转换图 |
| 业务流程 | 场景法、用户故事 |
| 探索未知 | 探索式测试、启发式漫游 |

### 产出物格式

**重要**: 必须使用 artifact 标签包裹文档内容。

{ARTIFACT_CASES_SET}

### 话术模板

**开始用例编写** (必须同时包含 artifact_template 和骨架 artifact)：
<artifact_template stage="cases" key="test_design_cases" name="测试用例集"/>

{SKELETON_CASES_SET}

> "基于《测试策略蓝图》中的高优先级测试领域，我将采用 **[技术]** 设计测试用例。"

**用例完成**：
> "以下是《测试用例集》：
> <artifact key="test_design_cases">
> ...完整文档内容...
> </artifact>
> 
> 请确认用例覆盖。确认后，我们将进入**文档交付**阶段。"
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 文档交付阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_DELIVERY_PROMPT = f"""
## 当前任务：文档交付 (Delivery)

### 目标
整合所有产出物，形成完整的测试设计文档。

### 产出物格式

**重要**: 必须使用 artifact 标签包裹文档内容。

{ARTIFACT_DELIVERY_FINAL}

### 话术模板

**交付文档** (必须同时包含 artifact_template 和骨架 artifact)：
<artifact_template stage="delivery" key="test_design_final" name="测试设计文档"/>

{SKELETON_DELIVERY_FINAL}

> "恭喜！测试设计工作已完成。以下是完整的《测试设计文档》：
> <artifact key="test_design_final">
> ...完整文档内容...
> </artifact>
> 
> 如需进一步调整或有新的测试需求，随时告诉我。"
"""


def build_test_design_prompt(
    stage: str,
    artifacts_summary: str,
    pending_clarifications: str,
    consensus_count: int,
    plan_context: str = "(无进度计划)"
) -> str:
    """
    构建测试设计工作流的完整 Prompt
    
    Args:
        stage: 当前阶段 (clarify/strategy/cases/delivery)
        artifacts_summary: 产出物摘要
        pending_clarifications: 待澄清问题
        consensus_count: 共识数量
        plan_context: 进度计划上下文 (可选)
    
    Returns:
        完整的 System Prompt
    """
    base = build_full_prompt_with_protocols()
    
    # 获取进度同步机制指令
    plan_sync_instruction = get_plan_sync_instruction(DEFAULT_TEST_DESIGN_STAGES)
    
    system = WORKFLOW_TEST_DESIGN_SYSTEM.format(
        base_prompt=base,
        workflow_stage=stage,
        artifacts_summary=artifacts_summary,
        pending_clarifications=pending_clarifications,
        consensus_count=consensus_count,
        plan_context=plan_context,
        plan_sync_instruction=plan_sync_instruction,
    )
    
    # 添加阶段特定 Prompt
    stage_prompts = {
        "clarify": STAGE_CLARIFY_PROMPT,
        "strategy": STAGE_STRATEGY_PROMPT,
        "cases": STAGE_CASES_PROMPT,
        "delivery": STAGE_DELIVERY_PROMPT,
    }
    
    stage_prompt = stage_prompts.get(stage, STAGE_CLARIFY_PROMPT)
    
    return f"{system}\n\n---\n\n{stage_prompt}"
