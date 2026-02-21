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
    extract_tool_input_args,
    assert_stream_integrity,
)
from .judge import judge_output


# ═══════════════════════════════════════
# 对话脚本常量
# ═══════════════════════════════════════

# R1: 详细登录需求（按 DoR 标准覆盖三项要求）
# DoR: ①被测对象明确 ②主流程可达 ③无阻塞疑问
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

# R2: 兜底确认（处理 LLM 可能的追问不确定性）
CONFIRM_REQUIREMENTS = (
    "以上分析都没问题。"
    "所有未解答的问题都按系统默认行为处理即可，"
    "我没有更多补充。请进入下一阶段。"
)

# R3-R5: 阶段推进指令
CONFIRM_STRATEGY = "策略没问题，请开始编写测试用例。"
CONFIRM_CASES = "用例没问题，请输出最终交付文档。"
CONFIRM_DELIVERY = "文档确认，交付完成。"


@pytest.mark.slow
class TestLisaTestDesignHappyPath:
    """
    测试设计工作流 Happy Path

    一个 session，5 轮对话，走完 4 个工作流阶段：
    clarify → strategy → cases → delivery

    跑完 = 人工验收了一遍完整工作流。
    """

    def test_full_workflow_journey(
        self, client, lisa_session
    ):
        """
        完整旅程: clarify → strategy → cases → delivery

        核心断言：每轮用 Judge 验证产出物文档和对话回复
        对用户来说是否正确、合理。
        """
        # ════════════════════════════════
        # R1: 提出详细的登录功能测试需求
        # ════════════════════════════════
        events_r1 = send_and_collect(
            client, lisa_session, REQUIREMENT_INPUT
        )
        assert_stream_integrity(events_r1)

        # 核心断言: 产出物内容相关性
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
                "产出物应是一份登录功能的需求分析文档，"
                "包含以下要素中的至少 3 项：\n"
                "- 被测对象（POST /api/login）\n"
                "- 参数校验规则"
                "（手机号格式、密码规则）\n"
                "- 正常流程描述\n"
                "- 异常规则（锁定机制）\n"
                "- 测试范围边界"
            ),
            actual_output=body_r1[:1000]
        )
        assert r1_artifact_verdict.passed, (
            f"R1 需求分析文档内容不合理: "
            f"{r1_artifact_verdict.reason}"
        )

        # 核心断言: 对话回复相关性
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
        # R2: 确认需求，通过 DoR 关卡
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
