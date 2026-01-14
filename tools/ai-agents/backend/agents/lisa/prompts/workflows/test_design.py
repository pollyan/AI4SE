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

### 阶段与产出物 Key 映射

| 阶段 | Key | 产出物名称 |
|------|-----|-----------|
| clarify | `test_design_requirements` | 需求分析文档 |
| strategy | `test_design_strategy` | 测试策略蓝图 |
| cases | `test_design_cases` | 测试用例集 |
| delivery | `test_design_final` | 测试设计文档 |

### ⚠️ 产出物管理（核心规则）

1. **所有文档内容存储在 JSON `artifacts` 中**，不要在自然语言回复中输出完整文档
2. **每次用户回复后都要更新 artifacts**，将新确认的信息累积到 content 中
3. **content 必须是完整文档**，不是增量片段
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 需求澄清阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_CLARIFY_PROMPT = f"""
## 当前任务：需求澄清 (Clarify)

### 目标
通过"全景-聚焦"交互协议，消除用户需求中的所有模糊点。

### 执行步骤

参考"全景-聚焦"交互协议中的步骤

### 产出物

**Key**: `test_design_requirements`
**Name**: 需求分析文档

文档结构参考：
{ARTIFACT_CLARIFY_REQUIREMENTS}


"""

# ═══════════════════════════════════════════════════════════════════════════════
# 策略制定阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_STRATEGY_PROMPT = f"""
## 当前任务：策略制定 (Strategy)

### 目标
通过技术选型协议选择合适的技术，制定测试策略蓝图。

### 执行步骤

1. **确定技术**：根据技术选型协议和当前需求的特征，选择合适的技术
2. **风险识别**：使用上一步确定的技术，分析需求中的风险点
3. **优先级排序**：按风险等级对测试重点排序
4. **策略选择**：选择合适的测试策略和技术
5. **资源规划**：估算测试范围和工作量

### 产出物要求

**Key**: `test_design_strategy`
**Name**: 测试策略蓝图

文档结构参考：
{ARTIFACT_STRATEGY_BLUEPRINT}

"""

# ═══════════════════════════════════════════════════════════════════════════════
# 用例编写阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_CASES_PROMPT = f"""
## 当前任务：用例编写 (Cases)

### 目标
通过技术选型协议选择合适的技术，基于测试策略，设计具体的测试点和测试用例。

### 执行步骤

1. **测试点设计**：按测试策略蓝图中的优先级，设计测试点
2. **技术选择**：为每个测试点选择合适的技术来设计测试用例
3. **用例编写**：编写并输出测试用例

### 产出物要求

**Key**: `test_design_cases`
**Name**: 测试用例集

文档结构参考：
{ARTIFACT_CASES_SET}

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
