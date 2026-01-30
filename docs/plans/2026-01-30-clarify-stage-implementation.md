# Clarify 阶段重构实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 重构 Lisa 测试设计工作流的 clarify 阶段，明确阶段目标/边界，改进对话策略，实现 LLM 语义意图解析

**Architecture:** 
- Phase 1: 重写 `STAGE_CLARIFY_PROMPT`，嵌入新的阶段目标、问题分级、DoR 检查指引
- Phase 2: 新增 `UserIntentInClarify` Schema，在 reasoning_node 前添加意图解析层

**Tech Stack:** LangGraph, LangChain (with_structured_output), Pydantic, Python 3.11+

**Design Reference:** `docs/plans/2026-01-30-clarify-stage-redesign.md`

---

## Phase 1: Prompt 重构

### Task 1.1: 更新 STAGE_CLARIFY_PROMPT 阶段目标部分

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py:94-159`
- Test: `tools/ai-agents/backend/tests/prompts/test_clarify_prompt.py` (新建)

**Step 1: 创建 Prompt 测试文件**

```python
# tools/ai-agents/backend/tests/prompts/test_clarify_prompt.py
"""测试 clarify 阶段 Prompt 内容完整性"""
import pytest
from backend.agents.lisa.prompts.workflows.test_design import STAGE_CLARIFY_PROMPT


class TestClarifyPrompt:
    """clarify 阶段 Prompt 测试"""

    def test_contains_stage_goal(self):
        """Prompt 应包含阶段目标定义"""
        assert "Testing Foundation" in STAGE_CLARIFY_PROMPT or "测试基础信息" in STAGE_CLARIFY_PROMPT

    def test_contains_hard_requirements(self):
        """Prompt 应包含必须完成的事项"""
        required_items = ["SUT", "Scope", "Main Flow", "阻塞性"]
        for item in required_items:
            assert item in STAGE_CLARIFY_PROMPT, f"Missing required item: {item}"

    def test_contains_dor_criteria(self):
        """Prompt 应包含 DoR 准出标准"""
        assert "DoR" in STAGE_CLARIFY_PROMPT or "Definition of Ready" in STAGE_CLARIFY_PROMPT

    def test_contains_question_levels(self):
        """Prompt 应包含问题分级机制"""
        levels = ["阻塞性", "建议澄清", "可选"]
        found = sum(1 for level in levels if level in STAGE_CLARIFY_PROMPT)
        assert found >= 2, "Should contain at least 2 question levels"
```

**Step 2: 运行测试确认失败**

```bash
cd /Users/anhui/Documents/myProgram/AI4SE
pytest tools/ai-agents/backend/tests/prompts/test_clarify_prompt.py -v
```
Expected: FAIL (文件不存在或断言失败)

**Step 3: 重写 STAGE_CLARIFY_PROMPT**

```python
# tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py
# 替换原有的 STAGE_CLARIFY_PROMPT

STAGE_CLARIFY_PROMPT = f"""
## 当前任务：需求澄清 (Clarify)

### 阶段目标
**建立测试基础信息 (Testing Foundation)** - 为后续测试设计打下坚实基础。

#### 必须完成 (Hard Requirements)
| 事项 | 说明 | 完成标志 |
|------|------|----------|
| ✅ 识别被测对象 (SUT) | 明确测试的系统/模块/功能边界 | 用户确认了测试目标 |
| ✅ 确定测试范围 (Scope) | 明确 In-Scope 和 Out-of-Scope | 已写入产出物 |
| ✅ 梳理核心业务流程 | 至少 1 条主流程可绘制为图 | 产出物包含流程描述 |
| ✅ 收集阻塞性疑问 | 识别所有影响测试设计的模糊点 | 已分类列出 |

#### 可选/后续处理 (Soft Requirements)
- ⏳ 详细的业务规则分析
- ⏳ 非功能需求细化 (性能、安全等)
- ⏳ 完整的异常场景枚举
- ⏳ 测试环境/数据需求

### 准出标准 (Definition of Ready)

**DoR = 以下 3 项全部满足方可进入下一阶段：**

1. **[被测对象明确]** SUT 已识别，用户确认了测试目标和边界
2. **[主流程可达]** 至少 1 条核心业务流程已梳理，可绘制时序图/流程图
3. **[无阻塞疑问]** 所有 🔴 阻塞性问题已解决，或用户明确选择"带风险继续"

**严格规则**: 如果 DoR 未满足，**绝对不允许**设置 `request_transition_to`，即使用户要求跳过。

### 问题分级机制

当识别出待澄清问题时，**必须按以下三级分类**呈现：

```markdown
## 待澄清问题

### 🔴 阻塞性问题 (必须解决)
> 这些问题不解决将直接影响测试设计的有效性
1. [Q1] 问题描述...
2. [Q2] 问题描述...

### 🟡 建议澄清 (推荐解决)
> 这些问题会影响测试覆盖的完整性，但可以带风险继续
3. [Q3] 问题描述...

### ⚪ 可选细化 (后续补充)
> 这些问题可以在后续阶段逐步明确
5. [Q5] 问题描述...
```

### 对话策略

1. **第 1 轮 (欢迎)**: 发送欢迎语，引导用户提供 4 类信息：被测对象、需求来源、业务背景、时间约束
2. **第 2 轮 (分析)**: 分析材料，生成产出物，**一次性列出所有疑问**（按三级分类呈现）
3. **第 3+ 轮 (澄清)**: 根据用户回答更新产出物，检查 DoR，如有新疑问继续追问
4. **最后 1 轮 (确认)**: DoR 满足后，呈现总结 + 遗留风险 + 征求确认

### 欢迎语模板 (首轮必用)

如果这是对话的**第一轮**，请使用以下欢迎语：

> "您好，我是测试领域专家Lisa Song。我已准备就绪，随时可以开始测试设计工作。
> 
> 我遵循\"规划优先\"的原则，在开展测试设计前，需要先与您对齐以下关键信息：
> 
> - **被测系统/功能**: 请提供本次需要测试的对象描述
> - **需求来源**: 是需求文档、用户故事、接口规范，还是其他形式？
> - **业务背景**: 本次测试的业务上下文是什么？
> - **时间约束**: 本次测试设计的时间窗口或紧急程度如何？
> 
> 请提供任何现有的需求材料，我将立即进行专业的需求分析。"

### 阶段流转指令

- 仅当 **DoR 全部满足** 且 **用户明确确认** 时 -> 设置 `request_transition_to="strategy"`
- 用户说"继续"但 DoR 未满足 -> 回复阻塞原因，不设置流转
- 用户说"忽略那些问题" -> 需二次确认风险后才可流转

### 产出物要求

**Key**: `test_design_requirements`
**Name**: 需求分析文档

文档结构参考：
{ARTIFACT_CLARIFY_REQUIREMENTS}
"""
```

**Step 4: 运行测试确认通过**

```bash
pytest tools/ai-agents/backend/tests/prompts/test_clarify_prompt.py -v
```
Expected: PASS

**Step 5: 提交**

```bash
git add tools/ai-agents/backend/agents/lisa/prompts/workflows/test_design.py
git add tools/ai-agents/backend/tests/prompts/test_clarify_prompt.py
git commit -m "refactor(lisa): rewrite STAGE_CLARIFY_PROMPT with clear goals and DoR"
```

---

### Task 1.2: 确保测试目录结构存在

**Files:**
- Create: `tools/ai-agents/backend/tests/prompts/__init__.py`

**Step 1: 创建目录和 __init__.py**

```bash
mkdir -p tools/ai-agents/backend/tests/prompts
touch tools/ai-agents/backend/tests/prompts/__init__.py
```

**Step 2: 提交**

```bash
git add tools/ai-agents/backend/tests/prompts/__init__.py
git commit -m "chore: add prompts test directory"
```

---

## Phase 2: 意图解析实现

### Task 2.1: 新增 UserIntentInClarify Schema

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/schemas.py`
- Test: `tools/ai-agents/backend/tests/schemas/test_user_intent.py` (新建)

**Step 1: 创建 Schema 测试文件**

```python
# tools/ai-agents/backend/tests/schemas/test_user_intent.py
"""测试 UserIntentInClarify Schema"""
import pytest
from pydantic import ValidationError

from backend.agents.lisa.schemas import UserIntentInClarify


class TestUserIntentInClarify:
    """UserIntentInClarify Schema 测试"""

    def test_valid_intent_confirm_proceed(self):
        """测试有效的 confirm_proceed 意图"""
        intent = UserIntentInClarify(
            intent="confirm_proceed",
            confidence=0.95,
            answered_question_ids=[],
            extracted_info=None
        )
        assert intent.intent == "confirm_proceed"
        assert intent.confidence == 0.95

    def test_valid_intent_answer_question(self):
        """测试有效的 answer_question 意图"""
        intent = UserIntentInClarify(
            intent="answer_question",
            confidence=0.85,
            answered_question_ids=["Q1", "Q2"],
            extracted_info="用户确认了登录重试次数为3次"
        )
        assert intent.intent == "answer_question"
        assert len(intent.answered_question_ids) == 2

    def test_invalid_intent_value(self):
        """测试无效的意图值应抛出错误"""
        with pytest.raises(ValidationError):
            UserIntentInClarify(
                intent="invalid_intent",
                confidence=0.5
            )

    def test_confidence_range_validation(self):
        """测试置信度必须在 0-1 范围内"""
        with pytest.raises(ValidationError):
            UserIntentInClarify(
                intent="confirm_proceed",
                confidence=1.5  # 超出范围
            )

    def test_all_intent_types(self):
        """测试所有 7 种意图类型都有效"""
        intent_types = [
            "provide_material",
            "answer_question",
            "confirm_proceed",
            "need_more_clarify",
            "accept_risk",
            "change_scope",
            "off_topic"
        ]
        for intent_type in intent_types:
            intent = UserIntentInClarify(intent=intent_type, confidence=0.8)
            assert intent.intent == intent_type
```

**Step 2: 运行测试确认失败**

```bash
pytest tools/ai-agents/backend/tests/schemas/test_user_intent.py -v
```
Expected: FAIL (UserIntentInClarify 不存在)

**Step 3: 实现 UserIntentInClarify Schema**

```python
# 在 tools/ai-agents/backend/agents/lisa/schemas.py 末尾添加

class UserIntentInClarify(BaseModel):
    """
    clarify 阶段用户意图解析结果
    
    用于语义理解用户回复的意图，而非关键字匹配。
    """
    
    intent: Literal[
        "provide_material",    # 提供需求材料/补充信息
        "answer_question",     # 回答特定问题
        "confirm_proceed",     # 确认继续到下一阶段
        "need_more_clarify",   # 需要更多澄清/有新问题
        "accept_risk",         # 接受风险，忽略未解决问题继续
        "change_scope",        # 调整测试范围
        "off_topic"            # 离题/无关请求
    ] = Field(description="用户当前回复的核心意图")
    
    confidence: float = Field(
        ge=0.0, 
        le=1.0, 
        description="意图识别置信度 (0.0-1.0)"
    )
    
    answered_question_ids: List[str] = Field(
        default_factory=list,
        description="如果是回答问题，标记回答了哪些问题的 ID (如 Q1, Q2)"
    )
    
    extracted_info: Optional[str] = Field(
        default=None,
        description="从用户回复中提取的关键信息摘要"
    )
```

**Step 4: 添加必要的 import**

```python
# 确保 schemas.py 顶部有:
from typing import Literal, Optional, List
```

**Step 5: 运行测试确认通过**

```bash
pytest tools/ai-agents/backend/tests/schemas/test_user_intent.py -v
```
Expected: PASS

**Step 6: 提交**

```bash
git add tools/ai-agents/backend/agents/lisa/schemas.py
git add tools/ai-agents/backend/tests/schemas/test_user_intent.py
git commit -m "feat(lisa): add UserIntentInClarify schema for semantic intent parsing"
```

---

### Task 2.2: 创建意图解析函数

**Files:**
- Create: `tools/ai-agents/backend/agents/lisa/intent_parser.py`
- Test: `tools/ai-agents/backend/tests/test_intent_parser.py`

**Step 1: 创建测试文件**

```python
# tools/ai-agents/backend/tests/test_intent_parser.py
"""测试意图解析器"""
import pytest
from unittest.mock import Mock, patch

from backend.agents.lisa.intent_parser import parse_user_intent, ClarifyContext
from backend.agents.lisa.schemas import UserIntentInClarify


class TestParseUserIntent:
    """意图解析器测试"""

    def test_parse_returns_user_intent_schema(self):
        """解析结果应返回 UserIntentInClarify 类型"""
        mock_llm = Mock()
        mock_llm.model.with_structured_output.return_value.invoke.return_value = {
            "intent": "confirm_proceed",
            "confidence": 0.9,
            "answered_question_ids": [],
            "extracted_info": None
        }
        
        context = ClarifyContext(
            blocking_questions=["Q1: 登录重试机制?"],
            optional_questions=["Q3: 国际化?"]
        )
        
        result = parse_user_intent("好的，继续吧", context, mock_llm)
        
        assert isinstance(result, UserIntentInClarify)
        assert result.intent == "confirm_proceed"

    def test_parse_with_answered_questions(self):
        """测试识别用户回答了哪些问题"""
        mock_llm = Mock()
        mock_llm.model.with_structured_output.return_value.invoke.return_value = {
            "intent": "answer_question",
            "confidence": 0.85,
            "answered_question_ids": ["Q1"],
            "extracted_info": "登录失败后重试3次"
        }
        
        context = ClarifyContext(
            blocking_questions=["Q1: 登录重试机制?"],
            optional_questions=[]
        )
        
        result = parse_user_intent("重试3次后锁定账户", context, mock_llm)
        
        assert result.intent == "answer_question"
        assert "Q1" in result.answered_question_ids
        assert result.extracted_info is not None


class TestClarifyContext:
    """ClarifyContext 数据类测试"""

    def test_context_creation(self):
        """测试上下文创建"""
        context = ClarifyContext(
            blocking_questions=["Q1", "Q2"],
            optional_questions=["Q3"]
        )
        assert len(context.blocking_questions) == 2
        assert len(context.optional_questions) == 1
```

**Step 2: 运行测试确认失败**

```bash
pytest tools/ai-agents/backend/tests/test_intent_parser.py -v
```
Expected: FAIL (模块不存在)

**Step 3: 实现意图解析器**

```python
# tools/ai-agents/backend/agents/lisa/intent_parser.py
"""
用户意图语义解析器

使用 LLM 进行语义理解，而非关键字匹配。
"""

import logging
from dataclasses import dataclass
from typing import List, Any

from langchain_core.messages import SystemMessage, HumanMessage

from .schemas import UserIntentInClarify

logger = logging.getLogger(__name__)


@dataclass
class ClarifyContext:
    """clarify 阶段上下文"""
    blocking_questions: List[str]
    optional_questions: List[str]


INTENT_PARSING_PROMPT = """
你是一个意图分析专家。请分析用户在需求澄清阶段的回复意图。

## 当前上下文
- 阶段: 需求澄清 (clarify)
- 待解决的阻塞性问题: {blocking_questions}
- 待解决的建议澄清问题: {optional_questions}

## 用户回复
"{user_message}"

## 任务
1. 判断用户意图类型 (7 种之一)
2. 如果用户在回答问题，识别回答了哪些问题 (返回问题 ID 如 Q1, Q2)
3. 提取用户回复中的关键信息摘要

## 意图类型说明
- provide_material: 用户正在提供需求文档、材料或补充信息
- answer_question: 用户正在回答之前提出的具体问题
- confirm_proceed: 用户确认可以继续到下一阶段 (如: "好的", "继续", "没问题")
- need_more_clarify: 用户表示需要更多澄清或有新问题
- accept_risk: 用户明确表示接受风险，忽略未解决问题继续 (如: "先这样吧", "忽略那些问题")
- change_scope: 用户要求调整测试范围
- off_topic: 用户说的内容与需求澄清无关

## 注意
- 使用语义理解，不要依赖关键字匹配
- 考虑上下文，同样的词在不同语境下可能有不同含义
- "好的"可能是确认继续，也可能是回应某个问题 - 需结合上下文判断
"""


def parse_user_intent(
    user_message: str,
    context: ClarifyContext,
    llm: Any
) -> UserIntentInClarify:
    """
    语义解析用户意图
    
    Args:
        user_message: 用户最新消息
        context: 当前上下文（包含待解决问题列表）
        llm: LLM 实例 (需支持 with_structured_output)
    
    Returns:
        UserIntentInClarify: 解析后的用户意图
    """
    prompt = INTENT_PARSING_PROMPT.format(
        blocking_questions=context.blocking_questions,
        optional_questions=context.optional_questions,
        user_message=user_message
    )
    
    structured_llm = llm.model.with_structured_output(
        UserIntentInClarify,
        method="function_calling"
    )
    
    try:
        result = structured_llm.invoke([
            SystemMessage(content=prompt)
        ])
        
        # 如果返回的是 dict，转换为 Pydantic 对象
        if isinstance(result, dict):
            result = UserIntentInClarify(**result)
        
        logger.info(f"意图解析结果: intent={result.intent}, confidence={result.confidence}")
        return result
        
    except Exception as e:
        logger.error(f"意图解析失败: {e}", exc_info=True)
        # 降级：返回默认意图
        return UserIntentInClarify(
            intent="need_more_clarify",
            confidence=0.5,
            answered_question_ids=[],
            extracted_info=None
        )
```

**Step 4: 运行测试确认通过**

```bash
pytest tools/ai-agents/backend/tests/test_intent_parser.py -v
```
Expected: PASS

**Step 5: 提交**

```bash
git add tools/ai-agents/backend/agents/lisa/intent_parser.py
git add tools/ai-agents/backend/tests/test_intent_parser.py
git commit -m "feat(lisa): implement semantic intent parser for clarify stage"
```

---

### Task 2.3: 创建 tests/schemas 目录结构

**Files:**
- Create: `tools/ai-agents/backend/tests/schemas/__init__.py`

**Step 1: 创建目录**

```bash
mkdir -p tools/ai-agents/backend/tests/schemas
touch tools/ai-agents/backend/tests/schemas/__init__.py
```

**Step 2: 提交**

```bash
git add tools/ai-agents/backend/tests/schemas/__init__.py
git commit -m "chore: add schemas test directory"
```

---

### Task 2.4: 集成意图解析到 reasoning_node (可选 - 标记为后续实现)

> **注意**: 此任务涉及修改核心业务逻辑，建议在前面任务都通过测试后再实施。
> 当前 reasoning_node 已经较复杂，集成需要谨慎评估。

**Files:**
- Modify: `tools/ai-agents/backend/agents/lisa/nodes/reasoning_node.py`

**设计思路**:

```python
# 在 reasoning_node 开头添加意图解析
def reasoning_node(state: LisaState, llm: Any) -> Command:
    # ... 现有初始化代码 ...
    
    # 新增: 如果在 clarify 阶段，先解析用户意图
    current_stage = state.get("current_stage_id", "clarify")
    if current_stage == "clarify":
        user_intent = parse_user_intent_from_state(state, llm)
        
        # 根据意图调整 Prompt 或直接返回 Command
        if user_intent.intent == "confirm_proceed":
            # 检查 DoR
            if not check_dor(state):
                return Command(
                    update={"messages": [AIMessage(content="DoR 未满足，请先解决阻塞性问题")]},
                    goto="__end__"
                )
    
    # ... 继续现有逻辑 ...
```

**此任务暂标记为后续实现**，原因：
1. 需要更全面的集成测试
2. 需要确保不破坏现有功能
3. 可能需要与前端协调 (进度显示等)

---

## 验收检查清单

运行以下命令确保所有测试通过：

```bash
cd /Users/anhui/Documents/myProgram/AI4SE

# 1. 运行所有新增测试
pytest tools/ai-agents/backend/tests/prompts/ -v
pytest tools/ai-agents/backend/tests/schemas/ -v
pytest tools/ai-agents/backend/tests/test_intent_parser.py -v

# 2. 运行完整测试套件确保无回归
pytest tools/ai-agents/backend/tests/ -v

# 3. Lint 检查
flake8 tools/ai-agents/backend/agents/lisa/intent_parser.py
flake8 tools/ai-agents/backend/agents/lisa/schemas.py

# 4. 类型检查 (如果有 mypy)
# mypy tools/ai-agents/backend/agents/lisa/
```

---

## 提交历史预期

```
refactor(lisa): rewrite STAGE_CLARIFY_PROMPT with clear goals and DoR
chore: add prompts test directory
feat(lisa): add UserIntentInClarify schema for semantic intent parsing
feat(lisa): implement semantic intent parser for clarify stage
chore: add schemas test directory
```

---

## 风险与注意事项

1. **向后兼容**: Prompt 修改可能影响现有对话行为，需要 E2E 测试验证
2. **LLM 依赖**: 意图解析依赖 LLM 响应质量，需考虑降级策略 (已在代码中实现)
3. **性能影响**: 意图解析增加了一次 LLM 调用，但 clarify 阶段交互频率低，可接受
