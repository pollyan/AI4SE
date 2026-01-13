"""
Product Design Workflow Prompts
产品设计工作流 Prompt 定义
"""

import json
from typing import List, Dict
from ..shared import build_full_prompt_with_protocols

# ═══════════════════════════════════════════════════════════════════════════════
# 系统 Prompt
# ═══════════════════════════════════════════════════════════════════════════════

WORKFLOW_PRODUCT_DESIGN_SYSTEM = """
{base_prompt}

# 当前工作流: 产品需求澄清 (Product Design)

**当前阶段**: {workflow_stage}

## 上下文信息
- **产出物摘要**: 
{artifacts_summary}
- **待澄清问题**: {pending_clarifications}
- **已达成共识**: {consensus_count} 项

## 动态进度计划

{plan_context}

{plan_sync_instruction}

### 阶段定义与产出物 Key

#### elevator (电梯演讲)
- **目标**: 明确价值定位 (1-2句话)
- **产出物 Key**: `product_elevator`
- **产出物名称**: 电梯演讲

#### persona (用户画像)
- **目标**: 明确目标用户特征与痛点
- **产出物 Key**: `product_persona`
- **产出物名称**: 用户画像分析

#### journey (用户旅程)
- **目标**: 梳理 As-is 和 To-be 旅程
- **产出物 Key**: `product_journey`
- **产出物名称**: 用户旅程地图

#### brd (BRD文档)
- **目标**: 整合生成最终需求文档
- **产出物 Key**: `product_brd`
- **产出物名称**: 业务需求文档 (BRD)

### 产出物管理规则

**核心规则**: 所有文档内容必须存储在 JSON 输出的 `artifacts` 列表中，而不是直接在消息中输出。

1. **初始化**: 进入新阶段时，在 `artifacts` 列表中创建一个新的产出物条目，内容为初始骨架或 null。
2. **更新**: 每次获得新信息，在 `artifacts` 列表中更新对应 Key 的 `content` 字段。
3. **展示**: 前端会自动渲染 `artifacts` 中的内容，你在 `message` 中只需引导用户查看右侧文档。
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 阶段 1: 电梯演讲 (Elevator Pitch)
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_ELEVATOR_PROMPT = """
## 当前任务：电梯演讲 (Elevator Pitch) - 价值定位澄清

### 目标
想象在电梯里遇到了理想的投资人，用 1-2 分钟时间清晰介绍产品价值。

### 核心问题
1. **产品定义**: 您的产品是什么？(1-2句话)
2. **核心问题**: 主解决什么问题？问题有多严重？
3. **竞争优势**: 为什么选择您而不是竞品？

### 话术模板

**开场**:
> "让我们从电梯演讲开始！请试着用一句话告诉我，您的产品究竟是什么，主要解决谁的什么痛点？"

**深挖**:
> "您提到了 [功能]，但这似乎是解决方案而非问题本身。用户在没有这个产品时，最痛苦的是什么？"

### 产出物要求 (JSON artifacts)
Key: `product_elevator`
Name: 电梯演讲

**完成标志**:
当价值定位清晰且用户确认无误后，将 `elevator` 阶段状态设为 completed，`persona` 阶段设为 active。
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 阶段 2: 用户画像 (User Persona)
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_PERSONA_PROMPT = """
## 当前任务：用户画像 (User Persona) - 目标用户分析

### 目标
深入刻画目标用户群体，拒绝模糊的用户描述。

### 核心分析维度
1. **基础特征**: B端(规模/行业/决策链) 或 C端(年龄/地域/收入)。
2. **行为模式**: 使用场景、习惯、信息渠道。
3. **核心痛点**: 具体的困扰、损失、现有方案的不足。

### 话术模板

**开场**:
> "价值定位已清晰。现在让我们通过用户画像来具体化您的目标客户。
> 您的核心用户主要在什么场景下使用产品？"

### 产出物要求 (JSON artifacts)
Key: `product_persona`
Name: 用户画像分析

**完成标志**:
当用户画像具体且生动后，将 `persona` 阶段状态设为 completed，`journey` 阶段设为 active。
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 阶段 3: 用户旅程 (User Journey)
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_JOURNEY_PROMPT = """
## 当前任务：用户旅程 (User Journey)

### 目标
梳理用户从接触道完成目标的完整旅程，挖掘痛点和机会。

### 核心活动
1. **As-is 旅程**: 用户现在是怎么解决问题的？(痛点在哪里)
2. **To-be 旅程**: 使用您的产品后，流程将如何优化？(价值在哪里)
3. **机会识别**: 在哪些关键触点可以提供超预期体验？

### 话术模板

**开场**:
> "接下来我们梳理用户旅程。在这个用户解决 [核心问题] 的过程中，通常分为哪几个步骤？"

### 产出物要求 (JSON artifacts)
Key: `product_journey`
Name: 用户旅程地图

**完成标志**:
当关键路径梳理完毕，将 `journey` 阶段状态设为 completed，`brd` 阶段设为 active。
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 阶段 4: BRD 文档生成
# ═══════════════════════════════════════════════════════════════════════════════

STAGE_BRD_PROMPT = """
## 当前任务：业务需求文档 (BRD) 生成

### 目标
基于前三步的分析，整合生成结构化的业务需求文档。

### 执行步骤
1. **MVP 确认**: 确认最小可行性产品的范围 (Core Features)。
2. **文档生成**: 将 Value, Persona, Journey 整合为标准 BRD。
3. **下一步建议**: 建议技术评审或原型设计方向。

### 产出物要求 (JSON artifacts)
Key: `product_brd`
Name: 业务需求文档 (BRD)

**完成标志**:
生成完整 BRD 后，将 `brd` 阶段设为 completed。
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 构建函数
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_PRODUCT_STAGES = [
    {"id": "elevator", "name": "价值定位"},
    {"id": "persona", "name": "用户画像"},
    {"id": "journey", "name": "用户旅程"},
    {"id": "brd", "name": "BRD文档"}
]

def build_product_design_prompt(
    stage: str,
    artifacts_summary: str,
    pending_clarifications: str,
    consensus_count: int,
    plan_context: str = "(无进度计划)"
) -> str:
    """构建产品设计工作流 Prompt"""
    base = build_full_prompt_with_protocols()
    
    # 构造动态 Plan 示例 (如果当前没有 plan_context，需要引导生成)
    # 这里我们生成一个 One-Shot 示例，展示如何输出 Plan
    # 注意：我们这里不硬编码当前状态，而是提供一个通用的示例
    
    example_stages = []
    for i, s in enumerate(DEFAULT_PRODUCT_STAGES):
        st = s.copy()
        # 示例状态：假设处于第一个阶段
        st["status"] = "active" if i == 0 else "pending"
        example_stages.append(st)
        
    example_obj = {
        "plan": example_stages,
        "current_stage_id": example_stages[0]["id"],
        "artifacts": []
    }
    example_json = json.dumps(example_obj, ensure_ascii=False, indent=2)
    
    plan_sync_instruction = f"""
### 工作计划同步

请在回复末尾的 JSON 中输出当前工作流的完整状态。

**示例**: 如果这是第一次回复，你的 JSON 应该包含如下初始计划：
```json
{example_json}
```
"""

    system = WORKFLOW_PRODUCT_DESIGN_SYSTEM.format(
        base_prompt=base,
        workflow_stage=stage,
        artifacts_summary=artifacts_summary,
        pending_clarifications=pending_clarifications,
        consensus_count=consensus_count,
        plan_context=plan_context,
        plan_sync_instruction=plan_sync_instruction,
    )
    
    stage_prompts = {
        "elevator": STAGE_ELEVATOR_PROMPT,
        "persona": STAGE_PERSONA_PROMPT,
        "journey": STAGE_JOURNEY_PROMPT,
        "brd": STAGE_BRD_PROMPT,
    }
    
    stage_prompt = stage_prompts.get(stage, STAGE_ELEVATOR_PROMPT)
    
    return f"{system}\n\n---\n\n{stage_prompt}"
