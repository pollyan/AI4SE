"""
Alex Shared Prompts
Alex 智能体共享的 Prompt 定义，包括结构化输出协议。
"""

from .system import ALEX_IDENTITY, ALEX_STYLE, ALEX_PRINCIPLES

# ═══════════════════════════════════════════════════════════════════════════════
# 结构化输出协议 (JSON)
# ═══════════════════════════════════════════════════════════════════════════════

STRUCTURED_OUTPUT_PROMPT = """
### 结构化输出协议 (Structured Output Protocol)

本系统采用**混合模式 (Mixed Mode)**进行响应：
1. 先输出自然语言回复（Markdown 格式），用于与用户交互。
2. 最后输出**全量状态快照 JSON**，用于更新系统状态。

#### 核心规则
- **顺序强制**: 必须 **先** 输出回复内容，**最后** 输出 JSON 代码块。
- **位置强制**: JSON 代码块必须位于回复的**最末尾**。
- **JSON 格式**: 使用 ```json 代码块包裹。

#### JSON 数据格式
必须包含以下字段（注意：回复内容**不**包含在 JSON 中）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `plan` | array | 工作流阶段列表，每个元素包含 id、name、status |
| `current_stage_id` | string | 当前活跃阶段的 ID |
| `artifacts` | array | 产出物列表，包含 stage_id、key、name、content |

**plan 中每个阶段的字段**:
- `id`: 阶段唯一标识符
- `name`: 阶段显示名称
- `status`: 当前状态 (pending/active/completed)

**artifacts 中每个产出物的字段**:
- `stage_id`: 所属阶段 ID
- `key`: 产出物唯一键
- `name`: 产出物显示名称
- `content`: 产出物内容（Markdown 格式），未生成时为 null

#### One-Shot 样例

**场景**: 价值定位(elevator)阶段完成，准备进入用户画像(persona)阶段。

> 好的，您的电梯演讲非常清晰。我们要解决的核心痛点是...
> 
> 接下来我们进入用户画像分析阶段。
>
> ```json
> {example_json}
> ```

**注意**: JSON 代码块会被系统自动隐藏，用户只会看到前面的回复内容。
"""

# ═══════════════════════════════════════════════════════════════════════════════
# 基础 System Prompt 构建
# ═══════════════════════════════════════════════════════════════════════════════

def build_base_prompt() -> str:
    """构建基础 Prompt (Identity + Style + Principles)"""
    return f"""
{ALEX_IDENTITY}

{ALEX_STYLE}

{ALEX_PRINCIPLES}

# 交互规则
- 每轮对话提出少于 5 个问题，避免给用户造成压力。
- 始终以专业、友好的方式与用户交互。
- 只有在信息充分澄清后，才进入下一个分析阶段。
""".strip()

def build_full_prompt_with_protocols() -> str:
    """构建包含所有协议的完整 Prompt"""
    return f"""
{build_base_prompt()}

---

{STRUCTURED_OUTPUT_PROMPT}
""".strip()
