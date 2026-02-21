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
    assert_stream_integrity,
    read_structured_artifact,
)
from .judge import judge_output, judge_artifact_slice


def _print_round(round_num: str, user_msg: str, events) -> None:
    """每轮对话完成后实时打印摘要，方便当场观察。"""
    trajectory = extract_tool_trajectory(events)
    text = extract_full_text(events)

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"[{round_num}] 用户: {user_msg[:80]}..." if len(user_msg) > 80  # noqa: E501
          else f"[{round_num}] 用户: {user_msg}")
    print(f"[{round_num}] 工具调用: "
          f"{[(t.tool_name, t.artifact_key) for t in trajectory]}")
    print(f"[{round_num}] 智能体回复前 300 字: {text[:300]}")
    print(sep)


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
    "针对你提的问题，统一回复：手机号格式仅限中国大陆11位纯数字；密码不必须包含特殊字符；"
    "锁定机制是连续 5 次累计失败则锁定，成功登录清零；仅需返回 user_id 和 token；同一账号的锁定不限设备和IP。"
    "其他没有提到的情况都属于约定俗成的基本逻辑，所有你提出的异常情况和问题都无需验证和考虑了，"
    "也没有其他的需求或关联系统了，我们就按最简版测试，不再补充任何细节。所有阻塞问题确认完毕。"
)

# R3-R5: 阶段推进指令
GENERATE_STRATEGY = "需求已全部明确，没有任何阻塞问题了。请你流转到策略阶段，根据现在的进展分析输出测试策略蓝图。"
GENERATE_CASES = "策略没问题，请根据该策略开始编写并输出测试用例。"
GENERATE_DELIVERY = "用例没问题，请根据之前的分析整合输出最终交付文档。"


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
        _print_round("R1", REQUIREMENT_INPUT, events_r1)
        assert_stream_integrity(events_r1)

        # 核心断言: 工具调用被正确触发
        trajectory_r1 = extract_tool_trajectory(events_r1)
        assert len(trajectory_r1) >= 1, (
            "R1 未触发工具调用，"
            "智能体可能没有分析需求。\n"
            f"事件类型: "
            f"{[e.event_type for e in events_r1]}"
        )
        assert trajectory_r1[0].artifact_key == (
            "test_design_requirements"
        ), (
            f"R1 工具调用的 key 错误: "
            f"{trajectory_r1[0].artifact_key}"
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
        _print_round("R2", CONFIRM_REQUIREMENTS, events_r2)
        text_r2 = extract_full_text(events_r2)
        assert len(text_r2) > 10, (
            f"R2 回复过短: {repr(text_r2[:100])}"
        )
        # 核心断言: 对话回复相关性
        r2_verdict = judge_output(
            user_input=CONFIRM_REQUIREMENTS,
            expected_behavior=(
                "智能体应当确认所有用户提供的P0需求问题细节，"
                "并提出可以流转到下一个阶段（策略制定）。"
                "不再有未解决的问题，不应该继续追问任何需求细节。"
            ),
            actual_output=text_r2[:500]
        )
        assert r2_verdict.passed, (
            f"R2 确认回复不合理: {r2_verdict.reason}"
        )

        # ═══ R2 产出物语义验证: Assumptions 状态同步 ═══
        r2_artifact = read_structured_artifact(
            lisa_graph, lisa_session, "test_design_requirements"
        )
        assumptions = r2_artifact.get("assumptions", [])
        import json
        assumptions_json = json.dumps(
            assumptions, ensure_ascii=False, indent=2
        )

        r2_artifact_verdict = judge_artifact_slice(
            conversation_context=(
                "用户在 R2 中回答了所有待确认问题：\n"
                f"{CONFIRM_REQUIREMENTS}"
            ),
            expected_behavior=(
                "所有 assumptions 条目的 status 都应该从 'pending' "
                "变为 'confirmed' 或 'assumed'。\n"
                "每个 assumption 的 note 字段应包含"
                "用户确认的结论摘要。\n"
                "不应有任何条目的 status 仍为 'pending'。"
            ),
            artifact_slice=assumptions_json,
        )
        assert r2_artifact_verdict.passed, (
            f"R2 产出物 assumptions 状态未同步: "
            f"{r2_artifact_verdict.reason}\n"
            f"实际 assumptions: {assumptions_json[:500]}"
        )

        # ════════════════════════════════
        # R3: 进入策略阶段并生成策略
        # ════════════════════════════════
        events_r3 = send_and_collect(
            client, lisa_session, GENERATE_STRATEGY
        )
        _print_round("R3", GENERATE_STRATEGY, events_r3)
        assert_stream_integrity(events_r3)

        # 严格断言: 策略阶段工具调用被触发
        trajectory_r3 = extract_tool_trajectory(events_r3)
        assert len(trajectory_r3) >= 1, "R3 缺少工具调用"
        assert trajectory_r3[0].artifact_key == (
            "test_design_strategy"
        ), f"R3 artifact_key 错误: {trajectory_r3[0].artifact_key}"

        # 核心断言: 对话回复
        text_r3 = extract_full_text(events_r3)
        r3_reply_verdict = judge_output(
            user_input=GENERATE_STRATEGY,
            expected_behavior=(
                "智能体应根据要求生成测试策略蓝图，"
                "并表达该策略包含的主要方向或维度，询问用户是否可进入用例编写阶段。"
                "不得重新提出新的澄清问题。"
            ),
            actual_output=text_r3[:500]
        )
        assert r3_reply_verdict.passed, (
            f"R3 对话回复不合理: "
            f"{r3_reply_verdict.reason}"
        )

        # ════════════════════════════════
        # R4: 进入用例阶段并生成用例
        # ════════════════════════════════
        events_r4 = send_and_collect(
            client, lisa_session, GENERATE_CASES
        )
        _print_round("R4", GENERATE_CASES, events_r4)
        assert_stream_integrity(events_r4)

        # 严格断言: 用例阶段工具调用被触发
        trajectory_r4 = extract_tool_trajectory(events_r4)
        assert len(trajectory_r4) >= 1, "R4 缺少工具调用"
        assert trajectory_r4[0].artifact_key == (
            "test_design_cases"
        ), f"R4 artifact_key 错误: {trajectory_r4[0].artifact_key}"

        # 核心断言: 对话回复
        text_r4 = extract_full_text(events_r4)
        r4_reply_verdict = judge_output(
            user_input=GENERATE_CASES,
            expected_behavior=(
                "智能体应确认收到开始编写用例的指令，"
                "并基于测试策略产出具体的测试用例。"
                "同时询问用户是否可以输出最终的交付文档。"
            ),
            actual_output=text_r4[:500]
        )
        assert r4_reply_verdict.passed, (
            f"R4 对话回复不合理: "
            f"{r4_reply_verdict.reason}"
        )

        # ═══ R4 产出物语义验证: 测试用例内容 ═══
        r4_artifact = read_structured_artifact(
            lisa_graph, lisa_session, "test_design_cases"
        )
        cases = r4_artifact.get("cases", [])
        # 只取前 3 个用例做语义验证，控制 Token 开销
        cases_slice = cases[:3] if len(cases) > 3 else cases
        import json
        cases_json = json.dumps(
            cases_slice, ensure_ascii=False, indent=2
        )

        r4_artifact_verdict = judge_artifact_slice(
            conversation_context=(
                "此测试针对 POST /api/login 接口，"
                "参数为手机号(11位)和密码(6-20位含字母数字)。\n"
                "业务规则：密码连续错误5次锁定30分钟，锁定期间返回锁定提示。\n"
                "用户已确认：密码不需要特殊字符，手机号仅限中国大陆格式。"
            ),
            expected_behavior=(
                "测试用例应覆盖登录功能的核心场景，包括但不限于：\n"
                "1. 正常登录成功\n"
                "2. 密码格式校验（如纯数字、纯字母等非法密码）\n"
                "3. 手机号格式校验\n"
                "4. 密码连续错误锁定机制\n"
                "每个用例应有明确的步骤(steps)和预期结果(expect)。\n"
                "用例内容必须与登录功能相关，不能出现注册、找回密码等范围外的用例。"
            ),
            artifact_slice=cases_json,
        )
        assert r4_artifact_verdict.passed, (
            f"R4 产出物 cases 内容不合理: "
            f"{r4_artifact_verdict.reason}\n"
            f"实际用例切片: {cases_json[:500]}"
        )

        # ════════════════════════════════
        # R5: 交付阶段
        # ════════════════════════════════
        events_r5 = send_and_collect(
            client, lisa_session, GENERATE_DELIVERY
        )
        _print_round("R5", GENERATE_DELIVERY, events_r5)

        # 严格断言: 交付阶段工具调用被触发
        trajectory_r5 = extract_tool_trajectory(events_r5)
        assert len(trajectory_r5) >= 1, "R5 缺少工具调用"
        assert trajectory_r5[-1].artifact_key == (
            "test_design_final"
        ), f"R5 artifact_key 错误: {trajectory_r5[-1].artifact_key}"

        # 核心断言: 对话回复
        text_r5 = extract_full_text(events_r5)
        assert len(text_r5) > 10, (
            f"R5 回复过短: {repr(text_r5[:100])}"
        )
        r5_reply_verdict = judge_output(
            user_input=GENERATE_DELIVERY,
            expected_behavior=(
                "智能体应当确认最终交付任务，"
                "并表明已完成文档整合交付，测试设计流程顺利结束。"
            ),
            actual_output=text_r5[:500]
        )
        assert r5_reply_verdict.passed, (
            f"R5 交付回复不合理: "
            f"{r5_reply_verdict.reason}"
        )
