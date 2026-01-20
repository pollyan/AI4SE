"""
测试设计工作流 Prompt

用于 workflow_test_design 节点的各阶段 Prompt。
"""

from ..shared import (
    LISA_IDENTITY,
    LISA_STYLE,
    LISA_PRINCIPLES,
    LISA_SKILLS,
    LISA_SKILLS,
    PROTOCOL_TECH_SELECTION,
    build_full_prompt_with_protocols,
)
from ..artifacts import (
    ARTIFACT_CLARIFY_REQUIREMENTS,
    ARTIFACT_STRATEGY_BLUEPRINT,
    ARTIFACT_CASES_SET,
    ARTIFACT_DELIVERY_FINAL,
)


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

### 阶段与产出物 Key 映射

| 阶段 | Key | 产出物名称 |
|------|-----|-----------|
| clarify | `test_design_requirements` | 需求分析文档 |
| strategy | `test_design_strategy` | 测试策略蓝图 |
| cases | `test_design_cases` | 测试用例集 |
| delivery | `test_design_final` | 测试设计文档 |
| review | `req_review_report` | 评审报告 |

## 产出物更新原则 (Universal Artifact Update Principles)

所有产出物均为 **Living Documents**，你必须遵守以下原则：

1. **全量内容输出 (Full Content Output)**:
    - 每次更新 `update_artifact` 时，必须输出该文档的**完整 Markdown 内容**。
    - 严禁只输出"新增部分"或"修改部分"。前端将使用你的输出直接覆盖旧内容。
    - 内容应随对话进展而"增量丰富"（填入更多章节），但物理输出必须是"全量"的。

2. **拒绝口头空谈 (No "Thought-Only" Confirmations)**:
    - 严禁仅在 `thought` 中说"我已记下"或"分析如下"而无实际产出物更新。
    - 任何属于文档范畴的信息（需求、风险、用例），必须立即同步到 `update_artifact` 字段中。

3. **结构化字段填充 (Field-Based Update)**:
    - 你正在使用 Structured Output 模式。不要寻找或调用外部工具。
    - 直接将内容填充响应结构体中的 `update_artifact` 字段。
    - 保持 Markdown 模板结构，仅填充已知信息，未知部分保留占位符。

## 响应协议 (Structured Response Protocol)
你必须严格遵守 `WorkflowResponse` 工具的结构进行输出：

1. **thought** (必填): 你的思考过程或回复用户的自然语言内容。
2. **progress_step** (必填): 当前正在进行的具体步骤名称（如"正在分析需求文档", "生成测试用例中..."），用于前端即时显示进度。
3. **update_artifact** (可选): 当且仅当需要生成或修改产出物时使用。**严禁**在 `thought` 中直接输出 Markdown 文档，必须放入此字段。

请直接调用工具返回结果，**不要**输出 Markdown 代码块 (```json ... ```)。
**注意**: 如果本次不需要更新文档，请显式返回 `"update_artifact": null`。

"""

# ═══════════════════════════════════════════════════════════════════════════════
# 需求澄清阶段 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_CLARIFY_PROMPT = f"""
## 当前任务：需求澄清 (Clarify)

### 目标
快速与用户对齐被测需求，并一次性识别出所有的待确认问题。

### 执行步骤

1. **需求理解与对齐**: 
    - 不仅仅是复述，而是要用专业的测试视角总结被测需求的核心业务逻辑和技术架构。
    - 确认测试范围（Scope）和非测试范围（Out of Scope）。

2. **批量提出疑问**:
    - 深度扫描需求文档，识别**所有**模糊、矛盾或缺失的信息。
    - **严禁**在对话内容（thought/text）中罗列问题详情。
    - **必须**将所有问题、疑点、模糊之处完整写入 `update_artifact` 的 `test_design_requirements` 文档中（通常在 "待确认问题" 或 "Pending Clarifications" 章节）。
    - 对话回复仅需简单总结："已完成需求分析，共识别出 X 个待确认问题，请查阅右侧文档。"

3. **文档更新**:
    - 将整理好的需求理解、测试范围以及待确认的问题清单，实时更新到 `test_design_requirements` 产出物中。

### 交互原则
- **文档驱动**: 所有的实质性信息交换都应通过文档进行，对话仅用于通知状态。
- **高效**: 避免不必要的礼节性对话，直奔主题。
- **专业**: 体现资深测试工程师的洞察力。
- **一次性**: 尽最大可能在第一轮交互中就暴露所有显性问题。

### 产出物要求

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
    
    system = WORKFLOW_TEST_DESIGN_SYSTEM.format(
        base_prompt=base,
        workflow_stage=stage,
        artifacts_summary=artifacts_summary,
        pending_clarifications=pending_clarifications,
        consensus_count=consensus_count,
        plan_context=plan_context,
    )
    
    # 添加阶段特定 Prompt
    stage_prompts = {
        "clarify": STAGE_CLARIFY_PROMPT,
        "strategy": STAGE_STRATEGY_PROMPT,
        "cases": STAGE_CASES_PROMPT,
        "delivery": STAGE_DELIVERY_PROMPT,
    }
    
    stage_prompt = stage_prompts.get(stage, STAGE_CLARIFY_PROMPT)
    
    # 结构化输出协议放在最末尾，LLM 对末尾指令记忆更强
    return f"{system}\n\n---\n\n{stage_prompt}"
