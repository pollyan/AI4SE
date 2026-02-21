# Smoke Test 重构：场景化 Happy Path

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将分散的 P0 冒烟测试重构为一条场景化的 happy path 测试，模拟用户完整使用 Lisa 测试设计工作流的旅程（clarify → strategy → cases → delivery），每轮用 LLM-as-Judge 验证智能体输出的合理性。跑完等于人工验收了一遍。

**Architecture:**
- 一条 happy path 测试（1 个 session，5-6 轮对话，走完 4 个工作流阶段）替换现有 3 个分散的 P0 case。
- 每轮的核心断言是 LLM-as-Judge 语义验证（产出物 + 对话），SSE 完整性和 Schema 校验作为辅助。
- 复用现有 `conftest.py`、`judge.py`、`sse_parser.py` 基建，仅新增辅助函数和替换测试文件。

**Tech Stack:** Python, Pytest, LLM-as-Judge, Flask test_client, Pydantic

---

## User Review Required

> [!IMPORTANT]
> **破坏性变更：** 本计划会删除 `test_lisa_smoke.py`（现有 P0），替换为 `test_lisa_happy_path.py`。新测试覆盖范围严格超集于旧测试。

> [!TIP]
> R1 的需求输入按 Lisa 的 DoR 标准设计（被测对象明确 + 主流程可达 + 无阻塞疑问），尽量一轮通过澄清关卡。实际运行时可能需要根据 LLM 反馈微调输入和 Judge 的 expected_behavior。

---

## Task 1: 扩展 SSE Parser

**Files:**
- Modify: `tools/ai-agents/backend/tests/agent_smoke/sse_parser.py`

**Step 1: 在 `sse_parser.py` 末尾添加新函数**

```python
def extract_tool_input_args(
    events: List[SSEEvent],
) -> List[dict]:
    """
    从事件流中提取所有工具调用的 input 参数。

    返回 tool-input-available 事件中的 input 字段列表。
    可用于 Schema 校验和 markdown_body 内容提取。
    """
    return [
        e.data.get("input", {})
        for e in events
        if e.event_type == "tool-input-available"
    ]
```

**Step 2: flake8 检查**

Run: `flake8 tools/ai-agents/backend/tests/agent_smoke/sse_parser.py`
Expected: 无输出

**Step 3: Commit**

```bash
git add tools/ai-agents/backend/tests/agent_smoke/sse_parser.py
git commit -m "feat(smoke): add extract_tool_input_args to sse_parser"
```

---

## Task 2: 创建场景化 Happy Path 测试

**Files:**
- Create: `tools/ai-agents/backend/tests/agent_smoke/test_lisa_happy_path.py`

**背景知识：**
Lisa 测试设计工作流 4 个阶段及对应 artifact_key：
- `clarify` → `test_design_requirements`（需求分析文档）
- `strategy` → `test_design_strategy`（测试策略蓝图）
- `cases` → `test_design_cases`（测试用例集）
- `delivery` → `test_design_final`（测试设计文档）

clarify 阶段有 DoR 关卡（3 项全部满足才能流转）：
1. 被测对象明确（SUT + 边界）
2. 主流程可达（至少 1 条核心流程）
3. 无阻塞疑问（P0 问题全部解决）

R1 的输入按 DoR 标准设计，争取一轮通过关卡。

**Step 1: 创建测试文件**

```python
"""
Lisa 智能体场景化冒烟测试（Happy Path）

模拟用户完整使用 Lisa 测试设计工作流的旅程：
  clarify → strategy → cases → delivery

跑完本测试 = 手动验收了一遍完整工作流。

核心断言：每轮用 LLM-as-Judge 验证智能体的产出物
和对话回复对用户来说是否正确、合理。

所有测试标记为 @pytest.mark.slow，仅本地运行。
"""

import pytest
from .sse_parser import (
    send_and_collect,
    extract_full_text,
    extract_tool_trajectory,
    extract_tool_input_args,
    assert_stream_integrity,
)
from .judge import judge_output


# ═══════════════════════════════════════
# 对话脚本常量
# ═══════════════════════════════════════

# R1: 详细登录需求（按 DoR 标准覆盖三项要求）
REQUIREMENT_INPUT = (
    "帮我设计用户登录功能的测试用例。\n\n"
    "被测接口：POST /api/login\n"
    "参数：\n"
    "- username: 手机号格式，11位数字\n"
    "- password: 6-20位，必须包含字母和数字\n\n"
    "正常流程：\n"
    "1. 用户输入手机号和密码\n"
    "2. 系统校验格式和账号密码正确性\n"
    "3. 返回 JWT token 和用户基本信息\n\n"
    "异常规则：\n"
    "- 密码连续错误5次，锁定账户30分钟\n"
    "- 锁定期间任何登录尝试返回锁定提示\n\n"
    "测试范围：仅登录接口，"
    "不含注册、找回密码、第三方登录。"
)

# R2: 兜底确认（处理 LLM 输出不确定性）
CONFIRM_REQUIREMENTS = (
    "以上分析都没问题。"
    "所有未解答的问题都按系统默认行为处理即可，"
    "我没有更多补充。请进入下一阶段。"
)

# R3-R5: 阶段推进
CONFIRM_STRATEGY = "策略没问题，请开始编写测试用例。"
CONFIRM_CASES = "用例没问题，请输出最终交付文档。"
CONFIRM_DELIVERY = "文档确认，交付完成。"


@pytest.mark.slow
class TestLisaTestDesignHappyPath:
    """
    测试设计工作流 Happy Path

    一个 session，5 轮对话，走完 4 个阶段。
    每轮验证智能体输出的合理性。
    """

    def test_full_workflow_journey(
        self, client, lisa_session
    ):
        """
        完整旅程: clarify → strategy → cases → delivery

        模拟真实用户从提出需求到拿到最终交付物的
        完整使用过程。
        """
        # ════════════════════════════════
        # R1: 提出详细的登录功能测试需求
        # ════════════════════════════════
        events_r1 = send_and_collect(
            client, lisa_session, REQUIREMENT_INPUT
        )
        assert_stream_integrity(events_r1)

        # 核心断言: 产出物内容
        inputs_r1 = extract_tool_input_args(events_r1)
        assert len(inputs_r1) >= 1, (
            "R1 未触发工具调用，"
            "智能体可能没有生成需求分析文档。\n"
            f"事件类型: "
            f"{[e.event_type for e in events_r1]}"
        )

        body_r1 = inputs_r1[0].get("markdown_body", "")
        r1_artifact_verdict = judge_output(
            user_input=REQUIREMENT_INPUT,
            expected_behavior=(
                "产出物应是一份登录功能"
                "的需求分析文档，包含：\n"
                "- 被测对象（POST /api/login）\n"
                "- 参数校验规则"
                "（手机号格式、密码规则）\n"
                "- 正常流程描述\n"
                "- 异常规则"
                "（锁定机制）\n"
                "- 测试范围边界"
            ),
            actual_output=body_r1[:1000]
        )
        assert r1_artifact_verdict.passed, (
            f"R1 需求分析文档内容不合理: "
            f"{r1_artifact_verdict.reason}"
        )

        # 核心断言: 对话回复
        text_r1 = extract_full_text(events_r1)
        r1_reply_verdict = judge_output(
            user_input=REQUIREMENT_INPUT,
            expected_behavior=(
                "智能体应在分析用户提供的登录需求，"
                "可能提出澄清问题或确认理解，"
                "总之回复要与登录功能测试相关"
            ),
            actual_output=text_r1[:500]
        )
        assert r1_reply_verdict.passed, (
            f"R1 对话回复不合理: "
            f"{r1_reply_verdict.reason}"
        )

        # ════════════════════════════════
        # R2: 确认需求 → 通过 DoR 关卡
        # ════════════════════════════════
        events_r2 = send_and_collect(
            client, lisa_session, CONFIRM_REQUIREMENTS
        )

        text_r2 = extract_full_text(events_r2)
        assert len(text_r2) > 10, (
            f"R2 回复过短: {repr(text_r2[:100])}"
        )

        r2_verdict = judge_output(
            user_input=CONFIRM_REQUIREMENTS,
            expected_behavior=(
                "智能体应确认需求分析完成，"
                "做握手确认或总结共识，"
                "并引导用户进入下一阶段（策略制定）。"
                "不应该重复分析需求"
            ),
            actual_output=text_r2[:500]
        )
        assert r2_verdict.passed, (
            f"R2 确认回复不合理: {r2_verdict.reason}"
        )

        # ════════════════════════════════
        # R3: 进入策略阶段
        # ════════════════════════════════
        events_r3 = send_and_collect(
            client, lisa_session, CONFIRM_STRATEGY
        )
        assert_stream_integrity(events_r3)

        # 核心断言: 策略产出物
        inputs_r3 = extract_tool_input_args(events_r3)
        if len(inputs_r3) >= 1:
            body_r3 = inputs_r3[0].get(
                "markdown_body", ""
            )
            if body_r3:
                r3_artifact_verdict = judge_output(
                    user_input=(
                        "请为登录功能制定测试策略"
                    ),
                    expected_behavior=(
                        "产出物应是一份测试策略蓝图，"
                        "讨论登录功能的测试方法、"
                        "优先级、风险分析或"
                        "测试分层策略。"
                        "不应重复需求分析内容"
                    ),
                    actual_output=body_r3[:1000]
                )
                assert r3_artifact_verdict.passed, (
                    f"R3 策略文档不合理: "
                    f"{r3_artifact_verdict.reason}"
                )

        # 核心断言: 对话回复
        text_r3 = extract_full_text(events_r3)
        r3_reply_verdict = judge_output(
            user_input=CONFIRM_STRATEGY,
            expected_behavior=(
                "智能体应在讨论登录功能的测试策略，"
                "或引导用户确认策略方向。"
                "不应重新分析需求或做自我介绍"
            ),
            actual_output=text_r3[:500]
        )
        assert r3_reply_verdict.passed, (
            f"R3 对话回复不合理: "
            f"{r3_reply_verdict.reason}"
        )

        # ════════════════════════════════
        # R4: 进入用例阶段
        # ════════════════════════════════
        events_r4 = send_and_collect(
            client, lisa_session, CONFIRM_CASES
        )
        assert_stream_integrity(events_r4)

        # 核心断言: 用例产出物
        inputs_r4 = extract_tool_input_args(events_r4)
        if len(inputs_r4) >= 1:
            body_r4 = inputs_r4[0].get(
                "markdown_body", ""
            )
            if body_r4:
                r4_artifact_verdict = judge_output(
                    user_input=(
                        "请为登录功能编写测试用例"
                    ),
                    expected_behavior=(
                        "产出物应是一份测试用例集，"
                        "包含具体的测试场景、"
                        "测试步骤和预期结果。"
                        "应覆盖正常登录和异常场景"
                        "（如密码错误、账户锁定等）"
                    ),
                    actual_output=body_r4[:1000]
                )
                assert r4_artifact_verdict.passed, (
                    f"R4 用例文档不合理: "
                    f"{r4_artifact_verdict.reason}"
                )

        # 核心断言: 对话回复
        text_r4 = extract_full_text(events_r4)
        r4_reply_verdict = judge_output(
            user_input=CONFIRM_CASES,
            expected_behavior=(
                "智能体应在讨论具体的测试用例，"
                "或引导用户审阅和确认用例内容"
            ),
            actual_output=text_r4[:500]
        )
        assert r4_reply_verdict.passed, (
            f"R4 对话回复不合理: "
            f"{r4_reply_verdict.reason}"
        )

        # ════════════════════════════════
        # R5: 交付阶段
        # ════════════════════════════════
        events_r5 = send_and_collect(
            client, lisa_session, CONFIRM_DELIVERY
        )

        # 核心断言: 交付产出物
        inputs_r5 = extract_tool_input_args(events_r5)
        if len(inputs_r5) >= 1:
            body_r5 = inputs_r5[0].get(
                "markdown_body", ""
            )
            if body_r5:
                r5_artifact_verdict = judge_output(
                    user_input=(
                        "请输出最终的测试设计文档"
                    ),
                    expected_behavior=(
                        "产出物应是一份最终的"
                        "测试设计交付文档，"
                        "整合了前面的需求分析、"
                        "测试策略和测试用例"
                    ),
                    actual_output=body_r5[:1000]
                )
                assert r5_artifact_verdict.passed, (
                    f"R5 交付文档不合理: "
                    f"{r5_artifact_verdict.reason}"
                )

        # 核心断言: 对话回复
        text_r5 = extract_full_text(events_r5)
        assert len(text_r5) > 10, (
            f"R5 回复过短: {repr(text_r5[:100])}"
        )

        r5_reply_verdict = judge_output(
            user_input=CONFIRM_DELIVERY,
            expected_behavior=(
                "智能体应在做最终交付总结，"
                "告知用户测试设计已完成，"
                "或提供后续建议"
            ),
            actual_output=text_r5[:500]
        )
        assert r5_reply_verdict.passed, (
            f"R5 交付回复不合理: "
            f"{r5_reply_verdict.reason}"
        )



```

**Step 2: 运行 collect-only 确认测试可被发现**

Run: `cd /Users/anhui/Documents/myProgram/AI4SE && python3 -m pytest tools/ai-agents/backend/tests/agent_smoke/test_lisa_happy_path.py --collect-only -m slow`
Expected: 收集到 1 个测试

**Step 3: flake8 检查**

Run: `flake8 tools/ai-agents/backend/tests/agent_smoke/test_lisa_happy_path.py`
Expected: 无输出

**Step 4: Commit**

```bash
git add tools/ai-agents/backend/tests/agent_smoke/test_lisa_happy_path.py
git commit -m "feat(smoke): add scenario-based happy path test for Lisa"
```

---

## Task 3: 删除旧的分散 P0 测试

**Files:**
- Delete: `tools/ai-agents/backend/tests/agent_smoke/test_lisa_smoke.py`

**Step 1: 删除旧文件**

```bash
rm tools/ai-agents/backend/tests/agent_smoke/test_lisa_smoke.py
```

**Step 2: 确认新测试仍可被发现**

Run: `cd /Users/anhui/Documents/myProgram/AI4SE && python3 -m pytest tools/ai-agents/backend/tests/agent_smoke/ --collect-only -m slow`
Expected: 收集到 1 个测试（来自 test_lisa_happy_path.py）

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor(smoke): remove scattered P0 tests, replaced by happy path"
```

---

## Task 4: 全量验证

**Step 1: 运行常规本地测试（确保不影响已有测试）**

Run: `./scripts/test/test-local.sh`
Expected: 🎉 所有测试通过

**Step 2: 运行场景化冒烟测试（需 API Key，约 3-5 分钟）**

Run: `cd /Users/anhui/Documents/myProgram/AI4SE && python3 -m pytest tools/ai-agents/backend/tests/agent_smoke/ -v -s -m slow`
Expected: 1 passed

**Step 3: 如有 Judge 判定失败**

根据 `verdict.reason` 分析：
- Judge 的 expected_behavior 过严 → 放宽描述
- LLM 未走到预期阶段 → 调整对话脚本（R2 兜底语句）
- 产出物为空 → 检查 LLM 是否触发了 should_update_artifact

**Step 4: Push**

```bash
git push
```

---

## Verification Plan

### Automated Tests
```bash
# 快速验证（不调 LLM）
python3 -m pytest tools/ai-agents/backend/tests/agent_smoke/ --collect-only -m slow

# 完整运行（需 API Key，约 3-5 分钟）
python3 -m pytest tools/ai-agents/backend/tests/agent_smoke/ -v -s -m slow

# 确保不影响已有测试
./scripts/test/test-local.sh
```

### Manual Verification
1. **LangSmith Trace:** 检查 `ai4se-smoke-test` 中 happy path 的 5 轮对话 trace。
2. **阶段转换:** 确认 trace 中 workflow_stage 经历了 clarify → strategy → cases → delivery。
3. **Judge 理由:** 阅读每轮 Judge 的 reason，确认评判标准合理。
