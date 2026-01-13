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

### 阶段定义与产出物 Key

#### clarify (需求澄清)
- **目标**: 消除需求中的所有模糊点
- **产出物 Key**: `test_design_requirements`
- **产出物名称**: 需求分析文档
- **完成条件**: 用户确认需求分析文档

#### strategy (策略制定)
- **目标**: 应用 FMEA 等技术制定测试策略
- **产出物 Key**: `test_design_strategy`
- **产出物名称**: 测试策略蓝图
- **完成条件**: 用户确认测试策略蓝图

#### cases (用例编写)
- **目标**: 设计测试点和测试用例
- **产出物 Key**: `test_design_cases`
- **产出物名称**: 测试用例集
- **完成条件**: 用户确认测试用例集

#### delivery (文档交付)
- **目标**: 整合形成最终测试设计文档
- **产出物 Key**: `test_design_final`
- **产出物名称**: 测试设计文档

### 产出物管理规则

**核心规则**: 所有文档内容必须存储在 JSON 输出的 `artifacts` 列表中，而不是直接在消息中输出。

1. **初始化**: 进入新阶段时，在 `artifacts` 列表中创建一个新的产出物条目，内容为初始骨架或 null。
2. **更新**: 每次获得新信息，在 `artifacts` 列表中更新对应 Key 的 `content` 字段。
3. **展示**: 前端会自动渲染 `artifacts` 中的内容，你在 `message` 中只需引导用户查看右侧文档。

**示例** (JSON artifacts 字段):
```json
"artifacts": [
  {{
    "stage_id": "clarify", 
    "key": "test_design_requirements", 
    "name": "需求分析文档", 
    "content": "# 需求分析文档\\n\\n..."
  }}
]
```
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
4. **更新文档**：在澄清完成后，更新需求分析文档的内容

### 产出物要求

**Key**: `test_design_requirements`
**Name**: 需求分析文档

文档结构参考：
{ARTIFACT_CLARIFY_REQUIREMENTS}

### 话术模板

**首次回复** (初始化产出物):
请在 JSON `artifacts` 中初始化 `test_design_requirements`，内容使用以下骨架：
{SKELETON_CLARIFY_REQUIREMENTS}

Message:
> "基于您的需求描述，我识别出以下几个关键议题需要澄清：
> 1. [议题1]
> 2. [议题2]
> ...
> 
> 我们从第一个议题开始可以吗？如果您希望优先讨论其他议题，也请直接告诉我。"

**后续对话**: 持续在 JSON 中更新 `test_design_requirements` 的内容。

**澄清完成**:
> "我们已完成需求澄清阶段。请查看右侧的《需求分析文档》。
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

### 产出物要求

**Key**: `test_design_strategy`
**Name**: 测试策略蓝图

文档结构参考：
{ARTIFACT_STRATEGY_BLUEPRINT}

### 话术模板

**开始策略制定** (初始化产出物):
请在 JSON `artifacts` 中初始化 `test_design_strategy`，内容使用以下骨架：
{SKELETON_STRATEGY_BLUEPRINT}

Message:
> "基于《需求分析文档》，我将使用 **FMEA (失效模式与影响分析)** 来制定测试策略。"

**策略完成**:
> "已更新《测试策略蓝图》，请查看右侧文档面板。
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

### 产出物要求

**Key**: `test_design_cases`
**Name**: 测试用例集

文档结构参考：
{ARTIFACT_CASES_SET}

### 话术模板

**开始用例编写** (初始化产出物):
请在 JSON `artifacts` 中初始化 `test_design_cases`，内容使用以下骨架：
{SKELETON_CASES_SET}

Message:
> "基于《测试策略蓝图》中的高优先级测试领域，我将采用 **[技术]** 设计测试用例。"

**用例完成**:
> "已生成《测试用例集》，请查看右侧文档面板。
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

### 产出物要求

**Key**: `test_design_final`
**Name**: 测试设计文档

文档结构参考：
{ARTIFACT_DELIVERY_FINAL}

### 话术模板

**交付文档** (生成最终产出物):
请整合此前所有内容，在 JSON `artifacts` 中生成 `test_design_final`。

Message:
> "恭喜！测试设计工作已完成。请查看右侧完整的《测试设计文档》。
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
